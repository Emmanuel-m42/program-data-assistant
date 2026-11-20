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
        msg = r.json()["message"]
        msg["content"] = THINK_BLOCK.sub("", msg.get("content") or "").strip()  # in case thinking text leaks into content
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
    """Anthropic Messages API. Needs ANTHROPIC_API_KEY and `uv sync --extra anthropic`."""

    name = "anthropic"

    def __init__(self, model: str | None = None, max_tokens: int = 1500):
        import anthropic

        self.model = model or os.environ.get("PDA_ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic()

    supports_format = False  # structured citations fall back to citations typed in the text

    def chat(self, messages, tools, format=None):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        out: list[dict] = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                blocks += [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]} for c in m.get("tool_calls", [])]
                out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        kwargs = {}
        if tools:
            kwargs["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
        resp = self.client.messages.create(model=self.model, max_tokens=self.max_tokens, system=system, messages=out, **kwargs)
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return Reply(text, calls)


def get_provider(name: str | None = None, model: str | None = None) -> Provider:
    name = name or os.environ.get("PDA_PROVIDER", "ollama")
    if name == "ollama":
        return OllamaProvider(model)
    if name == "anthropic":
        return AnthropicProvider(model)
    raise ValueError(f"unknown provider '{name}'")
