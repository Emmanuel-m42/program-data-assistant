"""Validation for model-written SQL before it reaches the database.

The database role is already read-only with a statement timeout; this guard is the first layer.
It accepts one SELECT (with CTEs and set operations) over the program tables and views, and
rejects everything else with a message the model can act on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {
    "program_settings", "offices", "pay_rates", "canvassers", "shifts", "precincts", "knocks", "daily_goals",
    "client_daily_report", "qc_flags", "candidate_office_sites", "vr_goals", "vr_cards", "vr_qc_calls",
    "v_daily_doors", "v_office_pace", "v_precinct_coverage", "v_site_options", "v_vr_pace", "v_weekly_hours",
    "v_qc_weekly", "v_contact_rates", "v_cost_per_door", "v_weekly_report", "v_canvasser_status", "v_qc_flags_detail",
    "v_shifts_to_fix", "v_vr_canvassers", "v_qc_call_outcomes", "v_gotv_staff", "v_turf_summary",
    "v_weekly_pace", "v_weekly_shifts", "v_vr_weekly",
    # program totals, one view per office view
    "v_daily_doors_total", "v_office_pace_total", "v_vr_pace_total", "v_qc_weekly_total", "v_contact_rates_total",
    "v_cost_per_door_total", "v_weekly_report_total", "v_gotv_staff_total", "v_turf_summary_total",
    "v_qc_call_outcomes_total", "v_weekly_pace_total", "v_weekly_shifts_total", "v_vr_weekly_total",
}
ALLOWED_SCHEMAS = {"", "program"}
DENIED_FUNCTIONS = re.compile(
    r"\b(pg_sleep\w*|pg_read\w*|pg_ls_dir|pg_stat_file|pg_terminate_backend|pg_cancel_backend|lo_\w+|dblink\w*|"
    r"set_config|current_setting|query_to_xml\w*|copy)\s*\(",
    re.IGNORECASE,
)
WRITE_NODES = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command, exp.Merge,
               exp.Into, exp.Lock, exp.TruncateTable, exp.Grant)


class SQLRejected(ValueError):
    pass


@dataclass
class CheckedSQL:
    sql: str
    tables: list[str] = field(default_factory=list)


def check(sql: str) -> CheckedSQL:
    """Return the cleaned statement and the program tables it reads, or raise SQLRejected."""
    text = (sql or "").strip().rstrip(";").strip()
    if not text:
        raise SQLRejected("Empty query. Send one SELECT statement.")
    if DENIED_FUNCTIONS.search(text):
        raise SQLRejected("That function is not allowed. Use plain SELECT queries over the program tables.")
    try:
        statements = [s for s in sqlglot.parse(text, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise SQLRejected(f"Could not parse the SQL: {str(e).splitlines()[0]}") from None
    if len(statements) != 1:
        raise SQLRejected("Send exactly one statement.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.SetOperation)):
        raise SQLRejected("Only SELECT queries are allowed (WITH ... SELECT is fine).")
    for node in tree.walk():
        if isinstance(node, WRITE_NODES):
            raise SQLRejected("Only read-only SELECT queries are allowed.")
    ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    tables = []
    for t in tree.find_all(exp.Table):
        name, schema = t.name.lower(), (t.db or "").lower()
        if not name or name in ctes:
            continue
        if schema not in ALLOWED_SCHEMAS or name not in ALLOWED_TABLES:
            raise SQLRejected(
                f"Unknown table '{t.sql()}'. Use only these tables and views: {', '.join(sorted(ALLOWED_TABLES))}."
            )
        if name not in tables:
            tables.append(name)
    return CheckedSQL(text, tables)
