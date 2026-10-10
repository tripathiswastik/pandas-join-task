import os
from pathlib import Path
import pandas as pd

_APP_DIR = Path('/app') if Path('/app').exists() else Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('DATA_DIR', str(_APP_DIR / 'data')))
OUTPUT_PATH = Path(os.environ.get('OUTPUT_PATH', str(_APP_DIR / 'output' / 'report.csv')))
WINDOW_START = pd.Timestamp('2024-01-01 00:00:00+00:00')
WINDOW_END = pd.Timestamp('2024-12-31 23:59:59+00:00')


def normalize_emp_id(series: pd.Series) -> pd.Series:
    return series.astype('string').str.strip().str.upper()


def build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
    # Intentionally flawed starter implementation.
    emp = employees.copy()
    sal = salaries.copy()
    emp['event_ts'] = pd.to_datetime(emp['event_ts'], errors='raise')
    emp = emp[(emp['event_ts'] >= WINDOW_START.tz_localize(None)) & (emp['event_ts'] <= WINDOW_END.tz_localize(None))]
    merged = emp.merge(sal, on='emp_id', how='left')
    merged['adjusted_salary'] = merged['annual_salary'].fillna(0)
    merged.loc[merged['employment_type'] == 'CONTRACTOR', 'adjusted_salary'] * 0.85  # noqa: B018
    result = merged.groupby('emp_id', sort=False).agg(
        headcount=('emp_id', 'size'), total_salary=('adjusted_salary', 'sum')
    ).reset_index()
    return result[['emp_id', 'headcount', 'total_salary']]


def main() -> None:
    employees = pd.read_csv(DATA_DIR / 'employees.csv')
    salaries = pd.read_csv(DATA_DIR / 'salaries.csv')
    result = build_report(employees, salaries)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)


if __name__ == '__main__':
    main()
