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

# Metric views the get_view tool can return, with the order rows come back in.
VIEWS = {
    "v_office_pace": "office",
    "v_contact_rates": "week_start DESC, office",
    "v_cost_per_door": "cost_per_door DESC",
    "v_weekly_report": "week_start DESC, office",
    "v_precinct_coverage": "pct_touched, doors_per_sq_mi DESC",
    "v_site_options": "avg_km_to_untouched_doors",
    "v_canvasser_status": "active DESC, days_worked DESC",
    "v_qc_flags_detail": "flag_date DESC, full_name",
    "v_qc_weekly": "week_start DESC, office",
    "v_vr_pace": "office",
    "v_vr_canvassers": "duplicate_cards DESC",
    "v_qc_call_outcomes": "office, calls DESC",
    "v_weekly_hours": "week_start DESC, paid_hours DESC NULLS LAST",
    "v_shifts_to_fix": "shift_date DESC",
    "v_daily_doors": "knock_date DESC, office",
}
WEEK_COLUMN = {"v_contact_rates", "v_weekly_report", "v_qc_weekly", "v_weekly_hours", "v_shifts_to_fix", "v_qc_flags_detail"}
OFFICE_COLUMN = set(VIEWS) - {"v_site_options"}
ALL_OFFICES = {"all", "all offices", "all_offices", "any", "*", "program", "total"}

TOOL_SPECS = [
    {
        "name": "get_view",
        "description": (
            "Answers: program metrics that already have a view, read as is. Pace, projection and shortfall by office, "
            "shifts needed, contact rate by week, cost per door, the weekly client report, turf coverage by precinct, "
            "sites for a new office, staff status (active, regular), QC flags with evidence, QC rate by week, "
            "registration pace and cards per hour, duplicates by canvasser, QC call outcomes, weekly hours and overtime, "
            "shifts waiting for a fix or approval. "
            "Doesn't answer: one specific day or shift, custom joins, rules or definitions. "
            'Example: {"view": "v_office_pace"}. '
            "Use this before query_program_data; switch to SQL only when no view has the columns you need."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "view": {"type": "string", "enum": sorted(VIEWS)},
                "office": {"type": "string", "description": "Only when the question names one office: 'Northside', 'Eastgate' or 'Harbor'. Leave it out otherwise."},
                "week_start": {"type": "string", "description": "Only when the question names one week, for weekly views. Leave it out to compare weeks. This week is 2026-10-12, last week 2026-10-05."},
            },
            "required": ["view"],
        },
    },
    {
        "name": "query_program_data",
        "description": (
            "Answers: numbers no view covers, such as one day (for example Oct 12), one shift, one canvasser's knocks, "
            "or a join across tables. Runs one read-only Postgres SELECT over the tables and views in the system prompt; "
            "results are capped at 200 rows. "
            "Doesn't answer: rules or definitions, or anything a view already gives as a column. "
            "Example: {\"sql\": \"SELECT office, doors, attempts, rolled_back_attempts FROM v_daily_doors WHERE knock_date = '2026-10-16'\"}."
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
            "Answers: definitions, rules, methods and the reasons behind numbers: how doors, attempts and contacts are "
            "counted, why the client's report differs from ours, QC rules (flash knocking, householding, gaps, apartments), "
            "the program plan (goals, projection method, regulars, more doors or a second pass, a new office), payroll "
            "rules (overtime, approval, deadline), client reporting and the registration drive. "
            "Doesn't answer: numbers. "
            'Example: {"query": "how overtime is approved"}. '
            "Use it with a data tool whenever the question asks why, or uses a program term that needs a definition."
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
        self.seen_sql: set[str] = set()  # per question; reset by the agent

    def reset(self):
        self.seen_sql = set()

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
        if name == "get_view":
            return self.get_view(args)
        return ToolResult(name, args, False, f"Unknown tool '{name}'.", "unknown tool")

    def query_program_data(self, sql: str) -> ToolResult:
        args = {"sql": sql}
        if sql.strip() in self.seen_sql:
            return ToolResult("query_program_data", args, False,
                              "You already ran this exact query; its result is above. Change the query or answer from what you have.",
                              "repeated query")
        self.seen_sql.add(sql.strip())
        try:
            checked = sql_guard.check(sql)
        except sql_guard.SQLRejected as e:
            return ToolResult("query_program_data", args, False, f"Query rejected: {e}", f"rejected: {e}")
        return self._run_select(checked.sql, checked.tables, args, "query_program_data")

    def _run_select(self, sql: str, tables: list[str], args: dict, tool: str, params=None) -> ToolResult:
        try:
            cur = self.reader.execute(sql, params or None)
            columns = [d.name for d in cur.description]
            rows = [[_plain(v) for v in r] for r in cur.fetchmany(MAX_ROWS + 1)]
        except psycopg.Error as e:
            msg = (e.diag.message_primary or str(e)).strip()
            hint = self.column_hint(tables) if isinstance(e, psycopg.errors.UndefinedColumn) else ""
            return ToolResult(tool, args, False, f"Database error: {msg}{hint}\nFix the query and run it again.", f"error: {msg}")
        checked = sql_guard.CheckedSQL(sql, tables)
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        shown = rows[:MODEL_ROWS]
        lines = [" | ".join(columns)] + [" | ".join(_fmt(v) for v in r) for r in shown]
        note = ""
        if not rows and tool == "query_program_data":
            note = ("\n(0 rows. The WHERE conditions are probably narrower than the question. "
                    "Run it again without the extra conditions; do not answer with numbers you have not seen.)")
        elif len(rows) > len(shown) or truncated:
            note = f"\n({len(rows)}{'+' if truncated else ''} rows, first {len(shown)} shown; filter or aggregate to see the rest)"
        content = f"tables: {', '.join(checked.tables)}\n" + "\n".join(lines) + note
        summary = f"{len(rows)}{'+' if truncated else ''} row{'s' if len(rows) != 1 else ''} from {', '.join(checked.tables) or 'query'}"
        return ToolResult(tool, args, True, content, summary, checked.tables, columns, rows)

    def get_view(self, args: dict) -> ToolResult:
        view = str(args.get("view", ""))
        if view not in VIEWS:
            return ToolResult("get_view", args, False, f"Unknown view '{view}'. Choose one of: {', '.join(sorted(VIEWS))}.",
                              "unknown view")
        where, params = [], []
        office = str(args.get("office") or "").strip()
        if office.lower() in ALL_OFFICES:  # "all offices" means no filter, not only the total row
            office = ""
        if office and view in OFFICE_COLUMN:
            where.append("office = %s")
            params.append(office)
        week = str(args.get("week_start") or "").strip()
        if week and view in WEEK_COLUMN:  # ignored on views without a week column
            where.append("week_start = %s")
            params.append(week)
        # Built only from the fixed view names and order clauses above; values are bound parameters.
        sql = f"SELECT * FROM {view}" + (f" WHERE {' AND '.join(where)}" if where else "") + f" ORDER BY {VIEWS[view]}"
        res = self._run_select(sql, [view], args, "get_view", params)
        if res.ok and not res.rows and (office or week):
            res.content += "\n(No rows for that filter. Offices are Northside, Eastgate and Harbor; leave office out for all.)"
        return res

    def column_hint(self, tables: list[str]) -> str:
        """The real columns of the tables a failed query used, so the model can correct itself."""
        if not tables:
            return ""
        rows = self.reader.execute(
            """SELECT table_name, string_agg(column_name, ', ' ORDER BY ordinal_position) FROM information_schema.columns
               WHERE table_schema = 'program' AND table_name = ANY(%s) GROUP BY table_name""",
            (tables,),
        ).fetchall()
        return "".join(f"\nColumns of {t}: {cols}" for t, cols in rows)

    def search_documents(self, query: str) -> ToolResult:
        args = {"query": query}
        if not query.strip():
            return ToolResult("search_documents", args, False, "Empty query.", "empty query")
        hits = retrieval.search(self.docs, query)
        content = "\n\n".join(f"[doc:{h['chunk_id']}]\n{h['text']}" for h in hits)
        summary = f"{len(hits)} passages: " + ", ".join(h["chunk_id"] for h in hits)
        return ToolResult("search_documents", args, True, content, summary, passages=hits)
