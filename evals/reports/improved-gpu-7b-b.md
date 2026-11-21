# Eval report: improved-gpu-7b-b

Model `ollama/qwen2.5:7b`, commit `ba7e0f3`, 2026-11-20T01:47:18+00:00, 28 cases (split all, 1 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.84 | 25 |
| retrieval | 0.98 | 25 |
| facts | 0.68 | 25 |
| citation | 0.84 | 25 |
| refusal | 0.96 | 28 |
| pass | 0.57 | 28 |
| pass_all | 0.57 | 28 |

Average latency 6.9 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 15 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 3 |
| q05 | door gaps | 0.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 12 |
| q06 | office siting | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 3 |
| q07 | client report | 0.00 | 1.00 | 0.25 | 0.00 | 1.00 | 0.00 | 9 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 31 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q11 | QC | 1.00 | 0.50 | 0.60 | 0.00 | 1.00 | 0.00 | 16 |
| q12 | QC | 1.00 | 1.00 | 0.50 | 0.00 | 1.00 | 0.00 | 11 |
| q13 | QC | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 4 |
| q14 | VR rate | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 5 |
| q15 | VR rate | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 6 |
| q16 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 4 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 2 |
| x03 | QC | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 2 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 13 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 1 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 4 |

## Missed facts

- q04: active regulars, active canvassers
- q05: untouched doors left in turf, doors we can knock in the days left
- q06: picks the Mill Street site
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12
- q08: untouched doors in dense untouched precincts
- q11: Tomas Reyes, Dorian's householding flags this week
- q12: Andre Whitfield (open gap), open flag count
- q13: Harbor flags per 100 shifts this week, program flags per 100 shifts this week, program flags per 100 shifts last week
- q14: current cards per hour, last 7 days
- q15: Eastgate is under, Harbor is under, Eastgate cards per hour, last 7 days
- q16: Harbor duplicates
- x03: wrong information calls
