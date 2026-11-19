import pytest

from program_data_assistant.sql_guard import SQLRejected, check


@pytest.mark.parametrize("sql,tables", [
    ("SELECT * FROM v_office_pace", ["v_office_pace"]),
    ("select office, count(*) from knocks where not rolled_back group by office;", ["knocks"]),
    ("WITH d AS (SELECT office, doors FROM v_daily_doors) SELECT office, sum(doors) FROM d GROUP BY office", ["v_daily_doors"]),
    ("SELECT office FROM offices UNION ALL SELECT office FROM vr_goals", ["offices", "vr_goals"]),
    ("SELECT c.full_name FROM program.canvassers c JOIN shifts s USING (canvasser_id)", ["canvassers", "shifts"]),
    ("SELECT km_between(1, 2, 3, 4)", []),
])
def test_accepts_read_only_selects(sql, tables):
    assert check(sql).tables == tables


@pytest.mark.parametrize("sql", [
    "",
    "DELETE FROM knocks",
    "UPDATE shifts SET paid_hours = 0",
    "INSERT INTO offices VALUES ('X', 'y', 0, 0, now())",
    "DROP TABLE knocks",
    "SELECT 1; DROP TABLE knocks",
    "SELECT * INTO copy_of_knocks FROM knocks",
    "SELECT * FROM shifts FOR UPDATE",
    "SELECT pg_sleep(10)",
    "SELECT set_config('statement_timeout', '0', false)",
    "SELECT * FROM pg_catalog.pg_roles",
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM docs.chunks",
    "SELECT * FROM voters",
    "COPY knocks TO '/tmp/x.csv'",
    "GRANT ALL ON knocks TO public",
    "SELEC office FROM offices",
])
def test_rejects_everything_else(sql):
    with pytest.raises(SQLRejected):
        check(sql)


def test_rejection_message_lists_tables():
    with pytest.raises(SQLRejected, match="v_office_pace"):
        check("SELECT * FROM goals")
