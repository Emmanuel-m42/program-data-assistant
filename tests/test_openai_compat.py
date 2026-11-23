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
    # Names an office, so the program-total check doesn't add a step to this wiring test.
    body = TestClient(create_app(Assistant(p))).post(
        "/ask", json={"question": "Does Eastgate cost the most per door?"}).json()
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


def test_thinking_switch_effort_and_output_cap_are_sent(env, monkeypatch):
    monkeypatch.setenv("PDA_OPENAI_THINKING", "enabled")
    monkeypatch.setenv("PDA_OPENAI_REASONING_EFFORT", "high")
    monkeypatch.setenv("PDA_OPENAI_MAX_TOKENS", "8000")
    http = FakeHttp([completion("ok")])
    llm.OpenAICompatProvider(client=http).chat([{"role": "user", "content": "q"}], None)
    body = http.bodies[0]
    assert body["thinking"] == {"type": "enabled"} and body["reasoning_effort"] == "high" and body["max_tokens"] == 8000
    monkeypatch.setenv("PDA_OPENAI_THINKING", "disabled")
    monkeypatch.delenv("PDA_OPENAI_REASONING_EFFORT")
    http = FakeHttp([completion("ok")])
    llm.OpenAICompatProvider(client=http).chat([{"role": "user", "content": "q"}], None)
    assert http.bodies[0]["thinking"] == {"type": "disabled"} and "reasoning_effort" not in http.bodies[0]


def test_reasoning_goes_back_on_guardrail_rewrite_turns_too(env):
    # DeepSeek's thinking mode with tools needs reasoning_content on every earlier assistant turn, including the
    # answer the citation check sends back for a rewrite (no tool calls on that turn).
    http = FakeHttp([
        completion(tool_calls=call("get_view", {"view": "v_cost_per_door"}), reasoning="look first"),
        completion("Eastgate costs the most per door at $2.07 [table:v_made_up].", reasoning="draft"),
        completion("Eastgate costs the most per door at $2.07 [table:v_cost_per_door].", reasoning="fixed"),
    ])
    Assistant(llm.OpenAICompatProvider(client=http)).ask("Which office costs the most per door?")
    rewrite = http.bodies[2]["messages"]
    drafts = [m for m in rewrite if m["role"] == "assistant" and not m.get("tool_calls")]
    assert drafts and drafts[-1]["reasoning_content"] == "draft"
    assert [m for m in rewrite if m.get("tool_calls")][0]["reasoning_content"] == "look first"


def test_strict_mode_makes_every_property_required_and_drops_none(env, monkeypatch):
    from program_data_assistant.tools import TOOL_SPECS

    monkeypatch.setenv("PDA_OPENAI_STRICT", "1")
    http = FakeHttp([completion(tool_calls=call("get_view", {"view": "v_office_pace", "office": "none", "week_start": "none"}))])
    reply = llm.OpenAICompatProvider(client=http).chat([{"role": "user", "content": "q"}], TOOL_SPECS)
    assert reply.tool_calls[0].args == {"view": "v_office_pace"}  # "none" means left out
    for t in http.bodies[0]["tools"]:
        f = t["function"]
        params = f["parameters"]
        assert f["strict"] is True and params["additionalProperties"] is False
        assert sorted(params["required"]) == sorted(params["properties"])
    gv = next(t["function"]["parameters"]["properties"] for t in http.bodies[0]["tools"] if t["function"]["name"] == "get_view")
    assert gv["office"]["enum"][-1] == "none" and "none" not in gv["view"]["enum"]  # view stays required
