# Eval report: improved-gpu-qwen35-9b

Model `ollama/qwen3.5:9b`, commit `8f3bd66`, 2026-11-20T02:28:07+00:00, 28 cases (split all, 1 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.88 | 25 |
| retrieval | 0.98 | 25 |
| facts | 0.71 | 25 |
| citation | 0.88 | 25 |
| refusal | 0.93 | 28 |
| pass | 0.64 | 28 |
| pass_all | 0.64 | 28 |

Average latency 8.5 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 23 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 8 |
| q05 | door gaps | 0.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 11 |
| q06 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| q07 | client report | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 6 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 21 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q11 | QC | 1.00 | 0.50 | 0.00 | 0.00 | 0.00 | 0.00 | 9 |
| q12 | QC | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 14 |
| q13 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 13 |
| q14 | VR rate | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 27 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q16 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 8 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 5 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 6 |

## Missed facts

- q01: projected doors, all offices
- q04: active regulars, active canvassers
- q05: untouched doors left in turf, doors we can knock in the days left
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12, explains rollback
- q08: untouched doors in dense untouched precincts
- q11: Dorian Pratt, Jalen Ortiz, Tomas Reyes, Priya Nandakumar, Dorian's householding flags this week
- q12: Dorian Pratt (open householding), Andre Whitfield (open gap), Priya Nandakumar (open flash knocking), open flag count
- q13: program flags per 100 shifts this week, program flags per 100 shifts last week
- q14: cards per hour needed, current cards per hour, last 7 days, says not on pace
- q16: Harbor duplicates
