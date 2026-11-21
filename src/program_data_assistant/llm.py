"""Model providers behind one small interface.

Messages use one neutral format:
  {"role": "system" | "user", "content": str}
  {"role": "assistant", "content": str, "tool_calls": [{"id", "name", "args"}]}
  {"role": "tool", "tool_call_id": str, "name": str, "content": str}
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx


THINKING_MODELS = re.compile(r"^(qwen3|deepseek-r1|gpt-oss)", re.IGNORECASE)
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class Reply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: str = ""  # a thinking model's reasoning, kept only where an API needs it sent back; never shown


class Provider(Protocol):
    name: str
    model: str

    def chat(self, messages: list[dict], tools: list[dict] | None, format: dict | None = None) -> Reply: ...


class OllamaProvider:
    """Local open model served by Ollama (default qwen2.5:7b)."""

    name = "ollama"
    supports_format = True

    def __init__(self, model: str | None = None, host: str | None = None, num_ctx: int = 8192, timeout: float = 600):
        self.model = model or os.environ.get("PDA_OLLAMA_MODEL", "qwen2.5:7b")
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        if not self.host.startswith("http"):
            self.host = "http://" + self.host
        # Ollama drops the oldest messages when a conversation outgrows the context, which can drop the question.
        self.num_ctx = int(os.environ.get("PDA_OLLAMA_CTX", num_ctx))
        # Fewer threads than cores keeps generation steady on a shared machine.
        self.num_thread = int(os.environ.get("PDA_OLLAMA_THREADS", "5"))
        # Thinking models (qwen3 and later) get think=false: answers come back without a reasoning block.
        # PDA_OLLAMA_THINK=true/false overrides; other models get no think field at all.
        flag = os.environ.get("PDA_OLLAMA_THINK", "").lower()
        if flag in ("true", "false"):
            self.think = flag == "true"
        else:
            self.think = False if THINKING_MODELS.match(self.model) else None
        self.client = httpx.Client(timeout=timeout)
        self.usage: dict[str, int] = {}  # token counts, done_reason counts and thinking length, for eval reports
        self.calls = 0

    def chat(self, messages, tools, format=None):
        out = []
        for m in messages:
            if m["role"] == "assistant":
                out.append({"role": "assistant", "content": m.get("content", ""),
                            "tool_calls": [{"function": {"name": c["name"], "arguments": c["args"]}} for c in m.get("tool_calls", [])]})
            elif m["role"] == "tool":
                out.append({"role": "tool", "content": m["content"], "tool_name": m["name"]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        body = {
            "model": self.model,
            "messages": out,
            "stream": False,
            "options": {"temperature": 0, "seed": 7, "num_ctx": self.num_ctx, "num_predict": 900,
                        "num_thread": self.num_thread},
        }
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in tools]
        if self.think is not None:
            body["think"] = self.think
        if format is not None:  # Ollama structured output: a JSON schema the reply must follow
            body["format"] = format
        r = self.client.post(f"{self.host}/api/chat", json=body)
        r.raise_for_status()
        data = r.json()
        msg = data["message"]
        raw = msg.get("content") or ""
        leaked = THINK_BLOCK.findall(raw)
        msg["content"] = THINK_BLOCK.sub("", raw).strip()  # in case thinking text leaks into content
        # Per-run counts, so a reply cut off by num_predict or num_ctx can't pass for a reasoning miss.
        self.calls += 1
        reason = data.get("done_reason") or "unknown"
        self.usage[f"done_reason.{reason}"] = self.usage.get(f"done_reason.{reason}", 0) + 1
        for k in ("prompt_eval_count", "eval_count"):
            self.usage[k] = self.usage.get(k, 0) + int(data.get(k) or 0)
        thinking = len(msg.get("thinking") or "") + sum(len(t) for t in leaked)
        self.usage["thinking_chars"] = self.usage.get("thinking_chars", 0) + thinking
        calls = []
        for i, c in enumerate(msg.get("tool_calls") or []):
            fn = c.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            calls.append(ToolCall(c.get("id") or f"call_{i}", fn.get("name", ""), args))
        return Reply(msg.get("content") or "", calls)


class AnthropicProvider:
    """Claude through the Anthropic Messages API. Needs ANTHROPIC_API_KEY and `uv sync --extra anthropic`.

    Pass `client` to use another client with the same interface (Bedrock below, or a fake in tests).
    """

    name = "anthropic"
    supports_format = False  # structured citations fall back to citations typed in the text

    def __init__(self, model: str | None = None, max_tokens: int = 1500, client=None):
        self.model = model or os.environ.get("PDA_ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self.max_tokens = max_tokens
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client

    @staticmethod
    def to_messages(messages: list[dict]) -> tuple[str, list[dict]]:
        """Neutral messages to (system, Messages API turns). Tool results and nudges share one user turn."""
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        out: list[dict] = []

        def user_block(block):
            if out and out[-1]["role"] == "user":
                if isinstance(out[-1]["content"], str):
                    out[-1]["content"] = [{"type": "text", "text": out[-1]["content"]}]
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})

        for m in messages:
            if m["role"] == "user":
                user_block({"type": "text", "text": m["content"]})
            elif m["role"] == "assistant":
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                blocks += [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]} for c in m.get("tool_calls", [])]
                if blocks:
                    out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool":
                user_block({"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]})
        return system, out

    def chat(self, messages, tools, format=None):
        system, out = self.to_messages(messages)
        kwargs = {}
        if tools:
            kwargs["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
        resp = self.client.messages.create(model=self.model, max_tokens=self.max_tokens, system=system, messages=out, **kwargs)
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return Reply(text, calls)


class VertexProvider(AnthropicProvider):
    """Claude on Google Vertex AI. Signs in as the runtime's own Google identity (on Cloud Run, its
    service account with roles/aiplatform.user), so there is no API key. Needs `uv sync --extra vertex`.

    PDA_VERTEX_PROJECT and PDA_VERTEX_REGION pick the project and region; PDA_VERTEX_MODEL the model ID
    as Vertex names it.
    """

    name = "vertex"

    def __init__(self, model: str | None = None, max_tokens: int = 1500, client=None):
        # PDA_VERTEX_ACCESS_TOKEN_FILE: a file holding a short-lived access token that something else keeps
        # fresh. It is read again whenever the file changes, and the token is never logged.
        self.token_file = os.environ.get("PDA_VERTEX_ACCESS_TOKEN_FILE") if client is None else None
        self._token_mtime: float | None = None
        if client is None:
            client = self._client_from_token_file() if self.token_file else self._make_client(None)
        super().__init__(model or os.environ.get("PDA_VERTEX_MODEL"), max_tokens, client)

    @staticmethod
    def _make_client(access_token: str | None):
        from anthropic import AnthropicVertex

        kwargs = {"access_token": access_token} if access_token else {}
        return AnthropicVertex(project_id=os.environ.get("PDA_VERTEX_PROJECT"),
                               region=os.environ.get("PDA_VERTEX_REGION", "global"), **kwargs)

    def _client_from_token_file(self):
        path = Path(self.token_file)
        try:
            mtime = path.stat().st_mtime
            token = path.read_text().strip()
        except OSError as e:
            raise RuntimeError(f"PDA_VERTEX_ACCESS_TOKEN_FILE {path} can't be read ({type(e).__name__})") from None
        if not token:
            raise RuntimeError(f"PDA_VERTEX_ACCESS_TOKEN_FILE {path} is empty")
        self._token_mtime = mtime
        return self._make_client(token)

    def _refresh_if_token_changed(self):
        if not self.token_file:
            return
        try:
            mtime = Path(self.token_file).stat().st_mtime
        except OSError as e:
            raise RuntimeError(f"PDA_VERTEX_ACCESS_TOKEN_FILE {self.token_file} can't be read ({type(e).__name__})") from None
        if mtime != self._token_mtime:
            self.client = self._client_from_token_file()

    def chat(self, messages, tools, format=None):
        self._refresh_if_token_changed()  # cheap: one stat per request
        return super().chat(messages, tools, format)


STRICT_NONE = "none"


def strict_spec(tool: dict) -> dict:
    """A tool spec in strict form: every property required, no extra properties, and each optional property given
    an explicit "none" choice (its enum gains "none"; a free string becomes anyOf the string or "none")."""
    params = tool["parameters"]
    required = set(params.get("required", []))
    props = {}
    for name, p in params["properties"].items():
        p = dict(p)
        if name not in required:
            if "enum" in p:
                p["enum"] = [*p["enum"], STRICT_NONE]
            else:
                desc = p.pop("description", "")
                p = {"anyOf": [p, {"type": "string", "enum": [STRICT_NONE]}], "description": desc}
            p["description"] = (p.get("description", "") + f' Use "{STRICT_NONE}" to leave it out.').strip()
        props[name] = p
    return {**tool, "strict": True,
            "parameters": {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}}


class OpenAICompatProvider:
    """Any OpenAI-compatible chat completions API with tool calling, for example DeepSeek's hosted API.

    PDA_OPENAI_BASE_URL   API base, e.g. https://api.deepseek.com
    PDA_OPENAI_MODEL      model id, e.g. deepseek-v4-pro
    PDA_OPENAI_API_KEY_ENV  name of the environment variable that holds the key (default OPENAI_API_KEY);
                            the key itself is never read from a file in this repo, logged or stored
    PDA_OPENAI_SEND_REASONING  "1" sends a thinking model's reasoning_content back on every earlier assistant
                            turn (DeepSeek's thinking mode with tools requires it on all of them); default "1"
    PDA_OPENAI_THINKING     "enabled" or "disabled" sends {"thinking": {"type": ...}} (DeepSeek's switch);
                            unset leaves the API's default. Thinking mode ignores temperature.
    PDA_OPENAI_REASONING_EFFORT  optional reasoning_effort, e.g. high
    PDA_OPENAI_MAX_TOKENS   output cap per call (default 2000; reasoning counts toward it, so raise it for thinking)
    PDA_OPENAI_STRICT       "1" sends the tools in DeepSeek's strict mode (beta): every function strict, every
                            property required, no additional properties. An optional parameter gets a "none"
                            choice, and "none" is dropped from the arguments before the tool runs. Strict mode
                            needs the beta base URL, e.g. https://api.deepseek.com/beta
    Token usage from every response is added up in `usage`.
    """

    name = "openai_compat"
    supports_format = False

    def __init__(self, model: str | None = None, max_tokens: int = 2000, timeout: float = 300, client=None):
        self.base_url = os.environ.get("PDA_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.environ.get("PDA_OPENAI_MODEL")
        if not self.model:
            raise ValueError("set PDA_OPENAI_MODEL (for example deepseek-v4-pro)")
        key_env = os.environ.get("PDA_OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
        key = os.environ.get(key_env)
        if not key and client is None:
            raise ValueError(f"the API key environment variable {key_env} is not set")
        self.max_tokens = int(os.environ.get("PDA_OPENAI_MAX_TOKENS", max_tokens))
        self.send_reasoning = os.environ.get("PDA_OPENAI_SEND_REASONING", "1") == "1"
        self.thinking = os.environ.get("PDA_OPENAI_THINKING", "")
        self.reasoning_effort = os.environ.get("PDA_OPENAI_REASONING_EFFORT", "")
        self.strict = os.environ.get("PDA_OPENAI_STRICT", "") == "1"
        self.client = client or httpx.Client(timeout=timeout, headers={"Authorization": f"Bearer {key}"})
        self.usage: dict[str, int] = {}
        self.calls = 0

    def to_messages(self, messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "assistant":
                msg = {"role": "assistant", "content": m.get("content") or ""}
                if m.get("tool_calls"):
                    msg["tool_calls"] = [{"id": c["id"], "type": "function",
                                          "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}
                                         for c in m["tool_calls"]]
                if self.send_reasoning and m.get("reasoning"):
                    msg["reasoning_content"] = m["reasoning"]
                out.append(msg)
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def _count(self, usage: dict | None):
        self.calls += 1
        for k, v in (usage or {}).items():
            if isinstance(v, int):
                self.usage[k] = self.usage.get(k, 0) + v
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    if isinstance(v2, int):
                        self.usage[f"{k}.{k2}"] = self.usage.get(f"{k}.{k2}", 0) + v2

    def chat(self, messages, tools, format=None):
        body = {"model": self.model, "messages": self.to_messages(messages), "temperature": 0,
                "max_tokens": self.max_tokens}
        if self.thinking in ("enabled", "disabled"):
            body["thinking"] = {"type": self.thinking}
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if tools:
            body["tools"] = [{"type": "function", "function": strict_spec(t) if self.strict else t} for t in tools]
        r = self.client.post(f"{self.base_url}/chat/completions", json=body)
        if r.status_code >= 400:
            # The error body, never the request headers (which carry the key).
            raise RuntimeError(f"{self.base_url} returned {r.status_code}: {r.text[:300]}")
        data = r.json()
        self._count(data.get("usage"))
        msg = data["choices"][0]["message"]
        calls = []
        for i, c in enumerate(msg.get("tool_calls") or []):
            fn = c.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {"raw": fn.get("arguments")}
            args = args if isinstance(args, dict) else {}
            if self.strict:  # an optional parameter's "none" choice means the parameter was left out
                args = {k: v for k, v in args.items() if v != STRICT_NONE}
            calls.append(ToolCall(c.get("id") or f"call_{i}", fn.get("name", ""), args))
        content = THINK_BLOCK.sub("", msg.get("content") or "").strip()
        return Reply(content, calls, msg.get("reasoning_content") or "")


PROVIDERS = {"ollama": OllamaProvider, "anthropic": AnthropicProvider, "vertex": VertexProvider,
             "openai_compat": OpenAICompatProvider}


def get_provider(name: str | None = None, model: str | None = None) -> Provider:
    """PDA_PROVIDER picks the backend: ollama (open model, default), anthropic (Claude), vertex (Claude on Vertex
    AI) or openai_compat (any OpenAI-compatible API, such as DeepSeek's)."""
    name = name or os.environ.get("PDA_PROVIDER", "ollama")
    if name not in PROVIDERS:
        raise ValueError(f"unknown provider '{name}', choose one of {', '.join(PROVIDERS)}")
    return PROVIDERS[name](model)
