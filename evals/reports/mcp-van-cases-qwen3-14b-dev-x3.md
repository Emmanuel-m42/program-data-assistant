# Eval report: mcp-van-cases-qwen3-14b-dev-x3

Model `ollama/qwen3:14b`, commit `6498b17`, 2026-11-21T02:19:19+00:00, 4 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 3 |
| facts | 0.56 | 3 |
| citation | 0.67 | 3 |
| refusal | 0.75 | 4 |
| pass | 0.50 | 4 |
| pass_all | 0.50 | 4 |

Average latency 9.1 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v01 | VAN | 1.00 | n/a | 0.67 | 1.00 | 1.00 | 0.00 | 28 |
| v02 | VAN | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 12 |
| v03 | VAN | 1.00 | n/a | 0.00 | 0.00 | 0.00 | 0.00 | 4 |
| v04 | VAN | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 3 |

## Missed facts

- v01: Northside untouched precinct doors
- v03: active activist codes
