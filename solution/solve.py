"""
Python Version: 3.10+ (Target: Python 3.11, Pandas 2.2.2, NumPy 1.26.4)
Purpose: Reference solution execution runner for pandas-join-final-task-hard benchmark.
Runs-in: Host evaluation environment or container sandbox (/app) deployed via solve.sh.
"""

import os
import pathlib
import shutil
import sys
import pandas as pd

SOLUTION_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SOLUTION_DIR.parent
APP_DIR = pathlib.Path(
    os.environ.get(
        "APP_DIR",
        "/app" if pathlib.Path("/app").exists() else str(REPO_ROOT / "environment" / "app"),
    )
)

# Mirror solve.sh by deploying reference solution into application directory
if (SOLUTION_DIR / "pipeline.py").exists() and (APP_DIR / "pipeline.py").resolve() != (SOLUTION_DIR / "pipeline.py").resolve():
    shutil.copy(SOLUTION_DIR / "pipeline.py", APP_DIR / "pipeline.py")

sys.path.insert(0, str(SOLUTION_DIR))
from pipeline import build_report  # noqa: E402


def main() -> None:
    data_dir = pathlib.Path(os.environ.get("DATA_DIR", str(APP_DIR / "data")))
    output_path = pathlib.Path(os.environ.get("OUTPUT_PATH", str(APP_DIR / "output" / "report.csv")))

    employees_path = data_dir / "employees.csv"
    salaries_path = data_dir / "salaries.csv"

    print(f"Loading input datasets from {data_dir}...")
    employees = pd.read_csv(employees_path)
    salaries = pd.read_csv(salaries_path)

    print("Executing reference build_report pipeline...")
    result = build_report(employees, salaries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Successfully generated output report at {output_path}:")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
