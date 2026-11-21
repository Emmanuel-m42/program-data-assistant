"""The OpenAI-compatible provider (for example DeepSeek's hosted API), with a fake HTTP client: no network, no key."""

import json

import pytest
from fastapi.testclient import TestClient

from program_data_assistant import evals, llm
from program_data_assistant.agent import Assistant
from program_data_assistant.api import create_app


class FakeResponse:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status
        self.text = json.dumps(data)

    def json(self):
        return self.data


class FakeHttp:
    """Replays chat completion responses and records each request body."""

    def __init__(self, responses):
        self.responses, self.bodies, self.urls = list(responses), [], []

    def post(self, url, json):
        self.urls.append(url)
        self.bodies.append(json)
        return self.responses.pop(0)


def completion(content="", tool_calls=None, reasoning="", usage=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    if reasoning:
        msg["reasoning_content"] = reasoning
    return FakeResponse({"choices": [{"message": msg, "finish_reason": "tool_calls" if tool_calls else "stop"}],
                         "usage": usage or {"prompt_tokens": 100, "completion_tokens": 20,
                                            "completion_tokens_details": {"reasoning_tokens": 5}}})


def call(name, args, id="call_1"):
    return [{"id": id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("PDA_PROVIDER", "openai_compat")
    monkeypatch.setenv("PDA_OPENAI_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("PDA_OPENAI_MODEL", "test-model")
    monkeypatch.setenv("PDA_OPENAI_API_KEY_ENV", "TEST_COMPAT_KEY")
    monkeypatch.setenv("TEST_COMPAT_KEY", "not-a-real-key")


def test_selectable_by_config_and_key_read_from_the_named_variable(env, monkeypatch):
    p = llm.get_provider()
    assert isinstance(p, llm.OpenAICompatProvider) and p.model == "test-model"
    assert p.client.headers["authorization"] == "Bearer not-a-real-key"
    monkeypatch.delenv("TEST_COMPAT_KEY")
    with pytest.raises(ValueError, match="TEST_COMPAT_KEY is not set"):
        llm.get_provider()


def test_ask_through_the_api_with_tool_calls_and_usage(env):
    http = FakeHttp([
        completion(tool_calls=call("get_view", {"view": "v_cost_per_door"}), reasoning="look at the view"),
        completion("Eastgate costs the most per door at $2.07 [table:v_cost_per_door]."),
    ])
    p = llm.OpenAICompatProvider(client=http)
    body = TestClient(create_app(Assistant(p))).post("/ask", json={"question": "Which office costs the most per door?"}).json()
    assert body["model"] == "openai_compat/test-model" and body["refused"] is False
    assert body["tool_calls"][0]["name"] == "get_view" and body["sources"][0]["table"] == "v_cost_per_door"
    first, second = http.bodies
    assert http.urls[0] == "https://api.example.test/chat/completions"
    assert first["model"] == "test-model" and first["temperature"] == 0
    assert {t["function"]["name"] for t in first["tools"]} == {"get_view", "query_program_data", "search_documents"}
    asst, tool = second["messages"][-2], second["messages"][-1]
    assert asst["tool_calls"][0]["function"] == {"name": "get_view", "arguments": json.dumps({"view": "v_cost_per_door"})}
    assert asst["reasoning_content"] == "look at the view"  # sent back within the tool-calling turn
    assert tool["role"] == "tool" and tool["tool_call_id"] == "call_1" and "Eastgate" in tool["content"]
    assert "look at the view" not in body["answer"]
    assert p.usage == {"prompt_tokens": 200, "completion_tokens": 40, "completion_tokens_details.reasoning_tokens": 10}


def test_reasoning_goes_back_on_turns_without_tool_calls_too(env):
    """An agent nudge adds an assistant turn with no tool call; its reasoning must still be sent back."""
    http = FakeHttp([
        completion(tool_calls=call("query_program_data", {"sql": "SELECT no_such FROM offices"}), reasoning="r1"),
        completion("I can't confirm that from the program data or documents.", reasoning="r2"),
        completion(tool_calls=call("get_view", {"view": "v_office_pace"}, id="call_2"), reasoning="r3"),
        completion("Eastgate misses goal [table:v_office_pace].", reasoning="r4"),
    ])
    p = llm.OpenAICompatProvider(client=http)
    Assistant(p).ask("Which office misses goal?")
    after_nudge = http.bodies[2]["messages"]
    assistant_turns = [m for m in after_nudge if m["role"] == "assistant"]
    assert [m.get("reasoning_content") for m in assistant_turns] == ["r1", "r2"]
    assert "tool_calls" not in assistant_turns[1]


def test_reasoning_can_be_left_out(env, monkeypatch):
    monkeypatch.setenv("PDA_OPENAI_SEND_REASONING", "0")
    p = llm.OpenAICompatProvider(client=FakeHttp([]))
    msgs = p.to_messages([{"role": "assistant", "content": "", "reasoning": "r",
                           "tool_calls": [{"id": "c", "name": "get_view", "args": {}}]}])
    assert "reasoning_content" not in msgs[0]


def test_api_errors_never_include_the_key(env):
    p = llm.OpenAICompatProvider(client=FakeHttp([FakeResponse({"error": "bad request"}, status=400)]))
    with pytest.raises(RuntimeError) as e:
        p.chat([{"role": "user", "content": "q"}], None)
    assert "400" in str(e.value) and "not-a-real-key" not in str(e.value)


def test_eval_runner_records_usage(env, monkeypatch, tmp_path):
    http = FakeHttp([
        completion(tool_calls=call("search_documents", {"query": "flash knocking rule"})),
        completion("Flash knocking is 10 or more consecutive knocks under 30 seconds apart [doc:qc-rules#flash-knocking]."),
    ])
    p = llm.OpenAICompatProvider(client=http)
    monkeypatch.setattr(evals, "get_provider", lambda name=None, model=None: p)
    report = evals.run("compat-mock", "openai_compat", None, ["x04"], tmp_path)
    assert report["model"] == "openai_compat/test-model" and report["cases"][0]["scores"]["pass"] == 1.0
    assert report["api_usage"]["prompt_tokens"] == 200 and report["api_calls"] == 2
