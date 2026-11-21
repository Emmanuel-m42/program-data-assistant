"""The demo exporter through its CLI entry point, on the committed reports (no database, no model)."""

import json
import sys

from program_data_assistant import demo
from program_data_assistant.db import REPO

REPORTS = REPO / "evals" / "reports"


def test_pda_demo_rebuilds_the_scoreboard_and_notes(tmp_path, monkeypatch):
    out = tmp_path / "recorded_runs.json"
    monkeypatch.setattr(sys, "argv", [
        "pda-demo", "--before", str(REPORTS / "baseline.json"),
        "--after", str(REPORTS / "final-qwen38-27b-dev-x3.json"),
        "--after", str(REPORTS / "final-qwen38-27b-test-x3.json"),
        "--note", "q13=reads its rows backwards", "--out", str(out),
    ])
    demo.main()
    data = json.loads(out.read_text())
    after = data["scoreboard"]["after"]
    assert (after["tuned"]["pass"], after["tuned"]["pass_all_runs"]) == (12, 12)
    assert (after["heldout"]["pass"], after["heldout"]["pass_all_runs"]) == (12, 12)  # q12 counts since the scorer reads words
    by = {q["id"]: q for q in data["questions"]}
    assert by["q13"]["eval"]["note"] == "reads its rows backwards" and by["q13"]["eval"]["after"]["pass"] == 0
    assert "note" not in by["q01"]["eval"]


def test_committed_demo_file_matches_the_reports():
    committed = json.loads((REPO / "demo" / "recorded_runs.json").read_text())
    dev = json.loads((REPORTS / "final-qwen38-27b-dev-x3.json").read_text())
    failed = {c["id"] for c in dev["cases"] if c["scores"]["pass"] < 1}
    assert failed == {"q07", "q13"}
    assert committed["scoreboard"]["after"]["tuned"]["pass"] == 14 - len(failed)
