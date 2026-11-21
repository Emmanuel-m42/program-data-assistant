# API

The FastAPI backend (`src/program_data_assistant/api.py`). All responses are JSON. All data is the fictional demo program.

The web app calls the API at `PUBLIC_API_URL`. When that is unset or `demo`, it runs in demo mode and reads the recorded runs bundled at build time (`demo/recorded_runs.json`) instead of calling the API.

CORS: allowed origins come from `PDA_CORS_ORIGINS` (comma-separated, default `http://localhost:5173`).

## GET /health

```json
{"status": "ok", "database": "ok", "model": "ollama/qwen3.8:27b"}
```

## POST /ask

Request: `{"question": "Which offices will miss their goal, and by how much?"}` (3 to 500 characters).

Response:

```json
{
  "question": "...",
  "answer": "Eastgate and Harbor will miss goal ... [table:v_office_pace]",
  "refused": false,
  "tool_calls": [{"name": "get_view", "args": {"view": "v_office_pace"}, "ok": true, "result": "4 rows from v_office_pace"}],
  "sources": [
    {"type": "rows", "table": "v_office_pace", "columns": ["office", "goal_total"], "rows": [["Eastgate", 17800]], "row_count": 4, "sql": "SELECT ..."},
    {"type": "passage", "doc": "program-plan#pace-and-projection", "text": "..."}
  ],
  "citations": [{"type": "table", "id": "v_office_pace"}, {"type": "doc", "id": "program-plan#pace-and-projection"}],
  "latency_ms": 41000,
  "model": "ollama/qwen3.8:27b"
}
```

Citations in `answer` look like `[table:<name>]` and `[doc:<passage id>]`. Each one matches a `sources` entry: `rows` by `table` (a comma-separated list when one query read several tables), `passage` by `doc`.

## GET /offices

Office tabs. One entry per office plus `All offices`, computed straight from the metric views, no model involved.

```json
{
  "as_of": "2026-10-18",
  "offices": [
    {
      "office": "Eastgate",
      "pace": {"goal_total": 17800, "doors_to_date": 8505, "projected_total": 14596, "projected_vs_goal": -3204, "projected_pct_of_goal": 82.0, "extra_shifts_per_day_needed": 4.4},
      "contact_rates": [{"week_start": "2026-10-05", "contact_rate_pct": 28.8}, {"week_start": "2026-10-12", "contact_rate_pct": 25.0}],
      "cost_per_door": 2.07,
      "registration": {"card_goal": 1380, "valid_cards": 941, "cards_per_hour_last_7d": 2.41, "cards_per_hour_needed": 2.75},
      "qc_this_week": {"flags": 5, "flags_per_100_shifts": 8.6}
    }
  ]
}
```

## GET /evals

The eval scoreboard and the per-question results for the "How it's tested" page. Read from `demo/recorded_runs.json` (`scoreboard` plus per-question `id`, `question`, `category`, `eval`).

```json
{
  "model": "ollama/qwen3.8:27b",
  "scoreboard": {"before": {"...": "..."}, "after": {"heldout": {"cases": 14, "pass": 12, "pass_all_runs": 12}, "tuned": {"cases": 14, "pass": 12, "pass_all_runs": 12}}, "headline": "...", "headline_note": "...", "comparison": [{"model": "...", "code": "after", "groups": {"dev": {"cases": 14, "pass": 14, "pass_all_runs": 14}, "heldout_v2": {"...": "..."}}}], "split_note": "..."},
  "questions": [{"id": "q01", "question": "...", "category": "pace", "eval": {"before": {}, "after": {}, "note": "optional: why it scored as it did"}}]
}
```

## GET /recorded

The full `demo/recorded_runs.json` (the shape is in `demo/README.md`). The web app bundles the same file for demo mode.
