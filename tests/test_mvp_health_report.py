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
