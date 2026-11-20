# Eval report: improved

Model `ollama/qwen2.5:7b`, commit `1daaefa`, 2026-11-20T00:35:15+00:00, 28 cases.

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.76 | 25 |
| retrieval | 0.98 | 25 |
| facts | 0.48 | 25 |
| citation | 0.60 | 25 |
| refusal | 0.86 | 28 |
| pass | 0.29 | 28 |

Average latency 124.5 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 287 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 53 |
| q03 | staffing | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 30 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30 |
| q05 | door gaps | 0.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 82 |
| q06 | office siting | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 39 |
| q07 | client report | 0.00 | 1.00 | 0.25 | 1.00 | 1.00 | 0.00 | 216 |
| q08 | door gaps | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 38 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 113 |
| q10 | payroll | 1.00 | 1.00 | 0.25 | 1.00 | 1.00 | 0.00 | 37 |
| q11 | QC | 1.00 | 0.50 | 0.80 | 0.00 | 1.00 | 0.00 | 600 |
| q12 | QC | 1.00 | 1.00 | 0.75 | 0.00 | 1.00 | 0.00 | 660 |
| q13 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 66 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 105 |
| q15 | VR rate | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 15 |
| q16 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 184 |
| q17 | QC | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 83 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 515 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 103 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 59 |
| x02 | payroll | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 21 |
| x03 | QC | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 22 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 76 |
| x05 | payroll | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 17 |
| x06 | QC | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 10 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 7 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 7 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 11 |

## Missed facts

- q03: Harbor extra shifts per day, Northside needs none
- q04: active regulars, active canvassers
- q05: untouched doors left in turf, doors we can knock in the days left
- q06: picks the Mill Street site
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12
- q08: names the dense untouched cluster, untouched doors in dense untouched precincts
- q10: Northside cost per door, Eastgate cost per door, Eastgate is most expensive
- q11: Tomas Reyes
- q12: open flag count
- q13: Harbor flags per 100 shifts this week
- q15: Eastgate is under, Harbor is under, Eastgate cards per hour, last 7 days
- q16: Harbor duplicates
- q17: confirmed share, unreachable share, wrong information share
- x02: Eastgate, Eastgate cost per door
- x03: wrong information calls
- x05: Tuesday at noon, field director approves
- x06: inaccessible, once, not per unit
