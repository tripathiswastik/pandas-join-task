"""
Mutation Verification Test Suite.

Proves that the verifier test suite (test_outputs.py) correctly fails
whenever any of the 5 required contract behaviors (A through E) is broken.
"""

from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import pytest

from tests import test_outputs
from tests.test_outputs import COLS

WINDOW_START = pd.Timestamp("2024-01-01 00:00:00+00:00")
WINDOW_END = pd.Timestamp("2024-12-31 23:59:59+00:00")


def normalize_emp_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def round_half_up(value) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class MockPipelineModule:
    """Mock pipeline module holding a mutated build_report function and required constants."""

    def __init__(self, build_report_fn):
        self.build_report = build_report_fn
        self.WINDOW_START = WINDOW_START
        self.WINDOW_END = WINDOW_END
        self.OUTPUT_COLUMNS = COLS


def _make_mock_module(build_report_fn) -> MockPipelineModule:
    """Create a mock pipeline module holding a mutated build_report function."""
    return MockPipelineModule(build_report_fn)


def _correct_build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
    """The fully compliant reference logic."""
    e = employees.copy()
    s = salaries.copy()
    e["emp_id"] = normalize_emp_id(e["emp_id"])
    s["emp_id"] = normalize_emp_id(s["emp_id"])

    dup_mask = s["emp_id"].duplicated(keep=False)
    if dup_mask.any():
        duplicates = list(s.loc[dup_mask, "emp_id"].unique())
        raise ValueError(f"Duplicate normalized salary keys: {duplicates}")

    try:
        e["_event_utc"] = pd.to_datetime(e["event_ts"], errors="raise", utc=True, format="mixed")
    except (ValueError, TypeError):
        e["_event_utc"] = pd.to_datetime(e["event_ts"], errors="raise", utc=True)
    e = e.loc[e["_event_utc"].between(WINDOW_START, WINDOW_END, inclusive="both")]

    merged = e.merge(s[["emp_id", "annual_salary"]], on="emp_id", how="left", validate="many_to_one", sort=False)
    base_salaries = merged["annual_salary"].fillna(0)
    merged["adjusted_salary"] = base_salaries.apply(round_half_up).astype("int64")

    contractor_mask = merged["employment_type"].eq("CONTRACTOR")
    if contractor_mask.any():
        contractor_salaries = base_salaries.loc[contractor_mask]
        unique_salaries = contractor_salaries.unique()
        discount_cache = {
            val: round_half_up(Decimal(str(val)) * Decimal("0.85"))
            for val in unique_salaries
        }
        merged.loc[contractor_mask, "adjusted_salary"] = contractor_salaries.map(discount_cache).astype("int64")

    result = merged.groupby("emp_id", sort=False, as_index=False).agg(
        headcount=("emp_id", "size"), total_salary=("adjusted_salary", "sum")
    )
    result = result.reindex(columns=COLS)
    result["emp_id"] = result["emp_id"].astype(object)
    result["headcount"] = result["headcount"].fillna(0).astype("int64")
    result["total_salary"] = result["total_salary"].fillna(0).astype("int64")
    return result.reset_index(drop=True)


def test_mutation_a_silent_duplicate_salary_keys_is_caught(monkeypatch):
    """Mutation A: Omitting duplicate key validation MUST fail test_a."""
    def mutated_build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
        e = employees.copy()
        s = salaries.copy()
        e["emp_id"] = normalize_emp_id(e["emp_id"])
        s["emp_id"] = normalize_emp_id(s["emp_id"])
        # SKIPPED duplicate validation!
        merged = e.merge(s[["emp_id", "annual_salary"]], on="emp_id", how="left")
        merged["adjusted_salary"] = merged["annual_salary"].fillna(0).astype("int64")
        result = merged.groupby("emp_id", as_index=False).agg(
            headcount=("emp_id", "size"), total_salary=("adjusted_salary", "sum")
        )
        return result.reindex(columns=COLS)

    mock_mod = _make_mock_module(mutated_build_report)
    monkeypatch.setattr("tests.test_outputs.load", lambda: mock_mod)

    with pytest.raises(AssertionError, match="Expected descriptive duplicate normalized salary key exception"):
        test_outputs.test_a_duplicate_normalized_salary_keys_raise_descriptive_error()


def test_mutation_b_missing_emp_id_normalization_is_caught(monkeypatch):
    """Mutation B: Skipping identifier normalization MUST fail test_b."""
    def mutated_build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
        e = employees.copy()
        s = salaries.copy()
        # Skipped normalizing employees emp_id! (only normalize salaries)
        s["emp_id"] = normalize_emp_id(s["emp_id"])
        try:
            e["_event_utc"] = pd.to_datetime(e["event_ts"], errors="raise", utc=True, format="mixed")
        except (ValueError, TypeError):
            e["_event_utc"] = pd.to_datetime(e["event_ts"], errors="raise", utc=True)
        e = e.loc[e["_event_utc"].between(WINDOW_START, WINDOW_END, inclusive="both")]

        merged = e.merge(s[["emp_id", "annual_salary"]], on="emp_id", how="left", validate="many_to_one", sort=False)
        base_salaries = merged["annual_salary"].fillna(0)
        merged["adjusted_salary"] = base_salaries.apply(round_half_up).astype("int64")

        result = merged.groupby("emp_id", sort=False, as_index=False).agg(
            headcount=("emp_id", "size"), total_salary=("adjusted_salary", "sum")
        )
        result = result.reindex(columns=COLS)
        result["emp_id"] = result["emp_id"].astype(object)
        result["headcount"] = result["headcount"].fillna(0).astype("int64")
        result["total_salary"] = result["total_salary"].fillna(0).astype("int64")
        return result.reset_index(drop=True)

    mock_mod = _make_mock_module(mutated_build_report)
    monkeypatch.setattr("tests.test_outputs.load", lambda: mock_mod)

    with pytest.raises(AssertionError):
        test_outputs.test_b_only_emp_id_is_normalized_and_other_whitespace_is_preserved()


def test_mutation_c_naive_datetime_comparison_is_caught(monkeypatch):
    """Mutation C: Failing to unify mixed timezones to UTC MUST fail test_c."""
    def mutated_build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
        e = employees.copy()
        s = salaries.copy()
        # Flawed naive datetime parsing without UTC unification
        e["event_ts"] = pd.to_datetime(e["event_ts"], errors="raise")
        e = e[(e["event_ts"] >= WINDOW_START.tz_localize(None)) & (e["event_ts"] <= WINDOW_END.tz_localize(None))]
        return _correct_build_report(e, s)

    mock_mod = _make_mock_module(mutated_build_report)
    monkeypatch.setattr("tests.test_outputs.load", lambda: mock_mod)

    with pytest.raises((TypeError, AssertionError)):
        test_outputs.test_c_naive_and_offset_timestamps_are_normalized_by_pipeline()


def test_mutation_d_float_drift_on_unmatched_is_caught(monkeypatch):
    """Mutation D: Allowing total_salary to drift to float64 on unmatched rows MUST fail test_d."""
    def mutated_build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
        res = _correct_build_report(employees, salaries)
        # Mutate total_salary to float64 when unmatched rows exist
        if len(salaries) < len(employees):
            res["total_salary"] = res["total_salary"].astype("float64")
        return res

    mock_mod = _make_mock_module(mutated_build_report)
    monkeypatch.setattr("tests.test_outputs.load", lambda: mock_mod)

    with pytest.raises(AssertionError):
        test_outputs.test_d_int64_types_are_explicit_for_nonempty_and_empty_results()


def test_mutation_e_improper_contractor_rounding_is_caught(monkeypatch):
    """Mutation E: Using banker's rounding / float truncation instead of round-half-up MUST fail test_e."""
    def mutated_build_report(employees: pd.DataFrame, salaries: pd.DataFrame) -> pd.DataFrame:
        e = employees.copy()
        s = salaries.copy()
        e["emp_id"] = normalize_emp_id(e["emp_id"])
        s["emp_id"] = normalize_emp_id(s["emp_id"])
        merged = e.merge(s[["emp_id", "annual_salary"]], on="emp_id", how="left")
        # Mutated: standard float multiplication without round-half-up
        merged["adjusted_salary"] = (merged["annual_salary"].fillna(0) * 0.85).astype("int64")
        result = merged.groupby("emp_id", as_index=False).agg(
            headcount=("emp_id", "size"), total_salary=("adjusted_salary", "sum")
        )
        result["headcount"] = result["headcount"].astype("int64")
        result["total_salary"] = result["total_salary"].astype("int64")
        return result.reindex(columns=COLS)

    mock_mod = _make_mock_module(mutated_build_report)
    monkeypatch.setattr("tests.test_outputs.load", lambda: mock_mod)

    with pytest.raises(AssertionError):
        test_outputs.test_e_contractor_adjustment_is_downstream_and_rounds_half_up()
