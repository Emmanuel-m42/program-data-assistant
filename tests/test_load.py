from program_data_assistant import db, load


def reader_has_password(conn) -> bool:
    return conn.execute("SELECT rolpassword IS NOT NULL FROM pg_authid WHERE rolname = %s",
                        (db.READER_ROLE,)).fetchone()[0]


def test_reader_password_comes_from_the_reader_url():
    with db.connect_admin() as conn:
        try:
            assert not load.set_reader_password(conn, None)
            assert not load.set_reader_password(conn, "postgresql://pda_reader@localhost/postgres")
            assert not reader_has_password(conn)
            # Percent-encoded characters are decoded before they reach Postgres.
            url = "postgresql://pda_reader:it%27s%40demo@/postgres?host=/cloudsql/demo:us-central1:pda"
            assert load.set_reader_password(conn, url)
            assert reader_has_password(conn)
        finally:
            conn.execute(f"ALTER ROLE {db.READER_ROLE} WITH PASSWORD NULL")
