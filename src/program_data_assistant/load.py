"""Create the schema, load the CSVs and embed the program documents.

Run: uv run pda-load
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from psycopg import sql

from . import db, retrieval

SQL_DIR = Path(__file__).parent / "sql"
DATA_DIR = db.REPO / "data" / "csv"
CORPUS_DIR = db.REPO / "corpus"

# Load order respects foreign keys.
TABLES = [
    "program_settings", "offices", "pay_rates", "canvassers", "shifts", "precincts", "knocks", "daily_goals",
    "client_daily_report", "qc_flags", "candidate_office_sites", "vr_goals", "vr_cards", "vr_qc_calls",
]


def load_tables(conn, data_dir: Path) -> dict[str, int]:
    counts = {}
    for table in TABLES:
        path = data_dir / f"{table}.csv"
        with open(path, newline="") as fh:
            header = next(csv.reader(fh))
        cols = ", ".join(header)
        with conn.cursor() as cur, open(path, "rb") as fh:
            with cur.copy(f"COPY program.{table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')") as cp:
                while data := fh.read(1 << 16):
                    cp.write(data)
        counts[table] = conn.execute(f"SELECT count(*) FROM program.{table}").fetchone()[0]
    conn.execute("ANALYZE")
    return counts


def load_docs(conn, corpus_dir: Path) -> int:
    corpus = retrieval.load_corpus(corpus_dir)
    chunks = [c for *_, cs in corpus for c in cs]
    vectors = retrieval.embed_passages([retrieval.passage_text(c) for c in chunks])
    with conn.cursor() as cur:
        for doc_id, title, path, _ in corpus:
            cur.execute("INSERT INTO docs.documents VALUES (%s, %s, %s)", (doc_id, title, path.name))
        for c, v in zip(chunks, vectors):
            cur.execute("INSERT INTO docs.chunks VALUES (%s, %s, %s, %s, %s::vector)",
                        (c.chunk_id, c.doc_id, c.heading, c.text, str(v)))
    return len(chunks)


def set_reader_password(conn, reader_url: str | None) -> bool:
    """Give the read-only role the password in PDA_READER_URL, if it has one.

    Local pgserver trusts local connections, so its URL has no password and nothing changes. A hosted
    Postgres such as Cloud SQL needs one, and this keeps the reader URL the single place it is set.
    """
    password = urlsplit(reader_url).password if reader_url else None
    if not password:
        return False
    conn.execute(sql.SQL("ALTER ROLE {} WITH PASSWORD {}").format(
        sql.Identifier(db.READER_ROLE), sql.Literal(unquote(password))))
    return True


def load_all(data_dir: Path = DATA_DIR, corpus_dir: Path = CORPUS_DIR) -> dict:
    with db.connect_admin() as conn:
        conn.execute((SQL_DIR / "schema.sql").read_text())
        set_reader_password(conn, os.environ.get("PDA_READER_URL"))
        counts = load_tables(conn, data_dir)
        counts["docs.chunks"] = load_docs(conn, corpus_dir)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description="Create the schema and load data and documents.")
    ap.add_argument("--data", default=str(DATA_DIR))
    ap.add_argument("--corpus", default=str(CORPUS_DIR))
    args = ap.parse_args()
    for table, n in load_all(Path(args.data), Path(args.corpus)).items():
        print(f"{table:24} {n}")


if __name__ == "__main__":
    main()
