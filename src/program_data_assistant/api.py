"""HTTP API. Run: uv run uvicorn program_data_assistant.api:app"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import overview
from .agent import Assistant
from .llm import get_provider
from .tools import Toolbox
from .van_mcp import VanMcp


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


def create_app(assistant: Assistant | None = None) -> FastAPI:
    state: dict = {"assistant": assistant}

    @asynccontextmanager
    async def lifespan(_app):
        yield
        van = state["assistant"].toolbox.van if state["assistant"] else None
        if van is not None:
            van.close()  # stops the VAN MCP server subprocess

    app = FastAPI(title="Program data assistant", lifespan=lifespan)
    origins = [o.strip() for o in os.environ.get("PDA_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["content-type"])

    def get_assistant() -> Assistant:
        if state["assistant"] is None:
            # VAN tools come on with PDA_VAN_MCP=demo (or PDA_VAN_MCP_COMMAND); off otherwise.
            state["assistant"] = Assistant(get_provider(), Toolbox(van=VanMcp.from_env()))
        return state["assistant"]

    @app.get("/health")
    def health():
        a = get_assistant()
        try:
            a.toolbox.reader.execute("SELECT 1").fetchone()
            database = "ok"
        except Exception as e:  # report, don't crash the health check
            database = f"error: {type(e).__name__}"
        out = {"status": "ok" if database == "ok" else "degraded", "database": database,
               "model": f"{a.provider.name}/{a.provider.model}"}
        if a.toolbox.van is not None:
            out["van"] = {"server": "ngpvan-mcp", "tools": sorted(a.toolbox.van.tools)}
        return out

    @app.get("/offices")
    def offices():
        return overview.offices(get_assistant().toolbox.reader)

    @app.get("/evals")
    def evals():
        return overview.evals()

    @app.get("/recorded")
    def recorded():
        return overview.recorded()

    @app.post("/ask")
    def ask(req: AskRequest):
        try:
            ans = get_assistant().ask(req.question.strip())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"model or tool failure: {type(e).__name__}") from e
        return {"question": ans.question, "answer": ans.answer, "refused": ans.refused, "tool_calls": ans.tool_calls,
                "sources": ans.sources, "citations": ans.citations, "latency_ms": ans.latency_ms, "model": ans.model}

    return app


app = create_app()
