# Eval report: improved-gpu-7b

Model `ollama/qwen2.5:7b`, commit `8f3bd66`, 2026-11-20T01:56:45+00:00, 28 cases (split all, 1 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.84 | 25 |
| retrieval | 0.98 | 25 |
| facts | 0.72 | 25 |
| citation | 0.84 | 25 |
| refusal | 0.93 | 28 |
| pass | 0.57 | 28 |
| pass_all | 0.57 | 28 |

Average latency 7.9 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 25 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 2 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 3 |
| q05 | door gaps | 0.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 21 |
| q06 | office siting | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 2 |
| q07 | client report | 0.00 | 1.00 | 0.50 | 0.00 | 1.00 | 0.00 | 10 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 34 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q11 | QC | 1.00 | 0.50 | 0.60 | 0.00 | 1.00 | 0.00 | 17 |
| q12 | QC | 1.00 | 1.00 | 0.50 | 0.00 | 1.00 | 0.00 | 12 |
| q13 | QC | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 4 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| q16 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 4 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x03 | QC | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 2 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x05 | payroll | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 8 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x07 | pace | n/a | n/a | n/a | n/a | 0.00 | 0.00 | 4 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 1 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 2 |

## Missed facts

- q04: active regulars, active canvassers
- q05: untouched doors left in turf
- q06: picks the Mill Street site
- q07: client reported doors Oct 12, dashboard doors Oct 12
- q08: untouched doors in dense untouched precincts
- q11: Tomas Reyes, Dorian's householding flags this week
- q12: Andre Whitfield (open gap), open flag count
- q13: Harbor flags per 100 shifts this week, program flags per 100 shifts this week, program flags per 100 shifts last week
- q16: Harbor duplicates
- x03: wrong information calls
- x05: Tuesday at noon, field director approves
