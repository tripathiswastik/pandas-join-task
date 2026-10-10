import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import pandas as pd

_APP_DIR = Path('/app') if Path('/app').exists() else Path(__file__).resolve().parent.parent / 'environment' / 'app'
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

    duplicates = sal.loc[sal['emp_id'].duplicated(keep=False), 'emp_id'].drop_duplicates().tolist()
    if duplicates:
        raise ValueError(f'Duplicate normalized salary keys: {duplicates}')

    emp['_event_utc'] = pd.to_datetime(emp['event_ts'], errors='raise', utc=True, format='mixed')
    emp = emp.loc[emp['_event_utc'].between(WINDOW_START, WINDOW_END, inclusive='both')].copy()

    merged = emp.merge(sal[['emp_id', 'annual_salary']], on='emp_id', how='left', validate='many_to_one', sort=False)
    merged['adjusted_salary'] = merged['annual_salary'].fillna(0).apply(round_half_up).astype('int64')
    contractor = merged['employment_type'].eq('CONTRACTOR')
    merged.loc[contractor, 'adjusted_salary'] = (
        merged.loc[contractor, 'annual_salary']
        .fillna(0)
        .astype(str)
        .apply(lambda x: round_half_up(Decimal(x) * Decimal('0.85')))
        .astype('int64')
    )

    result = merged.groupby('emp_id', sort=False, as_index=False).agg(
        headcount=('emp_id', 'size'), total_salary=('adjusted_salary', 'sum')
    )
    result = result.reindex(columns=OUTPUT_COLUMNS)
    result['emp_id'] = result['emp_id'].astype(object)
    result['headcount'] = result['headcount'].astype('int64')
    result['total_salary'] = result['total_salary'].astype('int64')
    return result.reset_index(drop=True)


def main() -> None:
    employees = pd.read_csv(DATA_DIR / 'employees.csv')
    salaries = pd.read_csv(DATA_DIR / 'salaries.csv')
    result = build_report(employees, salaries)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)


if __name__ == '__main__':
    main()
