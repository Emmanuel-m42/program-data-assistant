"""Reporting groups: dev, old held-out (contaminated) and new held-out, with pass^k, through the evals CLI."""

import sys

from program_data_assistant import evals
from program_data_assistant.db import REPO

REPORTS = REPO / "evals" / "reports"


def test_groups_cli_prints_each_group_with_pass_k(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evals", "--groups", str(REPORTS / "final-qwen38-27b-dev-x3.json"),
                                      str(REPORTS / "final-qwen38-27b-test-x3.json")])
    evals.main()
    out = capsys.readouterr().out
    assert "| group | cases | pass | pass^3 |" in out
    assert "| dev (tuned) | 14 | 12 of 14 | 12 of 14 |" in out
    assert "| old held-out (contaminated) | 14 | 12 of 14 | 12 of 14 |" in out
    assert "new held-out" not in out  # no heldout_v2 answers in these reports


def test_groups_count_pass_and_pass_all_separately():
    def row(i, p, pa):
        return {"id": i, "scores": {"tool_choice": 1.0, "retrieval": None, "facts": 1.0, "citation": 1.0,
                                    "refusal": 1.0, "pass": p, "pass_all": pa}, "answer": {"latency_ms": 1000}}
    rows = [row("n01", 1.0, 1.0), row("n02", 0.667, 0.0), row("q01", 1.0, 1.0)]
    gs = evals.groups(rows, {"n01": "heldout_v2", "n02": "heldout_v2", "q01": "dev"})
    assert [g["split"] for g in gs] == ["dev", "heldout_v2"]
    fresh = gs[1]
    assert (fresh["label"], fresh["cases"], fresh["pass"], fresh["pass_all"]) == ("new held-out", 2, 2, 1)


def test_run_takes_several_splits(monkeypatch, tmp_path):
    asked = []

    class Fake:
        def __init__(self, provider):
            self.provider = type("P", (), {"name": "fake", "model": "m"})()

        def ask(self, question):
            asked.append(question)
            return type("A", (), {"to_dict": lambda self: {
                "answer": "I can't confirm that from the program data or documents.", "refused": True,
                "tool_calls": [], "citations_valid": True, "latency_ms": 1}})()

    monkeypatch.setattr(evals, "Assistant", Fake)
    monkeypatch.setattr(evals, "get_provider", lambda name=None, model=None: None)
    report = evals.run("groups", None, None, ["x07", "x08", "n14"], tmp_path, split=["dev", "heldout_v2"])
    assert [c["id"] for c in report["cases"]] == ["x07", "n14"] and report["split"] == "dev+heldout_v2"
    assert [(g["split"], g["pass"]) for g in report["groups"]] == [("dev", 1), ("heldout_v2", 1)]
