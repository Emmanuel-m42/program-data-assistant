"""The Claude backend, with a fake Messages client: no network, no key, no paid calls."""

import json
from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

from program_data_assistant import evals, llm
from program_data_assistant.agent import Assistant
from program_data_assistant.api import create_app


class FakeMessages:
    """Replays scripted Messages API responses and records each request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def tool_use(name, args, id="toolu_1"):
    return NS(content=[NS(type="tool_use", id=id, name=name, input=args)])


def text(t):
    return NS(content=[NS(type="text", text=t)])


def provider(responses):
    fake = FakeMessages(responses)
    return llm.AnthropicProvider("claude-test-model", client=NS(messages=fake)), fake


def test_provider_is_selectable_by_config(monkeypatch):
    monkeypatch.setenv("PDA_PROVIDER", "anthropic")
    monkeypatch.setenv("PDA_ANTHROPIC_MODEL", "claude-test-model")
    monkeypatch.setattr(llm.AnthropicProvider, "__init__",
                        lambda self, model=None, max_tokens=1500, client=None: setattr(self, "model", model or "claude-test-model"))
    p = llm.get_provider()
    assert isinstance(p, llm.AnthropicProvider) and p.model == "claude-test-model"


def test_messages_conversion_keeps_turns_alternating():
    system, out = llm.AnthropicProvider.to_messages([
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t1", "name": "get_view", "args": {"view": "v_office_pace"}}]},
        {"role": "tool", "tool_call_id": "t1", "name": "get_view", "content": "rows"},
        {"role": "user", "content": "nudge"},
    ])
    assert system == "sys"
    assert [m["role"] for m in out] == ["user", "assistant", "user"]
    assert out[1]["content"] == [{"type": "tool_use", "id": "t1", "name": "get_view", "input": {"view": "v_office_pace"}}]
    assert [b["type"] for b in out[2]["content"]] == ["tool_result", "text"]


def test_ask_through_the_api_with_claude_shows_the_model():
    p, fake = provider([
        tool_use("get_view", {"view": "v_cost_per_door"}),
        text("Eastgate costs the most per door at $2.07 [table:v_cost_per_door]."),
    ])
    body = TestClient(create_app(Assistant(p))).post("/ask", json={"question": "Which office costs the most per door?"}).json()
    assert body["model"] == "anthropic/claude-test-model"
    assert body["tool_calls"][0]["name"] == "get_view" and body["refused"] is False
    assert body["sources"][0]["table"] == "v_cost_per_door"
    first = fake.requests[0]
    assert first["model"] == "claude-test-model" and {t["name"] for t in first["tools"]} == {"get_view", "query_program_data", "search_documents"}
    # the second request carries the real tool result back as a tool_result block
    assert fake.requests[1]["messages"][-1]["content"][0]["type"] == "tool_result"
    assert "Eastgate" in fake.requests[1]["messages"][-1]["content"][0]["content"]


def test_eval_harness_scores_the_claude_backend(monkeypatch, tmp_path):
    p, _ = provider([
        tool_use("search_documents", {"query": "flash knocking rule"}),
        text("Flash knocking is 10 or more consecutive knocks under 30 seconds apart [doc:qc-rules#flash-knocking]."),
    ])
    monkeypatch.setattr(evals, "get_provider", lambda name=None, model=None: p)
    report = evals.run("claude-mock", "anthropic", None, ["x04"], tmp_path)
    assert report["model"] == "anthropic/claude-test-model"
    case = report["cases"][0]
    assert case["scores"]["pass"] == 1.0 and case["scores"]["citation"] == 1.0
    assert json.loads((tmp_path / "claude-mock.json").read_text())["summary"]["pass"] == 1.0
