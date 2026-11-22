# Eval report: v2-ds-pro-before-x3

Model `openai_compat/deepseek-v4-pro`, commit `3b10a2e`, 2026-11-21T03:28:06+00:00, 43 cases (split dev+test+heldout_v2, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.97 | 38 |
| retrieval | 0.93 | 38 |
| facts | 0.87 | 38 |
| citation | 1.00 | 38 |
| refusal | 1.00 | 43 |
| pass | 0.82 | 43 |
| pass_all | 0.79 | 43 |

By group:

| group | cases | pass | pass^3 | tool choice | retrieval | facts | citation | refusal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev (tuned) | 14 | 12 of 14 | 11 of 14 | 1.00 | 0.96 | 0.91 | 1.00 | 1.00 |
| old held-out (contaminated) | 14 | 12 of 14 | 12 of 14 | 0.92 | 1.00 | 0.89 | 1.00 | 1.00 |
| held-out v2 (contaminated) | 15 | 12 of 15 | 11 of 15 | 1.00 | 0.85 | 0.83 | 1.00 | 1.00 |

Average latency 5.1 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 6 |
| q05 | door gaps | 1.00 | 1.00 | 0.89 | 1.00 | 1.00 | 0.67 | 9 |
| q06 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q07 | client report | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 5 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 6 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q11 | QC | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q12 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q13 | QC | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 4 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q16 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| n01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| n02 | pace | 1.00 | 1.00 | 0.25 | 1.00 | 1.00 | 0.00 | 6 |
| n03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| n04 | staffing | 1.00 | 0.00 | 0.67 | 1.00 | 1.00 | 0.00 | 6 |
| n05 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| n06 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| n07 | QC | 1.00 | 1.00 | 0.83 | 1.00 | 1.00 | 0.67 | 8 |
| n08 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| n09 | VR rate | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 4 |
| n10 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| n11 | payroll | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 14 |
| n12 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| n13 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| n14 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |
| n15 | payroll | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |

## Missed facts

- q04: active regulars, active canvassers
- q07: client reported doors Oct 12, dashboard doors Oct 12
- q08: untouched doors in dense untouched precincts
- q13: program-wide QC is getting better, program flags per 100 shifts this week, program flags per 100 shifts last week
- n02: program doors last week, program door goal last week, Eastgate doors last week
- n04: Harbor average shift
- n09: Northside cards per hour last week, Eastgate cards per hour last week, Harbor cards per hour last week
