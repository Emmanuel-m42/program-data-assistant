"""Eval runner. Run: uv run evals --label baseline

The MCP version (VAN tools from ngpvan-mcp alongside the program tools) is scored separately:
  uv run evals --van demo --cases evals/cases_mcp_van.yaml --label mcp-van-cases-...   the VAN-routed cases
  uv run evals --van demo --label mcp-van-original-...                                 the 28 originals, VAN tools present

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
from .tools import Toolbox

CASES = db.REPO / "evals" / "cases.yaml"
REPORTS = db.REPO / "evals" / "reports"
METRICS = ["tool_choice", "retrieval", "facts", "citation", "refusal"]
NUMBER = re.compile(r"(?<![\w.])-?\$?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)")
CITE_MARK = re.compile(r"\[[^\]]*\]")


def load_cases(path: Path = CASES) -> tuple[list[dict], dict]:
    data = yaml.safe_load(path.read_text())
    return data["cases"], data.get("defaults", {})


def needs_van(cases: list[dict]) -> bool:
    return any("mcp" in f for c in cases for f in c.get("facts", []))


def compute_truth(conn, cases: list[dict], van=None) -> dict[tuple[str, str], object]:
    """Ground truth for every fact that has one: SQL straight on the raw tables, or a VAN tool called directly
    (never through the model) and read with a JMESPath expression."""
    conn.execute("SET search_path = program, public")
    truth: dict[tuple[str, str], object] = {}
    for c in cases:
        for f in c.get("facts", []):
            if "sql" in f:
                v = conn.execute(f["sql"]).fetchone()[0]
                truth[(c["id"], f["name"])] = float(v)
            elif "mcp" in f:
                if van is None:
                    raise RuntimeError(f"{c['id']} needs the VAN tools for its ground truth; pass --van demo")
                import jmespath

                data = van.call_direct(f["mcp"]["tool"], f["mcp"].get("args", {}))
                v = jmespath.search(f["path"], data)
                truth[(c["id"], f["name"])] = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    return truth


def numbers_in(text: str) -> list[float]:
    plain = CITE_MARK.sub(" ", text)
    return [float(m.group(1).replace(",", "")) for m in NUMBER.finditer(plain)]


def fact_matches(fact: dict, truth, answer: str, defaults: dict) -> bool:
    low = answer.lower()
    if "any_of" in fact:
        return any(s.lower() in low for s in fact["any_of"])
    if truth is None:
        return False
    if isinstance(truth, str):  # a name or label: it must appear
        return truth.lower() in low
    if isinstance(truth, list):  # several names or labels: all must appear
        return bool(truth) and all(str(t).lower() in low for t in truth)
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


def score_case(case: dict, answer: dict, truth: dict, retrieved: list[str], defaults: dict) -> dict:
    should_refuse = bool(case.get("should_refuse"))
    called = {t["name"] for t in answer["tool_calls"]}
    if "get_view" in called:  # get_view is a narrower way to query program data
        called.add("query_program_data")
    scores: dict[str, float | None] = dict.fromkeys(METRICS)
    details = []
    scores["refusal"] = 1.0 if answer["refused"] == should_refuse else 0.0
    if case.get("expected_docs"):
        exp = case["expected_docs"]
        scores["retrieval"] = round(sum(1 for d in exp if d in retrieved) / len(exp), 3)
    if not should_refuse:
        exp_tools = case.get("expected_tools", [])
        scores["tool_choice"] = 1.0 if all(t in called for t in exp_tools) else 0.0
        facts = case.get("facts", [])
        hits = 0
        for f in facts:
            t = truth.get((case["id"], f["name"]))
            ok = (not answer["refused"]) and fact_matches(f, t, answer["answer"], defaults)
            hits += ok
            details.append({"name": f["name"], "expected": f["any_of"] if "any_of" in f else t, "matched": ok})
        scores["facts"] = round(hits / len(facts), 3) if facts else None
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


class GuardStop(RuntimeError):
    """The --guard-cmd check failed; the partial report keeps every finished case."""


def start_van(mode: str | None):
    """VAN tools for an eval run: 'demo' launches ngpvan-mcp --demo; None leaves them off."""
    if not mode:
        return None
    from .van_mcp import VanMcp, _ngpvan_command

    if mode != "demo":
        raise ValueError("--van takes 'demo'")
    return VanMcp(_ngpvan_command()).start()


def run(label: str, provider: str | None, model: str | None, only: list[str] | None, out_dir: Path,
        resume: bool = False, split: str | None = None, repeat: int = 1, cases_path: Path = CASES,
        van_mode: str | None = None, guard_cmd: str | None = None) -> dict:
    cases, defaults = load_cases(cases_path)
    if only:
        cases = [c for c in cases if c["id"] in only]
    if split:
        cases = [c for c in cases if c.get("split") == split]
    if needs_van(cases) and not van_mode:
        raise ValueError(f"{cases_path.name} has VAN cases; run it with --van demo")
    van = start_van(van_mode)
    try:
        return _run(label, provider, model, out_dir, resume, split, repeat, cases_path, cases, defaults, van, guard_cmd)
    finally:
        if van is not None:
            van.close()


def _run(label, provider, model, out_dir, resume, split, repeat, cases_path, cases, defaults, van, guard_cmd=None) -> dict:
    with db.connect_admin() as conn:
        truth = compute_truth(conn, cases, van)
        retrieved = {c["id"]: [h["chunk_id"] for h in retrieval.search(conn, c["question"])] for c in cases}
    assistant = Assistant(get_provider(provider, model), Toolbox(van=van))
    tools_offered = [t["name"] for t in assistant.toolbox.specs()]
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
            "split": split or "all",
            "repeat": repeat,
            "cases_file": str(cases_path.relative_to(db.REPO)) if cases_path.is_relative_to(db.REPO) else str(cases_path),
            "tools": tools_offered,  # the tool set this score belongs to
            "summary": summarize(rows),
            "cases": rows,
        }

    for c in cases:
        if c["id"] in done:
            continue
        if guard_cmd:  # e.g. a memory check on a shared model host; non-zero exit stops the run, progress kept
            check = subprocess.run(guard_cmd, shell=True, capture_output=True, text=True)
            if check.returncode != 0:
                reason = (check.stdout + check.stderr).strip()[-300:]
                print(f"stopped before {c['id']}: guard said no ({reason})", flush=True)
                raise GuardStop(reason)
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
    cases, defaults = load_cases(db.REPO / report.get("cases_file", "evals/cases.yaml"))
    by_id = {c["id"]: c for c in cases}
    van = start_van("demo") if needs_van(cases) else None
    try:
        with db.connect_admin() as conn:
            truth = compute_truth(conn, cases, van)
    finally:
        if van is not None:
            van.close()
    with db.connect_admin() as conn:
        for r in report["cases"]:
            c = by_id[r["id"]]
            r["retrieved"] = [h["chunk_id"] for h in retrieval.search(conn, c["question"])]
            first = score_case(c, r["answer"], truth, r["retrieved"], defaults)
            for x in r.get("repeats", []):
                x.update(score_case(c, x["answer"], truth, r["retrieved"], defaults))
            r["facts"] = first["facts"]
            r["scores"] = combine_scores([first["scores"]] + [x["scores"] for x in r.get("repeats", [])])
    report["summary"] = summarize(report["cases"])
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
    ap.add_argument("--split", choices=["dev", "test"], help="run only the dev or the held-out test cases")
    ap.add_argument("--repeat", type=int, default=1, help="runs per case; scores are means, pass_all is pass^k")
    ap.add_argument("--rescore", help="re-score a saved report with the current cases instead of running the model")
    ap.add_argument("--cases", default=str(CASES), help="cases file (evals/cases_mcp_van.yaml for the VAN cases)")
    ap.add_argument("--van", choices=["demo"], help="offer the VAN tools from ngpvan-mcp --demo (the MCP version)")
    ap.add_argument("--guard-cmd", help="shell command run before each case; a non-zero exit stops the run (partial kept)")
    args = ap.parse_args()
    if args.rescore:
        report = rescore(Path(args.rescore))
        s = report["summary"]
        print("  ".join(f"{m}={fmt(s[m])}" for m in METRICS + ["pass", "pass_all"]))
        return
    if args.van and not args.label.startswith("mcp-van"):
        ap.error("runs with the VAN tools are scored separately: use a label starting with mcp-van")
    report = run(args.label, args.provider, args.model, args.only, Path(args.out), args.resume, args.split, args.repeat,
                 Path(args.cases).resolve(), args.van, args.guard_cmd)
    s = report["summary"]
    print("\n" + "  ".join(f"{m}={fmt(s[m])}" for m in METRICS + ["pass", "pass_all"]))
    print(f"wrote {args.out}/{args.label}.json and .md")


if __name__ == "__main__":
    main()
