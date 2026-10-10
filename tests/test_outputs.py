"""Verifier for the five independent root causes and their interactions."""
import importlib.util
import pathlib
import subprocess
import sys
import pandas as pd
import numpy as np
import os

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
APP = pathlib.Path(os.environ.get('APP_DIR', '/app' if pathlib.Path('/app').exists() else str(BASE_DIR / 'environment' / 'app')))
OUT = pathlib.Path(os.environ.get('OUTPUT_PATH', str(APP / 'output/report.csv')))
COLS = ['emp_id', 'headcount', 'total_salary']

def load():
    spec = importlib.util.spec_from_file_location('pipeline', APP / 'pipeline.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def emp(rows, columns=('emp_id','employment_type','event_ts','notes')):
    return pd.DataFrame(rows, columns=columns)

def sal(rows, columns=('emp_id','annual_salary')):
    return pd.DataFrame(rows, columns=columns)

def assert_frame(got, rows):
    expected = pd.DataFrame(rows, columns=COLS)
    expected['headcount'] = expected['headcount'].astype('int64')
    expected['total_salary'] = expected['total_salary'].astype('int64')
    got = got.reset_index(drop=True)
    expected = expected.reset_index(drop=True)

    # emp_id is semantically a string key; its pandas storage dtype is not part
    # of the contract, so do not fail on object vs. nullable StringDtype.
    assert list(got.columns) == COLS
    assert got['emp_id'].astype('string').tolist() == expected['emp_id'].astype('string').tolist()

    # The aggregate columns are explicitly part of the contract as int64, so
    # keep strict dtype checks for them while comparing their exact values.
    assert got['headcount'].dtype == np.dtype('int64')
    assert got['total_salary'].dtype == np.dtype('int64')
    pd.testing.assert_series_equal(
        got['headcount'], expected['headcount'], check_dtype=True, check_names=True
    )
    pd.testing.assert_series_equal(
        got['total_salary'], expected['total_salary'], check_dtype=True, check_names=True
    )

# A = 20%
def test_a_duplicate_normalized_salary_keys_raise_descriptive_error():
    """A: duplicate salary keys after normalization must be rejected."""
    m = load(); e = emp([['E1','FULL_TIME','2024-01-01','x']])
    s = sal([[' e1 ',10],['E1',20]])
    try: m.build_report(e,s)
    except Exception as exc: assert 'duplicate' in str(exc).lower() and 'E1' in str(exc).upper()
    else: raise AssertionError('Expected descriptive duplicate normalized salary key exception')

# B = 20%
def test_b_only_emp_id_is_normalized_and_other_whitespace_is_preserved():
    """B: matching strips/uppercases only emp_id, not unrelated fields."""
    m=load(); e=emp([[' e1 ','FULL_TIME','2024-01-01','  untouched  '],['E2 ','FULL_TIME','2024-01-02',' keep ']])
    s=sal([['E1',10],[' e2',20]])
    got=m.build_report(e,s); assert_frame(got,[['E1',1,10],['E2',1,20]])
    assert e.loc[0,'notes']=='  untouched  '

def test_b_column_order_and_index_values_do_not_change_result():
    """B: pandas index values and input column order cannot define matching behavior."""
    m=load(); e=emp([[' a ','FULL_TIME','2024-01-01','x'],['B','FULL_TIME','2024-01-02','y']]); e.index=[91,3]
    e=e[['notes','event_ts','employment_type','emp_id']]
    s=sal([[200,'b'],[100,'A']], columns=('annual_salary','emp_id')); s.index=[8,4]
    got=m.build_report(e,s); assert_frame(got,[['A',1,100],['B',1,200]])

# C = 20%
def test_c_naive_and_offset_timestamps_are_normalized_by_pipeline():
    """C: pipeline itself must normalize naive, -05:00 and +05:30 timestamps to UTC."""
    m=load(); e=emp([
      ['A','FULL_TIME','2024-01-01 00:00:00','x'],
      ['B','FULL_TIME','2024-12-31T18:30:00-05:00','x'],
      ['C','FULL_TIME','2025-01-01T00:30:00+05:30','x'],
      ['D','FULL_TIME','2023-12-31T18:29:59-05:00','x'],
    ]); s=sal([['A',1],['B',2],['C',3],['D',4]])
    got=m.build_report(e,s); assert_frame(got,[['A',1,1],['B',1,2],['C',1,3]])

def test_c_chronology_is_not_lexical_and_boundaries_are_inclusive():
    """C: chronological UTC filtering must include both window endpoints."""
    m=load(); e=emp([['A','FULL_TIME','2024-01-01T00:00:00Z','x'],['B','FULL_TIME','2024-12-31T23:59:59Z','x'],['C','FULL_TIME','2025-01-01T00:00:00Z','x']]); s=sal([['A',1],['B',2],['C',3]])
    assert_frame(m.build_report(e,s),[['A',1,1],['B',1,2]])

# D = 20%
def test_d_int64_types_are_explicit_for_nonempty_and_empty_results():
    """D: both aggregate columns must be int64 even when no rows qualify."""
    m=load(); s=sal([['A',10]])
    got=m.build_report(emp([['A','FULL_TIME','2024-01-01','x']]),s)
    assert str(got.headcount.dtype)=='int64' and str(got.total_salary.dtype)=='int64'
    empty=m.build_report(emp([['A','FULL_TIME','2025-01-01','x']]),s)
    assert list(empty.columns)==COLS and empty.empty
    assert str(empty.headcount.dtype)=='int64' and str(empty.total_salary.dtype)=='int64'

# E = 20%
def test_e_contractor_adjustment_is_downstream_and_rounds_half_up():
    """E: contractor salary uses 85% round-half-up and the adjusted value reaches aggregation."""
    m=load(); e=emp([['A','CONTRACTOR','2024-06-01','x'],['A','FULL_TIME','2024-06-02','x'],['B','CONTRACTOR','2024-06-03','x']]); s=sal([['A',117648],['B',1]])
    got=m.build_report(e,s); assert_frame(got,[['A',2,217649],['B',1,1]])

def test_e_unmatched_contractor_is_zero_without_type_drift():
    """E: unmatched contractor records contribute integer zero."""
    m=load(); got=m.build_report(emp([['Z','CONTRACTOR','2024-06-01','x']]),sal([]))
    assert_frame(got,[['Z',1,0]])

# Combined regression (not weighted)
def test_combined_all_five_rules_interact_correctly():
    """Combined: normalization, timezone filtering, cardinality, int64, and contractor rounding work together."""
    m=load(); e=emp([
      [' a ','CONTRACTOR','2024-12-31T18:30:00-05:00',' keep '],
      ['A','FULL_TIME','2024-01-01 00:00:00',' keep2 '],
      [' b ','CONTRACTOR','2025-01-01T00:30:00+05:30','x'],
      ['C','FULL_TIME','2025-01-01T00:00:00Z','x'],
    ]); e.index=[50,10,90,2]
    s=sal([[117648,'A '],[50000,'B'],[99,'C']], columns=('annual_salary','emp_id')); s.index=[7,8,9]
    got=m.build_report(e,s); assert_frame(got,[['A',2,217649],['B',1,42500]])
    assert str(got.headcount.dtype)=='int64' and str(got.total_salary.dtype)=='int64'

def test_combined_reordered_inputs_interleaved_ids_and_half_up_boundaries():
    """Combined: reordered columns, arbitrary indices, interleaved normalized IDs, UTC edges, and exact half-up ties must all compose."""
    m=load()
    e=emp([
      [' x ','CONTRACTOR','2024-01-01T05:00:00-05:00',' untouched x1 '],
      ['Y','FULL_TIME','2024-01-01 00:00:00',' untouched y1 '],
      ['X','FULL_TIME','2024-12-31T23:59:59+05:30',' untouched x2 '],
      [' y ','CONTRACTOR','2023-12-31T23:59:59-05:00',' untouched y2 '],
      ['Z','CONTRACTOR','2025-01-01T00:00:00+05:30',' untouched z1 '],
      ['W','FULL_TIME','2025-01-01T00:00:00Z',' outside '],
    ])
    e.index=[101,7,55,2,88,19]
    e=e[['notes','emp_id','event_ts','employment_type']]
    s=sal([[50,'z'],[30,' Y '],[10,'X']], columns=('annual_salary','emp_id'))
    s.index=[44,3,91]
    got=m.build_report(e,s)
    assert_frame(got,[['X',2,19],['Y',2,56],['Z',1,43]])

def test_written_pipeline_output_matches_contract_fixture():
    """Combined: executable pipeline writes the shipped fixture with the required schema and values."""
    subprocess.run([sys.executable, str(APP/'pipeline.py')], check=True)
    out=pd.read_csv(OUT)
    assert list(out.columns)==COLS
    assert out.to_dict('records') == [
      {'emp_id':'E001','headcount':2,'total_salary':200000},
      {'emp_id':'E002','headcount':1,'total_salary':100001},
      {'emp_id':'E003','headcount':1,'total_salary':50000},
      {'emp_id':'E004','headcount':1,'total_salary':68000},
    ]
