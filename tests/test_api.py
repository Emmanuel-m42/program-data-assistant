from conftest import ScriptedProvider, search_call, sql_call
from fastapi.testclient import TestClient

from program_data_assistant.agent import Assistant
from program_data_assistant.api import create_app
from program_data_assistant.llm import Reply


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
    c, provider = client([sql_call("DROP TABLE knocks"), Reply("I can't confirm that from the program data or documents.")])
    body = c.post("/ask", json={"question": "Delete the knocks"}).json()
    assert body["tool_calls"][0]["ok"] is False
    assert provider.seen[1]["content"].startswith("Query rejected")
    assert body["refused"] is True


def test_refusal_flag():
    c, _ = client([Reply("I can't confirm that from the program data or documents. There is no turnout data.")])
    body = c.post("/ask", json={"question": "What will turnout be?"}).json()
    assert body["refused"] is True and body["tool_calls"] == []


def test_step_limit_forces_an_answer():
    loop = [sql_call("SELECT 1 FROM offices") for _ in range(6)]
    c, _ = client(loop + [Reply("Three offices [table:offices].")])
    body = c.post("/ask", json={"question": "How many offices?"}).json()
    assert len(body["tool_calls"]) == 6
    assert body["answer"] == "Three offices [table:offices]."


def test_question_validation():
    c, _ = client([])
    assert c.post("/ask", json={"question": ""}).status_code == 422
    assert c.post("/ask", json={}).status_code == 422
