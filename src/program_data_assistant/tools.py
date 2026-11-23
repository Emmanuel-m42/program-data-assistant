"""The two tools the model can call, and their executors."""

from __future__ import annotations

import datetime as dt
import decimal
import re
from dataclasses import dataclass, field
from typing import Any

import psycopg

from . import db, retrieval, sql_guard

MAX_ROWS = 200  # rows fetched from the database
MODEL_ROWS = 60  # rows shown to the model

# Metric views the get_view tool can return, with the order rows come back in. Office views have one row per office
# (per week or day where they have one); program totals are in the matching *_total view, never mixed in.
_OFFICE_VIEWS = {
    "v_office_pace": "office",
    "v_contact_rates": "week_start DESC, office",
    "v_cost_per_door": "cost_per_door DESC",
    "v_weekly_report": "week_start DESC, office",
    "v_weekly_pace": "week_start DESC, office",
    "v_weekly_shifts": "week_start DESC, program, office",
    "v_vr_weekly": "week_start DESC, office",
    "v_gotv_staff": "office",
    "v_turf_summary": "office, coverage, density",
    "v_qc_weekly": "week_start DESC, office",
    "v_vr_pace": "office",
    "v_qc_call_outcomes": "office, calls DESC",
    "v_daily_doors": "knock_date DESC, office",
    "v_client_vs_dashboard": "report_date DESC, office",
}
VIEWS = {
    **_OFFICE_VIEWS,
    **{f"{v}_total": order.replace(", office", "").replace("office, ", "").replace("office", "1")
       for v, order in _OFFICE_VIEWS.items()},
    "v_precinct_coverage": "pct_touched, doors_per_sq_mi DESC",
    "v_site_options": "avg_km_to_untouched_doors",
    "v_canvasser_status": "active DESC, days_worked DESC",
    "v_qc_flags_detail": "flag_date DESC, full_name",
    "v_vr_canvassers": "duplicate_cards DESC",
    "v_weekly_hours": "week_start DESC, paid_hours DESC NULLS LAST",
    "v_shifts_to_fix": "shift_date DESC",
}
_WEEKLY = {"v_contact_rates", "v_weekly_report", "v_weekly_pace", "v_weekly_shifts", "v_vr_weekly", "v_qc_weekly"}
WEEK_COLUMN = _WEEKLY | {f"{v}_total" for v in _WEEKLY} | {"v_weekly_hours", "v_shifts_to_fix", "v_qc_flags_detail"}
OFFICE_COLUMN = {v for v in VIEWS if not v.endswith("_total")} - {"v_site_options"}
COUNT_BY_WEEK = {"v_qc_flags_detail", "v_shifts_to_fix", "v_weekly_hours"}  # one row per flag, shift or person-week
ALL_OFFICES = {"all", "all offices", "all_offices", "any", "*", "program", "total"}
OFFICES = ["Northside", "Eastgate", "Harbor"]
WEEKS = ["2026-09-21", "2026-09-28", "2026-10-05", "2026-10-12"]  # Mondays; data runs Sep 21 to Sun Oct 18
DATA_START, DATA_END = "2026-09-21", "2026-10-18"

# What one row of each view is, shown with its results so the model knows the grain before using the numbers.
VIEW_NOTES = {
    "v_office_pace": "one row per office, to date (Sep 21 to Oct 18); doors_untouched = turf doors never knocked",
    "v_contact_rates": "one row per office per week (week_start = Monday)",
    "v_cost_per_door": "one row per office, GOTV wages and doors to date",
    "v_weekly_report": "one row per office per week (week_start = Monday); the weekly report we send, in our "
                       "dashboard counts, not the client's daily sheets (client_daily_report)",
    "v_weekly_pace": "one row per office per week: door goal, doors, contacts for that week",
    "v_weekly_shifts": "one row per office, program and week; avg_shift_hours counts only shifts with a clock out",
    "v_vr_weekly": "one row per office per week: valid registration cards, hours, cards per hour",
    "v_gotv_staff": "one row per office, GOTV canvassers only",
    "v_turf_summary": "one row per office, coverage band and density band; counts only, no precinct names "
                      "(v_precinct_coverage names each precinct)",
    "v_qc_weekly": "one row per office per week; flags per 100 GOTV shifts",
    "v_vr_pace": "one row per office, registration to date; last_7d = Oct 12 to 18 (this week)",
    "v_qc_call_outcomes": "one row per office per call outcome",
    "v_daily_doors": "one row per office per knocking day",
    "v_client_vs_dashboard": "one row per office per day: the client's daily sheet (doors_reported counts attempts "
                             "before rollbacks) next to our dashboard doors; gap = doors_reported - doors",
    "v_precinct_coverage": "one row per precinct",
    "v_site_options": "one row per candidate site for a new office",
    "v_canvasser_status": "one row per person (GOTV and registration)",
    "v_qc_flags_detail": "one row per QC flag",
    "v_vr_canvassers": "one row per registration canvasser",
    "v_weekly_hours": "one row per person per week; shifts_with_hours excludes shifts with no clock out",
    "v_shifts_to_fix": "one row per shift not yet approved",
}
VIEW_NOTES.update({f"{v}_total": "the program total (all offices): " + VIEW_NOTES[v].replace("one row per office, ", "")
                   .replace("one row per office per ", "one row per ").replace("one row per office ", "one row ")
                   for v in _OFFICE_VIEWS})

TOOL_SPECS = [
    {
        "name": "get_view",
        "description": (
            "Call this first for any number about the program. It returns a metric view's rows as they are: pace, "
            "projection and shortfall, untouched doors, shifts needed, doors and goal by week, contact rate by week, "
            "cost per door, the weekly client report, the client's daily sheet against our dashboard by day, shifts, "
            "shift length and wages by week, turf coverage, sites for "
            "a new office, staff counts (active, regulars, one-day hires), QC flags and QC rate by week, registration "
            "pace and cards per hour by week, duplicates, QC call outcomes, weekly hours and overtime, shifts waiting "
            "for a fix or approval. Office views have one row per office; for the whole program read the matching "
            "*_total view. "
            "Don't call it for: one specific day or shift, custom joins, rules or definitions. "
            'Example: {"view": "v_office_pace_total"}.'
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "view": {"type": "string", "enum": sorted(VIEWS)},
                "office": {"type": "string", "enum": OFFICES,
                           "description": "Only when the question names one office. Leave it out otherwise."},
                "week_start": {"type": "string", "enum": WEEKS,
                               "description": "Only when the question names one week, for weekly views. Leave it out "
                                              "to compare weeks. This week is 2026-10-12, last week 2026-10-05; "
                                              "\"this week\" and \"last week\" name a week."},
            },
            "required": ["view"],
        },
    },
    {
        "name": "query_program_data",
        "description": (
            "Call this only when no view has the number: one day (for example Oct 12), one shift, one canvasser's "
            "knocks, or a join across tables. Runs one read-only Postgres SELECT over the tables and views in the "
            "system prompt; results are capped at 200 rows. "
            "Don't call it for rules or definitions, or for anything a view already gives as a column. "
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
            "Call this for definitions, rules, methods and the reasons behind numbers: how doors, attempts and contacts are "
            "counted, why the client's report differs from ours, QC rules (flash knocking, householding, gaps, apartments), "
            "the program plan (goals, projection method, regulars, more doors or a second pass, a new office), payroll "
            "rules (overtime, approval, deadline), client reporting and the registration drive. "
            "Don't call it for numbers. "
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


DATE_LITERAL = re.compile(r"'(20\d\d-\d\d-\d\d)'")


def date_lint(sql: str, tables: list[str]) -> str:
    """A hint when a query's dates fall outside the data (Sep 21 to Oct 18; goals run to Nov 3)."""
    dates = DATE_LITERAL.findall(sql)
    late = [d for d in dates if d > DATA_END]
    early = [d for d in dates if d < DATA_START]
    if late and "daily_goals" not in tables:
        return (f"\n(Note: {', '.join(sorted(set(late)))} is after the last day of data, {DATA_END}. "
                "This week is Oct 12 to 18 and last week Oct 5 to 11.)")
    if early:
        return f"\n(Note: {', '.join(sorted(set(early)))} is before the first day of data, {DATA_START}.)"
    return ""


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
        about = [f"{t}: {VIEW_NOTES[t]}" for t in checked.tables if t in VIEW_NOTES]
        note += date_lint(sql, checked.tables) if tool == "query_program_data" else ""
        content = (f"tables: {', '.join(checked.tables)}\n" + "".join(f"rows of {a}\n" for a in about)
                   + "\n".join(lines) + note)
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
        # Lists of single flags, shifts or people across weeks: say how many rows each week has, so a reader picking
        # out one week's rows can check the count.
        if res.ok and res.rows and not week and view in COUNT_BY_WEEK and "week_start" in res.columns:
            i = res.columns.index("week_start")
            counts: dict[str, int] = {}
            for r in res.rows:
                counts[str(r[i])] = counts.get(str(r[i]), 0) + 1
            line = "Rows per week_start: " + ", ".join(f"{w}: {n}" for w, n in sorted(counts.items(), reverse=True))
            lines = res.content.split("\n")
            res.content = "\n".join(lines[:2] + [line] + lines[2:])  # after the table and grain lines
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
