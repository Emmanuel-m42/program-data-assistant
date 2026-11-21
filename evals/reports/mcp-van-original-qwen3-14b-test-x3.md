# Eval report: mcp-van-original-qwen3-14b-test-x3

Model `ollama/qwen3:14b`, commit `6498b17`, 2026-11-21T02:40:36+00:00, 14 cases (split test, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.92 | 13 |
| retrieval | 1.00 | 13 |
| facts | 0.69 | 13 |
| citation | 0.95 | 13 |
| refusal | 0.95 | 14 |
| pass | 0.57 | 14 |
| pass_all | 0.57 | 14 |

Average latency 13.8 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 0.33 | 0.33 | 0.00 | 11 |
| q06 | office siting | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 8 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 34 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| q12 | QC | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 47 |
| q14 | VR rate | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 8 |
| q16 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 13 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 18 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 18 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 3 |

## Missed facts

- q04: active regulars, active canvassers
- q06: picks the Mill Street site
- q08: untouched doors in dense untouched precincts
- q12: Andre Whitfield (open gap), open flag count
- q14: current cards per hour, last 7 days, says not on pace
- q16: Harbor duplicates
