# Eval report: final-qwen38-27b-test-x3

Model `ollama/qwen3.8:27b`, commit `9e132c7`, 2026-11-20T05:27:08+00:00, 14 cases (split test, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.92 | 13 |
| retrieval | 1.00 | 13 |
| facts | 0.86 | 13 |
| citation | 1.00 | 13 |
| refusal | 1.00 | 14 |
| pass | 0.79 | 14 |
| pass_all | 0.79 | 14 |

Average latency 58.7 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 80 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 65 |
| q06 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 36 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 125 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 65 |
| q12 | QC | 1.00 | 1.00 | 0.75 | 1.00 | 1.00 | 0.00 | 83 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 74 |
| q16 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 58 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 102 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 53 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 21 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 36 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 29 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 32 |

## Missed facts

- q04: active regulars, active canvassers
- q08: untouched doors in dense untouched precincts
- q12: open flag count
