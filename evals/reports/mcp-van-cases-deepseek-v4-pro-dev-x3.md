# Eval report: mcp-van-cases-deepseek-v4-pro-dev-x3

Model `openai_compat/deepseek-v4-pro`, commit `6155e6e`, 2026-11-21T02:58:02+00:00, 4 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 3 |
| facts | 1.00 | 3 |
| citation | 1.00 | 3 |
| refusal | 0.83 | 4 |
| pass | 0.83 | 4 |
| pass_all | 0.75 | 4 |

Average latency 7.8 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v01 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| v02 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| v03 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| v04 | VAN | n/a | n/a | n/a | n/a | 0.33 | 0.33 | 15 |

## Missed facts

