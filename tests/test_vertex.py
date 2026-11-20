"""Claude on Vertex AI: configuration only. Building the client makes no network call; no request is sent."""

import pytest

from program_data_assistant import llm


def test_vertex_is_selectable_by_config(monkeypatch):
    pytest.importorskip("google.auth")  # `uv sync --extra vertex`
    monkeypatch.setenv("PDA_PROVIDER", "vertex")
    monkeypatch.setenv("PDA_VERTEX_PROJECT", "riverbend-demo")
    monkeypatch.setenv("PDA_VERTEX_REGION", "us-east5")
    monkeypatch.setenv("PDA_VERTEX_MODEL", "claude-vertex-test-model")
    p = llm.get_provider()
    assert isinstance(p, llm.VertexProvider)
    assert (p.name, p.model) == ("vertex", "claude-vertex-test-model")
    assert (p.client.project_id, p.client.region) == ("riverbend-demo", "us-east5")


def test_vertex_uses_the_same_messages_translation():
    calls = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type("R", (), {"content": []})()

    p = llm.VertexProvider("claude-vertex-test-model", client=type("C", (), {"messages": FakeMessages()})())
    p.chat([{"role": "system", "content": "s"}, {"role": "user", "content": "q"}], tools=[])
    assert calls[0]["model"] == "claude-vertex-test-model"
    assert calls[0]["system"] == "s"
