# Eval report: gpd-qwen38-27b-16gb

Model `ollama/qwen3.8:27b`, commit `ef41770`, 2026-11-20T23:35:08+00:00, 5 cases (split all, 1 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 5 |
| retrieval | 1.00 | 5 |
| facts | 1.00 | 5 |
| citation | 1.00 | 5 |
| refusal | 1.00 | 5 |
| pass | 1.00 | 5 |
| pass_all | 1.00 | 5 |

Average latency 37.5 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 94 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 19 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 27 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 30 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 17 |

## Missed facts

