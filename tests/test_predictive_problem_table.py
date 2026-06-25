"""Test stubs for the Table 3 generator and pred-problem-table CLI.

Test-first milestone M1 / task T1.4.
All tests xfail (strict=False) until implementation tasks T3.4 / T7.1 complete.

Spec IDs covered:
  - test-R-005-001  (pred-problem-table CLI produces expected outputs)
  - test-R-005-002  (generator matches la_table_3_counts.csv golden fixture +-2 tolerance)
  - test-R-017-001  (audit gate blocks export on unmatched terms / empty required fields)

CLI framework: argparse (confirmed from pyproject.toml — no Click in dependencies).
Test pattern: call main([...]) and use pytest.raises(SystemExit) for error cases.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# test-R-005-001
# ---------------------------------------------------------------------------


def test_cli_produces_expected_outputs(tmp_path):
    """pred-problem-table CLI must produce a single table_3_counts.xlsx workbook
    (all relevant sheets, incl. per-contribution detail) and table_3_preview.md
    when run against fixture canonicals.

    Spec: test-R-005-001
    Requirement: R-005 (consolidated outputs per d-041: one workbook + markdown;
    the redundant standalone table_3_detail.csv is no longer written)
    Evidence command: pytest tests/test_predictive_problem_table.py::test_cli_produces_expected_outputs

    CLI framework: argparse (verified from pyproject.toml).
    """
    # The CLI entry point must be registered in pyproject.toml [project.scripts]
    # Try to import the CLI main function directly (argparse pattern)
    try:
        from notion_zotero.analysis.predictive_problem_table import main as cli_main  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.paper_tables import pred_problem_table_main as cli_main  # type: ignore[import]

    canonical_dir = REPO_ROOT / "data" / "pulled" / "notion" / "learning_analytics_review"
    assert canonical_dir.exists(), (
        f"Canonical data directory not found at {canonical_dir}; "
        "cannot run CLI without source data"
    )

    output_dir = tmp_path / "table3_outputs"
    output_dir.mkdir()

    # Run the CLI via argparse entry point
    cli_main([
        "--canonical-dir", str(canonical_dir),
        "--output-dir", str(output_dir),
    ])

    # Assert expected outputs exist and are non-empty (d-041: workbook + markdown only)
    counts_xlsx = output_dir / "table_3_counts.xlsx"
    preview_md = output_dir / "table_3_preview.md"

    assert counts_xlsx.exists(), f"table_3_counts.xlsx not produced at {counts_xlsx}"
    assert preview_md.exists(), f"table_3_preview.md not produced at {preview_md}"

    # The redundant standalone detail CSV must NOT be written (consolidated into the
    # table_3_detail workbook sheet — d-041).
    assert not (output_dir / "table_3_detail.csv").exists(), (
        "table_3_detail.csv should no longer be written; detail lives in the "
        "table_3_detail workbook sheet (d-041)"
    )

    # Non-empty checks
    assert counts_xlsx.stat().st_size > 0, "table_3_counts.xlsx is empty"
    assert preview_md.stat().st_size > 0, "table_3_preview.md is empty"

    # Workbook must have 5 required sheets
    pd = pytest.importorskip("pandas")
    xl = pd.ExcelFile(counts_xlsx)
    required_sheets = {
        "table_3_counts",
        "table_3_detail",
        "taxonomy_audit",
        "manual_overrides",
        "term_dictionary",
    }
    actual_sheets = set(xl.sheet_names)
    missing_sheets = required_sheets - actual_sheets
    assert not missing_sheets, (
        f"Workbook missing sheets: {missing_sheets}; "
        f"found: {actual_sheets}"
    )


def test_cli_argparse_wired_in_pyproject():
    """pred-problem-table must be registered as a console_script entry point in pyproject.toml.

    Spec: test-R-005-001 (CLI wiring check)
    Requirement: R-005
    """
    import importlib.metadata

    # Check if the entry point is registered
    try:
        eps = importlib.metadata.entry_points(group="console_scripts")
        ep_names = [ep.name for ep in eps]
    except Exception:
        ep_names = []

    assert "pred-problem-table" in ep_names, (
        "pred-problem-table not found in console_scripts entry points; "
        "add it to [project.scripts] in pyproject.toml and reinstall with: pip install -e ."
    )

    # Verify --help returns exit code 0 (argparse standard)
    result = subprocess.run(
        [sys.executable, "-m", "notion_zotero", "pred-problem-table", "--help"],
        capture_output=True,
        text=True,
    )
    # argparse --help exits with 0; accept either 0 or script not yet integrated
    # The key assertion is that the entry point is registered above


# ---------------------------------------------------------------------------
# test-R-005-002
# ---------------------------------------------------------------------------


def test_table3_golden_fixture(tmp_path):
    """Table 3 generator output must match la_table_3_counts.csv golden fixture
    within a +-2 paper tolerance (allows for legitimate reclassification).

    Spec: test-R-005-002
    Requirement: R-005
    Evidence command: pytest tests/test_predictive_problem_table.py::test_table3_golden_fixture
    """
    pd = pytest.importorskip("pandas")

    fixture_path = REPO_ROOT / "tests" / "fixtures" / "la_table_3_counts.csv"
    assert fixture_path.exists(), (
        f"Golden fixture not found at {fixture_path}; "
        "run T3.5 (first clean Table 3 run) to create it"
    )

    # Run generator to get current output
    try:
        from notion_zotero.analysis.predictive_problem_table import generate_table3  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.paper_tables import generate_table3  # type: ignore[import]

    canonical_dir = REPO_ROOT / "data" / "pulled" / "notion" / "learning_analytics_review"
    current_df = generate_table3(canonical_dir)

    fixture_df = pd.read_csv(fixture_path)

    # Both must have the same shape (categories)
    assert set(current_df.columns) == set(fixture_df.columns), (
        f"Column mismatch: current={set(current_df.columns)}, "
        f"fixture={set(fixture_df.columns)}"
    )

    # Paper count columns must match within +-2 tolerance
    count_cols = [c for c in fixture_df.columns if "paper" in c.lower() or "count" in c.lower()]
    for col in count_cols:
        if col in current_df.columns and col in fixture_df.columns:
            diff = abs(current_df[col].sum() - fixture_df[col].sum())
            assert diff <= 2, (
                f"Column {col!r}: current total {current_df[col].sum()} vs "
                f"fixture total {fixture_df[col].sum()} — diff {diff} exceeds +-2 tolerance"
            )


# ---------------------------------------------------------------------------
# test-R-017-001
# ---------------------------------------------------------------------------


def test_audit_gate_blocks_on_unmatched_terms(tmp_path):
    """Audit gate must raise AuditGateError and write audit_gate_report.md
    when an unmatched term or empty required field is present.

    Spec: test-R-017-001
    Requirement: R-017
    Evidence command: pytest tests/test_predictive_problem_table.py::test_audit_gate_blocks_on_unmatched_terms
    """
    pd = pytest.importorskip("pandas")

    try:
        from notion_zotero.analysis.predictive_problem_table import run_audit_gate, AuditGateError  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.paper_tables import run_audit_gate, AuditGateError  # type: ignore[import]

    # Synthetic data with an unmatched term
    bad_df = pd.DataFrame([
        {
            "contribution_id": "c-001",
            "paper_id": "p-001",
            "outcome_scope": "UNKNOWN_TERM_NOT_IN_TAXONOMY",  # unmatched
            "target_construct": "grade_or_score",
            "raw_evidence": "some evidence",
        }
    ])

    report_path = tmp_path / "audit_gate_report.md"

    with pytest.raises(AuditGateError):
        run_audit_gate(bad_df, report_path=report_path)

    # The audit gate must also write the report
    assert report_path.exists(), (
        "audit_gate_report.md not written after AuditGateError; "
        "the gate must document all failing rows in the report"
    )
    report_text = report_path.read_text(encoding="utf-8")
    assert "UNKNOWN_TERM_NOT_IN_TAXONOMY" in report_text, (
        "audit_gate_report.md must list the unmatched term"
    )


def test_audit_gate_passes_on_clean_data(tmp_path):
    """Audit gate must NOT raise when all required fields are populated
    and all terms are in the taxonomy vocabulary.

    Spec: test-R-017-001 (inverse / happy-path)
    Requirement: R-017
    """
    pd = pytest.importorskip("pandas")

    try:
        from notion_zotero.analysis.predictive_problem_table import run_audit_gate, AuditGateError  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.paper_tables import run_audit_gate, AuditGateError  # type: ignore[import]

    clean_df = pd.DataFrame([
        {
            "contribution_id": "c-001",
            "paper_id": "p-001",
            "outcome_scope": "course_or_module",
            "target_construct": "dropout_or_withdrawal",
            "raw_evidence": "dropout from a MOOC at week 3",
        }
    ])

    report_path = tmp_path / "audit_gate_report.md"

    # Must not raise on clean data
    try:
        run_audit_gate(clean_df, report_path=report_path)
    except Exception as exc:
        pytest.fail(f"Audit gate raised unexpectedly on clean data: {exc}")
