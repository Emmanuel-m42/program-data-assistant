"""Database connections.

Set PDA_DATABASE_URL to use any Postgres with pgvector (for example the docker-compose service).
Without it, a local Postgres is started from the `pgserver` package with its data in PDA_PGDATA
(default .pgdata/ in the repo), which needs no Docker or root.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg

REPO = Path(__file__).resolve().parents[2]
READER_ROLE = "pda_reader"


@lru_cache(maxsize=None)
def _local_server(pgdata: str):
    import pgserver

    return pgserver.get_server(pgdata, cleanup_mode="stop")


def admin_url() -> str:
    url = os.environ.get("PDA_DATABASE_URL")
    if url:
        return url
    pgdata = os.environ.get("PDA_PGDATA", str(REPO / ".pgdata"))
    return _local_server(str(Path(pgdata).resolve())).get_uri()


def reader_url() -> str:
    """Same database, connecting as the read-only role used by the SQL tool."""
    url = os.environ.get("PDA_READER_URL")
    if url:
        return url
    parts = urlsplit(admin_url())
    host = parts.netloc.split("@", 1)[-1]
    return urlunsplit((parts.scheme, f"{READER_ROLE}@{host}", parts.path, parts.query, parts.fragment))


def connect_admin() -> psycopg.Connection:
    return psycopg.connect(admin_url(), autocommit=True)


def connect_reader() -> psycopg.Connection:
    conn = psycopg.connect(reader_url(), autocommit=True)
    # Belt and braces: the role already defaults to these.
    conn.execute("SET default_transaction_read_only = on")
    conn.execute("SET statement_timeout = '5s'")
    conn.execute("SET search_path = program")
    return conn
