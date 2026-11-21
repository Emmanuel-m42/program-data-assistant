# Eval report: mcp-van-cases-deepseek-flash-dev-x3

Model `openai_compat/deepseek-flash`, commit `6155e6e`, 2026-11-21T02:59:23+00:00, 4 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 3 |
| facts | 0.78 | 3 |
| citation | 0.78 | 3 |
| refusal | 0.83 | 4 |
| pass | 0.83 | 4 |
| pass_all | 0.50 | 4 |

Average latency 6.7 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v01 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| v02 | VAN | 1.00 | n/a | 0.67 | 0.67 | 0.67 | 0.67 | 5 |
| v03 | VAN | 1.00 | n/a | 0.67 | 0.67 | 0.67 | 0.67 | 6 |
| v04 | VAN | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |

## Missed facts

- v03: active activist codes
