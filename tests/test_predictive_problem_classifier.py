"""Test stubs for the 8+2-dimension predictive-problem classifier.

Test-first milestone M1 / task T1.3.
All tests xfail (strict=False) until implementation tasks T3.3 complete.

Spec IDs covered:
  - test-R-003-001  (pred_contribution_rows.csv schema)
  - test-R-004-001  (dropout-from-MOOC golden-input classification)
  - test-R-004-002  (ambiguous term 'Course Grade or Completion' flagged as CONFLICT)
  - test-R-014-001  (LLM overlay: llm_primary tag in contribution rows)

Disambiguation cases from nlp_taxonomy_specialist.DRAFT.md:
  - dropout from a MOOC  -> outcome_scope=course_or_module,
                            target_construct=dropout_or_withdrawal,
                            context_type=MOOC
  - GPA at graduation    -> outcome_scope=program_or_degree,
                            target_construct=gpa_or_cumulative_performance
  - next question correctness -> outcome_scope=interaction_or_item,
                                  target_construct=next_interaction_correctness
  - Course Grade or Completion -> CONFLICT flagged (not collapsed)

Classifier contract (Guardrail 1, d-020):
  Every classify_contribution() call returns per-dimension dicts with:
    {label: str, confidence: "high"|"medium"|"low", evidence: str}
  Conflicts carry an additional conflict_flag: True field.
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# test-R-003-001
# ---------------------------------------------------------------------------


def test_contribution_rows_schema():
    """pred_contribution_rows.csv must have required columns and >=1 row per PRED paper.

    Spec: test-R-003-001
    Requirement: R-003
    Evidence command: pytest tests/test_predictive_problem_classifier.py::test_contribution_rows_schema
    """
    pd = pytest.importorskip("pandas")
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    csv_path = (
        repo_root
        / "data"
        / "analysis_outputs"
        / "la_review"
        / "audits"
        / "pred_contribution_rows.csv"
    )
    assert csv_path.exists(), (
        f"pred_contribution_rows.csv not found at {csv_path}; "
        "run the contribution-row builder (T3.2) first"
    )

    df = pd.read_csv(csv_path)

    # Required columns
    required_columns = ["contribution_id", "paper_id", "raw_evidence"]
    for col in required_columns:
        assert col in df.columns, (
            f"Column {col!r} missing from pred_contribution_rows.csv"
        )

    # contribution_id must be stable (non-null, non-empty, unique)
    assert df["contribution_id"].notna().all(), "contribution_id has null values"
    assert df["contribution_id"].astype(str).str.strip().ne("").all(), (
        "contribution_id has empty string values"
    )

    # raw_evidence must be preserved
    assert df["raw_evidence"].notna().all(), "raw_evidence column has null values"

    # Row count must cover at least one row per PRED paper
    # Minimum from canonical dataset (determined at audit time — use 50 as lower bound)
    MIN_PRED_PAPERS = 50
    unique_papers = df["paper_id"].nunique()
    assert unique_papers >= MIN_PRED_PAPERS, (
        f"Only {unique_papers} unique papers in contribution rows; "
        f"expected >= {MIN_PRED_PAPERS} PRED papers from canonical dataset"
    )


# ---------------------------------------------------------------------------
# test-R-004-001
# ---------------------------------------------------------------------------


def test_dropout_mooc_classification():
    """Golden-input test: 'dropout from a MOOC predicted at week 3' must yield
    correct labels across key dimensions.

    Spec: test-R-004-001
    Requirement: R-004
    Evidence command: pytest tests/test_predictive_problem_classifier.py::test_dropout_mooc_classification
    """
    # Import the classifier — expected to live in analysis module after T3.3
    try:
        from notion_zotero.analysis.pred_horizon_summary import classify_contribution  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.education_learning_analytics import classify_contribution  # type: ignore[import]

    input_row = {
        "raw_evidence": "dropout from a MOOC predicted at week 3",
        "Student Performance Definition": "dropout from a MOOC",
        "Moment of Prediction": "week 3",
        "Context": "MOOC",
    }

    result = classify_contribution(input_row)

    # Each dimension must return label + confidence + evidence
    for dim in ("outcome_scope", "target_construct", "context_type", "prediction_timing"):
        assert dim in result, f"Dimension {dim!r} missing from classifier output"
        assert "label" in result[dim], f"result[{dim!r}] missing 'label' key"
        assert "confidence" in result[dim], f"result[{dim!r}] missing 'confidence' key"
        assert "evidence" in result[dim], f"result[{dim!r}] missing 'evidence' key"
        assert result[dim]["confidence"] in ("high", "medium", "low"), (
            f"result[{dim!r}]['confidence'] = {result[dim]['confidence']!r}; "
            "must be one of 'high', 'medium', 'low'"
        )

    # Verify the correct labels for the golden disambiguation case
    assert result["outcome_scope"]["label"] == "course_or_module", (
        f"outcome_scope={result['outcome_scope']['label']!r}; "
        "expected 'course_or_module' for MOOC dropout"
    )
    assert result["target_construct"]["label"] == "dropout_or_withdrawal", (
        f"target_construct={result['target_construct']['label']!r}; "
        "expected 'dropout_or_withdrawal'"
    )
    assert result["context_type"]["label"] == "MOOC", (
        f"context_type={result['context_type']['label']!r}; expected 'MOOC'"
    )
    # prediction_timing anchored to feature-extraction cutoff (d-011), week 3 -> early_course
    assert result["prediction_timing"]["label"] == "early_course", (
        f"prediction_timing={result['prediction_timing']['label']!r}; "
        "expected 'early_course' for week-3 feature cutoff"
    )


def test_additional_golden_input_classifications():
    """Additional disambiguation cases from nlp_taxonomy_specialist spec.

    Spec: test-R-004-001 (additional cases)
    Requirement: R-004
    """
    try:
        from notion_zotero.analysis.pred_horizon_summary import classify_contribution  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.education_learning_analytics import classify_contribution  # type: ignore[import]

    # Case 2: GPA at graduation
    gpa_row = {
        "raw_evidence": "GPA at graduation",
        "Student Performance Definition": "GPA",
        "Moment of Prediction": "end of program",
    }
    gpa_result = classify_contribution(gpa_row)
    assert gpa_result["outcome_scope"]["label"] == "program_or_degree", (
        f"GPA at graduation: outcome_scope={gpa_result['outcome_scope']['label']!r}; "
        "expected 'program_or_degree'"
    )
    assert gpa_result["target_construct"]["label"] == "gpa_or_cumulative_performance", (
        f"GPA at graduation: target_construct={gpa_result['target_construct']['label']!r}; "
        "expected 'gpa_or_cumulative_performance'"
    )

    # Case 3: next question correctness
    kt_row = {
        "raw_evidence": "next question correctness in ITS",
        "Student Performance Definition": "next question correctness",
    }
    kt_result = classify_contribution(kt_row)
    assert kt_result["outcome_scope"]["label"] == "interaction_or_item", (
        f"next question correctness: outcome_scope={kt_result['outcome_scope']['label']!r}; "
        "expected 'interaction_or_item'"
    )
    assert kt_result["target_construct"]["label"] == "next_interaction_correctness", (
        f"next question correctness: target_construct={kt_result['target_construct']['label']!r}; "
        "expected 'next_interaction_correctness'"
    )


# ---------------------------------------------------------------------------
# test-R-004-002
# ---------------------------------------------------------------------------


def test_ambiguous_term_flagged_in_audit():
    """'Course Grade or Completion' must be flagged as a CONFLICT (not silently resolved)
    and routed to taxonomy_audit.csv with confidence='low'.

    Spec: test-R-004-002
    Requirement: R-004
    Evidence command: pytest tests/test_predictive_problem_classifier.py::test_ambiguous_term_flagged_in_audit
    """
    try:
        from notion_zotero.analysis.pred_horizon_summary import classify_contribution  # type: ignore[import]
    except ImportError:
        from notion_zotero.analysis.education_learning_analytics import classify_contribution  # type: ignore[import]

    ambiguous_row = {
        "raw_evidence": "Course Grade or Completion",
        "Student Performance Definition": "Course Grade or Completion",
        "Target": "Course Grade or Completion",
    }

    result = classify_contribution(ambiguous_row)

    # The target_construct dimension must return low confidence
    assert "target_construct" in result, "target_construct missing from result"
    assert result["target_construct"]["confidence"] == "low", (
        f"Expected confidence='low' for ambiguous 'Course Grade or Completion'; "
        f"got {result['target_construct']['confidence']!r}"
    )

    # A conflict_flag must be present and True (not silently collapsed)
    assert result["target_construct"].get("conflict_flag") is True, (
        "conflict_flag must be True for 'Course Grade or Completion' — "
        "two target_construct values cannot be silently collapsed (Guardrail 2, d-020)"
    )

    # The row must be routed to taxonomy_audit.csv
    # Verify by checking the audit routing function or the CSV output
    pd = pytest.importorskip("pandas")
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    audit_csv = (
        repo_root
        / "data"
        / "analysis_outputs"
        / "la_review"
        / "audits"
        / "taxonomy_audit.csv"
    )
    assert audit_csv.exists(), (
        f"taxonomy_audit.csv not found at {audit_csv}; "
        "run the classifier pipeline to generate the audit file"
    )
    audit_df = pd.read_csv(audit_csv)
    # At least one row should mention the ambiguous term
    mask = audit_df.apply(
        lambda row: row.astype(str).str.contains("Course Grade or Completion", case=False).any(),
        axis=1,
    )
    assert mask.any(), (
        "'Course Grade or Completion' not found in taxonomy_audit.csv; "
        "low-confidence / conflict rows must be routed to audit (Guardrail 3, d-020)"
    )


# ---------------------------------------------------------------------------
# test-R-014-001
# ---------------------------------------------------------------------------


def test_llm_overlay_tag():
    """Papers using LLMs as primary method must be tagged llm_primary=True
    in their contribution row.

    Spec: test-R-014-001
    Requirement: R-014
    Evidence command: pytest tests/test_predictive_problem_classifier.py::test_llm_overlay_tag
    """
    pd = pytest.importorskip("pandas")
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    csv_path = (
        repo_root
        / "data"
        / "analysis_outputs"
        / "la_review"
        / "audits"
        / "pred_contribution_rows.csv"
    )
    assert csv_path.exists(), (
        f"pred_contribution_rows.csv not found; run T3.2 contribution-row builder first"
    )

    df = pd.read_csv(csv_path)

    # llm_primary column must exist (added by T6.5 LLM overlay tagger)
    assert "llm_primary" in df.columns, (
        "llm_primary column missing from pred_contribution_rows.csv; "
        "run the LLM overlay tagger (T6.5) to add it"
    )

    # At least one paper should be tagged True (the reviewed corpus includes LLM papers)
    llm_count = df["llm_primary"].sum()
    assert llm_count >= 1, (
        f"llm_primary is all False/NaN; expected at least 1 LLM paper in the 285-paper corpus"
    )

    # All values must be boolean (True/False/NaN), not arbitrary strings
    valid_values = {True, False, 1, 0, 1.0, 0.0}
    non_null_values = df["llm_primary"].dropna()
    unexpected = [v for v in non_null_values if v not in valid_values]
    assert not unexpected, (
        f"llm_primary column has unexpected non-boolean values: {unexpected[:5]}"
    )
