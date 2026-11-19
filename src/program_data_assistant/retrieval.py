"""Document chunking, embeddings and vector search over the program documents."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

EMBED_MODEL = os.environ.get("PDA_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DEFAULT_K = 4


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    heading: str
    text: str


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def chunk_markdown(doc_id: str, markdown: str) -> tuple[str, list[Chunk]]:
    """Split a document on its '## ' headings. Each chunk carries the document title and heading."""
    lines = markdown.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("# ") else doc_id
    chunks: list[Chunk] = []
    heading, buf = "Overview", []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            chunks.append(Chunk(f"{doc_id}#{slug(heading)}", doc_id, title, heading, body))

    for line in lines[1:]:
        if line.startswith("## "):
            flush()
            heading, buf = line[3:].strip(), []
        else:
            buf.append(line)
    flush()
    return title, chunks


def load_corpus(folder: Path) -> list[tuple[str, str, Path, list[Chunk]]]:
    out = []
    for path in sorted(folder.glob("*.md")):
        title, chunks = chunk_markdown(path.stem, path.read_text())
        out.append((path.stem, title, path, chunks))
    return out


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    cache = os.environ.get("FASTEMBED_CACHE_PATH", str(Path.home() / ".cache" / "pda-models"))
    return TextEmbedding(EMBED_MODEL, cache_dir=cache)


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _model().embed(texts)]


def embed_query(text: str) -> list[float]:
    return next(iter(_model().embed([QUERY_PREFIX + text]))).tolist()


def passage_text(c: Chunk) -> str:
    return f"{c.title}: {c.heading}\n{c.text}"


def search(conn, query: str, k: int = DEFAULT_K) -> list[dict]:
    """Top-k chunks by cosine distance. Returns chunk id, doc id, heading, text and score."""
    vec = embed_query(query)
    rows = conn.execute(
        """
        SELECT chunk_id, doc_id, heading, text, 1 - (embedding <=> %s::vector) AS score
        FROM docs.chunks ORDER BY embedding <=> %s::vector LIMIT %s
        """,
        (str(vec), str(vec), k),
    ).fetchall()
    return [dict(chunk_id=r[0], doc_id=r[1], heading=r[2], text=r[3], score=round(float(r[4]), 3)) for r in rows]
