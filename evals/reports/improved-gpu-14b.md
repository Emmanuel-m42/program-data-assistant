# Eval report: improved-gpu-14b

Model `ollama/qwen2.5:14b`, commit `8f3bd66`, 2026-11-20T02:23:43+00:00, 28 cases (split all, 1 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.84 | 25 |
| retrieval | 0.98 | 25 |
| facts | 0.67 | 25 |
| citation | 0.64 | 25 |
| refusal | 0.96 | 28 |
| pass | 0.46 | 28 |
| pass_all | 0.46 | 28 |

Average latency 57.1 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 193 |
| q02 | pace | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 79 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 102 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 233 |
| q05 | door gaps | 0.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 125 |
| q06 | office siting | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 198 |
| q07 | client report | 0.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 96 |
| q08 | door gaps | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 118 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 30 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 24 |
| q11 | QC | 1.00 | 0.50 | 0.40 | 1.00 | 1.00 | 0.00 | 13 |
| q12 | QC | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 107 |
| q13 | QC | 1.00 | 1.00 | 0.67 | 0.00 | 1.00 | 0.00 | 27 |
| q14 | VR rate | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 21 |
| q15 | VR rate | 1.00 | 1.00 | 0.67 | 0.00 | 1.00 | 0.00 | 24 |
| q16 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 26 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 21 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 50 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 17 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 20 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 19 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 13 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 14 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 3 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 2 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 3 |

## Missed facts

- q01: projected doors, all offices
- q02: Eastgate shortfall, Harbor shortfall, names Eastgate, names Harbor
- q04: active regulars, active canvassers
- q05: untouched doors left in turf, doors we can knock in the days left
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12, explains rollback
- q08: names the dense untouched cluster, untouched doors in dense untouched precincts
- q11: Jalen Ortiz, Tomas Reyes, Dorian's householding flags this week
- q12: Dorian Pratt (open householding), Andre Whitfield (open gap), Priya Nandakumar (open flash knocking), open flag count
- q13: program flags per 100 shifts this week, program flags per 100 shifts last week
- q14: current cards per hour, last 7 days, says not on pace
- q15: Eastgate cards per hour, last 7 days
- q16: Harbor duplicates
