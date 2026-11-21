# Eval report: mcp-van-original-deepseek-flash-dev-x3

Model `openai_compat/deepseek-flash`, commit `6155e6e`, 2026-11-21T03:05:39+00:00, 14 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 12 |
| retrieval | 0.96 | 12 |
| facts | 0.98 | 12 |
| citation | 1.00 | 12 |
| refusal | 1.00 | 14 |
| pass | 0.95 | 14 |
| pass_all | 0.86 | 14 |

Average latency 7.0 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q05 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 20 |
| q07 | client report | 1.00 | 1.00 | 0.83 | 1.00 | 1.00 | 0.67 | 19 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q11 | QC | 1.00 | 0.50 | 0.93 | 1.00 | 1.00 | 0.67 | 7 |
| q13 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 13 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |

## Missed facts

