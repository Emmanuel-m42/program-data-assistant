# Eval report: claude-opus-5-5-agent_heldout_v2_k3

Model: Claude Opus 5.5 as the agent through the tool CLI (OpenCode subagent; same tools and prompt, not the app's own agent loop). The app's in-loop guardrail rewrites (retry nudge, grounding, look-first and citation nudges) and its 7-step cap don't apply in this mode; the after-answer steps (dropping unknown citations, withholding a draft with unsupported numbers) do. Latency is not measured.

Model `agent-trace/claude-opus-5-5`, commit `e1081c2`, 2026-11-21T03:09:29+00:00, 15 cases (split heldout_v2, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 13 |
| retrieval | 0.85 | 13 |
| facts | 1.00 | 13 |
| citation | 1.00 | 13 |
| refusal | 1.00 | 15 |
| pass | 1.00 | 15 |
| pass_all | 1.00 | 15 |

By group:

| group | cases | pass | pass^3 | tool choice | retrieval | facts | citation | refusal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| new held-out | 15 | 15 of 15 | 15 of 15 | 1.00 | 0.85 | 1.00 | 1.00 | 1.00 |

Average latency 0.0 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n04 | staffing | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n05 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n06 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n07 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n08 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n09 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n10 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n11 | payroll | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n12 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n13 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| n14 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 0 |
| n15 | payroll | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 0 |

## Missed facts

