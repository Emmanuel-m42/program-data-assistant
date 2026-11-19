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
    (doors, attempts, rb), = q("SELECT sum(doors), sum(attempts), sum(rolled_back_attempts) FROM v_daily_doors WHERE knock_date = '2026-10-12'")
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
    needed = q("SELECT cards_per_hour_needed FROM v_vr_pace WHERE office = 'All offices'")[0][0]
    assert rows["Eastgate"] < needed and rows["Harbor"] < needed < rows["Northside"]
