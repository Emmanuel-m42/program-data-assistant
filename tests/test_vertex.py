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


class FakeVertexModule:
    """Stands in for the anthropic package: records each AnthropicVertex client built and what it sent."""

    def __init__(self):
        self.clients = []

    def AnthropicVertex(self, **kwargs):  # noqa: N802 - mirrors the SDK's class name
        sent = []

        class Messages:
            def create(self, **req):
                sent.append(req)
                return type("R", (), {"content": []})()

        client = type("Client", (), {"kwargs": kwargs, "sent": sent, "messages": Messages()})()
        self.clients.append(client)
        return client


def token_provider(monkeypatch, path):
    fake = FakeVertexModule()
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake)
    monkeypatch.setenv("PDA_VERTEX_PROJECT", "riverbend-demo")
    monkeypatch.setenv("PDA_VERTEX_REGION", "global")
    monkeypatch.setenv("PDA_VERTEX_MODEL", "claude-vertex-test-model")
    monkeypatch.setenv("PDA_VERTEX_ACCESS_TOKEN_FILE", str(path))
    return fake


def ask(p):
    p.chat([{"role": "user", "content": "q"}], tools=[])


def test_token_file_is_passed_to_the_client(monkeypatch, tmp_path):
    tok = tmp_path / "token"
    tok.write_text("tok-one\n")
    fake = token_provider(monkeypatch, tok)
    p = llm.get_provider("vertex")
    assert fake.clients[0].kwargs == {"project_id": "riverbend-demo", "region": "global", "access_token": "tok-one"}
    ask(p)
    assert len(fake.clients) == 1 and len(fake.clients[0].sent) == 1  # unchanged file: same client


def test_token_change_is_picked_up_mid_run(monkeypatch, tmp_path):
    import os

    tok = tmp_path / "token"
    tok.write_text("tok-one")
    fake = token_provider(monkeypatch, tok)
    p = llm.get_provider("vertex")
    ask(p)
    tok.write_text("tok-two")
    st = tok.stat()
    os.utime(tok, (st.st_atime, st.st_mtime + 5))  # the keeper rewrote it
    ask(p)
    assert [c.kwargs["access_token"] for c in fake.clients] == ["tok-one", "tok-two"]
    assert len(fake.clients[1].sent) == 1 and p.client is fake.clients[1]


def test_missing_or_empty_token_file_is_a_clear_error_without_the_token(monkeypatch, tmp_path):
    tok = tmp_path / "token"
    token_provider(monkeypatch, tok)
    with pytest.raises(RuntimeError, match="can't be read"):
        llm.get_provider("vertex")
    tok.write_text("  \n")
    with pytest.raises(RuntimeError, match="is empty"):
        llm.get_provider("vertex")
    tok.write_text("secret-token-value")
    p = llm.get_provider("vertex")
    tok.unlink()
    with pytest.raises(RuntimeError) as e:
        ask(p)
    assert "secret-token-value" not in str(e.value)
