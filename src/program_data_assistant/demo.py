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
    out = {m: case["scores"][m] for m in METRICS + ["pass"]}
    if "pass_all" in case["scores"]:
        out["pass_all"] = case["scores"]["pass_all"]  # passed on every repeated run
    return out


def merge_reports(reports: list[dict]) -> dict:
    """One report from several split runs (for example dev and held-out test) of the same code and model."""
    if len(reports) == 1:
        return reports[0]
    cases = [c for r in reports for c in r["cases"]]
    return {
        "label": " + ".join(r["label"] for r in reports),
        "model": reports[0]["model"],
        "commit": " + ".join(dict.fromkeys(r.get("commit", "") for r in reports)),
        "parts": reports,
        "cases": cases,
    }


def split_block(cases: list[dict], repeat: int = 1) -> dict:
    """Scores for one half: pass and pass_all_runs are case counts, the other metrics are means."""
    out = {"cases": len(cases), "runs_per_case": repeat,
           "pass": int(round(sum(c["scores"]["pass"] for c in cases))),
           "pass_all_runs": int(sum(c["scores"].get("pass_all", c["scores"]["pass"]) for c in cases))}
    for m in METRICS:
        vals = [c["scores"][m] for c in cases if c["scores"][m] is not None]
        out[m] = round(sum(vals) / len(vals), 3) if vals else None
    lat = [a["latency_ms"] for c in cases for a in [c["answer"]] + [x["answer"] for x in c.get("repeats", [])]]
    out["avg_latency_ms"] = int(sum(lat) / len(lat)) if lat else 0
    return out


def by_split(report: dict, splits: dict[str, str]) -> dict:
    repeat = max([p.get("repeat", 1) for p in report.get("parts", [report])])
    cases = report["cases"]
    return {"heldout": split_block([c for c in cases if splits.get(c["id"]) == "test"], repeat),
            "tuned": split_block([c for c in cases if splits.get(c["id"]) == "dev"], repeat)}


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


def comparison_row(spec: str) -> dict:
    """'model|code|report.json,report.json' -> per-group results from those reports; no reports means still running."""
    from .evals import GROUPS, groups, load_cases

    model, code, paths = (spec.split("|") + ["", ""])[:3]
    reports = [json.loads(Path(p).read_text()) for p in paths.split(",") if p.strip()]
    row = {"model": model, "code": code, "groups": {}}
    if not reports:
        row["status"] = "running"
        return row
    splits = {c["id"]: c.get("split", "") for c in load_cases()[0]}
    repeat = max(r.get("repeat", 1) for r in reports)
    for g in groups([c for r in reports for c in r["cases"]], splits):
        row["groups"][g["split"]] = {"label": GROUPS[g["split"]], "cases": g["cases"], "pass": g["pass"],
                                     "pass_all_runs": g["pass_all"], "runs_per_case": repeat,
                                     **{m: g[m] for m in METRICS}, "avg_latency_ms": g["avg_latency_ms"]}
    return row


def build(before: dict | None, after: dict | None, what_changed: str, ids: list[str], split_note: str = "",
          notes: dict[str, str] | None = None) -> dict:
    by_b = {c["id"]: c for c in (before or {}).get("cases", [])}
    by_a = {c["id"]: c for c in (after or {}).get("cases", [])}
    recorded_from = by_a or by_b
    questions = [question_entry(recorded_from[i], by_b.get(i), by_a.get(i)) for i in ids if i in recorded_from]
    for q in questions:
        if notes and q["id"] in notes:
            q["eval"]["note"] = notes[q["id"]]  # one line on why the shown answer was scored as it was
    scoreboard = {"before": totals(before), "after": totals(after) if after and "parts" not in after else None,
                  "what_changed": what_changed}
    if after and "parts" in after:
        from .evals import load_cases

        splits = {c["id"]: c.get("split") for c in load_cases()[0]}
        a = by_split(after, splits)
        # No single total that mixes in the tuned half: the held-out half is the headline.
        scoreboard["after"] = {"label": after["label"], "model": after["model"], "commit": after["commit"], **a}
        if before:
            scoreboard["before"] = {**totals(before), **by_split(before, splits),
                                    "split_note": "The baseline ran once on all 28 before the split existed; "
                                                  "its halves are the same answers grouped by today's split."}
        h = a["heldout"]
        scoreboard["headline"] = (f"Held-out half: {h['pass']} of {h['cases']} passed, the same {h['pass_all_runs']} "
                                  f"on each of {h['runs_per_case']} runs.")
        scoreboard["split_note"] = split_note
    shown = [q["latency_ms"] for q in questions]
    scoreboard["shown_answers_avg_latency_ms"] = int(sum(shown) / len(shown)) if shown else 0
    scoreboard["latency_note"] = ("shown_answers_avg_latency_ms averages the answers shown on the page (one run per "
                                  "demo question). Each half's avg_latency_ms averages every eval answer in that half "
                                  "across all runs, including fast document and refusal questions.")
    return {
        "program": PROGRAM,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "model": (after or before)["model"],
        "scoreboard": scoreboard,
        "questions": questions,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Export recorded demo runs for the website.")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", action="append", help="repeat to merge split runs, e.g. dev and held-out test")
    ap.add_argument("--what-changed", default="")
    ap.add_argument("--split-note", default="", help="how and when the dev/test split was made")
    ap.add_argument("--limit", type=int, help="only the first N demo questions (for a shape sample)")
    ap.add_argument("--note", action="append", default=[], metavar="ID=TEXT",
                    help="a one-line note on a question's score, e.g. why it missed; repeat per question")
    ap.add_argument("--compare", action="append", default=[], metavar="MODEL|CODE|REPORT[,REPORT]",
                    help="a row of the model comparison; leave the reports out for a run still going; repeat per row")
    ap.add_argument("--headline", help="the How it's tested headline (default: the shown run's held-out half)")
    ap.add_argument("--headline-note", default="", help="one line under the headline: which model and mode")
    ap.add_argument("--comparison-note", default="", help="a short note under the comparison table")
    ap.add_argument("--out", default="demo/recorded_runs.json")
    args = ap.parse_args()
    before = json.loads(Path(args.before).read_text())
    after = merge_reports([json.loads(Path(p).read_text()) for p in args.after]) if args.after else None
    ids = DEMO_IDS[: args.limit] if args.limit else DEMO_IDS
    notes = dict(n.split("=", 1) for n in args.note)
    data = build(before, after, args.what_changed, ids, args.split_note, notes)
    if args.compare:
        data["scoreboard"]["comparison"] = [comparison_row(s) for s in args.compare]
        data["scoreboard"]["comparison_note"] = args.comparison_note
    if args.headline:
        data["scoreboard"]["headline"] = args.headline
        data["scoreboard"]["headline_note"] = args.headline_note
        data["scoreboard"]["shown_run_note"] = (f"The answers shown in this demo are the recorded answers of "
                                                f"{data['model'].removeprefix('ollama/')}, the run in the table below.")
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    if "\u00b7" in text:
        raise SystemExit("refusing to write a middle dot")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text + "\n")
    print(f"wrote {args.out}: {len(data['questions'])} questions")


if __name__ == "__main__":
    main()
