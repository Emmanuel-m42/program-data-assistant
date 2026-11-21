# Eval report: mcp-van-original-deepseek-v4-pro-test-x3

Model `openai_compat/deepseek-v4-pro`, commit `6155e6e`, 2026-11-21T03:12:48+00:00, 14 cases (split test, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.95 | 13 |
| retrieval | 1.00 | 13 |
| facts | 0.92 | 13 |
| citation | 1.00 | 13 |
| refusal | 1.00 | 14 |
| pass | 0.81 | 14 |
| pass_all | 0.79 | 14 |

Average latency 9.5 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q04 | staffing | 0.33 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 16 |
| q06 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q08 | door gaps | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.33 | 33 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q12 | QC | 1.00 | 1.00 | 0.75 | 1.00 | 1.00 | 0.00 | 16 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| q16 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 12 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 11 |

## Missed facts

- q04: active canvassers
- q12: open flag count
