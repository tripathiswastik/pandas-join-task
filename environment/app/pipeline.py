import os
from pathlib import Path
import pandas as pd


def _find_app_dir() -> Path:
    if Path('/app/data').exists():
        return Path('/app')
    cur = Path(__file__).resolve().parent
    if (cur / 'data').exists():
        return cur
    for parent in [cur, cur.parent, cur.parent.parent]:
        candidate = parent / 'environment' / 'app'
        if (candidate / 'data').exists():
            return candidate
    return cur


_APP_DIR = _find_app_dir()
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
    emp = emp[(emp['event_ts'] >= WINDOW_START.tz_localize(None)) & (emp['event_ts'] <= WINDOW_END.tz_localize(None))]  # type: ignore
    merged = emp.merge(sal, on='emp_id', how='left')
    merged['adjusted_salary'] = merged['annual_salary'].fillna(0)
    merged.loc[merged['employment_type'] == 'CONTRACTOR', 'adjusted_salary'] * 0.85
    result = merged.groupby('emp_id', sort=False).agg(
        headcount=('emp_id', 'size'), total_salary=('adjusted_salary', 'sum')
    ).reset_index()
    return result[['emp_id', 'headcount', 'total_salary']]


def main() -> None:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    emp_file = DATA_DIR / 'employees.csv'
    sal_file = DATA_DIR / 'salaries.csv'

    if not emp_file.exists():
        raise FileNotFoundError(f"Employees file not found: {emp_file}")
    if not sal_file.exists():
        raise FileNotFoundError(f"Salaries file not found: {sal_file}")

    employees = pd.read_csv(emp_file)
    salaries = pd.read_csv(sal_file)
    assert isinstance(employees, pd.DataFrame)
    assert isinstance(salaries, pd.DataFrame)
    result = build_report(employees, salaries)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)


if __name__ == '__main__':
    main()
