"""M1 / T1.1 — test-first contract for the MVP reference-health report (built in M2).

These tests pin the report's *shape* (AC-002 fields) and renderers. They are
expected to fail with ModuleNotFoundError until `notion_zotero.analysis.mvp_health`
is implemented — i.e. they fail for *missing implementation*, not setup.
"""
from __future__ import annotations


def _bundles():
    # one complete record, one with missing DOI / year / journal / zotero key
    return [
        {"title": "A", "authors": ["X"], "year": 2020, "journal": "J",
         "doi": "10.1/a", "zotero_key": "K1"},
        {"title": "B", "authors": [], "year": None, "journal": None,
         "doi": None, "zotero_key": None},
    ]


def test_health_report_covers_ac002_fields():
    from notion_zotero.analysis import mvp_health

    report = mvp_health.build_health_report(bundles=_bundles())

    # metadata completeness must cover every AC-002 field
    mc = report["metadata_completeness"]
    for field in ("doi", "title", "authors", "year", "journal", "zotero_key"):
        assert field in mc, f"completeness missing field: {field}"

    # plus the triage sections AC-002 requires
    for key in ("duplicate_candidates", "ambiguous_matches",
                "source_only_records", "stale_snapshot_age_days"):
        assert key in report, f"report missing section: {key}"


def test_health_report_renders_json_and_markdown():
    from notion_zotero.analysis import mvp_health

    report = mvp_health.build_health_report(bundles=_bundles())
    assert isinstance(mvp_health.render_markdown(report), str)
    assert isinstance(mvp_health.render_json(report), str)


def test_health_report_links_review_artifact_and_unresolved(tmp_path):
    """M3/T3.2: health report references the review artifact + major unresolved actions."""
    from notion_zotero.analysis import mvp_health

    plan = {
        "version": 1,
        "operations": [],
        "ambiguous": [{"reason": "multiple_candidates", "zotero": {"title": "Z"}}],
        "review_actions": [
            {"operation": "create_notion_page_from_zotero_record",
             "status": "needs_review", "title": "Needs", "zotero_key": "Z9"},
        ],
    }
    review_path = tmp_path / "sync_plan_review.md"
    review_path.write_text("# review", encoding="utf-8")

    report = mvp_health.build_health_report(
        [], sync_plan=plan, review_report_path=str(review_path),
    )

    assert report["review_report"] == str(review_path)
    unresolved = report["unresolved_actions"]
    assert unresolved["ambiguous"] == 1
    assert unresolved["creates_needing_review"] == 1

    md = mvp_health.render_markdown(report)
    assert "sync_plan_review.md" in md
