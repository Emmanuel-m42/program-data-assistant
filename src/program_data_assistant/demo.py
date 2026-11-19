"""Build demo/recorded_runs.json from two eval reports, for a website to render without the backend.

Run: uv run pda-demo --before evals/reports/baseline.json --after evals/reports/improved.json \\
         --what-changed "..." --out demo/recorded_runs.json

The recorded run for each demo question is the one from the --after report (or --before when only
one report is given). Each question also carries its per-metric eval scores from both reports.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from .evals import METRICS

PROGRAM = "Riverbend Votes (GOTV) and Riverbend Registers (voter registration), fictional programs"
DEMO_IDS = [f"q{i:02d}" for i in range(1, 20)]
SOURCE_ROWS = 8


def metric_scores(case: dict | None) -> dict | None:
    if case is None:
        return None
    return {m: case["scores"][m] for m in METRICS + ["pass"]}


def clean_source(s: dict) -> dict:
    if s["type"] == "rows":
        return {"type": "rows", "table": s["table"], "columns": s["columns"], "rows": s["rows"][:SOURCE_ROWS]}
    return {"type": "passage", "doc": s["doc"], "text": s["text"]}


def run_fields(case: dict) -> dict:
    a = case["answer"]
    return {
        "tool_calls": [{"name": t["name"], "args": t["args"], "result": t["result"]} for t in a["tool_calls"]],
        "sources": [clean_source(s) for s in a["sources"]],
        "answer": a["answer"],
        "refused": a["refused"],
        "latency_ms": a["latency_ms"],
    }


def question_entry(recorded: dict, before: dict | None, after: dict | None) -> dict:
    """Top-level fields are the recorded (after) run; the baseline attempt sits under `baseline`."""
    entry = {
        "id": recorded["id"],
        "question": recorded["question"],
        "category": recorded["category"],
        "keywords": recorded.get("keywords", []),
        **run_fields(recorded),
        "model": recorded["answer"]["model"],
    }
    if after is not None and before is not None:
        entry["baseline"] = run_fields(before)
    entry["eval"] = {"before": metric_scores(before), "after": metric_scores(after)}
    return entry


def totals(report: dict | None) -> dict | None:
    if report is None:
        return None
    s = report["summary"]
    return {"label": report["label"], "commit": report.get("commit", ""), "cases": s["cases"],
            **{m: s[m] for m in METRICS + ["pass"]}, "avg_latency_ms": s["avg_latency_ms"]}


def build(before: dict | None, after: dict | None, what_changed: str, ids: list[str]) -> dict:
    by_b = {c["id"]: c for c in (before or {}).get("cases", [])}
    by_a = {c["id"]: c for c in (after or {}).get("cases", [])}
    recorded_from = by_a or by_b
    questions = [question_entry(recorded_from[i], by_b.get(i), by_a.get(i)) for i in ids if i in recorded_from]
    return {
        "program": PROGRAM,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "model": (after or before)["model"],
        "scoreboard": {"before": totals(before), "after": totals(after), "what_changed": what_changed},
        "questions": questions,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Export recorded demo runs for the website.")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after")
    ap.add_argument("--what-changed", default="")
    ap.add_argument("--limit", type=int, help="only the first N demo questions (for a shape sample)")
    ap.add_argument("--out", default="demo/recorded_runs.json")
    args = ap.parse_args()
    before = json.loads(Path(args.before).read_text())
    after = json.loads(Path(args.after).read_text()) if args.after else None
    ids = DEMO_IDS[: args.limit] if args.limit else DEMO_IDS
    data = build(before, after, args.what_changed, ids)
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    if "·" in text:
        raise SystemExit("refusing to write a middle dot")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text + "\n")
    print(f"wrote {args.out}: {len(data['questions'])} questions")


if __name__ == "__main__":
    main()
