# 🐼 Terminal-Bench: Pandas Join Final Task (Hard)

[![Benchmark](https://img.shields.io/badge/Benchmark-Terminal--Bench-blue.svg)](https://github.com/tripathiswastik/pandas-join-final-task-hard)
[![Category](https://img.shields.io/badge/Category-Data%20Pipelines%20%7C%20ETL-green.svg)](https://github.com/tripathiswastik/pandas-join-final-task-hard)
[![Difficulty](https://img.shields.io/badge/Difficulty-Hard-red.svg)](https://github.com/tripathiswastik/pandas-join-final-task-hard)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.2.2-blueviolet.svg)](https://pandas.pydata.org/)
[![Author](https://img.shields.io/badge/Author-Swastik%20Tripathi-purple.svg)](https://github.com/tripathiswastik)

An enterprise-grade, stateful data pipeline evaluation benchmark designed for autonomous AI coding agents and data engineering systems.

---

## 📌 Overview

This benchmark evaluates autonomous agents on diagnosing and resolving five interacting silent correctness bugs within a multi-source **Pandas ETL pipeline**.

The challenge requires repairing `/app/pipeline.py` to ingest employee audit logs (`employees.csv`) and salary master records (`salaries.csv`), producing a deterministic reconciliation report (`/app/output/report.csv`) conforming to strict accounting and schema contracts.

Unlike shallow syntax or unit test benchmarks, this task tests subtle runtime semantics: **join cardinality violations**, **selective key hygiene without data mutation**, **mixed-format and offset-aware timezone normalization**, **dtype stability on empty and sparse aggregations**, and **exact decimal round-half-up math**.

---

## 🏗️ Repository Architecture

```text
.
├── task.toml                  # Benchmark task specification, timeouts, and resource quotas
├── instruction.md             # Candidate prompt / instructions given to the agent
├── rubric.txt                 # Detailed scoring rubric (+26 positive, -22 penalty points)
├── README.md                  # Comprehensive documentation & architecture overview
├── pyproject.toml             # Tool configurations (ruff, mypy, pytest)
├── build_release.py           # Automated packaging tool for clean release distributions
├── .gitignore                 # Exclusion rules for caches, bytecodes, and build outputs
│
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI matrix (Python 3.10, 3.11, 3.12)
│
├── environment/               # Agent execution sandbox
│   ├── Dockerfile             # Container definition for execution runtime (Python 3.11-slim)
│   ├── .dockerignore          # Container build context filter
│   └── app/
│       ├── pipeline.py        # Intentionally flawed starter pipeline to be repaired
│       ├── data/
│       │   ├── employees.csv  # 5 raw employee records with mixed timestamps and padding
│       │   └── salaries.csv   # Master compensation dataset with arbitrary column ordering
│       ├── docs/
│       │   └── data_contract.md # Formal data contract and behavioral specifications
│       └── output/            # Destination for generated reconciliation reports
│
├── solution/                  # Ground truth reference implementation
│   ├── pipeline.py            # Corrected reference pipeline implementation
│   ├── solve.py               # Cross-platform execution runner for reference solution
│   └── solve.sh               # Shell script execution entrypoint
│
└── tests/                     # Isolated verifier harness (runs in separate container)
    ├── Dockerfile             # Verifier container definition
    ├── requirements.txt       # Pinned verifier test dependencies
    ├── test.sh                # Test runner producing CTRF JSON and reward.txt
    ├── test_outputs.py        # 10 comprehensive unit & integration tests
    ├── test_mutated_case.py   # Stress tests for idempotency, extreme timezones, & ties
    └── expected_report.csv    # Expected ground-truth output fixture
```

---

## ⚙️ Core Engineering Challenges & Root Cause Matrix

The starter pipeline contains five interacting bugs that must be diagnosed and resolved without altering the public pipeline API or corrupting unrelated fields:

| Root Cause | Area | Description & Required Resolution |
| :--- | :--- | :--- |
| **A** | **Cardinality Validation** | Duplicate normalized salary keys cause row multiplication or arbitrary row drops. The pipeline must reject duplicate normalized salary keys with a descriptive exception before joining (`validate='many_to_one'`). |
| **B** | **Identifier Hygiene** | Only `emp_id` must be normalized (stripping surrounding whitespace and converting to uppercase). Non-key fields (such as `notes` or `employment_type`) contain intentional whitespace that must remain untouched. |
| **C** | **Timezone Unification** | Employee timestamps arrive in mixed formats (naive strings and timezone offsets like `-05:00` and `+05:30`). All timestamps must be converted to UTC before filtering against the inclusive 2024 reporting window (`2024-01-01 00:00:00+00:00` to `2024-12-31 23:59:59+00:00`). |
| **D** | **Integer Dtype Preservation** | Output aggregates `headcount` and `total_salary` must strictly retain pandas/numpy `int64`, even when the filtered result is completely empty. Default pandas operations drift to `float64` when `NaN` or empty frames occur. |
| **E** | **Contractor Round-Half-Up** | For `CONTRACTOR` records, compensation must be scaled by `0.85` using strict round-half-up math (`Decimal.quantize(..., ROUND_HALF_UP)`) and applied to the actual downstream dataframe used for aggregation. Standard Python / NumPy banker's rounding (`round()`) fails edge cases (e.g., `117648 × 0.85 = 100000.8 → 100001`). |

---

## 📋 Data Contract & Expected Artifacts

### 1. Input Datasets

- **`/app/data/employees.csv`**: Contains `emp_id`, `employment_type`, `event_ts`, and `notes`. Note that column order and index values can be arbitrary.
- **`/app/data/salaries.csv`**: Master compensation table mapping `emp_id` to `annual_salary`.

### 2. Output Schema (`/app/output/report.csv`)

The generated report must strictly match the following column order, row ordering, and types:

| Column | Dtype | Description |
| :--- | :--- | :--- |
| `emp_id` | `object` / `string` | Normalized employee ID in first-appearance order |
| `headcount` | `int64` | Total eligible employee records in 2024 UTC window |
| `total_salary` | `int64` | Sum of adjusted annual salaries (unmatched employees use `0`) |

### 3. Expected Ground-Truth Fixture

```csv
emp_id,headcount,total_salary
E001,2,200000
E002,1,100001
E003,1,50000
E004,1,68000
```

---

## 🚀 Running the Benchmark

### 1. Run the Candidate Pipeline
Within the candidate sandbox:
```bash
python /app/pipeline.py
```

### 2. Execute Reference Solution
To test the reference solution directly:
```bash
python solution/solve.py
# Or inside container:
bash solution/solve.sh
```

### 3. Run the Verifier Harness
The evaluation suite validates all root causes, boundary conditions, and schema invariants:
```bash
# Standard pytest execution:
pytest tests/test_outputs.py tests/test_mutated_case.py -v

# Container verification entrypoint:
bash tests/test.sh
```

---

## 📊 Scoring Rubric

The benchmark applies an objective grading rubric (+26 positive points, -22 penalty points):

### Positive Scoring Criteria (+26 pts)
- **+5 pts:** Agent produces one output row per normalized employee ID with required headcount and total salary.
- **+5 pts:** Agent correctly joins employee rows to unique normalized salary records, preserving employees without salaries.
- **+3 pts:** Agent applies the employee timestamp reporting window with inclusive UTC boundaries.
- **+3 pts:** Agent correctly normalizes naive and timezone-aware timestamps to UTC before filtering.
- **+3 pts:** Agent calculates contractor salaries using the required 0.85 adjustment and round-half-up semantics.
- **+2 pts:** Agent preserves pandas `int64` for `headcount` and `total_salary`, including empty results.
- **+2 pts:** Agent preserves first-appearance order and keeps results independent of input column order and index values.
- **+3 pts:** Agent correctly handles the holistic interaction of normalization, timezone filtering, contractor rounding, and downstream aggregation.

### Negative Penalty Criteria (-22 pts)
- **-5 pts:** Agent silently accepts duplicate normalized salary keys and permits invalid cardinality.
- **-5 pts:** Agent compares timestamps without first unifying their timezone representation.
- **-3 pts:** Agent applies contractor adjustments without propagating the adjusted value to downstream aggregation.
- **-2 pts:** Agent modifies whitespace in non-key employee fields while normalizing identifiers.
- **-3 pts:** Agent relies on input column positions or pandas index alignment instead of column names.
- **-2 pts:** Agent returns headcount or total_salary with a dtype other than `int64`.
- **-2 pts:** Agent uses truncation or banker's rounding instead of round-half-up.

---

## 📦 Distribution & Packaging

To generate a pristine release distribution zip file free of cache files, bytecode, and git metadata:
```bash
python build_release.py
```
This builds `dist/pandas-join-final-task-hard.zip` and performs strict integrity validation.
