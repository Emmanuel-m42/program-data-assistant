# Eval report: step3-dev-qwen35-9b

Model `ollama/qwen3.5:9b`, commit `35a6bc5`, 2026-11-20T03:32:33+00:00, 14 cases (split dev, 1 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.83 | 12 |
| retrieval | 0.96 | 12 |
| facts | 0.84 | 12 |
| citation | 1.00 | 12 |
| refusal | 1.00 | 14 |
| pass | 0.71 | 14 |
| pass_all | 0.71 | 14 |

Average latency 5.3 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q05 | door gaps | 0.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 5 |
| q07 | client report | 0.00 | 1.00 | 0.25 | 1.00 | 1.00 | 0.00 | 4 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q11 | QC | 1.00 | 0.50 | 0.80 | 1.00 | 1.00 | 0.00 | 7 |
| q13 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 8 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 4 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |

## Missed facts

- q05: untouched doors left in turf, doors we can knock in the days left
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12
- q11: Dorian's householding flags this week
- q13: program flags per 100 shifts this week, program flags per 100 shifts last week
