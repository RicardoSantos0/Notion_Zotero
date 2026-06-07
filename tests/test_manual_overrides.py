"""Test stubs for manual overrides YAML layer and review_pipeline imports.

Test-first milestone M1 / task T1.1.
Tests are:
  - test_no_hardcoded_overrides_in_source: AST-walk (no xfail — verifies existing state)
  - test_review_pipeline_imports: xfail (review_pipeline/ does not exist before T7.3)
  - override YAML load / apply tests: xfail (YAML files created by T2.1)

Spec IDs covered:
  - test-R-001-001  (no paper-specific logic in Python source)
  - test-R-018-001  (review_pipeline 7 modules import without error)

CLI framework note: CLI is argparse (verified from pyproject.toml [project.scripts]:
  notion-zotero = "notion_zotero.cli:main"
  No Click in dependencies — do NOT use CliRunner).
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "notion_zotero"


# ---------------------------------------------------------------------------
# test-R-001-001  — no paper-specific logic in Python source
# ---------------------------------------------------------------------------


def test_no_hardcoded_overrides_in_source():
    """No paper-specific title-override strings must remain in Python source files.

    This test greps src/ for known paper-title override patterns and asserts
    that the count is zero (all overrides must be in manual_overrides.yaml or
    title_overrides.yaml).

    Spec: test-R-001-001
    Requirement: R-001
    Evidence command: pytest tests/test_manual_overrides.py::test_no_hardcoded_overrides_in_source

    Expected initial state: FAILS until WP1 (T2.1) moves overrides into YAML files.
    The test runs WITHOUT xfail so that it is immediately actionable.
    """
    # Paper-title fragment patterns that should only appear in YAML override files,
    # not in Python source.  These are representative substrings extracted from the
    # known hard-coded override dicts in pred_horizon_summary.py (current state).
    # Add more fragments here as new ones are discovered during WP1 review.
    PAPER_TITLE_FRAGMENTS = [
        # Fragments from known hard-coded title override dicts in pred_horizon_summary.py
        "Predicting student academic performance using multi-model",
        "subscription-based online learning environments",
        "Predicting student dropout in subscription",
        # Generic heuristic: dict literal with a paper-specific year-author pattern
        # e.g., {"Lopez et al., 2020": "Long-term"}
    ]

    violations: list[str] = []
    python_files = list(SRC_ROOT.rglob("*.py"))
    assert python_files, f"No Python files found under {SRC_ROOT}"

    for py_file in python_files:
        # Skip test files accidentally under src
        if "test_" in py_file.name:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for fragment in PAPER_TITLE_FRAGMENTS:
            if fragment in source:
                violations.append(f"{py_file.relative_to(REPO_ROOT)}: contains {fragment!r}")

    assert not violations, (
        "Paper-specific title overrides found in Python source files — "
        "they must be moved to configs/reviews/la_student_success_review/manual_overrides.yaml "
        "or title_overrides.yaml (WP1 T2.1):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_hardcoded_overrides_ast_walk():
    """AST-walk version: assert that pred_horizon_summary.py contains no dict literals
    whose keys look like paper title strings (all-word strings with spaces and year patterns).

    Spec: test-R-001-001 (AST guard complement)
    Requirement: R-001

    This test targets the specific pattern:
        TITLE_OVERRIDE_MAP = {"Predicting student ...: ...", ...}
    and asserts that no such string-keyed dict literal remains in the source.
    """
    pred_file = SRC_ROOT / "analysis" / "pred_horizon_summary.py"
    if not pred_file.exists():
        pytest.skip(f"pred_horizon_summary.py not found at {pred_file}")

    source = pred_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(pred_file))

    # Pattern: a dict literal where keys are long strings that look like paper titles.
    # Paper titles are characterised by:
    #   - Starting with an uppercase letter
    #   - Containing at least 5 words (spaces separate them)
    #   - NOT being a known column name pattern (column names tend to be short noun phrases)
    #   - Containing lowercase continuation words (verbs / connectives mark prose titles)
    #
    # We deliberately exclude short multi-word column names (e.g. "Student Performance
    # Definition", "Number of Research Papers") by requiring >=5 words AND at least one
    # typical prose connector or verb.
    PAPER_TITLE_PATTERN = re.compile(
        r"^[A-Z][a-z]+"                   # starts with a proper capitalised word
        r"(?:\s+\w+){4,}"                  # followed by at least 4 more words (>=5 total)
        r".*"
        r"(?:using|via|with|based|for|and|from|of|in|on|a\s|an\s|the\s)"  # prose connective
        r".*$",
        re.IGNORECASE,
    )

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key in node.keys:
            if key is None:
                continue
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                value = key.value.strip()
                # Skip short strings and known column-name patterns
                if len(value.split()) < 5:
                    continue
                if PAPER_TITLE_PATTERN.match(value):
                    violations.append(
                        f"Line {key.lineno}: dict key looks like paper title: "
                        f"{value[:60]!r}"
                    )

    assert not violations, (
        f"pred_horizon_summary.py contains dict literals with paper-title-like keys.\n"
        f"Move these overrides to configs/reviews/la_student_success_review/ YAML files (T2.1):\n"
        + "\n".join(f"  {v}" for v in violations[:10])
    )


# ---------------------------------------------------------------------------
# Override YAML load / apply tests (xfail until T2.1)
# ---------------------------------------------------------------------------


def test_manual_overrides_yaml_loads():
    """manual_overrides.yaml must load successfully and have a taxonomy_version_stamp header.

    Spec: test-R-001-001 (YAML existence)
    Requirement: R-001, d-013
    """
    yaml = pytest.importorskip("yaml")

    overrides_path = (
        REPO_ROOT
        / "configs"
        / "reviews"
        / "la_student_success_review"
        / "manual_overrides.yaml"
    )
    assert overrides_path.exists(), (
        f"manual_overrides.yaml not found at {overrides_path}; "
        "run T2.1 to create the configs/reviews/ directory and YAML files"
    )

    with overrides_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, dict), "manual_overrides.yaml must be a YAML mapping at the root"

    # d-013: taxonomy_version_stamp header field required
    assert "taxonomy_version_stamp" in data, (
        "manual_overrides.yaml missing 'taxonomy_version_stamp' header field (d-013); "
        "add it to match the taxonomy YAML version"
    )

    # Each override entry must have a rationale field
    overrides_list = data.get("overrides", [])
    for i, entry in enumerate(overrides_list):
        assert "rationale" in entry, (
            f"Override entry [{i}] missing 'rationale' field; "
            "every override must document its reasoning (R-001 requirement)"
        )


def test_title_overrides_yaml_loads():
    """title_overrides.yaml must load successfully as a valid YAML mapping.

    Spec: test-R-001-001
    Requirement: R-001
    """
    yaml = pytest.importorskip("yaml")

    title_overrides_path = (
        REPO_ROOT
        / "configs"
        / "reviews"
        / "la_student_success_review"
        / "title_overrides.yaml"
    )
    assert title_overrides_path.exists(), (
        f"title_overrides.yaml not found at {title_overrides_path}; "
        "run T2.1 to create it"
    )

    with title_overrides_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, dict), "title_overrides.yaml must be a YAML mapping at the root"


def test_overrides_apply_after_classification():
    """Manual overrides must be applied AFTER the rule-based classifier runs,
    not before. The final contribution row must reflect the override.

    Spec: test-R-001-001 (override apply order)
    Requirement: R-001
    """
    try:
        from notion_zotero.analysis.review_pipeline.overrides import apply_overrides  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.pred_horizon_summary import apply_overrides  # type: ignore[import]

    # Minimal synthetic override
    contribution_row = {
        "contribution_id": "c-test-001",
        "paper_id": "p-test-001",
        "target_construct": {"label": "grade_or_score", "confidence": "high", "evidence": "Final Grade"},
    }
    override = {
        "contribution_id": "c-test-001",
        "target_construct": "dropout_or_withdrawal",
        "rationale": "Paper actually predicts dropout despite title",
        "taxonomy_version_stamp": "1.1",
    }

    result = apply_overrides(contribution_row, overrides=[override])

    assert result["target_construct"]["label"] == "dropout_or_withdrawal", (
        "apply_overrides() must update the target_construct label"
    )
    # The override itself must be surfaced in audit output (not silently applied)
    assert result.get("_override_applied") is True or "rationale" in str(result), (
        "apply_overrides() must mark the row as override-applied for audit traceability"
    )


# ---------------------------------------------------------------------------
# test-R-018-001  — review_pipeline imports
# ---------------------------------------------------------------------------


def test_review_pipeline_imports():
    """All 7 review_pipeline modules must import without error and expose
    their documented public API functions.

    Spec: test-R-018-001
    Requirement: R-018
    Evidence command: pytest tests/test_manual_overrides.py::test_review_pipeline_imports
    """
    expected_modules_and_apis = {
        "notion_zotero.analysis.review_pipeline.contribution_rows": [
            "build_contribution_rows",
        ],
        "notion_zotero.analysis.review_pipeline.normalizers": [],
        "notion_zotero.analysis.review_pipeline.table_builder": [],
        "notion_zotero.analysis.review_pipeline.figure_data": [],
        "notion_zotero.analysis.review_pipeline.audit": [
            "run_audit_gate",
        ],
        "notion_zotero.analysis.review_pipeline.overrides": [
            "apply_overrides",
        ],
        "notion_zotero.analysis.review_pipeline.export": [],
    }

    import importlib

    failed_imports: list[str] = []
    missing_apis: list[str] = []

    for module_path, required_fns in expected_modules_and_apis.items():
        try:
            mod = importlib.import_module(module_path)
        except ImportError as exc:
            failed_imports.append(f"{module_path}: {exc}")
            continue

        for fn_name in required_fns:
            if not hasattr(mod, fn_name):
                missing_apis.append(f"{module_path} missing {fn_name!r}")

    errors = failed_imports + missing_apis
    assert not errors, (
        "review_pipeline module import / API check failed:\n"
        + "\n".join(f"  {e}" for e in errors)
    )
