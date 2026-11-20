# Web app

SvelteKit and TypeScript front end for the program data assistant: ask a question and see the answer with its citations, the tools the model called, and the SQL rows or document passages behind each number. It also has office tabs and a page on how the assistant is tested.

## Run it

```bash
npm install
npm run dev            # http://localhost:5173, demo mode
npm run check          # svelte-check
npm test               # vitest
npm run build          # static site in build/
```

## Demo mode and live mode

`PUBLIC_API_URL` is read at build (and dev) time.

- Unset or `demo`: demo mode. Answers come from the recorded runs in `../demo/recorded_runs.json`. A typed question is matched to the closest recorded question (exact text first, then shared words and keywords); anything else gets a note that the demo only has the listed questions. Office numbers come from `src/lib/demo/offices.json`, exported from the database with `uv run pda-offices`. No network calls.
- Set to the API's address, for example `PUBLIC_API_URL=http://localhost:8000 npm run dev`: live mode. The app calls `POST /ask`, `GET /offices` and `GET /evals` (see `../docs/api.md`). Start the API with `PDA_CORS_ORIGINS=http://localhost:5173 uv run uvicorn program_data_assistant.api:app` from the repo root.

## How it's built

- `adapter-static` with an `index.html` fallback, so `build/` can be served by any static host.
- Answers are parsed into tokens (paragraphs, bullets, bold, code, citations) and rendered as text nodes, never as HTML, so nothing in an answer can inject markup.
- A citation like `[table:v_office_pace]` links to the rows source for that table; `[doc:qc-rules#gaps]` links to that passage.
- Plain CSS, no UI framework.
