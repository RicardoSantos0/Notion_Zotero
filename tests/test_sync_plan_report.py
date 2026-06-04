from __future__ import annotations

import json


def _plan() -> dict:
    return {
        "version": 1,
        "generated_at": "2026-06-02T00:00:00Z",
        "inputs": {
            "notion_dir": "data/pulled/notion/learning_analytics_review",
            "zotero_dir": "data/pulled/zotero",
        },
        "summary": {
            "notion_records": 2,
            "zotero_records": 2,
            "matched": 1,
            "operations": 1,
            "only_zotero": 1,
            "only_notion": 1,
            "ambiguous": 1,
            "review_actions": 1,
        },
        "matches": [
            {
                "match_id": "match-0001",
                "match_key": {"type": "doi", "value": "10.1000/example"},
                "match_confidence": "strong",
                "notion": {"title": "Old Paper"},
                "zotero": {"title": "New Paper"},
                "bibliographic_diffs": [{"field": "title"}],
            }
        ],
        "operations": [
            {
                "operation": "update_notion_reference_field",
                "operation_id": "match-0001-title",
                "target": "notion",
                "source": "zotero",
                "field": "title",
                "notion_reference_id": "page-1",
                "old_value": "Old Paper",
                "new_value": "New Paper",
                "reason": "zotero_owned_field",
            }
        ],
        "ambiguous": [
            {
                "reason": "multiple_candidates",
                "zotero": {"title": "Ambiguous Zotero"},
                "candidates": [
                    {"notion": {"title": "Candidate A"}},
                    {"notion": {"title": "Candidate B"}},
                ],
            }
        ],
        "review_actions": [
            {
                "operation": "create_notion_page_from_zotero_record",
                "status": "needs_review",
                "zotero_key": "ZOT1",
                "title": "Only Zotero",
                "reason": "zotero_record_missing_from_notion",
            }
        ],
        "only_notion": [
            {"reference_id": "N1", "title": "Only Notion", "year": 2024, "doi": None}
        ],
    }


def test_render_sync_plan_markdown_contains_review_sections():
    from notion_zotero.services.sync_plan_report import render_sync_plan_markdown

    markdown = render_sync_plan_markdown(_plan())

    assert "# Sync Plan Review" in markdown
    assert "## Executable Operations" in markdown
    assert "match-0001-title" in markdown
    assert "## Ambiguous Matches" in markdown
    assert "Only Zotero" in markdown
    assert "Only Notion" in markdown


def test_write_sync_plan_report_from_file(tmp_path):
    from notion_zotero.services.sync_plan_report import write_sync_plan_report_from_file

    plan_path = tmp_path / "sync_plan.json"
    report_path = tmp_path / "sync_plan_review.md"
    plan_path.write_text(json.dumps(_plan()), encoding="utf-8")

    written = write_sync_plan_report_from_file(plan_path, report_path)

    assert written == report_path
    assert "Sync Plan Review" in report_path.read_text(encoding="utf-8")
