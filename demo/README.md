# Recorded demo runs

`recorded_runs.json` holds real runs of the 19 demo questions so a web page can show them without the backend or a model. Nothing in it is written or edited by hand: every answer, tool call and source is what the assistant produced in an eval run.

## How it was produced

1. `uv run pda-load` on the committed data in `data/csv`.
2. `uv run evals --label baseline` at the baseline commit, then `uv run evals --label improved` after the changes described in `scoreboard.what_changed`. Both used `qwen2.5:7b` through Ollama on an 8-core CPU machine with no GPU, at temperature 0.
3. `uv run pda-demo --before evals/reports/baseline.json --after evals/reports/improved.json --what-changed "..." --out demo/recorded_runs.json`.

## Shape

Top level: `program`, `generated_at`, `model`, `scoreboard` (`before` and `after` totals per metric, plus `what_changed`), and `questions`.

Each question:

| field | meaning |
| --- | --- |
| `id`, `question`, `category`, `keywords` | the case from `evals/cases.yaml`; `keywords` help match a typed question to a recorded one |
| `tool_calls[]` | `name`, `args`, and `result`, a short summary of what the tool returned |
| `sources[]` | `{type: "rows", table, columns, rows}` (at most 8 rows) or `{type: "passage", doc, text}` |
| `answer`, `refused`, `latency_ms`, `model` | the improved run |
| `baseline` | the same fields (`tool_calls`, `sources`, `answer`, `refused`, `latency_ms`) from the baseline run |
| `eval.before`, `eval.after` | per-metric scores for this question in each run (`null` where a metric doesn't apply) |

`recorded_runs.sample.json` is an early two-question sample from the baseline run, kept only so the page shape could be built before the full runs finished.

Latency is wall-clock time for the whole question (all model turns and tool calls) on that CPU machine.
