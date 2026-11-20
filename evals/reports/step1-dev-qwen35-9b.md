# Eval report: step1-dev-qwen35-9b

Model `ollama/qwen3.5:9b`, commit `b2621ed`, 2026-11-20T03:29:57+00:00, 14 cases (split dev, 1 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.92 | 12 |
| retrieval | 0.96 | 12 |
| facts | 0.75 | 12 |
| citation | 0.92 | 12 |
| refusal | 0.93 | 14 |
| pass | 0.71 | 14 |
| pass_all | 0.71 | 14 |

Average latency 6.5 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 17 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q05 | door gaps | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 9 |
| q07 | client report | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 11 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q11 | QC | 1.00 | 0.50 | 0.00 | 0.00 | 0.00 | 0.00 | 6 |
| q13 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 4 |

## Missed facts

- q01: projected doors, all offices
- q05: untouched doors left in turf, doors we can knock in the days left
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12, explains rollback
- q11: Dorian Pratt, Jalen Ortiz, Tomas Reyes, Priya Nandakumar, Dorian's householding flags this week
