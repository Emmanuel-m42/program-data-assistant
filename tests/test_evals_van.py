"""The eval harness for the MCP version: VAN cases, ground truth from the real ngpvan-mcp --demo, scripted model."""

import json

import pytest

pytest.importorskip("ngpvan_mcp")  # `uv sync --extra van`

from program_data_assistant import db, evals  # noqa: E402
from program_data_assistant.llm import Reply, ToolCall  # noqa: E402

VAN_CASES = db.REPO / "evals" / "cases_mcp_van.yaml"


class Script:
    name, model = "scripted", "test"

    def __init__(self, replies):
        self.replies = list(replies)

    def chat(self, messages, tools, format=None):
        return self.replies.pop(0)


def test_van_cases_are_well_formed_and_split_four_four():
    cases, _ = evals.load_cases(VAN_CASES)
    assert len(cases) == 8 and len({c["id"] for c in cases}) == 8
    assert sorted(c["split"] for c in cases) == ["dev"] * 4 + ["test"] * 4
    for c in cases:
        assert c.get("should_refuse") or c.get("facts"), c["id"]
        assert c.get("should_refuse") or any(t.startswith("van_") for t in c["expected_tools"]), c["id"]


def test_ground_truth_comes_from_the_server_not_the_model():
    cases, _ = evals.load_cases(VAN_CASES)
    van = evals.start_van("demo")
    try:
        with db.connect_admin() as conn:
            truth = evals.compute_truth(conn, cases, van)
    finally:
        van.close()
    assert truth[("v01", "Northside saved-list doors in VAN")] == 437
    assert truth[("v01", "Northside untouched precinct doors")] > 437  # precinct turf is a different, larger count
    roster = truth[("v02", "morning shift roster")]
    assert isinstance(roster, list) and roster and all(n.endswith(".") for n in roster)  # masked names
    assert isinstance(truth[("v05", "folder with the most doors")], str)
    assert truth[("v08", "total contact attempts")] == 0


def test_van_cases_need_the_van_tools(tmp_path):
    with pytest.raises(ValueError, match="--van demo"):
        evals.run("mcp-van-x", None, None, ["v03"], tmp_path, cases_path=VAN_CASES)


def test_a_van_case_scores_through_the_runner(monkeypatch, tmp_path):
    monkeypatch.setattr(evals, "get_provider", lambda name=None, model=None: Script([
        Reply("", [ToolCall("c1", "van_list_activist_codes", {})]),
        Reply("VAN has these active activist codes: Volunteer, Phone Banker, Canvasser, Event Host and Renter "
              "[van:list_activist_codes]."),
    ]))
    report = evals.run("mcp-van-cases-scripted", None, None, ["v03"], tmp_path, cases_path=VAN_CASES, van_mode="demo")
    case = report["cases"][0]
    assert case["scores"]["pass"] == 1.0, case["facts"]
    assert report["cases_file"] == "evals/cases_mcp_van.yaml"
    assert "van_list_activist_codes" in report["tools"] and "get_view" in report["tools"]
    src = case["answer"]["sources"][0]
    assert src["type"] == "mcp" and src["audit"]["tool"] == "list_activist_codes"
    saved = json.loads((tmp_path / "mcp-van-cases-scripted.json").read_text())
    assert saved["summary"]["pass"] == 1.0


def test_original_cases_rerun_with_the_van_tools_present(monkeypatch, tmp_path):
    monkeypatch.setattr(evals, "get_provider", lambda name=None, model=None: Script([
        Reply("", [ToolCall("c1", "search_documents", {"query": "flash knocking rule"})]),
        Reply("Flash knocking is 10 or more consecutive knocks under 30 seconds apart [doc:qc-rules#flash-knocking]."),
    ]))
    report = evals.run("mcp-van-original-scripted", None, None, ["x04"], tmp_path, van_mode="demo")
    assert report["cases_file"] == "evals/cases.yaml"
    assert any(t.startswith("van_") for t in report["tools"])
    assert report["cases"][0]["scores"]["pass"] == 1.0


def test_list_facts_need_every_item():
    fact = {"name": "codes"}
    assert evals.fact_matches(fact, ["Volunteer", "Canvasser"], "Volunteer and canvasser codes", {})
    assert not evals.fact_matches(fact, ["Volunteer", "Canvasser"], "Only Volunteer", {})
    assert evals.fact_matches(fact, "Northside Turfs", "the northside turfs folder", {})
