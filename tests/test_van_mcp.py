"""The VAN tools, against the real `ngpvan-mcp --demo` subprocess over stdio (fictional data, no network)."""

import json
import re

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("ngpvan_mcp")  # `uv sync --extra van`

from program_data_assistant import prompts  # noqa: E402
from program_data_assistant.agent import Assistant  # noqa: E402
from program_data_assistant.api import create_app  # noqa: E402
from program_data_assistant.llm import Reply, ToolCall  # noqa: E402
from program_data_assistant.tools import TOOL_SPECS, Toolbox  # noqa: E402
from program_data_assistant.van_mcp import VanMcp, _ngpvan_command  # noqa: E402

# Emails, phone numbers, street addresses and birth-date or contact fields must never come back.
PII = re.compile(r"@|\b\d{3}[ .-]?\d{3}[ .-]?\d{4}\b|\(\d{3}\)|\b\d{1,5} [A-Z][a-z]+ (St|Ave|Rd)\b"
                 r"|dateOfBirth|date_of_birth|birth|phoneNumber|addressLine|\"email\"", re.IGNORECASE)


@pytest.fixture(scope="module")
def van():
    v = VanMcp(_ngpvan_command()).start()
    yield v
    v.close()


class Recorder:
    """A scripted model that also records the tools and system prompt it was offered."""

    name, model = "scripted", "test"

    def __init__(self, replies):
        self.replies = list(replies)
        self.tools_seen = []
        self.systems = []

    def chat(self, messages, tools, format=None):
        self.tools_seen.append([t["name"] for t in tools or []])
        self.systems.append(messages[0]["content"])
        return self.replies.pop(0)


def test_read_tools_are_exposed_with_a_prefix_and_the_write_tool_never(van):
    names = sorted(van.tools)
    assert names and all(n.startswith("van_") for n in names)
    assert "van_turf_door_counts" in names and "van_event_signups_summary" in names
    assert not any("apply_canvass_response" in n for n in names)
    spec = next(s for s in van.specs() if s["name"] == "van_turf_door_counts")
    assert spec["description"].startswith("VAN (ngpvan-mcp):") and spec["parameters"]["type"] == "object"


def test_write_tool_stays_hidden_even_when_the_server_turns_it_on(tmp_path):
    cfg = tmp_path / "writes.toml"
    cfg.write_text(f'[writes]\napply_canvass_response = true\n\n[audit]\npath = "{tmp_path / "audit.jsonl"}"\n')
    v = VanMcp(_ngpvan_command() + ["--config", str(cfg)], audit_path=tmp_path / "audit.jsonl").start()
    try:
        assert v.tools and not any("apply" in n for n in v.tools)
        assert v.call("van_apply_canvass_response", {"van_id": 1}).ok is False
    finally:
        v.close()


def test_a_call_returns_the_masked_result_and_its_audit_line(van):
    call = van.call("van_event_signups_summary", {"event_id": 3001})
    assert call.ok and call.tool == "event_signups_summary"
    assert not PII.search(call.text), "contact details must never reach this app"
    assert call.audit["tool"] == "event_signups_summary" and call.audit["status"] == "ok"
    assert call.audit["args"]["event_id"] == 3001
    data = json.loads(call.text)
    roster = [p for shift in data.get("shifts", []) for p in shift.get("roster", [])]
    assert roster and all(re.fullmatch(r"\S+ [A-Z]\.", p["name"]) for p in roster)  # names shortened by the server


def test_errors_come_back_with_their_audit_line(van):
    call = van.call("van_get_person", {"van_id": 1})
    assert call.ok is False and "no record" in call.text
    assert call.audit["status"] == "error" and call.audit["error_kind"] == "not_found"


def test_without_van_the_tools_and_prompt_are_unchanged():
    tb = Toolbox()
    assert tb.specs() == TOOL_SPECS
    assert "VAN tools" not in prompts.system_prompt()


def test_ask_through_the_api_with_a_van_tool(van):
    provider = Recorder([
        Reply("", [ToolCall("c1", "van_turf_door_counts", {"folder_name": "Northside"})]),
        Reply("The Northside saved-list turfs in VAN hold 437 doors [van:turf_door_counts]. "
              "These are VAN walk-list doors, not precinct turf."),
    ])
    body = TestClient(create_app(Assistant(provider, Toolbox(van=van)))).post(
        "/ask", json={"question": "How many doors are on the Northside saved-list turfs in VAN?"}).json()
    assert "van_turf_door_counts" in provider.tools_seen[0] and "get_view" in provider.tools_seen[0]
    assert "VAN tools (van_*)" in provider.systems[0]
    assert body["refused"] is False and body["tool_calls"][0]["name"] == "van_turf_door_counts"
    src = body["sources"][0]
    assert src["type"] == "mcp" and src["server"] == "ngpvan-mcp" and src["tool"] == "turf_door_counts"
    assert src["args"] == {"folder_name": "Northside"}
    assert '"doors": 437' in src["result"] and not PII.search(src["result"])
    assert src["audit"]["tool"] == "turf_door_counts" and src["audit"]["status"] == "ok"
    assert body["citations"] == [{"type": "van", "id": "turf_door_counts"}]


def test_health_lists_the_van_tools(van):
    body = TestClient(create_app(Assistant(Recorder([]), Toolbox(van=van)))).get("/health").json()
    assert body["van"]["server"] == "ngpvan-mcp" and "van_list_events" in body["van"]["tools"]


def test_van_turns_on_from_the_environment(monkeypatch):
    monkeypatch.setenv("PDA_VAN_MCP", "demo")
    v = VanMcp.from_env()
    try:
        assert v is not None and "van_list_folders" in v.tools
    finally:
        v.close()
    monkeypatch.delenv("PDA_VAN_MCP")
    assert VanMcp.from_env() is None
