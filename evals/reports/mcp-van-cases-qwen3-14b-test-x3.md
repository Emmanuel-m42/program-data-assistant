# Eval report: mcp-van-cases-qwen3-14b-test-x3

Model `ollama/qwen3:14b`, commit `6498b17`, 2026-11-21T02:22:44+00:00, 4 cases (split test, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 4 |
| facts | 0.75 | 4 |
| citation | 1.00 | 4 |
| refusal | 1.00 | 4 |
| pass | 0.75 | 4 |
| pass_all | 0.75 | 4 |

Average latency 15.8 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v05 | VAN | 1.00 | n/a | 0.00 | 1.00 | 1.00 | 0.00 | 6 |
| v06 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 32 |
| v07 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 18 |
| v08 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 7 |

## Missed facts

- v05: folder with the most doors, its door count
