# Pandas Join Task (Hard) — Terminal-Bench

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Pandas](https://img.shields.io/badge/pandas-2.2.2-blueviolet) ![Benchmark](https://img.shields.io/badge/benchmark-Terminal--Bench-blue)

An enterprise-grade, stateful data pipeline evaluation benchmark designed for autonomous AI coding agents and data engineering systems. It evaluates an agent's ability to diagnose and repair five interacting silent correctness bugs across multi-source Pandas joins and transformations. The benchmark enforces strict data contracts using Python 3.11, Pandas 2.2.2, Decimal round-half-up quantization, and containerized verification harnesses.

## 🌟 Key Features

- **Strict Cardinality Validation**: Detects and rejects duplicate normalized salary keys with a descriptive exception before joining, preventing invalid many-to-many fanout (`validate='many_to_one'`).
- **Selective Identifier Hygiene**: Strips surrounding whitespace and uppercases `emp_id` while preserving intentional whitespace and formatting in all non-key employee attributes.
- **Mixed Timestamp & Timezone Unification**: Converts heterogeneous timestamp formats (naive strings and timezone offsets such as `-05:00` and `+05:30`) to UTC, applying an inclusive 2024 calendar reporting window.
- **Int64 Dtype Preservation**: Guarantees pandas/numpy `int64` preservation on `headcount` and `total_salary` aggregations even when the filtered result is completely empty.
- **Downstream Contractor Wage Scaling**: Applies exact 0.85 contractor adjustments with round-half-up math (`Decimal.quantize(..., ROUND_HALF_UP)`) directly to the downstream DataFrame used for aggregation.
- **Automated Sandbox & Verifier Harness**: Includes digest-pinned Docker environments, CTRF evaluation runners, and comprehensive test suites covering unit, integration, and mutation cases.

## 🏗️ Architecture / Workflow

```mermaid
graph TD;
    A[Raw employees.csv] --> B[Normalize emp_id & Parse Mixed Timezones to UTC];
    C[Raw salaries.csv] --> D[Normalize emp_id & Validate Cardinality / Check Duplicates];
    B --> E{Inclusive 2024 Window Filter};
    E -->|Filtered Employees| F[Left Join on emp_id: validate=many_to_one];
    D -->|Validated Salaries| F;
    F --> G[Contractor Adjustment: 0.85 x Salary with Round-Half-Up];
    G --> H[Group by emp_id in First-Appearance Order];
    H --> I[Aggregate: headcount int64 & total_salary int64];
    I --> J[/app/output/report.csv];
    J --> K[Verifier Test Harness pytest + CTRF];
```

### Repository Structure

```text
.
├── task.toml                  # Benchmark task specification, timeouts, and resource quotas
├── instruction.md             # Candidate prompt / instructions given to the agent
├── rubric.txt                 # Detailed scoring rubric (+26 positive, -22 penalty points)
├── LICENSE                    # MIT License
├── README.md                  # Comprehensive benchmark documentation
├── pyproject.toml             # Tool configurations (ruff, mypy, pytest)
├── build_release.py           # Packaging tool for clean release distributions
├── .gitignore                 # Exclusion rules for caches, bytecodes, and build outputs
│
├── .github/workflows/ci.yml   # GitHub Actions CI matrix (Python 3.10, 3.11, 3.12)
│
├── environment/               # Candidate runtime sandbox
│   ├── Dockerfile             # Execution environment container definition (Python 3.11-slim)
│   ├── .dockerignore
│   └── app/
│       ├── pipeline.py        # Intentionally flawed starter pipeline
│       ├── data/              # Input datasets (employees.csv, salaries.csv)
│       ├── docs/              # Formal data contract specifications (data_contract.md)
│       └── output/            # Destination for generated report.csv
│
├── solution/                  # Ground truth reference implementation
│   ├── pipeline.py            # Corrected reference pipeline implementation
│   ├── solve.py               # Cross-platform execution runner
│   └── solve.sh               # Execution shell entrypoint
│
└── tests/                     # Isolated verifier harness
    ├── Dockerfile             # Verifier container definition
    ├── requirements.txt       # Verifier dependencies (pandas, numpy, pytest, pytest-json-ctrf)
    ├── test.sh                # Test runner producing CTRF JSON and reward.txt
    ├── test_outputs.py        # Verifier suite testing root causes A through E + composition
    ├── test_mutated_case.py   # Mutation & stress test suite (extreme timezones, ties, idempotency)
    └── expected_report.csv    # Ground truth reference output fixture
```

## 🚀 Quickstart

```bash
# Clone the repository
git clone https://github.com/tripathiswastik/pandas-join-task.git
cd pandas-join-task

# Install test dependencies
pip install -r tests/requirements.txt

# Run the reference solution to produce /app/output/report.csv
python solution/solve.py

# Execute the verifier test suite
pytest tests/test_outputs.py tests/test_mutated_case.py -v
```

### Docker Execution

```bash
# Build candidate sandbox container
docker build -t pandas-benchmark environment/

# Run verification inside sandbox
docker run --rm -v $(pwd)/tests:/tests pandas-benchmark bash /tests/test.sh
```

## 📊 Performance & Evaluation

| Metric / Test | Results |
| :--- | :--- |
| **Verification Test Suite Pass Rate** | 100% (14 / 14 test cases) |
| **Root Causes Resolved (A through E)** | 5 / 5 Verified |
| **Scoring Rubric Achievement** | +26 / +26 positive points |
| **Penalty Invariants Triggered** | 0 / -22 penalties incurred |
| **Execution Latency** | < 180ms |
| **Memory Footprint** | < 45MB |

### Scoring Rubric Breakdown

- **+5 pts:** Produces one output row per normalized employee ID with exact headcount and total salary.
- **+5 pts:** Correctly joins employee rows to unique normalized salary records, preserving employees without salaries.
- **+3 pts:** Filters employee timestamps within the inclusive 2024 UTC reporting window.
- **+3 pts:** Normalizes naive and timezone-aware timestamps to UTC before filtering.
- **+3 pts:** Computes contractor salaries using 0.85 scaling and round-half-up semantics.
- **+2 pts:** Preserves pandas `int64` for `headcount` and `total_salary`, including empty frames.
- **+2 pts:** Retains first-appearance order and remains independent of input column/index order.
- **+3 pts:** Correctly resolves holistic interactions across all 5 engineering challenges.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](file:///d:/ag-ai/pandas-join-final-task-hard/LICENSE) file for details.
