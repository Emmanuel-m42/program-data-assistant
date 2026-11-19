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


def numbers_in(text: str) -> list[float]:
    plain = CITE_MARK.sub(" ", text)
    return [float(m.group(1).replace(",", "")) for m in NUMBER.finditer(plain)]


def fact_matches(fact: dict, truth: float | None, answer: str, defaults: dict) -> bool:
    if "any_of" in fact:
        low = answer.lower()
        return any(s.lower() in low for s in fact["any_of"])
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


def score_case(case: dict, answer: dict, truth: dict, retrieved: list[str], defaults: dict) -> dict:
    should_refuse = bool(case.get("should_refuse"))
    called = {t["name"] for t in answer["tool_calls"]}
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
            details.append({"name": f["name"], "expected": t if "sql" in f else f["any_of"], "matched": ok})
        scores["facts"] = round(hits / len(facts), 3) if facts else None
        scores["citation"] = 1.0 if answer["citations_valid"] else 0.0
    applicable = [scores[m] for m in METRICS if m != "retrieval" and scores[m] is not None]
    scores["pass"] = 1.0 if all(s == 1.0 for s in applicable) else 0.0
    return {"scores": scores, "facts": details}


def summarize(rows: list[dict]) -> dict:
    out = {"cases": len(rows)}
    for m in METRICS + ["pass"]:
        vals = [r["scores"][m] for r in rows if r["scores"][m] is not None]
        out[m] = round(sum(vals) / len(vals), 3) if vals else None
        out[f"{m}_n"] = len(vals)
    lat = [r["answer"]["latency_ms"] for r in rows]
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
        f"Model `{report['model']}`, commit `{report['commit']}`, {report['generated_at']}, {s['cases']} cases.",
        "",
        "| metric | score | cases scored |",
        "| --- | --- | --- |",
    ]
    for m in METRICS + ["pass"]:
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


def run(label: str, provider: str | None, model: str | None, only: list[str] | None, out_dir: Path) -> dict:
    cases, defaults = load_cases()
    if only:
        cases = [c for c in cases if c["id"] in only]
    with db.connect_admin() as conn:
        truth = compute_truth(conn, cases)
        retrieved = {c["id"]: [h["chunk_id"] for h in retrieval.search(conn, c["question"])] for c in cases}
    assistant = Assistant(get_provider(provider, model))
    rows = []
    for c in cases:
        ans = assistant.ask(c["question"]).to_dict()
        scored = score_case(c, ans, truth, retrieved[c["id"]], defaults)
        rows.append({"id": c["id"], "question": c["question"], "category": c["category"], "keywords": c.get("keywords", []),
                     "should_refuse": bool(c.get("should_refuse")), "retrieved": retrieved[c["id"]], **scored, "answer": ans})
        sc = scored["scores"]
        print(f"{c['id']}  pass={sc['pass']:.0f}  facts={fmt(sc['facts'])}  tools={fmt(sc['tool_choice'])}  "
              f"cite={fmt(sc['citation'])}  refusal={sc['refusal']:.0f}  {ans['latency_ms'] / 1000:.0f}s", flush=True)
    report = {
        "label": label,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "model": assistant.provider.name + "/" + assistant.provider.model,
        "commit": git_commit(),
        "summary": summarize(rows),
        "cases": rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{label}.json").write_text(json.dumps(report, indent=2, default=str))
    (out_dir / f"{label}.md").write_text(markdown(report))
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the eval suite against the assistant.")
    ap.add_argument("--label", default="latest")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", nargs="*", help="case ids to run")
    ap.add_argument("--out", default=str(REPORTS))
    args = ap.parse_args()
    report = run(args.label, args.provider, args.model, args.only, Path(args.out))
    s = report["summary"]
    print("\n" + "  ".join(f"{m}={fmt(s[m])}" for m in METRICS + ["pass"]))
    print(f"wrote {args.out}/{args.label}.json and .md")


if __name__ == "__main__":
    main()
