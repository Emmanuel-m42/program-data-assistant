# Eval report: final-qwen35-9b-x3

Model `ollama/qwen3.5:9b`, commit `cbb71d9`, 2026-11-20T03:55:40+00:00, 28 cases (split all, 3 run(s) per case; pass_all is pass^k).

| metric | score | cases scored |
| --- | --- | --- |
| tool_choice | 0.88 | 25 |
| retrieval | 0.98 | 25 |
| facts | 0.81 | 25 |
| citation | 1.00 | 25 |
| refusal | 1.00 | 28 |
| pass | 0.71 | 28 |
| pass_all | 0.71 | 28 |

Average latency 7.7 s per question.

| case | category | tool choice | retrieval | facts | citation | refusal | pass | latency s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 10 |
| q02 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q03 | staffing | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q04 | staffing | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 7 |
| q05 | door gaps | 0.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 | 11 |
| q06 | office siting | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q07 | client report | 0.00 | 1.00 | 0.25 | 1.00 | 1.00 | 0.00 | 5 |
| q08 | door gaps | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.00 | 23 |
| q09 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 7 |
| q10 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q11 | QC | 1.00 | 0.50 | 0.80 | 1.00 | 1.00 | 0.00 | 8 |
| q12 | QC | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 42 |
| q13 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 6 |
| q14 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 14 |
| q15 | VR rate | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| q16 | QC | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.00 | 8 |
| q17 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| q18 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 9 |
| q19 | client report | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x01 | pace | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x02 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 3 |
| x03 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x04 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 6 |
| x05 | payroll | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 5 |
| x06 | QC | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 4 |
| x07 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 4 |
| x08 | QC | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 4 |
| x09 | pace | n/a | n/a | n/a | n/a | 1.00 | 1.00 | 4 |

## Missed facts

- q04: active regulars, active canvassers
- q05: untouched doors left in turf, doors we can knock in the days left
- q07: client reported doors Oct 12, dashboard doors Oct 12, rolled-back attempts Oct 12
- q08: untouched doors in dense untouched precincts
- q11: Dorian's householding flags this week
- q12: Dorian Pratt (open householding), Andre Whitfield (open gap), Priya Nandakumar (open flash knocking), open flag count
- q13: program flags per 100 shifts this week, program flags per 100 shifts last week
- q16: Harbor duplicates
