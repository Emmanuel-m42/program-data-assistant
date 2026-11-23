# Eval report: v5-final-pro

Model `openai_compat/deepseek-v4-pro`, commit `e460351`, 2026-11-23T23:24:39+00:00, 50 cases (split all, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 1.00 | 42 |
| retrieval | 0.96 | 27 |
| facts | 0.94 | 42 |
| citation | 1.00 | 42 |
| refusal | 1.00 | 50 |
| pass | 0.93 | 50 |
| pass_all | 0.92 | 50 |

By group:

| group | cases | pass | pass^3 | tool choice | retrieval | facts | citation | refusal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| held-out v5 | 50 | 47 of 50 | 46 of 50 | 1.00 | 0.96 | 0.94 | 1.00 | 1.00 |

Average latency 5.0 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| y01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y02 | pace | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 2 |
| y03 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y04 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| y05 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y06 | staffing | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y07 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y08 | staffing | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y09 | staffing | 1.00 | n/a | 0.00 | 1.00 | 1.00 | 0.00 | 3 |
| y10 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y11 | office siting | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y12 | office siting | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| y13 | door gaps | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| y14 | door gaps | 1.00 | n/a | 0.00 | 1.00 | 1.00 | 0.00 | 3 |
| y15 | door gaps | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| y16 | door gaps | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y17 | QC | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 3 |
| y18 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 2 |
| y19 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y20 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y21 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y22 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| y23 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y24 | VR rate | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y25 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y26 | payroll | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y27 | payroll | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| y28 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y29 | payroll | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y30 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y31 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y32 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y33 | pace | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| y34 | payroll | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| y35 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y36 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y37 | staffing | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 62 |
| y38 | door gaps | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 8 |
| y39 | payroll | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |
| y40 | staffing | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| y41 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 2 |
| y42 | payroll | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| y43 | VR rate | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| y44 | payroll | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 4 |
| y45 | VR rate | 1.00 | 1.00 | 0.89 | 1.00 | 1.00 | 0.67 | 9 |
| y46 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| y47 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| y48 | QC | 1.00 | n/a | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| y49 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| y50 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |

## Missed facts

- y09: Eastgate registration canvassers
- y14: precincts with 90% or more of doors touched
- y17: open gap flags
