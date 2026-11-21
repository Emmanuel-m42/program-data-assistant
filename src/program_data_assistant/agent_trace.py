"""An agent outside this app as the model: a tool CLI it calls from a shell, and a replayer that scores it.

    pda-agent-tool setup                                  # load the demo data into PDA_PGDATA (once)
    pda-agent-tool prompt                                 # the system prompt and tool specs, as the app sends them
    pda-agent-tool get_view '{"view": "v_office_pace"}' --case q01 --trace run1.jsonl

A tool call runs the app's own Toolbox (SQL guard, read-only role, 5 s timeout, row caps, the repeated-query
check within a case) and prints exactly the text the model would get as the tool message, then appends the
call to the trace. The agent's final answers go in a JSON file, {"q01": "answer text", ...}. Then

    evals --provider agent-trace --trace run1.jsonl --answers run1.json --split dev --label claude-agent_dev

replays every traced call through a fresh Toolbox, checks the result matches what the agent was shown (a
mismatch fails the case), applies the app's after-answer steps (unknown citations dropped, a draft with two or
more unsupported numbers withheld), and scores with the usual scorer. Several --trace/--answers pairs give pass^k.

Not applied in this mode: the agent loop's in-loop nudges (retry after a failed query, the grounding, look-first
and citation rewrites) and its 7-step cap, since the agent runs its own loop. Latency is not measured.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from . import agent, db, prompts
from .tools import TOOL_SPECS, Toolbox

AGENT_LABEL = ("Claude Opus 5.5 as the agent through the tool CLI (same tools and prompt, not the app's own agent "
               "loop; the in-loop guardrail rewrites don't apply)")
NOT_APPLIED = ("The app's in-loop guardrail rewrites (retry nudge, grounding, look-first and citation nudges) and its "
               "7-step cap don't apply in this mode; the after-answer steps (dropping unknown citations, withholding "
               "a draft with unsupported numbers) do. Latency is not measured.")


def read_trace(path: Path | None) -> dict[str, list[dict]]:
    calls: dict[str, list[dict]] = {}
    if path and path.exists():
        for line in path.read_text("utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                calls.setdefault(entry["case"], []).append(entry)
    return calls


def case_ids() -> set[str]:
    from .evals import load_cases

    return {c["id"] for c in load_cases()[0]}


def tool_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pda-agent-tool", description="Call one assistant tool as the model would.")
    p.add_argument("tool", help="get_view, query_program_data or search_documents; or 'prompt' or 'setup'")
    p.add_argument("args", nargs="?", default="{}", help="the tool's arguments as a JSON object")
    p.add_argument("--case", help="case id the call belongs to")
    p.add_argument("--trace", help="JSONL file the call is appended to")
    a = p.parse_args(argv)
    if a.tool == "prompt":
        print("SYSTEM PROMPT\n\n" + prompts.system_prompt() + "\n\nTOOLS (name, description, JSON schema of the "
              "arguments)\n\n" + json.dumps(TOOL_SPECS, indent=1))
        return 0
    if a.tool == "setup":
        from .load import load_all

        for table, n in load_all().items():
            print(f"{table:24} {n}")
        return 0
    if a.case not in case_ids():
        print("--case must be one of the case ids in your brief", file=sys.stderr)
        return 2
    if not a.trace:
        print("--trace is required", file=sys.stderr)
        return 2
    try:
        args = json.loads(a.args)
    except json.JSONDecodeError as e:
        print(f"arguments aren't valid JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(args, dict):
        print("arguments must be a JSON object", file=sys.stderr)
        return 2
    toolbox = Toolbox()
    # The app keeps the queries already run in this question; rebuild that from the case's earlier calls.
    toolbox.seen_sql = {str(e["args"].get("sql", "")).strip() for e in read_trace(Path(a.trace)).get(a.case, [])
                        if e["tool"] == "query_program_data"}
    res = toolbox.run(a.tool, args)
    entry = {"case": a.case, "tool": a.tool, "args": args, "result": res.content, "ok": res.ok,
             "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    with open(a.trace, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    print(res.content)
    return 0


def replay(question: str, entries: list[dict], text: str | None, toolbox: Toolbox, model: str) -> dict:
    """Rebuild the app's Answer from an agent's calls and final text, as Assistant.ask's last steps would."""
    toolbox.reset()
    results, calls_log, mismatches = [], [], []
    for i, e in enumerate(entries):
        res = toolbox.run(e["tool"], e["args"])
        results.append(res)
        calls_log.append({"name": e["tool"], "args": e["args"], "ok": res.ok, "result": res.summary})
        if res.content != e["result"]:
            mismatches.append(i)
    if text is None or mismatches:
        why = "no answer in this run" if text is None else f"replay mismatch on call(s) {mismatches}"
        return {**agent.Answer(question, "", True, tool_calls=calls_log, model=model).to_dict(), "error": why}
    text = text.strip()
    text, dropped = agent.drop_unknown_citations(text, results)
    refused = bool(agent.REFUSAL.search(text)) or not text
    missing = [] if refused else agent.ungrounded_numbers(text, question, results)
    withheld = ""
    if len(missing) >= 2:
        withheld, text, refused = text, agent.WITHHELD, True
    cites = agent.parse_citations(text)
    return agent.Answer(
        question=question, answer=text, refused=refused, tool_calls=calls_log,
        sources=agent.build_sources(results, cites), citations=cites,
        citations_valid=agent.citations_valid(results, cites), ungrounded_numbers=missing, withheld_draft=withheld,
        dropped_citations=dropped, latency_ms=0, model=model, steps=len(entries) + 1,
    ).to_dict()


def run(label: str, traces: list[str], answers: list[str], out_dir: Path, split: list[str] | None = None,
        only: list[str] | None = None, model: str = "claude-opus-5-5") -> dict:
    from . import evals, retrieval

    if traces and len(traces) != len(answers):
        raise SystemExit("give one --trace per --answers file, in the same order")
    runs = [(read_trace(Path(t) if traces else None), json.loads(Path(a).read_text("utf-8")))
            for t, a in zip(traces or [None] * len(answers), answers)]
    cases, defaults = evals.load_cases()
    splits = {c["id"]: c.get("split", "") for c in cases}
    if only:
        cases = [c for c in cases if c["id"] in only]
    if split:
        cases = [c for c in cases if c.get("split") in split]
    elif not only:  # every case some run answered
        cases = [c for c in cases if any(c["id"] in r[1] for r in runs)]
    with db.connect_admin() as conn:
        truth = evals.compute_truth(conn, cases)
        retrieved = {c["id"]: [h["chunk_id"] for h in retrieval.search(conn, c["question"])] for c in cases}
    toolbox = Toolbox()
    rows, problems = [], []
    for c in cases:
        attempts = []
        for n, (calls, ans) in enumerate(runs):
            a = replay(c["question"], calls.get(c["id"], []), ans.get(c["id"]), toolbox, model)
            scored = evals.score_case(c, a, truth, retrieved[c["id"]], defaults)
            if a.get("error"):
                problems.append(f"{c['id']} run {n + 1}: {a['error']}")
                # Retrieval scores the retriever on the question, not the answer, so it stands.
                scored["scores"] = {m: (0.0 if v is not None and m != "retrieval" else v)
                                    for m, v in scored["scores"].items()}
            attempts.append({**scored, "answer": a})
        scores = evals.combine_scores([x["scores"] for x in attempts])
        first = attempts[0]
        rows.append({"id": c["id"], "question": c["question"], "category": c["category"], "split": c.get("split", ""),
                     "keywords": c.get("keywords", []), "should_refuse": bool(c.get("should_refuse")),
                     "retrieved": retrieved[c["id"]], "scores": scores, "facts": first["facts"],
                     "answer": first["answer"], "repeats": attempts[1:]})
        print(f"{c['id']}  pass={scores['pass']:.0f}  pass_all={scores['pass_all']:.0f}  facts={evals.fmt(scores['facts'])}  "
              f"tools={evals.fmt(scores['tool_choice'])}  cite={evals.fmt(scores['citation'])}  "
              f"refusal={evals.fmt(scores['refusal'])}", flush=True)
    report = {
        "label": label,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "model": f"agent-trace/{model}",
        "model_label": AGENT_LABEL,
        "mode_note": NOT_APPLIED,
        "commit": evals.git_commit(),
        "split": "+".join(split) if split else "all",
        "repeat": len(runs),
        "traces": traces,
        "answers": answers,
        "integrity_problems": problems,
        "summary": evals.summarize(rows),
        "groups": evals.groups(rows, splits),
        "cases": rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{label}.json").write_text(json.dumps(report, indent=2, default=str))
    md = evals.markdown(report).replace("\n\n", f"\n\nModel: {AGENT_LABEL}. {NOT_APPLIED}\n\n", 1)
    if problems:
        md += "\n## Failed by the harness\n\n" + "\n".join(f"- {p}" for p in problems) + "\n"
    (out_dir / f"{label}.md").write_text(md)
    return report


if __name__ == "__main__":
    raise SystemExit(tool_main())
