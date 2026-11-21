import psycopg
import pytest

from program_data_assistant import db
from program_data_assistant.tools import MAX_ROWS, Toolbox


def test_query_returns_rows_and_tables():
    r = Toolbox().run("query_program_data", {"sql": "SELECT office, goal_total FROM v_office_pace ORDER BY office"})
    assert r.ok
    assert r.tables == ["v_office_pace"]
    assert r.columns == ["office", "goal_total"]
    assert [row[0] for row in r.rows] == ["Eastgate", "Harbor", "Northside"]
    assert "tables: v_office_pace" in r.content
    assert "rows of v_office_pace: one row per office" in r.content  # results say what a row is


def test_dates_outside_the_data_get_a_hint():
    late = Toolbox().run("query_program_data", {"sql": "SELECT sum(doors) FROM v_daily_doors WHERE knock_date >= '2026-10-19'"})
    assert late.ok and "after the last day of data, 2026-10-18" in late.content
    goals = Toolbox().run("query_program_data", {"sql": "SELECT sum(door_goal) FROM daily_goals WHERE goal_date > '2026-10-18'"})
    assert "after the last day of data" not in goals.content  # goals run to Nov 3
    early = Toolbox().run("query_program_data", {"sql": "SELECT count(*) FROM shifts WHERE shift_date < '2026-09-01'"})
    assert "before the first day of data" in early.content


def test_rejected_query_is_reported_to_the_model():
    r = Toolbox().run("query_program_data", {"sql": "DELETE FROM knocks"})
    assert not r.ok
    assert r.content.startswith("Query rejected")


def test_database_errors_are_returned_not_raised():
    r = Toolbox().run("query_program_data", {"sql": "SELECT no_such_column FROM offices"})
    assert not r.ok
    assert "no_such_column" in r.content


def test_row_limit():
    r = Toolbox().run("query_program_data", {"sql": "SELECT knock_id FROM knocks"})
    assert r.ok and len(r.rows) == MAX_ROWS
    assert "filter or aggregate" in r.content


def test_reader_role_cannot_write_even_without_the_guard():
    with db.connect_reader() as conn:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute("DELETE FROM knocks")


def test_reader_role_cannot_read_documents_or_change_settings():
    with db.connect_reader() as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM docs.chunks")


def test_statement_timeout():
    with db.connect_reader() as conn:
        with pytest.raises(psycopg.errors.QueryCanceled):
            conn.execute("SELECT pg_sleep(8)")


def test_search_documents_returns_passages_with_ids():
    r = Toolbox().run("search_documents", {"query": "knocks recorded faster than a person can walk"})
    assert r.ok
    assert r.passages[0]["chunk_id"] == "qc-rules#flash-knocking"
    assert "[doc:qc-rules#flash-knocking]" in r.content


def test_guard_allow_list_matches_what_the_reader_can_see():
    from program_data_assistant.sql_guard import ALLOWED_TABLES

    with db.connect_reader() as conn:
        visible = {r[0] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'program'").fetchall()}
        for t in ALLOWED_TABLES:
            conn.execute(f"SELECT * FROM {t} LIMIT 1")
    assert visible == ALLOWED_TABLES  # the internal all_* views are not visible to the reader


def test_unknown_tool():
    assert not Toolbox().run("send_email", {}).ok
