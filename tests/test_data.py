"""The generated data is deterministic and tells the stories the demo questions rely on."""

import filecmp
import tempfile
from pathlib import Path

from program_data_assistant import datagen, db


def q(sql):
    with db.connect_reader() as conn:
        return conn.execute(sql).fetchall()


def test_generator_is_deterministic_and_matches_committed_csvs():
    out = Path(tempfile.mkdtemp(prefix="pda-gen-"))
    datagen.generate(out)
    committed = db.REPO / "data" / "csv"
    names = sorted(p.name for p in committed.glob("*.csv"))
    match, mismatch, errors = filecmp.cmpfiles(committed, out, names, shallow=False)
    assert mismatch == [] and errors == []


def test_eastgate_and_harbor_miss_goal_northside_does_not():
    rows = dict(q("SELECT office, projected_vs_goal FROM v_office_pace"))
    assert rows["Eastgate"] < rows["Harbor"] < 0 < rows["Northside"]


def test_oct_12_gap_is_mostly_a_rollback():
    (doors, attempts, rb), = q("SELECT doors, attempts, rolled_back_attempts FROM v_daily_doors_total "
                               "WHERE knock_date = '2026-10-12'")
    (reported,), = q("SELECT sum(doors_reported) FROM client_daily_report WHERE report_date = '2026-10-12'")
    assert reported == attempts and rb > (attempts - doors) / 2


def test_dense_untouched_cluster_and_best_site():
    dense = q("SELECT count(*) FROM v_precinct_coverage WHERE coverage = 'untouched' AND doors_per_sq_mi > 2000")[0][0]
    assert dense == 4
    best = q("SELECT name FROM v_site_options ORDER BY avg_km_to_untouched_doors LIMIT 1")[0][0]
    assert best == "Mill Street storefront"


def test_one_canvasser_drives_householding_and_one_drives_duplicates():
    top = q("""SELECT c.full_name, count(*) FROM qc_flags f JOIN canvassers c USING (canvasser_id)
               WHERE f.flag_date >= '2026-10-12' AND f.flag_type = 'householding' GROUP BY 1 ORDER BY 2 DESC""")
    assert top[0] == ("Dorian Pratt", 3) and all(n == 1 for _, n in top[1:])
    dup = q("""SELECT c.full_name FROM vr_cards v JOIN canvassers c USING (canvasser_id)
               GROUP BY 1 ORDER BY count(*) FILTER (WHERE is_duplicate) DESC LIMIT 1""")
    assert dup[0][0] == "Renata Cole"


def test_overtime_people():
    names = {r[0] for r in q("SELECT full_name FROM v_weekly_hours WHERE week_start = '2026-10-12' AND over_threshold")}
    assert names == {"Ellis Warren", "Sofia Lindqvist", "Marcus Bell"}


def test_registration_offices_under_needed_rate():
    rows = dict(q("SELECT office, cards_per_hour_last_7d FROM v_vr_pace"))
    needed = q("SELECT cards_per_hour_needed FROM v_vr_pace_total")[0][0]
    assert rows["Eastgate"] < needed and rows["Harbor"] < needed < rows["Northside"]


def test_regulars_follow_the_program_plan_and_leave_out_registration_canvassers():
    # Program plan: regular = 5 or more days worked, active = a shift in the last 7 days, GOTV canvassers only.
    (active, regulars), = q("SELECT active_canvassers, active_regulars FROM v_gotv_staff_total")
    (truth,), = q("""SELECT count(*) FROM (SELECT canvasser_id FROM shifts WHERE program = 'gotv' GROUP BY canvasser_id
                     HAVING count(DISTINCT shift_date) >= 5 AND max(shift_date) >= '2026-10-12') x""")
    assert (active, regulars) == (57, truth) == (57, 49)
    assert q("SELECT count(*) FROM v_canvasser_status WHERE program = 'vr' AND staff_type <> 'registration'") == [(0,)]
    by_office = q("SELECT sum(active_regulars) FROM v_gotv_staff")[0][0]
    assert by_office == regulars


SUMMABLE = [("v_daily_doors", "doors, contacts, attempts, rolled_back_attempts", "knock_date"),
            ("v_qc_weekly", "shifts, flags, householding", "week_start"),
            ("v_turf_summary", "precincts, target_doors, doors_untouched", "coverage, density"),
            ("v_office_pace", "goal_total, doors_to_date, turf_doors, doors_untouched", "1"),
            ("v_contact_rates", "doors, contacts", "week_start"),
            ("v_cost_per_door", "paid_hours, wages, doors", "1"),
            ("v_weekly_report", "doors, contacts, valid_cards, paid_hours", "week_start"),
            ("v_weekly_pace", "door_goal, doors, contacts", "week_start"),
            ("v_weekly_shifts", "shifts, shifts_with_hours, paid_hours, wages", "program, week_start"),
            ("v_vr_weekly", "valid_cards, duplicate_cards, paid_hours", "week_start"),
            ("v_vr_pace", "card_goal, cards_collected, valid_cards", "1"),
            ("v_gotv_staff", "gotv_canvassers, active_canvassers, active_regulars", "1"),
            ("v_qc_call_outcomes", "calls", "outcome")]


def test_office_views_hold_no_total_rows_and_add_up_to_their_total_view():
    # A model that adds up an office view's rows gets the program total, never twice it (the n01 / q05 lesson).
    for view, cols, key in SUMMABLE:
        assert q(f"SELECT count(*) FROM {view} WHERE office = 'All offices'") == [(0,)], view
        assert q(f"SELECT DISTINCT office FROM {view}_total") == [("All offices",)], view
        sums = ", ".join(f"round(sum({c}), 2)" for c in cols.split(", "))
        group = "" if key == "1" else f" GROUP BY {key} ORDER BY {key}"
        offices = q(f"SELECT {'' if key == '1' else key + ', '}{sums} FROM {view}{group}")
        total = q(f"SELECT {'' if key == '1' else key + ', '}{', '.join(f'round({c}, 2)' for c in cols.split(', '))} "
                  f"FROM {view}_total{'' if key == '1' else ' ORDER BY ' + key}")
        assert [tuple(map(str, r)) for r in offices] == [tuple(map(str, r)) for r in total], view
    # QC got better program-wide from last week to this week: 8 flags in 184 shifts, then 7 in 205.
    rows = q("SELECT week_start::text, flags, shifts, flags_per_100_shifts FROM v_qc_weekly_total "
             "WHERE week_start >= '2026-10-05' ORDER BY 1")
    assert [(f, s, float(r)) for _, f, s, r in rows] == [(8, 184, 4.3), (7, 205, 3.4)]


def test_views_built_on_daily_doors_do_not_count_the_total_twice():
    (pace,), = q("SELECT doors_to_date FROM v_office_pace_total")
    (doors,), = q("SELECT sum(doors) FROM v_daily_doors")
    assert pace == doors == 33503
    (week,), = q("SELECT doors FROM v_contact_rates_total WHERE week_start = '2026-10-12'")
    (report,), = q("SELECT doors FROM v_weekly_report_total WHERE week_start = '2026-10-12'")
    assert week == report == q("SELECT sum(doors) FROM v_daily_doors_total WHERE knock_date >= '2026-10-12'")[0][0]


def test_untouched_doors_shift_length_wages_and_weekly_views_match_the_raw_tables():
    # untouched doors across all turf, including the untouched doors of partly covered precincts
    (untouched,), = q("SELECT doors_untouched FROM v_office_pace_total")
    assert untouched == q("SELECT (SELECT sum(target_doors) FROM precincts) - count(DISTINCT door_id) FROM knocks "
                          "WHERE NOT rolled_back")[0][0]
    # shift length leaves out shifts with no clock out
    (avg, with_hours, shifts), = q("SELECT avg_shift_hours, shifts_with_hours, shifts FROM v_weekly_shifts "
                                   "WHERE office = 'Harbor' AND program = 'gotv' AND week_start = '2026-10-12'")
    raw = q("SELECT round(avg(paid_hours), 2), count(paid_hours), count(*) FROM shifts "
            "WHERE office = 'Harbor' AND program = 'gotv' AND shift_date >= '2026-10-12'")[0]
    assert (avg, with_hours, shifts) == raw and with_hours < shifts
    # wages use each person's own rate
    (wages,), = q("SELECT wages FROM v_weekly_shifts_total WHERE program = 'gotv' AND week_start = '2026-10-12'")
    assert wages == q("SELECT round(sum(s.paid_hours * p.hourly_rate), 2) FROM shifts s JOIN canvassers c USING "
                      "(canvasser_id) JOIN pay_rates p USING (role) WHERE s.program = 'gotv' AND s.shift_date >= '2026-10-12'")[0][0]
    # last week's goal and registration rate
    assert q("SELECT door_goal, doors FROM v_weekly_pace_total WHERE week_start = '2026-10-05'") == [(8779, 8863)]
    (rate,), = q("SELECT cards_per_hour FROM v_vr_weekly WHERE office = 'Eastgate' AND week_start = '2026-10-05'")
    assert float(rate) == 2.56
