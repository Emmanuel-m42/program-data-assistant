"""Eval runner. Run: uv run evals --label baseline

Scores every case in evals/cases.yaml on five metrics:
  tool_choice   the assistant called every expected tool
  retrieval     recall@4 of the expected passages when the retriever is given the question directly
  facts         share of expected facts found in the answer; numeric facts are checked against values
                computed straight from the raw tables, never from the model
  citation      the answer cites at least one source and every cited table or passage was returned by a tool
  refusal       refused exactly when the case says it should
A case passes when every metric that applies to it (retrieval aside) is a full score.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

import yaml

from . import db, retrieval
from .agent import Assistant
from .llm import get_provider

CASES = db.REPO / "evals" / "cases.yaml"
REPORTS = db.REPO / "evals" / "reports"
METRICS = ["tool_choice", "retrieval", "facts", "citation", "refusal"]
NUMBER = re.compile(r"(?<![\w.])-?\$?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)")
CITE_MARK = re.compile(r"\[[^\]]*\]")
# Counts written as words ("Four open flags"). Hyphenated forms like "one-day hire" are words, not counts.
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
WORD_VALUE = {w: float(i) for i, w in enumerate(WORDS)} | {"a dozen": 12.0}
WORD_NUMBER = re.compile(r"(?<![\w-])(a dozen|" + "|".join(WORDS) + r")(?![\w-])", re.IGNORECASE)


def load_cases(path: Path = CASES) -> tuple[list[dict], dict]:
    data = yaml.safe_load(path.read_text())
    return data["cases"], data.get("defaults", {})


def compute_truth(conn, cases: list[dict]) -> dict[tuple[str, str], float]:
    """Ground truth for every numeric fact, straight from the raw tables."""
    conn.execute("SET search_path = program, public")
    truth = {}
    for c in cases:
        for f in c.get("facts", []):
            if "sql" in f:
                v = conn.execute(f["sql"]).fetchone()[0]
                truth[(c["id"], f["name"])] = float(v)
    return truth


# Scorer fix (measurement only; the agent's own refusal handling is unchanged): besides the agent's
# "I can't confirm that" sentence, count a clear decline in the answer's first sentence, such as
# "I can't provide her phone number" or "That isn't something I can share". A first sentence that
# carries data (a number of two or more digits) is an answer, even if it mentions a refusal word.
DECLINE = re.compile(
    r"\b(?:can(?:'|’)?t|cannot|can not|won(?:'|’)?t|will not|(?:am )?unable to)\s+"
    r"(?:provide|share|give|tell you|look up|access|confirm)\b"
    r"|\b(?:is|are)\s*(?:n(?:'|’)?t|not)\s+available\b|\bnot available\b"
    r"|\bisn(?:'|’)?t something I can\b|\bis not something I can\b",
    re.IGNORECASE,
)
FIRST_SENTENCE = re.compile(r"^\s*(.+?)(?:(?<=[.!?])\s|\n|$)", re.DOTALL)
DATA_NUMBER = re.compile(r"\d[\d,]*\d|\d\.\d")


def declined(text: str) -> bool:
    from .agent import REFUSAL

    if REFUSAL.search(text or ""):
        return True
    m = FIRST_SENTENCE.match(text or "")
    if not m:
        return False
    first = CITE_MARK.sub(" ", m.group(1))
    return bool(DECLINE.search(first)) and not DATA_NUMBER.search(first)


def numbers_in(text: str) -> list[float]:
    plain = CITE_MARK.sub(" ", text)
    digits = [float(m.group(1).replace(",", "")) for m in NUMBER.finditer(plain)]
    return digits + [WORD_VALUE[m.group(1).lower()] for m in WORD_NUMBER.finditer(plain)]


# A plural label before a list of numbers names each one: "Precincts 39, 37 and 40" -> "Precinct 39 Precinct 37 ...".
NAME_LIST = re.compile(r"\b([A-Za-z]+)s\s+(\d+(?:\s*(?:,|and|&|or)\s*(?:and\s+)?\d+)+)")


def expand_name_lists(text: str) -> str:
    def expand(m: re.Match) -> str:
        return " ".join(f"{m.group(1)} {n}" for n in re.findall(r"\d+", m.group(2)))

    return NAME_LIST.sub(expand, text)


def fact_matches(fact: dict, truth: float | None, answer: str, defaults: dict) -> bool:
    if "any_of" in fact:
        low = answer.lower()
        listed = expand_name_lists(answer).lower()
        return any(s.lower() in low or s.lower() in listed for s in fact["any_of"])
    if truth is None:
        return False
    target = abs(truth)
    for n in numbers_in(answer):
        cands = [abs(n)]
        if fact.get("kind") == "percent" and abs(n) <= 1:
            cands.append(abs(n) * 100)
        for x in cands:
            if "abs" in fact:
                if abs(x - target) <= fact["abs"] + 1e-9:
                    return True
            elif abs(x - target) <= fact.get("tol", defaults.get("tol", 0.02)) * max(target, 1e-9):
                return True
    return False


def tools_called(answer: dict) -> set[str]:
    """Tool names called, plus "get_view:<view>" for each view read (by get_view or named in SQL). Reading a view's
    *_total also counts as reading the view: both carry the same definitions."""
    called = set()
    for t in answer["tool_calls"]:
        called.add(t["name"])
        args = t.get("args") or {}
        views = re.findall(r"\bv_\w+", str(args.get("sql", "")))
        if t["name"] == "get_view" and args.get("view"):
            views.append(args["view"])
        for v in views:
            called.update({f"get_view:{v}", f"get_view:{v.removesuffix('_total')}"})
    if "get_view" in called:  # get_view is a narrower way to query program data
        called.add("query_program_data")
    return called


def tool_expected(entry, called: set[str]) -> bool:
    """An expected_tools entry is a tool name, or a list of alternatives (any one is enough)."""
    return any(e in called for e in entry) if isinstance(entry, list) else entry in called


def score_case(case: dict, answer: dict, truth: dict, retrieved: list[str], defaults: dict) -> dict:
    should_refuse = bool(case.get("should_refuse"))
    called = tools_called(answer)
    scores: dict[str, float | None] = dict.fromkeys(METRICS)
    details = []
    refused = answer["refused"] or declined(answer["answer"])
    scores["refusal"] = 1.0 if refused == should_refuse else 0.0
    if case.get("expected_docs"):
        exp = case["expected_docs"]
        scores["retrieval"] = round(sum(1 for d in exp if d in retrieved) / len(exp), 3)
    if not should_refuse:
        exp_tools = case.get("expected_tools", [])
        scores["tool_choice"] = 1.0 if all(tool_expected(t, called) for t in exp_tools) else 0.0
        facts = case.get("facts", [])
        hits = scored = 0
        for f in facts:
            t = truth.get((case["id"], f["name"]))
            ok = (not refused) and fact_matches(f, t, answer["answer"], defaults)
            # An optional fact is context the question doesn't ask for: reported, not scored.
            if not f.get("optional"):
                hits += ok
                scored += 1
            details.append({"name": f["name"], "expected": t if "sql" in f else f["any_of"], "matched": ok,
                            **({"optional": True} if f.get("optional") else {})})
        scores["facts"] = round(hits / scored, 3) if scored else None
        scores["citation"] = 1.0 if answer["citations_valid"] else 0.0
    applicable = [scores[m] for m in METRICS if m != "retrieval" and scores[m] is not None]
    scores["pass"] = 1.0 if all(s == 1.0 for s in applicable) else 0.0
    return {"scores": scores, "facts": details}


def summarize(rows: list[dict]) -> dict:
    out = {"cases": len(rows)}
    for m in METRICS + ["pass", "pass_all"]:
        vals = [r["scores"].get(m) for r in rows if r["scores"].get(m) is not None]
        out[m] = round(sum(vals) / len(vals), 3) if vals else None
        out[f"{m}_n"] = len(vals)
    lat = [a["latency_ms"] for r in rows for a in [r["answer"]] + [x["answer"] for x in r.get("repeats", [])]]
    out["avg_latency_ms"] = int(sum(lat) / len(lat)) if lat else 0
    return out


# Reporting groups, in order. The first held-out half (test) and heldout_v2 are contaminated: their failures were read
# while choosing fixes. heldout_v3 is the clean held-out set.
GROUPS = {"dev": "dev (tuned)", "test": "old held-out (contaminated)", "heldout_v2": "held-out v2 (contaminated)",
          "heldout_v3": "held-out v3"}


def groups(rows: list[dict], splits: dict[str, str]) -> list[dict]:
    """Per-group scores: pass and pass_all (pass^k) as case counts, the other metrics as means."""
    out = []
    for split, label in GROUPS.items():
        g = [r for r in rows if splits.get(r["id"]) == split]
        if not g:
            continue
        s = summarize(g)
        out.append({"split": split, "label": label, "cases": len(g),
                    "pass": int(round(sum(r["scores"]["pass"] for r in g))),
                    "pass_all": int(sum(r["scores"].get("pass_all", r["scores"]["pass"]) for r in g)),
                    **{m: s[m] for m in METRICS}, "avg_latency_ms": s["avg_latency_ms"]})
    return out


def group_table(gs: list[dict], repeat: int) -> list[str]:
    lines = [f"| group | cases | pass | pass^{repeat} | tool choice | retrieval | facts | citation | refusal |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for g in gs:
        lines.append(f"| {g['label']} | {g['cases']} | {g['pass']} of {g['cases']} | {g['pass_all']} of {g['cases']} | "
                     + " | ".join(fmt(g[m]) for m in METRICS) + " |")
    return lines


def split_of() -> dict[str, str]:
    return {c["id"]: c.get("split", "") for c in load_cases()[0]}


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=db.REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return ""


def fmt(v) -> str:
    return "n/a" if v is None else f"{v:.2f}"


def markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        f"# Eval report: {report['label']}",
        "",
        f"Model `{report['model']}`, commit `{report['commit']}`, {report['generated_at']}, {s['cases']} cases "
        f"(split {report.get('split', 'all')}, {report.get('repeat', 1)} run(s) per case; pass_all is pass^k).",
        "",
        "| metric | score | cases scored |",
        "| --- | --- | --- |",
    ]
    for m in METRICS + ["pass", "pass_all"]:
        if s.get(m) is not None:
            lines.append(f"| {m} | {fmt(s[m])} | {s[f'{m}_n']} |")
    if report.get("groups"):
        lines += ["", "By group:", "", *group_table(report["groups"], report.get("repeat", 1))]
    lines += ["", f"Average latency {s['avg_latency_ms'] / 1000:.1f} s per question.", "",
              "| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in report["cases"]:
        sc = r["scores"]
        lines.append(f"| {r['id']} | {r['category']} | {fmt(sc['tool_choice'])} | {fmt(sc['retrieval'])} | {fmt(sc['facts'])} | "
                     f"{fmt(sc['citation'])} | {fmt(sc['refusal'])} | {fmt(sc['pass'])} | {r['answer']['latency_ms'] / 1000:.0f} |")
    lines += ["", "## Missed facts", ""]
    for r in report["cases"]:
        missed = [f["name"] for f in r["facts"] if not f["matched"]]
        if missed:
            lines.append(f"- {r['id']}: {', '.join(missed)}")
    return "\n".join(lines) + "\n"


def combine_scores(runs: list[dict]) -> dict:
    """Mean of each metric over repeated runs; pass_all is 1 only if every run passed (pass^k)."""
    out = {}
    for m in METRICS + ["pass"]:
        vals = [r[m] for r in runs if r[m] is not None]
        out[m] = round(sum(vals) / len(vals), 3) if vals else None
    out["pass_all"] = 1.0 if all(r["pass"] == 1.0 for r in runs) else 0.0
    return out


def run(label: str, provider: str | None, model: str | None, only: list[str] | None, out_dir: Path,
        resume: bool = False, split: list[str] | str | None = None, repeat: int = 1) -> dict:
    cases, defaults = load_cases()
    splits = {c["id"]: c.get("split", "") for c in cases}
    if isinstance(split, str):
        split = [split]
    if only:
        cases = [c for c in cases if c["id"] in only]
    if split:
        cases = [c for c in cases if c.get("split") in split]
    with db.connect_admin() as conn:
        truth = compute_truth(conn, cases)
        retrieved = {c["id"]: [h["chunk_id"] for h in retrieval.search(conn, c["question"])] for c in cases}
    assistant = Assistant(get_provider(provider, model))
    out_dir.mkdir(parents=True, exist_ok=True)
    partial = out_dir / f"{label}.partial.json"
    rows = []
    if resume and partial.exists():  # pick up after the last saved case
        rows = [r for r in json.loads(partial.read_text())["cases"] if r["id"] in {c["id"] for c in cases}]
        print(f"resuming after {len(rows)} saved cases", flush=True)
    done = {r["id"] for r in rows}

    def report_for(rows):
        return {
            "label": label,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "model": assistant.provider.name + "/" + assistant.provider.model,
            "commit": git_commit(),
            "split": "+".join(split) if split else "all",
            "repeat": repeat,
            "summary": summarize(rows),
            "groups": groups(rows, splits),
            "cases": rows,
        }

    for c in cases:
        if c["id"] in done:
            continue
        attempts = []
        for _ in range(repeat):
            ans = assistant.ask(c["question"]).to_dict()
            attempts.append({**score_case(c, ans, truth, retrieved[c["id"]], defaults), "answer": ans})
        first = attempts[0]
        scores = combine_scores([a["scores"] for a in attempts])
        rows.append({"id": c["id"], "question": c["question"], "category": c["category"], "split": c.get("split", ""),
                     "keywords": c.get("keywords", []), "should_refuse": bool(c.get("should_refuse")),
                     "retrieved": retrieved[c["id"]], "scores": scores, "facts": first["facts"], "answer": first["answer"],
                     "repeats": attempts[1:]})
        sc, ans = scores, first["answer"]
        print(f"{c['id']}  pass={sc['pass']:.0f}  facts={fmt(sc['facts'])}  tools={fmt(sc['tool_choice'])}  "
              f"cite={fmt(sc['citation'])}  refusal={sc['refusal']:.0f}  {ans['latency_ms'] / 1000:.0f}s", flush=True)
        partial.write_text(json.dumps(report_for(rows), indent=2, default=str))  # progress, in case a long run stops
    report = report_for(rows)
    report["api_usage"] = getattr(assistant.provider, "usage", None)  # token counts, when the API reports them
    report["api_calls"] = getattr(assistant.provider, "calls", None)
    (out_dir / f"{label}.json").write_text(json.dumps(report, indent=2, default=str))
    (out_dir / f"{label}.md").write_text(markdown(report))
    partial.unlink()
    return report


def rescore(path: Path) -> dict:
    """Score the saved answers in a report again with the current cases and scorers (no model calls)."""
    report = json.loads(path.read_text())
    cases, defaults = load_cases()
    by_id = {c["id"]: c for c in cases}
    with db.connect_admin() as conn:
        truth = compute_truth(conn, cases)
        for r in report["cases"]:
            c = by_id[r["id"]]
            r["retrieved"] = [h["chunk_id"] for h in retrieval.search(conn, c["question"])]
            first = score_case(c, r["answer"], truth, r["retrieved"], defaults)
            for x in r.get("repeats", []):
                x.update(score_case(c, x["answer"], truth, r["retrieved"], defaults))
            r["facts"] = first["facts"]
            r["scores"] = combine_scores([first["scores"]] + [x["scores"] for x in r.get("repeats", [])])
    report["summary"] = summarize(report["cases"])
    report["groups"] = groups(report["cases"], {c["id"]: c.get("split", "") for c in cases})
    report["rescored_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(report, indent=2, default=str))
    path.with_suffix(".md").write_text(markdown(report))
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the eval suite against the assistant.")
    ap.add_argument("--label", default="latest")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", nargs="*", help="case ids to run")
    ap.add_argument("--out", default=str(REPORTS))
    ap.add_argument("--resume", action="store_true", help="continue from <label>.partial.json")
    ap.add_argument("--split", nargs="+", choices=list(GROUPS),
                    help="run only these splits: dev, test (old held-out), heldout_v2 (contaminated), heldout_v3")
    ap.add_argument("--repeat", type=int, default=1, help="runs per case; scores are means, pass_all is pass^k")
    ap.add_argument("--rescore", help="re-score a saved report with the current cases instead of running the model")
    ap.add_argument("--groups", nargs="+", metavar="REPORT",
                    help="print the per-group table (dev and each held-out set) for one or more saved reports")
    ap.add_argument("--trace", action="append", help="agent-trace: a JSONL trace from pda-agent-tool (repeatable)")
    ap.add_argument("--answers", action="append", help="agent-trace: the answers JSON for the trace in the same position")
    args = ap.parse_args()
    if args.provider == "agent-trace":  # an outside agent's tool calls and answers, replayed (agent_trace.py)
        from . import agent_trace

        if not args.answers:
            ap.error("--provider agent-trace needs --answers (and its --trace)")
        report = agent_trace.run(args.label, args.trace or [], args.answers, Path(args.out), args.split, args.only,
                                 args.model or "claude-opus-5-5")
        s = report["summary"]
        print("\n" + "  ".join(f"{m}={fmt(s[m])}" for m in METRICS + ["pass", "pass_all"]))
        print(f"wrote {args.out}/{args.label}.json and .md")
        return
    if args.groups:
        reports = [json.loads(Path(p).read_text()) for p in args.groups]
        rows = [r for rep in reports for r in rep["cases"]]
        print("\n".join(group_table(groups(rows, split_of()), max(rep.get("repeat", 1) for rep in reports))))
        return
    if args.rescore:
        report = rescore(Path(args.rescore))
        s = report["summary"]
        print("  ".join(f"{m}={fmt(s[m])}" for m in METRICS + ["pass", "pass_all"]))
        return
    report = run(args.label, args.provider, args.model, args.only, Path(args.out), args.resume, args.split, args.repeat)
    s = report["summary"]
    print("\n" + "  ".join(f"{m}={fmt(s[m])}" for m in METRICS + ["pass", "pass_all"]))
    print(f"wrote {args.out}/{args.label}.json and .md")


if __name__ == "__main__":
    main()
