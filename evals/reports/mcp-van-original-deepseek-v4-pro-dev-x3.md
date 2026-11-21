# Eval report: mcp-van-original-deepseek-v4-pro-dev-x3

Model `openai_compat/deepseek-v4-pro`, commit `6155e6e`, 2026-11-21T03:06:05+00:00, 14 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 12 |
| retrieval | 0.96 | 12 |
| facts | 0.96 | 12 |
| citation | 1.00 | 12 |
| refusal | 1.00 | 14 |
| pass | 0.93 | 14 |
| pass_all | 0.93 | 14 |

Average latency 9.3 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q05 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 25 |
| q07 | client report | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 17 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q11 | QC | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 12 |
| q13 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 13 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 9 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 8 |

## Missed facts

- q07: client reported doors Oct 12, dashboard doors Oct 12
