"""Mutated stress tests and edge cases for the pandas reconciliation pipeline."""
from __future__ import annotations

import importlib.util
import os
import pathlib
import pandas as pd
import numpy as np

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
APP = pathlib.Path(os.environ.get('APP_DIR', '/app' if pathlib.Path('/app').exists() else str(BASE_DIR / 'environment' / 'app')))
COLS = ['emp_id', 'headcount', 'total_salary']


def load():
    spec = importlib.util.spec_from_file_location('pipeline', APP / 'pipeline.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def emp(rows, columns=('emp_id', 'employment_type', 'event_ts', 'notes')):
    return pd.DataFrame(rows, columns=columns)


def sal(rows, columns=('emp_id', 'annual_salary')):
    return pd.DataFrame(rows, columns=columns)


def test_idempotent_multiple_pipeline_invocations():
    """Ensure running the pipeline multiple times maintains deterministic output without side effects."""
    m = load()
    e = emp([
        [' E100 ', 'FULL_TIME', '2024-03-15 10:00:00', 'note1'],
        ['e100', 'CONTRACTOR', '2024-04-10 12:00:00', 'note2'],
        ['E200', 'CONTRACTOR', '2024-05-01 08:00:00', 'note3'],
    ])
    s = sal([
        ['e100', 100000],
        ['E200', 50000],
    ])

    res1 = m.build_report(e, s)
    res2 = m.build_report(e, s)

    pd.testing.assert_frame_equal(res1, res2)
    assert res1.to_dict('records') == [
        {'emp_id': 'E100', 'headcount': 2, 'total_salary': 185000},
        {'emp_id': 'E200', 'headcount': 1, 'total_salary': 42500},
    ]


def test_extreme_timezone_offsets_and_boundary_cases():
    """Ensure extreme timezone offsets (+14:00 and -12:00) correctly convert to UTC."""
    m = load()
    # +14:00: 2024-01-01 13:59:59+14:00 is 2023-12-31 23:59:59 UTC -> outside window
    # +14:00: 2024-01-01 14:00:00+14:00 is 2024-01-01 00:00:00 UTC -> exactly on start window
    # -12:00: 2024-12-31 11:59:59-12:00 is 2024-12-31 23:59:59 UTC -> exactly on end window
    # -12:00: 2024-12-31 12:00:00-12:00 is 2025-01-01 00:00:00 UTC -> outside window
    e = emp([
        ['OUT1', 'FULL_TIME', '2024-01-01T13:59:59+14:00', 'just before start'],
        ['IN1', 'FULL_TIME', '2024-01-01T14:00:00+14:00', 'exact start'],
        ['IN2', 'CONTRACTOR', '2024-12-31T11:59:59-12:00', 'exact end'],
        ['OUT2', 'CONTRACTOR', '2024-12-31T12:00:00-12:00', 'just after end'],
    ])
    s = sal([
        ['IN1', 60000],
        ['IN2', 100000],
    ])

    got = m.build_report(e, s)
    assert got['emp_id'].tolist() == ['IN1', 'IN2']
    assert got['headcount'].tolist() == [1, 1]
    assert got['total_salary'].tolist() == [60000, 85000]


def test_high_volume_contractors_precision_and_round_half_up():
    """Ensure exact round-half-up holds across diverse values ending in .5, .49, .51."""
    m = load()
    # 1: 1 * 0.85 = 0.85 -> 1
    # 3: 3 * 0.85 = 2.55 -> 3
    # 5: 5 * 0.85 = 4.25 -> 4
    # 7: 7 * 0.85 = 5.95 -> 6
    # 10: 10 * 0.85 = 8.5 -> 9 (round-half-up)
    e = emp([
        ['C1', 'CONTRACTOR', '2024-06-01', ''],
        ['C3', 'CONTRACTOR', '2024-06-01', ''],
        ['C5', 'CONTRACTOR', '2024-06-01', ''],
        ['C7', 'CONTRACTOR', '2024-06-01', ''],
        ['C10', 'CONTRACTOR', '2024-06-01', ''],
    ])
    s = sal([
        ['C1', 1],
        ['C3', 3],
        ['C5', 5],
        ['C7', 7],
        ['C10', 10],
    ])
    got = m.build_report(e, s)
    assert got['total_salary'].tolist() == [1, 3, 4, 6, 9]


def test_unmatched_employees_with_mixed_employment_types():
    """Employees not present in salaries table default to 0 salary without crashing."""
    m = load()
    e = emp([
        ['U1', 'FULL_TIME', '2024-02-01', ''],
        ['U2', 'CONTRACTOR', '2024-02-01', ''],
        ['U1', 'FULL_TIME', '2024-03-01', ''],
    ])
    s = sal([])
    got = m.build_report(e, s)
    assert got.to_dict('records') == [
        {'emp_id': 'U1', 'headcount': 2, 'total_salary': 0},
        {'emp_id': 'U2', 'headcount': 1, 'total_salary': 0},
    ]
    assert got['headcount'].dtype == np.dtype('int64')
    assert got['total_salary'].dtype == np.dtype('int64')
