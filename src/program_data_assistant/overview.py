"""Office summaries for the web app's office tabs, read straight from the metric views (no model)."""

from __future__ import annotations

import json
from pathlib import Path

from . import db
from .tools import _plain

OFFICES = ["All offices", "Northside", "Eastgate", "Harbor"]
RECORDED = db.REPO / "demo" / "recorded_runs.json"


def _rows(conn, sql: str, params=()) -> list[dict]:
    cur = conn.execute(sql, params)
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, (_plain(v) for v in r))) for r in cur.fetchall()]


def offices(conn) -> dict:
    """One entry per office plus 'All offices': pace, contact rate by week, cost per door, registration, QC."""
    as_of = _rows(conn, "SELECT as_of_date, this_week_start FROM program_settings")[0]
    week = as_of["this_week_start"]
    pace = {r["office"]: r for r in _rows(conn, "SELECT * FROM v_office_pace")}
    rates: dict[str, list] = {}
    for r in _rows(conn, "SELECT office, week_start, contact_rate_pct FROM v_contact_rates ORDER BY week_start"):
        rates.setdefault(r["office"], []).append({"week_start": r["week_start"], "contact_rate_pct": r["contact_rate_pct"]})
    cost = {r["office"]: r["cost_per_door"] for r in _rows(conn, "SELECT office, cost_per_door FROM v_cost_per_door")}
    vr = {r["office"]: r for r in _rows(conn, "SELECT * FROM v_vr_pace")}
    qc = {r["office"]: r for r in _rows(conn, "SELECT office, shifts, flags, flags_per_100_shifts FROM v_qc_weekly WHERE week_start = %s",
                                         (week,))}
    if qc:
        shifts = sum(r["shifts"] for r in qc.values())
        flags = sum(r["flags"] for r in qc.values())
        qc["All offices"] = {"flags": flags, "flags_per_100_shifts": round(100.0 * flags / shifts, 1) if shifts else None}
    out = []
    for office in OFFICES:
        p, v, q = pace.get(office, {}), vr.get(office, {}), qc.get(office, {})
        out.append({
            "office": office,
            "pace": {k: p.get(k) for k in ("goal_total", "goal_to_date", "doors_to_date", "projected_total", "projected_vs_goal",
                                           "projected_pct_of_goal", "avg_shifts_per_day_last_7d", "extra_shifts_per_day_needed")},
            "contact_rates": rates.get(office, []),
            "cost_per_door": cost.get(office),
            "registration": {k: v.get(k) for k in ("card_goal", "valid_cards", "duplicate_cards", "cards_per_hour_last_7d",
                                                   "cards_per_hour_needed", "projected_valid_cards")},
            "qc_this_week": {"flags": q.get("flags"), "flags_per_100_shifts": q.get("flags_per_100_shifts")},
        })
    return {"as_of": as_of["as_of_date"], "offices": out}


def main() -> None:
    """Write the office summaries to a JSON file (the web app's demo mode bundles it)."""
    import argparse

    ap = argparse.ArgumentParser(description="Export the office summaries as JSON.")
    ap.add_argument("--out", default=str(db.REPO / "web" / "src" / "lib" / "demo" / "offices.json"))
    args = ap.parse_args()
    with db.connect_reader() as conn:
        data = offices(conn)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {args.out}")


def recorded(path: Path = RECORDED) -> dict:
    return json.loads(path.read_text())


def evals(path: Path = RECORDED) -> dict:
    data = recorded(path)
    return {
        "model": data["model"],
        "scoreboard": data["scoreboard"],
        "questions": [{k: q[k] for k in ("id", "question", "category", "eval")} for q in data["questions"]],
    }
