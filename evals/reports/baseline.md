# Eval report: baseline

Model `ollama/qwen2.5:7b`, commit `c9cd063`, 2026-11-19T21:09:49+00:00, 28 cases.

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.76 | 25 |
| retrieval | 0.98 | 25 |
| facts | 0.26 | 25 |
| citation | 0.40 | 25 |
| refusal | 0.61 | 28 |
| pass | 0.25 | 28 |

Average latency 86.1 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 422 |
| q02 | pace | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 79 |
| q03 | staffing | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 63 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 41 |
| q05 | door gaps | 0.00 | 1.00 | 0.67 | 0.00 | 1.00 | 0.00 | 123 |
| q06 | office siting | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 40 |
| q07 | client report | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 159 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 111 |
| q09 | pace | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 42 |
| q10 | payroll | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 84 |
| q11 | QC | 1.00 | 0.50 | 0.20 | 1.00 | 1.00 | 0.00 | 113 |
| q12 | QC | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 146 |
| q13 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 277 |
| q14 | VR rate | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 191 |
| q15 | VR rate | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 24 |
| q16 | QC | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 59 |
| q17 | QC | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 44 |
| q18 | payroll | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 67 |
| q19 | client report | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 60 |
| x01 | pace | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 26 |
| x02 | payroll | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 60 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 17 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 55 |
| x05 | payroll | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 34 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 51 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 8 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 7 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 11 |

## Missed facts

- q01: projected doors, all offices, projected shortfall, all offices, says we are not on pace
- q02: Eastgate shortfall, Harbor shortfall, names Eastgate, names Harbor
- q03: Northside needs none
- q04: active regulars, active canvassers
- q05: untouched doors left in turf
- q06: picks the Mill Street site
- q07: client reported doors Oct 12, dashboard doors Oct 12
- q08: untouched doors in dense untouched precincts
- q09: Northside this week, Northside last week, Eastgate this week, Eastgate last week, Harbor this week, Harbor last week
- q10: Northside cost per door, Eastgate cost per door, Harbor cost per door, Eastgate is most expensive
- q11: Dorian Pratt, Jalen Ortiz, Tomas Reyes, Priya Nandakumar
- q12: Dorian Pratt (open householding), Andre Whitfield (open gap), Priya Nandakumar (open flash knocking), open flag count
- q14: cards per hour needed, current cards per hour, last 7 days, says not on pace
- q15: Eastgate is under, Harbor is under, Eastgate cards per hour, last 7 days
- q16: Renata Cole, Renata's duplicate cards, Harbor duplicates
- q17: confirmed share, unreachable share, wrong information share
- q18: Ellis Warren over 40, Sofia Lindqvist over 40, Marcus Bell over 40, Leon Mbeki needs fix, Carmen Ruiz needs fix, Hugo Brennan needs fix
- q19: Northside doors, Eastgate doors, Harbor doors, Northside contacts, Eastgate contacts, Harbor contacts, Northside cards, Eastgate cards, Harbor cards, Northside hours, Eastgate hours, Harbor hours
- x01: Eastgate
- x02: Eastgate, Eastgate cost per door
- x05: Tuesday at noon, field director approves
