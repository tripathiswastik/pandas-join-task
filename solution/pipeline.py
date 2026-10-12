import os
from decimal import Decimal, ROUND_HALF_UP
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
OUTPUT_COLUMNS = ['emp_id', 'headcount', 'total_salary']


def normalize_emp_id(series: pd.Series) -> pd.Series:
    return series.astype('string').str.strip().str.upper()


def round_half_up(value) -> int:
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
    emp = employees.copy()
    sal = salaries.copy()
    emp['emp_id'] = normalize_emp_id(emp['emp_id'])
    sal['emp_id'] = normalize_emp_id(sal['emp_id'])

    dup_mask = sal['emp_id'].duplicated(keep=False)
    if dup_mask.any():
        duplicates = list(sal.loc[dup_mask, 'emp_id'].unique())
        raise ValueError(f'Duplicate normalized salary keys: {duplicates}')

    try:
        emp['_event_utc'] = pd.to_datetime(emp['event_ts'], errors='raise', utc=True, format='mixed')
    except (ValueError, TypeError):
        emp['_event_utc'] = pd.to_datetime(emp['event_ts'], errors='raise', utc=True)
    emp = emp.loc[emp['_event_utc'].between(WINDOW_START, WINDOW_END, inclusive='both')]

    merged = emp.merge(sal[['emp_id', 'annual_salary']], on='emp_id', how='left', validate='many_to_one', sort=False)
    base_salaries = merged['annual_salary'].fillna(0)
    merged['adjusted_salary'] = base_salaries.apply(round_half_up).astype('int64')

    contractor_mask = merged['employment_type'].eq('CONTRACTOR')
    if contractor_mask.any():
        contractor_salaries = base_salaries.loc[contractor_mask]
        unique_salaries = contractor_salaries.unique()
        discount_cache = {
            s: round_half_up(Decimal(str(s)) * Decimal('0.85'))
            for s in unique_salaries
        }
        merged.loc[contractor_mask, 'adjusted_salary'] = contractor_salaries.map(discount_cache).astype('int64')

    result = merged.groupby('emp_id', sort=False, as_index=False).agg(
        headcount=('emp_id', 'size'), total_salary=('adjusted_salary', 'sum')
    )
    result = result.reindex(columns=OUTPUT_COLUMNS)
    result['emp_id'] = result['emp_id'].astype(object)
    result['headcount'] = result['headcount'].fillna(0).astype('int64')
    result['total_salary'] = result['total_salary'].fillna(0).astype('int64')
    return result.reset_index(drop=True)


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
    result = build_report(employees, salaries)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)


if __name__ == '__main__':
    main()
