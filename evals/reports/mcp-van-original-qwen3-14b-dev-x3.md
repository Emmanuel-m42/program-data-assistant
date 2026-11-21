# Eval report: mcp-van-original-qwen3-14b-dev-x3

Model `ollama/qwen3:14b`, commit `6498b17`, 2026-11-21T02:30:16+00:00, 14 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.83 | 12 |
| retrieval | 0.96 | 12 |
| facts | 0.78 | 12 |
| citation | 1.00 | 12 |
| refusal | 1.00 | 14 |
| pass | 0.71 | 14 |
| pass_all | 0.71 | 14 |

Average latency 9.8 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| q05 | door gaps | 0.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 38 |
| q07 | client report | 0.00 | 1.00 | 0.25 | 1.00 | 1.00 | 0.00 | 9 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 13 |
| q11 | QC | 1.00 | 0.50 | 0.40 | 1.00 | 1.00 | 0.00 | 14 |
| q13 | QC | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 11 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 13 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 11 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 3 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 3 |

## Missed facts

- q05: untouched doors left in turf, doors we can knock in the days left
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12
- q11: Jalen Ortiz, Tomas Reyes, Dorian's householding flags this week
- q13: Harbor flags per 100 shifts last week, program-wide QC is getting better, program flags per 100 shifts this week, program flags per 100 shifts last week
