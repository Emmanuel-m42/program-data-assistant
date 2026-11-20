# API image: FastAPI app, the pda-load job and the embedding model, on Python 3.12.
#
#   docker build -t pda-api .
#   docker run -p 8080:8080 -e PDA_DATABASE_URL=... -e PDA_READER_URL=... -e OLLAMA_HOST=... pda-api
#
# The same image runs the schema and data load: override the command with `pda-load`.

FROM python:3.12.16-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.14 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    FASTEMBED_CACHE_PATH=/app/models
WORKDIR /app

# Dependencies first, so code changes don't reinstall them. Both Claude extras are included so
# PDA_PROVIDER can switch between ollama, anthropic and vertex without a rebuild.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra anthropic --extra vertex --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --extra anthropic --extra vertex

# Bake the embedding model (BAAI/bge-small-en-v1.5, about 130 MB) into the image, so containers
# don't download it on every cold start. A separate layer from the install on purpose.
# hadolint ignore=DL3059
RUN /app/.venv/bin/python -c "from program_data_assistant.retrieval import embed_query; embed_query('warm up')"


FROM python:3.12.16-slim-trixie

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin app
WORKDIR /app

# The package is installed in editable mode and finds data/, corpus/ and demo/ next to src/.
COPY --from=build /app/.venv ./.venv
COPY --from=build --chown=app:app /app/models ./models
COPY --from=build /app/src ./src
COPY data/csv ./data/csv
COPY corpus ./corpus
COPY demo ./demo
COPY evals/cases.yaml ./evals/cases.yaml

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/models \
    HOME=/app

USER 10001
EXPOSE 8080
CMD ["uvicorn", "program_data_assistant.api:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
