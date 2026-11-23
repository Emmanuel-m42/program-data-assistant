import os
import shutil
import tempfile
from pathlib import Path

import pytest

from program_data_assistant.llm import Reply, ToolCall


@pytest.fixture(scope="session", autouse=True)
def database():
    """A throwaway local Postgres with the program data and documents loaded."""
    tmp = tempfile.mkdtemp(prefix="pda-test-pg-")
    old = {k: os.environ.get(k) for k in ("PDA_PGDATA", "PDA_DATABASE_URL", "PDA_READER_URL")}
    os.environ["PDA_PGDATA"] = tmp
    os.environ.pop("PDA_DATABASE_URL", None)
    os.environ.pop("PDA_READER_URL", None)
    from program_data_assistant import db, load

    load.load_all()
    yield Path(tmp)
    db._local_server(str(Path(tmp).resolve())).cleanup()
    shutil.rmtree(tmp, ignore_errors=True)
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


class ScriptedProvider:
    """Stands in for a model: returns the scripted replies in order."""

    name = "scripted"
    model = "test"

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def chat(self, messages, tools, format=None):
        self.seen.append(messages[-1])
        return self.replies.pop(0)


def sql_call(sql):
    return Reply("", [ToolCall("c1", "query_program_data", {"sql": sql})])


def search_call(query):
    return Reply("", [ToolCall("c2", "search_documents", {"query": query})])


def view_call(view):
    return Reply("", [ToolCall("c3", "get_view", {"view": view})])


@pytest.fixture
def scripted():
    return ScriptedProvider
