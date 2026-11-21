# Recorded demo runs

`recorded_runs.json` holds real runs of the 19 demo questions so a web page can show them without the backend or a model. No answer, tool call or source in it is written or edited by hand: each is what the assistant produced in an eval run. The only hand-written text is the one-line `eval.note` on some questions, which says why that answer was scored as it was.

## How it was produced

1. `uv run pda-load` on the committed data in `data/csv`.
2. The baseline: `uv run evals --label baseline` at the baseline commit, `qwen2.5:7b` through Ollama on an 8-core CPU machine with no GPU, at temperature 0.
3. The final code: `uv run evals --split dev --repeat 3 --label final-qwen38-27b-dev-x3` and `uv run evals --split test --repeat 3 --label final-qwen38-27b-test-x3`, `qwen3.8:27b` through Ollama on a laptop RTX 3080 with a 16k context, at temperature 0.
4. Every report rescored with the current cases: `uv run evals --rescore evals/reports/<name>.json` (no model calls).
5. The export:

```bash
uv run pda-demo --before evals/reports/baseline.json \
  --after evals/reports/final-qwen38-27b-dev-x3.json --after evals/reports/final-qwen38-27b-test-x3.json \
  --what-changed "..." --split-note "..." \
  --note 'q04=...' --note 'q07=...' --note 'q08=...' --note 'q12=...' --note 'q13=...' \
  --out demo/recorded_runs.json
```

The `--what-changed`, `--split-note` and `--note` texts are the ones in the file (`scoreboard.what_changed`, `scoreboard.split_note`, `questions[].eval.note`).

## Shape

Top level: `program`, `generated_at`, `model`, `scoreboard`, and `questions`.

`scoreboard.before` is the baseline: totals per metric, plus `heldout` and `tuned` blocks (the same answers grouped by today's split). `scoreboard.after` has `heldout` and `tuned` blocks for the final code: `cases`, `runs_per_case`, `pass` (cases passed), `pass_all_runs` (cases that passed on every run, pass^3 here), the per-metric means and `avg_latency_ms`. Also `headline`, `split_note`, `what_changed` and the latency fields.

Each question:

| field | meaning |
| --- | --- |
| `id`, `question`, `category`, `keywords` | the case from `evals/cases.yaml`; `keywords` help match a typed question to a recorded one |
| `tool_calls[]` | `name`, `args`, and `result`, a short summary of what the tool returned |
| `sources[]` | `{type: "rows", table, columns, rows}` (at most 8 rows) or `{type: "passage", doc, text}` |
| `answer`, `refused`, `latency_ms`, `model` | the final-code run (run 1 of 3) |
| `baseline` | the same fields (`tool_calls`, `sources`, `answer`, `refused`, `latency_ms`) from the baseline run |
| `eval.before`, `eval.after` | per-metric scores for this question in each run (`null` where a metric doesn't apply) |
| `eval.note` | optional: one line on why the shown answer was scored as it was |

`recorded_runs.sample.json` is an early two-question sample from the baseline run, kept only so the page shape could be built before the full runs finished.

Latency is wall-clock time for the whole question (all model turns and tool calls) on the machine that ran it.
