# Eval report: v3-ds-flash-strict-dev-x3

Model `openai_compat/deepseek-flash`, commit `e322795`, 2026-11-21T04:39:58+00:00, 14 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 12 |
| retrieval | 0.96 | 12 |
| facts | 1.00 | 12 |
| citation | 1.00 | 12 |
| refusal | 1.00 | 14 |
| pass | 1.00 | 14 |
| pass_all | 1.00 | 14 |

By group:

| group | cases | pass | pass^3 | tool choice | retrieval | facts | citation | refusal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev (tuned) | 14 | 14 of 14 | 14 of 14 | 1.00 | 0.96 | 1.00 | 1.00 | 1.00 |

Average latency 6.3 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q05 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| q07 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q11 | QC | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 26 |
| q13 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |

## Missed facts

