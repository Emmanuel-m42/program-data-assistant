import json

from conftest import ScriptedProvider, search_call, sql_call
from fastapi.testclient import TestClient

from program_data_assistant.agent import EMPTY_NUDGE, LOOK_NUDGE, RETRY_NUDGE, Assistant
from program_data_assistant.api import create_app
from program_data_assistant.llm import Reply, ToolCall
from program_data_assistant.tools import Toolbox


def client(replies):
    provider = ScriptedProvider(replies)
    return TestClient(create_app(Assistant(provider))), provider


def test_health():
    c, _ = client([])
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok", "model": "scripted/test"}


def test_ask_runs_tools_and_returns_sources():
    c, provider = client([
        sql_call("SELECT office, projected_vs_goal FROM v_office_pace WHERE projected_vs_goal < 0 ORDER BY projected_vs_goal"),
        search_call("how is the projection calculated"),
        Reply("Eastgate and Harbor will miss goal [table:v_office_pace], using the 7-day projection "
              "[doc:program-plan#pace-and-projection]."),
    ])
    r = c.post("/ask", json={"question": "Which offices will miss their goal, and by how much?"})
    assert r.status_code == 200
    body = r.json()
    assert body["refused"] is False
    assert [t["name"] for t in body["tool_calls"]] == ["query_program_data", "search_documents"]
    rows = [s for s in body["sources"] if s["type"] == "rows"]
    assert rows[0]["table"] == "v_office_pace"
    assert [r[0] for r in rows[0]["rows"]] == ["Eastgate", "Harbor"]
    assert [s["doc"] for s in body["sources"] if s["type"] == "passage"] == ["program-plan#pace-and-projection"]
    # the model saw the real query result
    assert "Eastgate" in provider.seen[1]["content"]


def test_rejected_sql_goes_back_to_the_model():
    refusal = Reply("I can't confirm that from the program data or documents.")
    c, provider = client([sql_call("DROP TABLE knocks"), refusal, refusal])
    body = c.post("/ask", json={"question": "Delete the knocks"}).json()
    assert body["tool_calls"][0]["ok"] is False
    assert provider.seen[1]["content"].startswith("Query rejected")
    assert provider.seen[2]["content"] == RETRY_NUDGE  # one retry nudge after a failed query, then it may refuse
    assert body["refused"] is True


def test_bad_column_gets_the_real_columns_and_a_retry():
    c, provider = client([
        sql_call("SELECT office, shifts_needed FROM v_office_pace"),
        sql_call("SELECT office, extra_shifts_per_day_needed FROM v_office_pace"),
        Reply("Eastgate needs the most extra shifts [table:v_office_pace]."),
    ])
    body = c.post("/ask", json={"question": "How many more shifts a day does each office need?"}).json()
    assert "Columns of v_office_pace:" in provider.seen[1]["content"]
    assert "extra_shifts_per_day_needed" in provider.seen[1]["content"]
    assert [t["ok"] for t in body["tool_calls"]] == [False, True]


def test_refusal_flag_after_looking_first():
    refusal = Reply("I can't confirm that from the program data or documents. There is no turnout data.")
    c, provider = client([refusal, search_call("turnout projection"), refusal])
    body = c.post("/ask", json={"question": "What will turnout be?"}).json()
    assert provider.seen[1]["content"] == LOOK_NUDGE
    assert body["refused"] is True and [t["name"] for t in body["tool_calls"]] == ["search_documents"]


def test_an_empty_reply_gets_one_retry():
    c, provider = client([sql_call("SELECT office, doors_untouched FROM v_office_pace"), Reply(""),
                          Reply("Harbor has 8,096 doors no one has knocked [table:v_office_pace].")])
    body = c.post("/ask", json={"question": "How many doors are left in Harbor?"}).json()
    assert provider.seen[-1]["content"] == EMPTY_NUDGE
    assert body["refused"] is False and "8,096" in body["answer"]


def test_missing_citations_get_one_rewrite_with_the_valid_ids():
    c, provider = client([
        sql_call("SELECT office, cost_per_door FROM v_cost_per_door"),
        Reply("Eastgate is most expensive at $2.07 per door."),
        Reply("Eastgate is most expensive at $2.07 per door [table:v_cost_per_door]."),
    ])
    body = c.post("/ask", json={"question": "Which office costs the most per door?"}).json()
    assert "[table:v_cost_per_door]" in provider.seen[2]["content"]
    assert body["answer"].endswith("[table:v_cost_per_door].")


def test_step_limit_forces_an_answer():
    loop = [sql_call(f"SELECT {i} FROM offices") for i in range(7)]
    c, _ = client(loop + [Reply("Three offices [table:offices].")])
    body = c.post("/ask", json={"question": "How many offices?"}).json()
    assert len(body["tool_calls"]) == 7
    assert body["answer"] == "Three offices [table:offices]."


def test_made_up_numbers_get_one_revision():
    sql = "SELECT office, projected_vs_goal FROM v_office_pace WHERE office = 'Eastgate'"
    c, provider = client([
        sql_call(sql),
        Reply("Eastgate misses goal by 1,234 doors [table:v_office_pace]."),
        Reply("Eastgate misses goal by the amount shown [table:v_office_pace]."),
    ])
    body = c.post("/ask", json={"question": "Will Eastgate miss goal?"}).json()
    assert "1234" in provider.seen[2]["content"] and "do not appear" in provider.seen[2]["content"]
    assert body["answer"].startswith("Eastgate misses goal by the amount")


def test_numbers_still_made_up_after_revision_are_withheld():
    sql = "SELECT office, projected_vs_goal FROM v_office_pace WHERE office = 'Eastgate'"
    made_up = Reply("Eastgate lands at 1,234 doors, 5,678 short [table:v_office_pace].")
    c, _ = client([sql_call(sql), made_up, made_up])
    body = c.post("/ask", json={"question": "Will Eastgate miss goal?"}).json()
    assert body["refused"] is True
    assert "aren't in the query results" in body["answer"]


def test_get_view_returns_a_whole_view_or_one_office():
    c, _ = client([Reply("", [ToolCall("v1", "get_view", {"view": "v_cost_per_door", "office": "Eastgate"})]),
                   Reply("Eastgate costs the most per door [table:v_cost_per_door].")])
    body = c.post("/ask", json={"question": "Which office costs the most per door?"}).json()
    src = body["sources"][0]
    assert src["table"] == "v_cost_per_door" and [r[0] for r in src["rows"]] == ["Eastgate"]
    assert Toolbox().run("get_view", {"view": "knocks"}).ok is False
    assert len(Toolbox().run("get_view", {"view": "v_office_pace"}).rows) == 3
    total = Toolbox().run("get_view", {"view": "v_office_pace_total", "office": "Harbor"})  # office ignored on totals
    assert [r[0] for r in total.rows] == ["All offices"] and "the program total" in total.content


def test_get_view_all_offices_means_no_filter_and_week_is_ignored_where_absent():
    tb = Toolbox()
    assert len(tb.run("get_view", {"view": "v_office_pace", "office": "All offices"}).rows) == 3
    assert len(tb.run("get_view", {"view": "v_precinct_coverage", "office": "all", "week_start": "2026-10-12"}).rows) == 40
    assert len(tb.run("get_view", {"view": "v_site_options", "office": "Harbor"}).rows) == 4
    assert {r[0] for r in tb.run("get_view", {"view": "v_contact_rates", "week_start": "2026-10-12"}).rows} == {
        "Eastgate", "Harbor", "Northside"}
    assert [r[0] for r in tb.run("get_view", {"view": "v_cost_per_door", "office": "Eastgate"}).rows] == ["Eastgate"]


def test_repeated_query_is_not_rerun():
    sql = "SELECT office FROM offices"
    c, provider = client([sql_call(sql), sql_call(sql), Reply("Three offices [table:offices].")])
    body = c.post("/ask", json={"question": "List the offices"}).json()
    assert [t["result"] for t in body["tool_calls"]][1] == "repeated query"


def test_zero_rows_tells_the_model_to_widen_the_query():
    c, provider = client([sql_call("SELECT office FROM offices WHERE office = 'Nowhere'"),
                          Reply("I can't confirm that from the program data or documents."),
                          Reply("I can't confirm that from the program data or documents.")])
    c.post("/ask", json={"question": "Which offices?"})
    assert "0 rows" in provider.seen[1]["content"]


def test_citations_are_rendered_from_provenance_and_unknown_ids_dropped(monkeypatch):
    lines = {"lines": [
        {"text": "Eastgate is the most expensive office [table:made_up].", "source": "table:v_cost_per_door"},
        {"text": "- Eastgate: $2.07 per door", "source": "table:v_cost_per_door"},
        {"text": "Rates come from the payroll rules.", "source": "doc:payroll-rules#nowhere"},
    ]}
    provider = ScriptedProvider([
        sql_call("SELECT office, cost_per_door FROM v_cost_per_door"),
        Reply("Eastgate is the most expensive office.\n- Eastgate: $2.07 per door"),
        Reply(json.dumps(lines)),
    ])
    provider.supports_format = True
    monkeypatch.setenv("PDA_STRUCTURED_CITATIONS", "1")
    c = TestClient(create_app(Assistant(provider)))
    body = c.post("/ask", json={"question": "Which office costs the most per door?"}).json()
    assert body["answer"] == ("Eastgate is the most expensive office. [table:v_cost_per_door]\n"
                              "- Eastgate: $2.07 per door [table:v_cost_per_door]\n"
                              "Rates come from the payroll rules.")


def test_offices_endpoint_reads_the_views():
    c, _ = client([])
    body = c.get("/offices").json()
    assert body["as_of"] == "2026-10-18"
    by = {o["office"]: o for o in body["offices"]}
    assert list(by) == ["All offices", "Northside", "Eastgate", "Harbor"]
    assert by["Eastgate"]["pace"]["projected_vs_goal"] < 0 < by["Northside"]["pace"]["projected_vs_goal"]
    assert by["Eastgate"]["cost_per_door"] == max(o["cost_per_door"] for o in body["offices"])
    assert [w["week_start"] for w in by["Harbor"]["contact_rates"]][-1] == "2026-10-12"
    assert by["All offices"]["qc_this_week"]["flags"] == sum(by[o]["qc_this_week"]["flags"] for o in ("Northside", "Eastgate", "Harbor"))


def test_evals_and_recorded_endpoints_serve_the_demo_file():
    c, _ = client([])
    ev = c.get("/evals").json()
    assert ev["scoreboard"]["after"]["heldout"]["pass"] == 12 and ev["scoreboard"]["after"]["tuned"]["pass"] == 12
    claude, flash = ev["scoreboard"]["comparison"][:2]
    for row in (claude, flash):
        assert row["code"] == "latest" and row.get("status") is None
        assert row["groups"]["heldout_v3"]["pass"] == row["groups"]["heldout_v3"]["pass_all_runs"] == 15
    assert not any(r.get("status") == "running" for r in ev["scoreboard"]["comparison"])
    assert ev["scoreboard"]["headline"].startswith("Fresh held-out (written before the latest fixes): Claude Opus 5.5 15 of 15")
    assert len(ev["questions"]) == 19 and "answer" not in ev["questions"][0]
    q13 = next(q for q in ev["questions"] if q["id"] == "q13")
    assert q13["eval"]["after"]["pass"] == 0 and "program-wide direction" in q13["eval"]["note"]
    rec = c.get("/recorded").json()
    assert len(rec["questions"]) == 19 and "baseline" in rec["questions"][0]


def test_cors_allows_the_configured_origin():
    c, _ = client([])
    r = c.options("/ask", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_question_validation():
    c, _ = client([])
    assert c.post("/ask", json={"question": ""}).status_code == 422
    assert c.post("/ask", json={}).status_code == 422
