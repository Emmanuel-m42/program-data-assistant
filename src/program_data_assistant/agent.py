"""The tool-calling loop: question in, answer with tool calls, sources and a refusal flag out."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field

from . import prompts
from .llm import Provider, Reply, ToolCall
from .tools import TOOL_SPECS, Toolbox, ToolResult

MAX_STEPS = 7
SOURCE_ROWS = 8
REFUSAL = re.compile(r"\bcan(?:'|no|’)?t confirm\b|\bcannot confirm\b|\bcan not confirm\b", re.IGNORECASE)
CITATION = re.compile(r"\b(table|doc)\s*:\s*([A-Za-z0-9_#\-]+)")
RETRY_NUDGE = ("Your last query failed because of the SQL, not because the data is missing. "
               "Fix the query using the listed columns and run it again before answering.")
NUMBER = re.compile(r"(?<![\w.])-?\$?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)")
BRACKETS = re.compile(r"\[[^\]]*\]")
DATES = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2}\b")
LOOK_NUDGE = ("You haven't used a tool yet, and answers must come from the tools. Call get_view or query_program_data "
              "for numbers and search_documents for rules or definitions now. Then answer, or say you can't confirm it "
              "if neither has it.")
CITE_NUDGE = ("Rewrite the same answer with citations. Put one after each number or rule, using exactly these ids: {ids}. "
              "Keep the numbers as they are.")
PROVENANCE_ASK = ("Return your answer above as JSON lines. Keep each sentence or bullet word for word, in order, but "
                  "without any bracketed citations. For each line, source is the id of the tool result its figure or "
                  "rule comes from, or 'none' if the line states no figure or rule.")
WITHHELD = ("I can't confirm that from the program data or documents. My draft answer used numbers that aren't in "
            "the query results, so I'm not giving it.")
GROUNDING_NUDGE = ("These numbers in your answer do not appear in any tool result: {numbers}. Rewrite the answer using "
                   "only numbers from the tool results above. If you need a number you don't have, query for it first.")
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
    ungrounded_numbers: list[float] = field(default_factory=list)
    withheld_draft: str = ""
    dropped_citations: list[str] = field(default_factory=list)
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
        if r.name != "search_documents":
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


def _numbers(text: str) -> list[float]:
    text = DATES.sub(" ", BRACKETS.sub(" ", text))
    return [float(m.group(1).replace(",", "")) for m in NUMBER.finditer(text)]


def ungrounded_numbers(answer: str, question: str, results: list[ToolResult]) -> list[float]:
    """Numbers in the answer that no tool result supports, directly or as a sum or difference of two results.

    Small whole numbers (up to 31) and years are ignored: they are usually days, counts read off a list, or dates.
    """
    seen = set(_numbers(question))
    for r in results:
        if r.ok:
            seen.update(_numbers(r.content))
    base = sorted(seen)
    derived = {round(a + b, 2) for i, a in enumerate(base) for b in base[i:]} | {round(abs(a - b), 2) for a in base for b in base}

    def close(n, pool):
        return any(abs(n - v) <= max(0.051, 0.006 * abs(v)) for v in pool)

    out = []
    for n in _numbers(answer):
        n = abs(n)
        if (n <= 31 and n == int(n)) or 1900 <= n <= 2100:
            continue
        if close(n, base) or close(n * 100, base) or close(n / 100, base) or close(n, derived):
            continue
        out.append(n)
    return out


def valid_citation_ids(results: list[ToolResult]) -> str:
    ids = []
    for r in results:
        if r.ok:
            ids += [f"[table:{t}]" for t in r.tables] + [f"[doc:{p['chunk_id']}]" for p in r.passages]
    return ", ".join(dict.fromkeys(ids))


def citations_valid(results: list[ToolResult], citations: list[dict]) -> bool:
    if not citations:
        return False
    tables = {t for r in results if r.ok for t in r.tables}
    docs = {p["chunk_id"] for r in results if r.ok for p in r.passages}
    return all((c["id"] in tables) if c["type"] == "table" else (c["id"] in docs) for c in citations)


def source_ids(results: list[ToolResult]) -> list[str]:
    ids = []
    for r in results:
        if r.ok:
            ids += [f"table:{t}" for t in r.tables] + [f"doc:{p['chunk_id']}" for p in r.passages]
    return list(dict.fromkeys(ids))


def drop_unknown_citations(text: str, results: list[ToolResult]) -> tuple[str, list[str]]:
    """Remove citations to tables or passages this conversation never returned; report which ones."""
    valid = set(source_ids(results))
    dropped: list[str] = []

    def keep(m: re.Match) -> str:
        parts = [f"{k}:{v.rstrip('-#')}" for k, v in CITATION.findall(m.group(0))]
        if not parts:
            return m.group(0)  # not a citation, leave it
        good = [p for p in parts if p in valid]
        dropped.extend(p for p in parts if p not in valid)
        return " ".join(f"[{p}]" for p in good)

    out = re.sub(r"\s*\[[^\]]*\b(?:table|doc)\s*:[^\]]*\]", lambda m: (" " + keep(m)) if keep(m) else "", text)
    out = re.sub(r"[ \t]+([.,;:])", r"\1", out)
    return out, list(dict.fromkeys(dropped))


def source_for_numbers(body: str, results: list[ToolResult]) -> str | None:
    """The result whose content holds the figures in this line, if one holds them all."""
    nums = [n for n in _numbers(body) if not (n <= 31 and n == int(n))]
    if not nums:
        return None
    for r in results:
        if not r.ok:
            continue
        have = _numbers(r.content)
        if all(any(abs(n - v) <= max(0.051, 0.006 * abs(v)) for v in have) for n in nums):
            return f"table:{r.tables[0]}" if r.tables else (f"doc:{r.passages[0]['chunk_id']}" if r.passages else None)
    return None


def render_lines(lines: list[dict], allowed: set[str], results: list[ToolResult] = ()) -> str:
    """Rebuild the answer from {text, source} pairs; citations come from provenance, never from typed text.

    A line the model left without a valid source gets the tool result that contains all its figures, if any.
    """
    out = []
    for line in lines:
        body = re.sub(r"\s+([.,;:])", r"\1", BRACKETS.sub("", str(line.get("text", "")))).rstrip()
        if not body.strip():
            continue
        src = line.get("source")
        if src not in allowed:
            src = source_for_numbers(body, list(results))
        out.append(f"{body} [{src}]" if src in allowed else body)
    return "\n".join(out)


class Assistant:
    def cite_from_provenance(self, messages: list[dict], draft: str, results: list[ToolResult]) -> str:
        """Second call with a JSON schema: each answer line paired with the id of the result it came from."""
        ids = source_ids(results)
        if not ids:
            return draft
        schema = {
            "type": "object",
            "properties": {"lines": {"type": "array", "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "source": {"type": "string", "enum": ids + ["none"]}},
                "required": ["text", "source"],
            }}},
            "required": ["lines"],
        }
        ask = messages + [{"role": "assistant", "content": draft}, {"role": "user", "content": PROVENANCE_ASK}]
        try:
            reply = self.provider.chat(ask, None, format=schema)
            lines = json.loads(reply.content)["lines"]
        except (ValueError, KeyError, TypeError):
            return draft
        rendered = render_lines(lines, set(ids), results)
        return rendered or draft

    def __init__(self, provider: Provider, toolbox: Toolbox | None = None, system: str | None = None):
        self.provider = provider
        self.toolbox = toolbox or Toolbox()
        self.system = system or prompts.system_prompt()
        # Off by default: on the dev split it scored below typed citations plus the citation check (README).
        self.structured_citations = (os.environ.get("PDA_STRUCTURED_CITATIONS") == "1"
                                     and getattr(provider, "supports_format", False))

    def ask(self, question: str) -> Answer:
        t0 = time.monotonic()
        messages: list[dict] = [{"role": "system", "content": self.system}, {"role": "user", "content": question}]
        results: list[ToolResult] = []
        calls_log: list[dict] = []
        reply = Reply("")
        steps = 0
        nudged = revised = looked = cite_fixed = False
        self.toolbox.reset()
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
                # Grounding check: every number in the answer must come from a tool result.
                missing = [] if REFUSAL.search(reply.content or "") else ungrounded_numbers(reply.content or "", question, results)
                if missing and not revised and steps < MAX_STEPS:
                    revised = True
                    shown = ", ".join(f"{n:g}" for n in missing[:8])
                    messages.append({"role": "assistant", "content": reply.content})
                    messages.append({"role": "user", "content": GROUNDING_NUDGE.format(numbers=shown)})
                    continue
                # Answering (or refusing) without having looked at anything: look first.
                if not results and not looked and steps < MAX_STEPS:
                    looked = True
                    messages.append({"role": "assistant", "content": reply.content})
                    messages.append({"role": "user", "content": LOOK_NUDGE})
                    continue
                # Citation check: an answer must cite sources this conversation actually returned.
                if (not self.structured_citations
                        and not REFUSAL.search(reply.content or "") and results and not cite_fixed and steps < MAX_STEPS
                        and not citations_valid(results, parse_citations(reply.content or ""))):
                    cite_fixed = True
                    messages.append({"role": "assistant", "content": reply.content})
                    messages.append({"role": "user", "content": CITE_NUDGE.format(ids=valid_citation_ids(results))})
                    continue
                break
            messages.append({"role": "assistant", "content": "" if not reply.tool_calls else reply.content,
                             "tool_calls": [{"id": c.id, "name": c.name, "args": c.args} for c in calls],
                             "reasoning": getattr(reply, "reasoning", "")})
            for c in calls:
                res = self.toolbox.run(c.name, c.args)
                results.append(res)
                calls_log.append({"name": c.name, "args": c.args, "ok": res.ok, "result": res.summary})
                messages.append({"role": "tool", "tool_call_id": c.id, "name": c.name, "content": res.content})
        else:
            messages.append({"role": "user", "content": "Answer now from the tool results above, with citations."})
            reply = self.provider.chat(messages, None)
        text = (reply.content or "").strip()
        if self.structured_citations and results and text and not REFUSAL.search(text):
            text = self.cite_from_provenance(messages, text, results)
        text, dropped = drop_unknown_citations(text, results)
        refused = bool(REFUSAL.search(text)) or not text
        missing = [] if refused else ungrounded_numbers(text, question, results)
        withheld = ""
        if len(missing) >= 2:
            # Still unsupported after a revision: don't pass made-up numbers on. Keep the draft for the record.
            withheld, text, refused = text, WITHHELD, True
        cites = parse_citations(text)
        return Answer(
            ungrounded_numbers=missing,
            withheld_draft=withheld,
            dropped_citations=dropped,
            question=question,
            answer=text,
            refused=refused,
            tool_calls=calls_log,
            sources=build_sources(results, cites),
            citations=cites,
            citations_valid=citations_valid(results, cites),
            latency_ms=int((time.monotonic() - t0) * 1000),
            model=f"{self.provider.name}/{self.provider.model}",
            steps=steps,
        )
