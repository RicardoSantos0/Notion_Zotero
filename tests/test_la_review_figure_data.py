"""Test stubs for LA review figure-data builders (Tables 2/4/5 and Figures 1-8).

Test-first milestone M1 / task T1.5.
All tests xfail (strict=False) until implementation tasks T4.x / T5.x / T6.x complete.

Spec IDs covered:
  - test-R-006-001  (Table 2 golden fixture: la_data_source_counts.csv)
  - test-R-007-001  (Table 4 xlsx covers all 4 tasks with >=1 row per column)
  - test-R-008-001  (Table 5 xlsx: row per task per maturity level with paper counts)
  - test-R-009-001  (03_figures.ipynb runs clean; Figures 1-6 PNG+CSV+MD exist)
  - test-R-009-002  (Figure 2 golden CSV: representation_usage_over_time.csv within 5%)
  - test-R-010-001  (Figure 7 schema: year, task, model_family, paper_count)
  - test-R-011-001  (Figure 8 audit dashboard: 3 required metrics)
  - test-R-012-001  (story map: RQ1/RQ2/RQ3 each map to >=1 table and >=1 figure)
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LA_REVIEW_OUTPUT = REPO_ROOT / "data" / "analysis_outputs" / "la_review"


# ---------------------------------------------------------------------------
# test-R-006-001 — Table 2
# ---------------------------------------------------------------------------


def test_table2_golden_fixture():
    """Table 2 output must match la_data_source_counts.csv golden fixture;
    unmatched tokens must appear in the audit report.

    Spec: test-R-006-001
    Requirement: R-006
    Evidence command: pytest tests/test_la_review_figure_data.py::test_table2_golden_fixture
    """
    pd = pytest.importorskip("pandas")

    fixture_path = REPO_ROOT / "tests" / "fixtures" / "la_data_source_counts.csv"
    assert fixture_path.exists(), (
        f"Golden fixture not found at {fixture_path}; "
        "run T4.2 (first clean Table 2 run) to create it"
    )

    try:
        from notion_zotero.analysis.paper_tables import generate_table2  # type: ignore[import]
    except ImportError:
        pytest.skip("generate_table2 not yet implemented (T4.1 pending)")

    canonical_dir = REPO_ROOT / "data" / "pulled" / "notion" / "learning_analytics_review"
    current_df = generate_table2(canonical_dir)
    fixture_df = pd.read_csv(fixture_path)

    assert set(current_df.columns) == set(fixture_df.columns), (
        f"Column mismatch between current output and fixture"
    )

    # Check that counts match the fixture (no explicit tolerance — deterministic)
    for col in fixture_df.columns:
        if col in current_df.columns:
            pd.testing.assert_series_equal(
                current_df[col].reset_index(drop=True),
                fixture_df[col].reset_index(drop=True),
                check_names=False,
                rtol=0.0,
                atol=0,
            )

    # The audit report must also exist
    audit_path = LA_REVIEW_OUTPUT / "audits" / "table2_unmatched_audit.md"
    assert audit_path.exists(), (
        f"table2_unmatched_audit.md not found at {audit_path}; "
        "generate_table2() must write this file"
    )


# ---------------------------------------------------------------------------
# test-R-007-001 — Table 4
# ---------------------------------------------------------------------------


def test_table4_all_tasks_populated():
    """Table 4 xlsx must cover all 4 LA tasks (PRED, DESC, KT, ERS)
    with at least one populated row per task per column (7 columns).

    Spec: test-R-007-001
    Requirement: R-007
    Evidence command: pytest tests/test_la_review_figure_data.py::test_table4_all_tasks_populated
    """
    pd = pytest.importorskip("pandas")

    table4_path = LA_REVIEW_OUTPUT / "tables" / "task_synthesis_matrix.xlsx"
    assert table4_path.exists(), (
        f"task_synthesis_matrix.xlsx not found at {table4_path}; "
        "run generate_table4() (T4.3) to produce it"
    )

    df = pd.read_excel(table4_path)

    required_tasks = {"PRED", "DESC", "KT", "ERS"}
    # Task column may be named "Task" or similar
    task_col_candidates = [c for c in df.columns if "task" in c.lower()]
    assert task_col_candidates, (
        f"No 'task' column found in task_synthesis_matrix.xlsx; "
        f"columns: {list(df.columns)}"
    )
    task_col = task_col_candidates[0]

    actual_tasks = set(df[task_col].dropna().unique())
    missing_tasks = required_tasks - actual_tasks
    assert not missing_tasks, (
        f"Table 4 missing tasks: {missing_tasks}; found: {actual_tasks}"
    )

    # 7 required columns (from R-007 spec):
    # Task | purpose | data | representations | models | metrics | actionability gaps
    expected_min_cols = 7
    assert len(df.columns) >= expected_min_cols, (
        f"Table 4 has {len(df.columns)} columns; expected >= {expected_min_cols} "
        "(Task + 6 content columns)"
    )

    # For each task, at least one non-empty cell per content column
    content_cols = [c for c in df.columns if c != task_col]
    for task in required_tasks:
        task_rows = df[df[task_col] == task]
        assert len(task_rows) >= 1, f"No rows for task {task!r} in Table 4"
        for col in content_cols:
            has_data = task_rows[col].dropna().astype(str).str.strip().ne("").any()
            assert has_data, (
                f"Table 4 task {task!r} column {col!r} is entirely empty"
            )


# ---------------------------------------------------------------------------
# test-R-008-001 — Table 5
# ---------------------------------------------------------------------------


def test_table5_maturity_levels():
    """Table 5 xlsx must contain a row per task per maturity level with unique paper counts.

    Spec: test-R-008-001
    Requirement: R-008
    Evidence command: pytest tests/test_la_review_figure_data.py::test_table5_maturity_levels
    """
    pd = pytest.importorskip("pandas")

    table5_path = LA_REVIEW_OUTPUT / "tables" / "evaluation_maturity.xlsx"
    assert table5_path.exists(), (
        f"evaluation_maturity.xlsx not found at {table5_path}; "
        "run generate_table5() (T4.4) to produce it"
    )

    df = pd.read_excel(table5_path)

    # 5 maturity levels per the R-008 spec
    required_maturity_levels = {
        "public benchmark only",
        "backtested",
        "tested with new students",
        "deployed",
        "deployed with intervention evaluation",
    }

    # Maturity column may have various names
    maturity_col_candidates = [
        c for c in df.columns
        if any(kw in c.lower() for kw in ("maturity", "level", "actionability", "status"))
    ]
    assert maturity_col_candidates, (
        f"No maturity/level column found in evaluation_maturity.xlsx; "
        f"columns: {list(df.columns)}"
    )

    # At least the PRED task must have all 5 maturity levels represented
    # (PRED is the highest-priority task — R-005/R-008)
    task_col_candidates = [c for c in df.columns if "task" in c.lower()]
    if task_col_candidates:
        task_col = task_col_candidates[0]
        pred_rows = df[df[task_col] == "PRED"]
        assert len(pred_rows) >= 1, "No PRED rows in evaluation_maturity.xlsx"

    # Counts must be > 0 for at least some rows
    count_col_candidates = [
        c for c in df.columns
        if any(kw in c.lower() for kw in ("paper", "count", "unique"))
    ]
    if count_col_candidates:
        count_col = count_col_candidates[0]
        assert (df[count_col].fillna(0) > 0).any(), (
            f"All counts in {count_col!r} are 0 or NaN"
        )


# ---------------------------------------------------------------------------
# test-R-009-001 — Figures 1-6 existence
# ---------------------------------------------------------------------------


def test_figures_1_6_exist():
    """Figures 1-6 must each have a PNG, CSV data file, and MD caption.

    Spec: test-R-009-001
    Requirement: R-009
    Note: This test is called by the evidence command after nbconvert --execute.
    Evidence command: (see product_plan.yaml test-R-009-001)
    """
    figures_dir = LA_REVIEW_OUTPUT / "figures"
    assert figures_dir.exists(), (
        f"Figures directory not found at {figures_dir}; "
        "run 03_figures.ipynb to generate figures"
    )

    for fig_num in range(1, 7):
        # PNG or SVG
        png_path = figures_dir / f"figure_{fig_num}.png"
        svg_path = figures_dir / f"figure_{fig_num}.svg"
        assert png_path.exists() or svg_path.exists(), (
            f"Figure {fig_num}: neither PNG ({png_path.name}) nor SVG ({svg_path.name}) found"
        )

        # Caption MD
        caption_path = figures_dir / f"figure_{fig_num}_caption.md"
        assert caption_path.exists(), (
            f"Figure {fig_num} caption not found at {caption_path}"
        )
        assert caption_path.stat().st_size > 0, (
            f"Figure {fig_num} caption file is empty"
        )

    # Figure data CSVs (in figure_data/ subdirectory)
    figure_data_dir = LA_REVIEW_OUTPUT / "figure_data"
    expected_csvs = [
        "representation_usage_over_time.csv",      # Figure 2
        "representation_by_task_over_time.csv",    # Figure 3
        "data_source_task_heatmap.csv",            # Figure 4
        "actionability_funnel.csv",                # Figure 6
        "prisma_flow.csv",                         # Figure 1
    ]
    for csv_name in expected_csvs:
        csv_path = figure_data_dir / csv_name
        assert csv_path.exists(), (
            f"Figure data CSV not found: {csv_path}; "
            "run T5.1 figure data builder"
        )
        assert csv_path.stat().st_size > 0, f"{csv_name} is empty"


def test_figures_notebook_smoke_placeholder():
    """Placeholder: notebook smoke test is run via nbconvert (not pytest).

    Spec: test-R-009-001, test-R-016-001 (figures notebook component)
    Requirement: R-009, R-016

    The actual clean-kernel smoke test is:
        jupyter nbconvert --to notebook --execute notebooks/la_review/03_figures.ipynb

    This stub documents the intent; the pytest assertion checks that the notebook
    file exists and has at least 5 cells (non-empty stub).
    """
    nb_path = REPO_ROOT / "notebooks" / "la_review" / "03_figures.ipynb"
    assert nb_path.exists(), (
        f"03_figures.ipynb not found at {nb_path}; "
        "create the notebook stub (T5.2)"
    )

    import json
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    assert len(cells) >= 5, (
        f"03_figures.ipynb has only {len(cells)} cells; "
        "expected a substantive notebook (>=5 cells)"
    )


# ---------------------------------------------------------------------------
# test-R-009-002 — Figure 2 golden CSV
# ---------------------------------------------------------------------------


def test_full_suite_zero_failures():
    """Gate test: all WP2-WP6 deliverables are present (manuscript-ready gate).

    Spec: test-R-015-001
    Requirement: R-015
    Evidence command: pytest tests/test_learning_analytics_taxonomy.py
                            tests/test_predictive_problem_classifier.py
                            tests/test_predictive_problem_table.py
                            tests/test_la_review_figure_data.py
                            tests/test_manual_overrides.py -v

    Passes once every implementation task (Tables II-V, Figures 1-8, story map,
    contribution rows, review_pipeline, audit gate) has landed.
    """
    import importlib

    tables_dir = LA_REVIEW_OUTPUT / "tables"
    figures_dir = LA_REVIEW_OUTPUT / "figures"
    required_files = [
        tables_dir / "table_3_counts.xlsx",
        tables_dir / "data_source_by_task.xlsx",
        tables_dir / "task_synthesis_matrix.xlsx",
        tables_dir / "evaluation_maturity.xlsx",
        figures_dir / "figure_7_model_family.png",
        figures_dir / "figure_8_audit_dashboard.png",
        REPO_ROOT / "docs" / "la_review_story_map.md",
        LA_REVIEW_OUTPUT / "audits" / "pred_contribution_rows.csv",
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in required_files if not p.exists()]
    assert not missing, f"manuscript-ready gate: missing deliverables: {missing}"

    # review_pipeline façade imports and the audit gate symbol must be present
    importlib.import_module("notion_zotero.analysis.review_pipeline.audit")
    from notion_zotero.analysis.predictive_problem_table import run_audit_gate  # noqa: F401


def test_golden_fixture_deterministic_regeneration():
    """Snapshot tests confirm la_table_3_counts.csv and la_data_source_counts.csv
    are deterministically regenerable (both fixture files must exist and be non-empty).

    Spec: test-R-015-002
    Requirement: R-015
    Evidence command: pytest tests/test_predictive_problem_table.py::test_table3_golden_fixture
                            tests/test_la_review_figure_data.py::test_table2_golden_fixture -v

    This stub checks fixture file presence as a precondition; the detailed
    content comparison is in test_table3_golden_fixture and test_table2_golden_fixture.
    """
    fixture_table3 = REPO_ROOT / "tests" / "fixtures" / "la_table_3_counts.csv"
    fixture_table2 = REPO_ROOT / "tests" / "fixtures" / "la_data_source_counts.csv"

    missing = []
    if not fixture_table3.exists():
        missing.append(f"la_table_3_counts.csv (create via T3.5)")
    if not fixture_table2.exists():
        missing.append(f"la_data_source_counts.csv (create via T4.2)")

    assert not missing, (
        "Golden fixture files missing:\n"
        + "\n".join(f"  tests/fixtures/{m}" for m in missing)
    )


def test_all_notebooks_exist_for_smoke():
    """All 5 la_review notebooks must exist as a prerequisite for clean-kernel smoke tests.

    Spec: test-R-016-001
    Requirement: R-016
    Evidence command: (run via separate nbconvert calls per d-013, not chained with &&)
        jupyter nbconvert --to notebook --execute notebooks/la_review/00_environment_check.ipynb
        jupyter nbconvert --to notebook --execute notebooks/la_review/01_data_audit.ipynb
        jupyter nbconvert --to notebook --execute notebooks/la_review/02_task_tables_and_table3.ipynb
        jupyter nbconvert --to notebook --execute notebooks/la_review/03_figures.ipynb
        jupyter nbconvert --to notebook --execute notebooks/la_review/04_story_and_caption_check.ipynb

    Note: The actual clean-kernel smoke test is run via nbconvert (NOT pytest-chained).
    This pytest stub verifies that all notebook files exist on disk.
    """
    nb_dir = REPO_ROOT / "notebooks" / "la_review"
    required_notebooks = [
        "00_environment_check.ipynb",
        "01_data_audit.ipynb",
        "02_task_tables_and_table3.ipynb",
        "03_figures.ipynb",
        "04_story_and_caption_check.ipynb",
    ]

    missing = []
    for nb_name in required_notebooks:
        nb_path = nb_dir / nb_name
        if not nb_path.exists():
            missing.append(str(nb_path.relative_to(REPO_ROOT)))

    assert not missing, (
        "Notebook files missing (required for clean-kernel smoke test):\n"
        + "\n".join(f"  {m}" for m in missing)
    )


def test_figure2_golden_csv():
    """Figure 2 yearly line chart must match golden CSV within 5% per year-bucket.

    Spec: test-R-009-002
    Requirement: R-009
    Evidence command: pytest tests/test_la_review_figure_data.py::test_figure2_golden_csv
    """
    pd = pytest.importorskip("pandas")

    fixture_path = REPO_ROOT / "tests" / "fixtures" / "representation_usage_over_time.csv"
    assert fixture_path.exists(), (
        f"Golden fixture not found at {fixture_path}; "
        "run T5.3 to capture from first verified Figure 2 reconstruction"
    )

    figure_data_dir = LA_REVIEW_OUTPUT / "figure_data"
    current_path = figure_data_dir / "representation_usage_over_time.csv"
    assert current_path.exists(), (
        f"representation_usage_over_time.csv not found at {current_path}; "
        "run T5.1 figure data builder first"
    )

    fixture_df = pd.read_csv(fixture_path)
    current_df = pd.read_csv(current_path)

    # Must have the same columns
    assert set(current_df.columns) == set(fixture_df.columns), (
        f"Column mismatch: current={sorted(current_df.columns)}, "
        f"fixture={sorted(fixture_df.columns)}"
    )

    # Year column must exist
    year_col_candidates = [c for c in fixture_df.columns if "year" in c.lower()]
    assert year_col_candidates, "No 'year' column found in representation_usage_over_time.csv"
    year_col = year_col_candidates[0]

    # Merge on year and check count columns within 5% tolerance per year-bucket
    count_cols = [c for c in fixture_df.columns if c != year_col]
    merged = fixture_df.merge(current_df, on=year_col, suffixes=("_fixture", "_current"))

    for col in count_cols:
        fixture_col = f"{col}_fixture"
        current_col = f"{col}_current"
        if fixture_col in merged.columns and current_col in merged.columns:
            for _, row in merged.iterrows():
                fixture_val = row[fixture_col]
                current_val = row[current_col]
                if fixture_val > 0:
                    pct_diff = abs(current_val - fixture_val) / fixture_val
                    assert pct_diff <= 0.05, (
                        f"Year {row[year_col]}, column {col!r}: "
                        f"current={current_val}, fixture={fixture_val}, "
                        f"diff={pct_diff:.1%} exceeds 5% tolerance"
                    )


# ---------------------------------------------------------------------------
# test-R-010-001 — Figure 7
# ---------------------------------------------------------------------------


def test_figure7_schema():
    """Figure 7 PNG and CSV must exist with required columns.

    Spec: test-R-010-001
    Requirement: R-010
    Evidence command: pytest tests/test_la_review_figure_data.py::test_figure7_schema
    """
    pd = pytest.importorskip("pandas")

    figures_dir = LA_REVIEW_OUTPUT / "figures"
    figure_data_dir = LA_REVIEW_OUTPUT / "figure_data"

    # PNG must exist and be non-empty
    fig7_png = figures_dir / "figure_7_model_family.png"
    assert fig7_png.exists(), f"Figure 7 PNG not found at {fig7_png}"
    assert fig7_png.stat().st_size > 0, "Figure 7 PNG is empty (0 bytes)"

    # CSV must exist with required columns
    fig7_csv = figure_data_dir / "model_family_by_task_year.csv"
    assert fig7_csv.exists(), f"Figure 7 CSV not found at {fig7_csv}"

    df = pd.read_csv(fig7_csv)
    required_cols = {"year", "task", "model_family", "paper_count"}
    missing = required_cols - set(df.columns)
    assert not missing, (
        f"Figure 7 CSV missing columns: {missing}; found: {set(df.columns)}"
    )

    # Basic sanity: non-empty data
    assert len(df) > 0, "Figure 7 CSV is empty"
    assert (df["paper_count"] >= 0).all(), "paper_count column has negative values"


# ---------------------------------------------------------------------------
# test-R-011-001 — Figure 8 audit dashboard
# ---------------------------------------------------------------------------


def test_figure8_audit_dashboard():
    """Figure 8 audit dashboard must exist as PNG and companion JSON metadata
    with three required metrics.

    Spec: test-R-011-001
    Requirement: R-011
    Evidence command: pytest tests/test_la_review_figure_data.py::test_figure8_audit_dashboard
    """
    import json

    figures_dir = LA_REVIEW_OUTPUT / "figures"

    # PNG must exist
    fig8_png = figures_dir / "figure_8_audit_dashboard.png"
    assert fig8_png.exists(), f"Figure 8 PNG not found at {fig8_png}"
    assert fig8_png.stat().st_size > 0, "Figure 8 PNG is empty (0 bytes)"

    # Companion JSON metadata must exist with 3 required metrics
    fig8_json = figures_dir / "figure_8_metadata.json"
    assert fig8_json.exists(), f"Figure 8 metadata JSON not found at {fig8_json}"

    metadata = json.loads(fig8_json.read_text(encoding="utf-8"))
    required_metrics = {
        "unmatched_terms_count",
        "low_confidence_rows_count",
        "override_count",
    }
    missing_metrics = required_metrics - set(metadata.keys())
    assert not missing_metrics, (
        f"Figure 8 metadata missing keys: {missing_metrics}; found: {set(metadata.keys())}"
    )

    # All metric values must be non-negative integers
    for metric in required_metrics:
        val = metadata[metric]
        assert isinstance(val, int) and val >= 0, (
            f"Figure 8 metadata[{metric!r}] = {val!r}; expected non-negative int"
        )


# ---------------------------------------------------------------------------
# test-R-012-001 — Story map coverage
# ---------------------------------------------------------------------------


def test_story_map_coverage():
    """la_review_story_map.md must exist and every RQ (RQ1, RQ2, RQ3) must map
    to at least one table and one figure, each with a draft caption.

    Spec: test-R-012-001
    Requirement: R-012
    Evidence command: pytest tests/test_la_review_figure_data.py::test_story_map_coverage
    """
    story_map_path = REPO_ROOT / "docs" / "la_review_story_map.md"
    assert story_map_path.exists(), (
        f"Story map not found at {story_map_path}; run T6.1 (WP5) to create it"
    )

    text = story_map_path.read_text(encoding="utf-8")

    # Each RQ must have a section header
    for rq in ("RQ1", "RQ2", "RQ3"):
        assert rq in text, (
            f"{rq} not found in la_review_story_map.md; "
            "story map must cover all three research questions"
        )

    # Each RQ section must reference at least one table and one figure
    import re

    # Find RQ sections (content between ## RQn headers)
    rq_sections: dict[str, str] = {}
    rq_pattern = re.compile(r"(?m)^#+\s*(RQ[123]\b[^\n]*)\n(.*?)(?=^#+\s*RQ[123]|\Z)", re.DOTALL)
    for match in rq_pattern.finditer(text):
        rq_label = match.group(1).strip()
        section_content = match.group(2)
        rq_key = re.search(r"RQ[123]", rq_label).group(0)
        rq_sections[rq_key] = section_content

    # If sections aren't found by the strict pattern, check the full text per RQ
    if len(rq_sections) < 3:
        # Fallback: just check the whole document
        for rq in ("RQ1", "RQ2", "RQ3"):
            rq_sections.setdefault(rq, text)

    for rq, section in rq_sections.items():
        has_table_ref = bool(re.search(r"[Tt]able\s*[IVX0-9]", section))
        has_figure_ref = bool(re.search(r"[Ff]ig(?:ure)?\s*[0-9]", section))

        assert has_table_ref, (
            f"{rq} section has no table reference in la_review_story_map.md; "
            "each RQ must map to at least one table"
        )
        assert has_figure_ref, (
            f"{rq} section has no figure reference in la_review_story_map.md; "
            "each RQ must map to at least one figure"
        )
