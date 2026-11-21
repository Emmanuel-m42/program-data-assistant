"""MCP client for ngpvan-mcp: VAN people, events, signups, saved lists and activist codes as extra tools.

`VanMcp` launches an MCP server over stdio (by default `ngpvan-mcp --demo`, the built-in fictional data),
lists its tools and exposes the read-only ones to the agent as `van_<tool>`. Write tools are never exposed.
Every call returns what the server returned (already masked by the server: no phone numbers, emails,
addresses or birth dates, names shortened) and the server's own audit line for that call.

Settings:
  PDA_VAN_MCP=demo            launch `ngpvan-mcp --demo` from this environment (`uv sync --extra van`)
  PDA_VAN_MCP_COMMAND="..."   launch another command instead (it must speak MCP over stdio)
  PDA_VAN_MCP_AUDIT=path      the server's audit file, when the command brings its own --config

The server runs on a background thread with its own event loop, so the synchronous agent loop can call it.
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import shutil
import sys
import tempfile
import threading
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PREFIX = "van_"
SERVER_NAME = "ngpvan-mcp"
NEVER_EXPOSE = {"apply_canvass_response"}  # writes stay off here even if a server turns one on
CALL_TIMEOUT = 60.0
MAX_RESULT_CHARS = 12_000  # what the model sees; the server caps its own results too


@dataclass
class VanTool:
    name: str  # the server's name, e.g. turf_door_counts
    description: str
    input_schema: dict

    @property
    def agent_name(self) -> str:
        return PREFIX + self.name

    def spec(self) -> dict:
        return {"name": self.agent_name, "description": f"VAN (ngpvan-mcp): {self.description}",
                "parameters": self.input_schema or {"type": "object", "properties": {}}}


@dataclass
class VanCall:
    tool: str
    args: dict
    ok: bool
    text: str  # the result exactly as the model sees it (masked by the server)
    data: Any  # the structured result, when the server sent one
    audit: dict | None


def _ngpvan_command() -> list[str]:
    exe = Path(sys.executable).with_name("ngpvan-mcp")
    found = str(exe) if exe.exists() else shutil.which("ngpvan-mcp")
    if not found:
        raise RuntimeError("ngpvan-mcp isn't installed; run `uv sync --extra van`")
    return [found, "--demo"]


class VanMcp:
    def __init__(self, command: list[str], audit_path: Path | None = None, workdir: Path | None = None):
        self.command = list(command)
        self.workdir = workdir or Path(tempfile.mkdtemp(prefix="pda-van-mcp-"))
        if "--config" not in self.command:
            # Our own settings for the server: names shortened, writes off, audit to a file we can read back.
            audit_path = self.workdir / "audit.jsonl"
            config = self.workdir / "ngpvan-mcp.toml"
            config.write_text(f'[privacy]\nnames = "initial"\n\n[writes]\napply_canvass_response = false\n\n'
                              f'[audit]\npath = "{audit_path}"\n')
            self.command += ["--config", str(config)]
        self.audit_path = audit_path
        self._audit_offset = 0
        self.tools: dict[str, VanTool] = {}  # by agent name
        self.instructions = ""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="van-mcp", daemon=True)
        self._session = None
        self._stop: asyncio.Event | None = None
        self._runner: Future | None = None
        self._lock = threading.Lock()

    # ---------- lifecycle ----------

    @classmethod
    def from_env(cls) -> VanMcp | None:
        command = os.environ.get("PDA_VAN_MCP_COMMAND")
        mode = os.environ.get("PDA_VAN_MCP", "").strip().lower()
        if command:
            audit = os.environ.get("PDA_VAN_MCP_AUDIT")
            return cls(shlex.split(command), Path(audit) if audit else None).start()
        if mode in ("demo", "1", "true", "on"):
            return cls(_ngpvan_command()).start()
        return None

    def start(self) -> VanMcp:
        self._thread.start()
        ready: Future = Future()
        self._runner = asyncio.run_coroutine_threadsafe(self._serve(ready), self._loop)
        try:
            ready.result(timeout=CALL_TIMEOUT)
        except Exception:
            self.close()
            raise
        return self

    async def _serve(self, ready: Future):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=self.command[0], args=self.command[1:], cwd=str(self.workdir))
        self._stop = asyncio.Event()
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await session.initialize()
                    self.instructions = getattr(init, "instructions", "") or ""
                    listed = await session.list_tools()
                    for t in listed.tools:
                        read_only = bool(t.annotations and t.annotations.read_only_hint)
                        if read_only and t.name not in NEVER_EXPOSE:
                            tool = VanTool(t.name, (t.description or "").strip(), dict(t.input_schema or {}))
                            self.tools[tool.agent_name] = tool
                    self._session = session
                    ready.set_result(True)
                    await self._stop.wait()
        except BaseException as e:  # report startup failures to start(); later ones end the session
            if not ready.done():
                ready.set_exception(RuntimeError(f"couldn't start the VAN MCP server: {type(e).__name__}: {e}"))
            if not isinstance(e, Exception):
                raise
        finally:
            self._session = None

    def close(self):
        if self._stop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._runner is not None:
            try:
                self._runner.result(timeout=10)
            except Exception:
                pass
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    # ---------- tools ----------

    def specs(self) -> list[dict]:
        return [t.spec() for t in self.tools.values()]

    def has(self, agent_name: str) -> bool:
        return agent_name in self.tools

    def call(self, agent_name: str, args: dict) -> VanCall:
        tool = self.tools.get(agent_name)
        if tool is None:
            return VanCall(agent_name, args, False, f"Unknown VAN tool '{agent_name}'.", None, None)
        if self._session is None:
            return VanCall(tool.name, args, False, "The VAN MCP server isn't running.", None, None)
        args = {k: v for k, v in (args or {}).items() if v is not None}
        with self._lock:  # one call at a time, so each audit line matches its call
            fut = asyncio.run_coroutine_threadsafe(self._session.call_tool(tool.name, args), self._loop)
            try:
                result = fut.result(timeout=CALL_TIMEOUT)
            except Exception as e:
                return VanCall(tool.name, args, False, f"The VAN tool call failed: {type(e).__name__}.", None,
                               self._new_audit(tool.name))
            text = "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text").strip()
            if len(text) > MAX_RESULT_CHARS:
                text = text[:MAX_RESULT_CHARS] + "\n(result cut to keep it short)"
            return VanCall(tool.name, args, not result.is_error, text, result.structured_content,
                           self._new_audit(tool.name))

    def call_direct(self, tool: str, args: dict) -> Any:
        """Call a server tool by its own name and return the structured result (used for eval ground truth)."""
        call = self.call(PREFIX + tool, args)
        if not call.ok:
            raise RuntimeError(f"{tool} failed: {call.text}")
        return call.data if call.data is not None else json.loads(call.text)

    def _new_audit(self, tool: str) -> dict | None:
        """The audit line the server wrote for the call that just finished."""
        if not self.audit_path or not self.audit_path.exists():
            return None
        with self.audit_path.open("r", encoding="utf-8") as fh:
            fh.seek(self._audit_offset)
            lines = fh.read()
            self._audit_offset = fh.tell()
        entries = [json.loads(line) for line in lines.splitlines() if line.strip()]
        mine = [e for e in entries if e.get("tool") == tool]
        return mine[-1] if mine else None
