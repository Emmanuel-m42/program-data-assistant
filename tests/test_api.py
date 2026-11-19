from conftest import ScriptedProvider, search_call, sql_call
from fastapi.testclient import TestClient

from program_data_assistant.agent import RETRY_NUDGE, Assistant
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
    assert [r[0] for r in rows[0]["rows"]][:3] == ["All offices", "Eastgate", "Harbor"]
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


def test_refusal_flag():
    c, _ = client([Reply("I can't confirm that from the program data or documents. There is no turnout data.")])
    body = c.post("/ask", json={"question": "What will turnout be?"}).json()
    assert body["refused"] is True and body["tool_calls"] == []


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
    assert len(Toolbox().run("get_view", {"view": "v_office_pace"}).rows) == 4


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


def test_question_validation():
    c, _ = client([])
    assert c.post("/ask", json={"question": ""}).status_code == 422
    assert c.post("/ask", json={}).status_code == 422
