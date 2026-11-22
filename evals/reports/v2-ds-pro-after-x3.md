# Eval report: v2-ds-pro-after-x3

Model `openai_compat/deepseek-v4-pro`, commit `c66cf79`, 2026-11-21T03:39:20+00:00, 43 cases (split dev+test+heldout_v2, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 38 |
| retrieval | 0.93 | 38 |
| facts | 0.92 | 38 |
| citation | 1.00 | 38 |
| refusal | 1.00 | 43 |
| pass | 0.88 | 43 |
| pass_all | 0.86 | 43 |

By group:

| group | cases | pass | pass^3 | tool choice | retrieval | facts | citation | refusal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev (tuned) | 14 | 13 of 14 | 13 of 14 | 1.00 | 0.96 | 0.98 | 1.00 | 1.00 |
| old held-out (contaminated) | 14 | 14 of 14 | 14 of 14 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| held-out v2 (contaminated) | 15 | 11 of 15 | 10 of 15 | 1.00 | 0.85 | 0.78 | 1.00 | 1.00 |

Average latency 5.1 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q04 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q05 | door gaps | 1.00 | 1.00 | 0.78 | 1.00 | 1.00 | 0.33 | 8 |
| q06 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q07 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q08 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q11 | QC | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q12 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q13 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q16 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| n01 | pace | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 3 |
| n02 | pace | 1.00 | 1.00 | 0.25 | 1.00 | 1.00 | 0.00 | 7 |
| n03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| n04 | staffing | 1.00 | 0.00 | 0.67 | 1.00 | 1.00 | 0.00 | 10 |
| n05 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| n06 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| n07 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| n08 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| n09 | VR rate | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 4 |
| n10 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| n11 | payroll | 1.00 | 0.00 | 0.75 | 1.00 | 1.00 | 0.67 | 6 |
| n12 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| n13 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| n14 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |
| n15 | payroll | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |

## Missed facts

- q04: active canvassers
- q05: untouched doors left in turf
- n01: doors on the biggest day
- n02: program doors last week, program door goal last week, Eastgate doors last week
- n04: Harbor average shift
- n09: Northside cards per hour last week, Eastgate cards per hour last week, Harbor cards per hour last week
