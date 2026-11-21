# Eval report: final-qwen38-27b-dev-x3

Model `ollama/qwen3.8:27b`, commit `5e6eac2`, 2026-11-20T06:08:10+00:00, 14 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 12 |
| retrieval | 0.96 | 12 |
| facts | 0.92 | 12 |
| citation | 1.00 | 12 |
| refusal | 1.00 | 14 |
| pass | 0.86 | 14 |
| pass_all | 0.86 | 14 |

Average latency 57.3 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 117 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 38 |
| q05 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 107 |
| q07 | client report | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 75 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 61 |
| q11 | QC | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 77 |
| q13 | QC | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 84 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 29 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 25 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 41 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 63 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 37 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 35 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 26 |

## Missed facts

- q07: client reported doors Oct 12, dashboard doors Oct 12
- q13: program-wide QC is getting better, program flags per 100 shifts this week, program flags per 100 shifts last week
