# Eval report: mcp-van-cases-deepseek-flash-test-x3

Model `openai_compat/deepseek-flash`, commit `6155e6e`, 2026-11-21T03:00:38+00:00, 4 cases (split test, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 4 |
| facts | 0.75 | 4 |
| citation | 0.83 | 4 |
| refusal | 0.75 | 4 |
| pass | 0.75 | 4 |
| pass_all | 0.50 | 4 |

Average latency 5.8 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v05 | VAN | 1.00 | n/a | 0.33 | 0.33 | 0.33 | 0.33 | 9 |
| v06 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| v07 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| v08 | VAN | 1.00 | n/a | 0.67 | 1.00 | 0.67 | 0.67 | 4 |

## Missed facts

- v05: folder with the most doors, its door count
