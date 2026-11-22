# Eval report: claude-opus-5-5-agent_v3_heldout_v3_k3

Model `agent-trace/claude-opus-5-5`, commit `306a6ac`, 2026-11-21T04:29:38+00:00, 15 cases (split heldout_v3, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 13 |
| retrieval | 0.92 | 13 |
| facts | 1.00 | 13 |
| citation | 1.00 | 13 |
| refusal | 1.00 | 15 |
| pass | 1.00 | 15 |
| pass_all | 1.00 | 15 |

By group:

| group | cases | pass | pass^3 | tool choice | retrieval | facts | citation | refusal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| held-out v3 | 15 | 15 of 15 | 15 of 15 | 1.00 | 0.92 | 1.00 | 1.00 | 1.00 |

Average latency 0.0 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v03 | staffing | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v04 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v05 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v06 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v07 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v08 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v09 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v10 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v11 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v12 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v13 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| v14 | staffing | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 0 |
| v15 | payroll | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 0 |

## Missed facts

