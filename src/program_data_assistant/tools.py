"""The two tools the model can call, and their executors."""

from __future__ import annotations

import datetime as dt
import decimal
from dataclasses import dataclass, field
from typing import Any

import psycopg

from . import db, retrieval, sql_guard

MAX_ROWS = 200  # rows fetched from the database
MODEL_ROWS = 60  # rows shown to the model

TOOL_SPECS = [
    {
        "name": "query_program_data",
        "description": (
            "Run one read-only SQL SELECT (Postgres) over the program tables and views described in the system "
            "prompt. Use it for every number: doors, goals, shifts, hours, flags, cards, costs. Returns columns and rows."
        ),
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "A single SELECT statement."}},
            "required": ["sql"],
        },
    },
    {
        "name": "search_documents",
        "description": (
            "Search the program documents (counting rules, QC rules, program plan, payroll rules, client reporting, "
            "registration drive). Use it for definitions, rules, methods and policies. Returns passages with ids."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for, in plain words."}},
            "required": ["query"],
        },
    },
]


@dataclass
class ToolResult:
    name: str
    args: dict
    ok: bool
    content: str  # what the model sees
    summary: str  # short human-readable result
    tables: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    passages: list[dict] = field(default_factory=list)


def _plain(v):
    if isinstance(v, decimal.Decimal):
        return float(v) if v != v.to_integral_value() else int(v)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat(sep=" ") if isinstance(v, dt.datetime) else v.isoformat()
    return v


def _fmt(v) -> str:
    return "" if v is None else str(v)


class Toolbox:
    def __init__(self, reader_conn: psycopg.Connection | None = None, docs_conn: psycopg.Connection | None = None):
        self._reader = reader_conn
        self._docs = docs_conn

    @property
    def reader(self):
        if self._reader is None or self._reader.closed:
            self._reader = db.connect_reader()
        return self._reader

    @property
    def docs(self):
        if self._docs is None or self._docs.closed:
            self._docs = db.connect_admin()
        return self._docs

    def run(self, name: str, args: dict) -> ToolResult:
        if name == "query_program_data":
            return self.query_program_data(str(args.get("sql", "")))
        if name == "search_documents":
            return self.search_documents(str(args.get("query", "")))
        return ToolResult(name, args, False, f"Unknown tool '{name}'.", "unknown tool")

    def query_program_data(self, sql: str) -> ToolResult:
        args = {"sql": sql}
        try:
            checked = sql_guard.check(sql)
        except sql_guard.SQLRejected as e:
            return ToolResult("query_program_data", args, False, f"Query rejected: {e}", f"rejected: {e}")
        try:
            cur = self.reader.execute(checked.sql)
            columns = [d.name for d in cur.description]
            rows = [[_plain(v) for v in r] for r in cur.fetchmany(MAX_ROWS + 1)]
        except psycopg.Error as e:
            msg = (e.diag.message_primary or str(e)).strip()
            return ToolResult("query_program_data", args, False, f"Database error: {msg}", f"error: {msg}")
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        shown = rows[:MODEL_ROWS]
        lines = [" | ".join(columns)] + [" | ".join(_fmt(v) for v in r) for r in shown]
        note = ""
        if len(rows) > len(shown) or truncated:
            note = f"\n({len(rows)}{'+' if truncated else ''} rows, first {len(shown)} shown; aggregate in SQL instead)"
        content = f"tables: {', '.join(checked.tables)}\n" + "\n".join(lines) + note
        summary = f"{len(rows)}{'+' if truncated else ''} row{'s' if len(rows) != 1 else ''} from {', '.join(checked.tables) or 'query'}"
        return ToolResult("query_program_data", args, True, content, summary, checked.tables, columns, rows)

    def search_documents(self, query: str) -> ToolResult:
        args = {"query": query}
        if not query.strip():
            return ToolResult("search_documents", args, False, "Empty query.", "empty query")
        hits = retrieval.search(self.docs, query)
        content = "\n\n".join(f"[doc:{h['chunk_id']}]\n{h['text']}" for h in hits)
        summary = f"{len(hits)} passages: " + ", ".join(h["chunk_id"] for h in hits)
        return ToolResult("search_documents", args, True, content, summary, passages=hits)
