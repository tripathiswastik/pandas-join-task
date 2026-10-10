# Data contract

The pipeline reads `employees.csv` and `salaries.csv` and writes `/app/output/report.csv`.

## Output

The output columns, in exactly this order, are:

`emp_id, headcount, total_salary`

Output row order must follow the first appearance order of each normalized `emp_id` in the employee input. Pandas index values and input column order are not part of the contract.

## A — Cardinality validation

Normalize salary keys using the same employee-key rule below. After normalization, there must be at most one salary record per `emp_id`. Duplicate normalized salary keys are invalid and must raise a descriptive exception rather than silently selecting or multiplying records.

## B — Identifier normalization

Only `emp_id` is normalized: strip leading/trailing whitespace and uppercase it before matching. Whitespace in every other field is data and must remain untouched.

## C — Timezone unification

Employee timestamps may be naive or timezone-aware, including offsets such as `-05:00` and `+05:30`. Normalize timestamps to UTC before chronological filtering. Keep only employee records whose UTC timestamp falls within the inclusive reporting window from `2024-01-01 00:00:00+00:00` through `2024-12-31 23:59:59+00:00`.

## D — Integer type preservation

`headcount` and `total_salary` must explicitly use pandas/numpy `int64`, including when the result is empty.

## E — Contractor adjustment correctness

For each eligible employee row, use the matched salary as the starting amount. If `employment_type` is exactly `CONTRACTOR`, multiply the salary by `0.85` and round to the nearest integer using round-half-up. Apply the adjusted value to the actual downstream DataFrame used for aggregation.

For example: `117648 × 0.85 = 100000.8 → 100001`.

For each normalized `emp_id`, `headcount` is the number of eligible employee rows and `total_salary` is the sum of their adjusted salaries. Unmatched employees use salary `0`.
