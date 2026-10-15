"""
Benchmark Integrity Safeguard Test.

Ensures that the candidate starter pipeline in `environment/app/pipeline.py`
and reference solution in `solution/pipeline.py` are distinct and that the
starter pipeline genuinely contains the intended defects for the benchmark.
"""

import ast
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CANDIDATE_PATH = BASE_DIR / "environment" / "app" / "pipeline.py"
SOLUTION_PATH = BASE_DIR / "solution" / "pipeline.py"


def test_candidate_and_reference_are_not_identical():
    """Verify that candidate and solution files are not textually identical."""
    assert CANDIDATE_PATH.exists(), f"Candidate file not found: {CANDIDATE_PATH}"
    assert SOLUTION_PATH.exists(), f"Solution file not found: {SOLUTION_PATH}"

    candidate_text = CANDIDATE_PATH.read_text(encoding="utf-8").strip()
    solution_text = SOLUTION_PATH.read_text(encoding="utf-8").strip()

    assert candidate_text != solution_text, (
        "CRITICAL BENCHMARK DEFECT: Candidate implementation (environment/app/pipeline.py) "
        "and reference solution (solution/pipeline.py) are identical! "
        "The candidate must contain the intended defects."
    )


def test_candidate_and_reference_are_not_semantically_equivalent():
    """Verify that candidate and solution have distinct AST structures and logic."""
    candidate_ast = ast.parse(CANDIDATE_PATH.read_text(encoding="utf-8"))
    solution_ast = ast.parse(SOLUTION_PATH.read_text(encoding="utf-8"))

    candidate_dump = ast.dump(candidate_ast)
    solution_dump = ast.dump(solution_ast)

    assert candidate_dump != solution_dump, (
        "Candidate and reference implementations are structurally equivalent."
    )


def test_candidate_has_intended_defect_markers():
    """Verify that candidate source code contains the intended starter defects."""
    candidate_text = CANDIDATE_PATH.read_text(encoding="utf-8")
    solution_text = SOLUTION_PATH.read_text(encoding="utf-8")

    # Solution must have duplicate validation and Decimal round-half-up
    assert "Duplicate normalized salary keys" in solution_text
    assert "ROUND_HALF_UP" in solution_text
    assert "Decimal" in solution_text

    # Candidate should lack the completed solution's duplicate exception or decimal import
    assert "Duplicate normalized salary keys" not in candidate_text, (
        "Candidate starter code must not contain the completed duplicate key validation."
    )
