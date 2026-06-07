"""Exercise the LA-review figure builders, renderers, and audit gate.

These drive the data builders and matplotlib renderers end-to-end against the
canonical bundles (into a temp dir) so they are covered as active regression
guards — complementing the file-existence checks in test_la_review_figure_data.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "data" / "pulled" / "notion" / "learning_analytics_review"


@pytest.mark.skipif(not CANONICAL.exists(), reason="canonical data not present")
def test_build_and_render_all_figures(tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("matplotlib")
    from notion_zotero.analysis import la_review_figure_data as fd

    data_dir = tmp_path / "figure_data"
    fig_dir = tmp_path / "figures"

    data = fd.build_all_figure_data(CANONICAL, data_dir)
    assert {
        "prisma_flow",
        "representation_usage_over_time",
        "representation_by_task_over_time",
        "data_source_task_heatmap",
        "actionability_funnel",
        "model_family_by_task_year",
    } <= set(data)

    for name in (
        "prisma_flow.csv",
        "representation_usage_over_time.csv",
        "representation_by_task_over_time.csv",
        "data_source_task_heatmap.csv",
        "actionability_funnel.csv",
        "model_family_by_task_year.csv",
    ):
        assert (data_dir / name).exists() and (data_dir / name).stat().st_size > 0

    # PRISMA: identified >= included > 0
    prisma = data["prisma_flow"].set_index("Stage")["Count"]
    assert prisma["Records identified"] >= prisma["Studies included"] > 0

    # model_family schema
    mfam = data["model_family_by_task_year"]
    assert set(mfam.columns) == {"year", "task", "model_family", "paper_count"}
    assert (mfam["paper_count"] >= 0).all()

    pngs = fd.render_all_figures(data_dir, fig_dir)
    assert len(pngs) >= 7
    for i in range(1, 7):
        assert (fig_dir / f"figure_{i}.png").exists()
        assert (fig_dir / f"figure_{i}_caption.md").stat().st_size > 0
    assert (fig_dir / "figure_7_model_family.png").exists()

    metrics = fd.build_audit_dashboard(CANONICAL, fig_dir)
    assert set(metrics) == {
        "unmatched_terms_count",
        "low_confidence_rows_count",
        "override_count",
    }
    assert all(isinstance(v, int) and v >= 0 for v in metrics.values())
    assert (fig_dir / "figure_8_audit_dashboard.png").exists()


def test_audit_gate_clean_dataframe_returns_none():
    pd = pytest.importorskip("pandas")
    from notion_zotero.analysis.predictive_problem_table import run_audit_gate

    df = pd.DataFrame(
        [
            {
                "contribution_id": "c1",
                "raw_evidence": "course dropout predicted mid-term",
                "outcome_scope": "course_or_module",
                "target_construct": "dropout_or_withdrawal",
            }
        ]
    )
    assert run_audit_gate(df) is None
