# Eval report: claude-opus-5-5-agent_v3_dev_k3

Model `agent-trace/claude-opus-5-5`, commit `306a6ac`, 2026-11-21T04:30:08+00:00, 14 cases (split dev, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 12 |
| retrieval | 0.96 | 12 |
| facts | 0.98 | 12 |
| citation | 1.00 | 12 |
| refusal | 1.00 | 14 |
| pass | 0.95 | 14 |
| pass_all | 0.93 | 14 |

By group:

| group | cases | pass | pass^3 | tool choice | retrieval | facts | citation | refusal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev (tuned) | 14 | 13 of 14 | 13 of 14 | 1.00 | 0.96 | 0.98 | 1.00 | 1.00 |

Average latency 0.0 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q05 | door gaps | 1.00 | 1.00 | 0.78 | 1.00 | 1.00 | 0.33 | 0 |
| q07 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q11 | QC | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q13 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 0 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 0 |

## Missed facts

