"""The tool-calling loop: question in, answer with tool calls, sources and a refusal flag out."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field

from . import prompts
from .llm import Provider, Reply, ToolCall
from .tools import TOOL_SPECS, Toolbox, ToolResult

MAX_STEPS = 6
SOURCE_ROWS = 8
REFUSAL = re.compile(r"\bcan(?:'|no|’)?t confirm\b|\bcannot confirm\b|\bcan not confirm\b", re.IGNORECASE)
CITATION = re.compile(r"\b(table|doc)\s*:\s*([A-Za-z0-9_#\-]+)")
RETRY_NUDGE = ("Your last query failed because of the SQL, not because the data is missing. "
               "Fix the query using the listed columns and run it again before answering.")
INLINE_CALL = re.compile(r"\{\s*\"name\"\s*:\s*\"(query_program_data|search_documents)\".*\}", re.DOTALL)


@dataclass
class Answer:
    question: str
    answer: str
    refused: bool
    tool_calls: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    citations_valid: bool = False
    latency_ms: int = 0
    model: str = ""
    steps: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def parse_citations(text: str) -> list[dict]:
    seen, out = set(), []
    for kind, ident in CITATION.findall(text):
        key = (kind, ident.rstrip("-#"))
        if key not in seen:
            seen.add(key)
            out.append({"type": kind, "id": key[1]})
    return out


def inline_tool_calls(content: str) -> list[ToolCall]:
    """Small models sometimes write the tool call as JSON text instead of a structured call."""
    m = INLINE_CALL.search(content or "")
    if not m:
        return []
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    args = obj.get("arguments") or obj.get("parameters") or {}
    return [ToolCall("inline_0", obj["name"], args if isinstance(args, dict) else {})]


def build_sources(results: list[ToolResult], citations: list[dict]) -> list[dict]:
    cited_tables = {c["id"] for c in citations if c["type"] == "table"}
    cited_docs = {c["id"] for c in citations if c["type"] == "doc"}
    rows, passages = [], []
    for r in results:
        if not r.ok:
            continue
        if r.name == "query_program_data":
            rows.append((bool(cited_tables & set(r.tables)),
                         {"type": "rows", "table": ", ".join(r.tables), "columns": r.columns, "rows": r.rows[:SOURCE_ROWS],
                          "row_count": len(r.rows), "sql": r.args.get("sql", "")}))
        else:
            for p in r.passages:
                passages.append((p["chunk_id"] in cited_docs, {"type": "passage", "doc": p["chunk_id"], "text": p["text"]}))
    picked = [s for cited, s in rows + passages if cited]
    if not picked:  # nothing cited: show what the answer was built from
        picked = [s for _, s in rows] + [s for _, s in passages[:2]]
    out, seen = [], set()
    for s in picked:
        key = (s["type"], s.get("doc") or s.get("sql"))
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def citations_valid(results: list[ToolResult], citations: list[dict]) -> bool:
    if not citations:
        return False
    tables = {t for r in results if r.ok for t in r.tables}
    docs = {p["chunk_id"] for r in results if r.ok for p in r.passages}
    return all((c["id"] in tables) if c["type"] == "table" else (c["id"] in docs) for c in citations)


class Assistant:
    def __init__(self, provider: Provider, toolbox: Toolbox | None = None, system: str | None = None):
        self.provider = provider
        self.toolbox = toolbox or Toolbox()
        self.system = system or prompts.system_prompt()

    def ask(self, question: str) -> Answer:
        t0 = time.monotonic()
        messages: list[dict] = [{"role": "system", "content": self.system}, {"role": "user", "content": question}]
        results: list[ToolResult] = []
        calls_log: list[dict] = []
        reply = Reply("")
        steps = 0
        nudged = False
        for steps in range(1, MAX_STEPS + 1):
            reply = self.provider.chat(messages, TOOL_SPECS)
            calls = reply.tool_calls or inline_tool_calls(reply.content)
            if not calls:
                # Giving up right after a failed query usually means a fixable SQL mistake, not missing data.
                if (REFUSAL.search(reply.content or "") and results and not results[-1].ok and not nudged
                        and steps < MAX_STEPS):
                    nudged = True
                    messages.append({"role": "assistant", "content": reply.content})
                    messages.append({"role": "user", "content": RETRY_NUDGE})
                    continue
                break
            messages.append({"role": "assistant", "content": "" if not reply.tool_calls else reply.content,
                             "tool_calls": [{"id": c.id, "name": c.name, "args": c.args} for c in calls]})
            for c in calls:
                res = self.toolbox.run(c.name, c.args)
                results.append(res)
                calls_log.append({"name": c.name, "args": c.args, "ok": res.ok, "result": res.summary})
                messages.append({"role": "tool", "tool_call_id": c.id, "name": c.name, "content": res.content})
        else:
            messages.append({"role": "user", "content": "Answer now from the tool results above, with citations."})
            reply = self.provider.chat(messages, None)
        text = (reply.content or "").strip()
        cites = parse_citations(text)
        return Answer(
            question=question,
            answer=text,
            refused=bool(REFUSAL.search(text)) or not text,
            tool_calls=calls_log,
            sources=build_sources(results, cites),
            citations=cites,
            citations_valid=citations_valid(results, cites),
            latency_ms=int((time.monotonic() - t0) * 1000),
            model=f"{self.provider.name}/{self.provider.model}",
            steps=steps,
        )
