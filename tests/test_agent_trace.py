"""An outside agent as the model: the tool CLI, then scoring from its trace and answers. No model runs here."""

import json
import sys

from program_data_assistant import agent_trace, evals


def call(capsys, trace, case, tool, args):
    assert agent_trace.tool_main([tool, json.dumps(args), "--case", case, "--trace", str(trace)]) == 0
    return capsys.readouterr().out


def test_prompt_is_the_apps_prompt_and_tools(capsys):
    from program_data_assistant import prompts

    assert agent_trace.tool_main(["prompt"]) == 0
    out = capsys.readouterr().out
    assert prompts.system_prompt() in out and '"query_program_data"' in out and '"search_documents"' in out


def test_cli_runs_the_real_tools_with_their_guards(tmp_path, capsys):
    trace = tmp_path / "t.jsonl"
    assert "v_office_pace" in call(capsys, trace, "q01", "get_view", {"view": "v_office_pace"})
    assert "Query rejected" in call(capsys, trace, "q01", "query_program_data", {"sql": "DELETE FROM knocks"})
    # The repeated-query check holds across CLI calls within one case, and not across cases.
    assert "already ran this exact query" in call(capsys, trace, "q01", "query_program_data", {"sql": "DELETE FROM knocks"})
    assert "Query rejected" in call(capsys, trace, "q02", "query_program_data", {"sql": "DELETE FROM knocks"})
    lines = [json.loads(x) for x in trace.read_text().splitlines()]
    assert [x["case"] for x in lines] == ["q01", "q01", "q01", "q02"] and lines[0]["ok"] and not lines[1]["ok"]
    assert agent_trace.tool_main(["get_view", "{}", "--case", "zz", "--trace", str(trace)]) == 2


def q01_run(tmp_path, capsys, name, answer):
    trace = tmp_path / f"{name}.jsonl"
    out = call(capsys, trace, "q01", "get_view", {"view": "v_office_pace"})
    total_row = next(line for line in out.splitlines() if line.startswith("All offices"))
    cols = [c.strip() for c in total_row.split("|")]
    projected, gap = cols[7], cols[8].lstrip("-")
    answers = {"q01": answer.format(projected=projected, gap=gap)}
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(answers))
    return str(trace), str(path)


GOOD = ("No, we're not on pace. If nothing changes we land at {projected} doors by election day, {gap} short of goal "
        "[table:v_office_pace].")


def test_scores_from_traces_with_pass_hat_k(tmp_path, capsys):
    t1, a1 = q01_run(tmp_path, capsys, "r1", GOOD)
    t2, a2 = q01_run(tmp_path, capsys, "r2", "We land at about 99999 doors [table:v_office_pace].")
    report = agent_trace.run("x", [t1, t2], [a1, a2], tmp_path / "rep", only=["q01"])
    row = report["cases"][0]
    first, second = row["answer"], row["repeats"][0]
    assert first["citations_valid"] and not first["refused"]
    assert row["repeats"][0]["scores"]["pass"] == 0.0 and second["answer"]["answer"]
    assert row["scores"]["pass"] == 0.5 and row["scores"]["pass_all"] == 0.0
    assert report["model_label"] == agent_trace.AGENT_LABEL and report["repeat"] == 2
    md = (tmp_path / "rep" / "x.md").read_text()
    assert "not the app's own agent loop" in md and "in-loop guardrail rewrites" in md


def test_first_run_passes_on_its_own(tmp_path, capsys):
    t1, a1 = q01_run(tmp_path, capsys, "r1", GOOD)
    report = agent_trace.run("x", [t1], [a1], tmp_path / "rep", only=["q01"])
    assert report["cases"][0]["scores"]["pass"] == 1.0, report["cases"][0]["facts"]


def test_tampered_trace_and_missing_answer_fail(tmp_path, capsys):
    t1, a1 = q01_run(tmp_path, capsys, "r1", GOOD)
    entry = json.loads(open(t1).read())
    entry["result"] = entry["result"].replace("All offices", "All offices ", 1)
    open(t1, "w").write(json.dumps(entry) + "\n")
    report = agent_trace.run("x", [t1], [a1], tmp_path / "rep", only=["q01", "q02"], split=None)
    assert [r["id"] for r in report["cases"]] == ["q01", "q02"]
    assert all(r["scores"]["pass"] == 0.0 for r in report["cases"])
    assert any("replay mismatch" in p for p in report["integrity_problems"])
    assert any("no answer" in p for p in report["integrity_problems"])


def test_evals_entry_point_dispatches(tmp_path, capsys, monkeypatch):
    t1, a1 = q01_run(tmp_path, capsys, "r1", GOOD)
    out = tmp_path / "rep"
    monkeypatch.setattr(sys, "argv", ["evals", "--provider", "agent-trace", "--trace", t1, "--answers", a1,
                                      "--only", "q01", "--out", str(out), "--label", "cli"])
    evals.main()
    assert json.loads((out / "cli.json").read_text())["summary"]["pass"] == 1.0
