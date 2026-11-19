"""Ask one question from the command line. Run: uv run pda-ask "Which offices will miss their goal?" """

from __future__ import annotations

import argparse
import json

from .agent import Assistant
from .llm import get_provider


def main() -> None:
    ap = argparse.ArgumentParser(description="Ask the program data assistant a question.")
    ap.add_argument("question")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--json", action="store_true", help="print the full answer record")
    args = ap.parse_args()
    ans = Assistant(get_provider(args.provider, args.model)).ask(args.question)
    if args.json:
        print(json.dumps(ans.to_dict(), indent=2, default=str))
        return
    for c in ans.tool_calls:
        arg = c["args"].get("sql") or c["args"].get("query") or c["args"]
        print(f"> {c['name']}: {arg}\n  {c['result']}")
    print(f"\n{ans.answer}\n\n({ans.latency_ms / 1000:.1f} s, {ans.model}, refused={ans.refused}, citations_valid={ans.citations_valid})")


if __name__ == "__main__":
    main()
