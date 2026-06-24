"""Create-flow hardening (M5 / AC-005).

Covers strong-key + normalized-title duplicate detection before create writes
(T5.1), recovery-grade create write-log fields (T5.2), and surfacing create
outcomes in reports (T5.3).
"""
from __future__ import annotations

import unittest.mock

import pytest


def _create_plan(status: str = "approved", *, doi: str | None = None,
                 zotero_key: str = "Z1", title: str = "New Zotero Paper") -> dict:
    reference = {
        "title": title,
        "authors": ["Ada Lovelace"],
        "year": 2026,
        "zotero_key": zotero_key,
    }
    if doi is not None:
        reference["doi"] = doi
    return {
        "version": 1,
        "operations": [],
        "review_actions": [
            {
                "operation": "create_notion_page_from_zotero_record",
                "operation_id": f"create-{zotero_key}",
                "target": "notion",
                "source": "zotero",
                "status": status,
                "zotero_reference_id": "zotero-1",
                "zotero_key": zotero_key,
                "doi": doi,
                "title": title,
                "reference": reference,
            }
        ],
    }


# --- T5.1: strong-key + normalized-title duplicate detection -----------------

def test_create_blocked_by_existing_zotero_key():
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    with pytest.raises(ValueError, match="duplicates an existing Notion"):
        apply_sync_plan(
            _create_plan(),
            dry_run=True,
            include_reviewed_creates=True,
            notion_database_id="db-1",
            existing_notion_keys={"z1"},  # casefolded zotero_key
        )


def test_create_blocked_by_existing_doi():
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    with pytest.raises(ValueError, match="duplicates an existing Notion"):
        apply_sync_plan(
            _create_plan(doi="https://doi.org/10.1/ABC"),
            dry_run=True,
            include_reviewed_creates=True,
            notion_database_id="db-1",
            existing_notion_keys={"10.1/abc"},  # normalized DOI
        )


def test_create_blocked_by_plan_internal_strong_key():
    """An approved create that shares a Zotero key with a matched Notion record."""
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    plan = _create_plan()
    plan["matches"] = [
        {
            "match_id": "match-0001",
            "match_key": {"type": "zotero_key", "value": "Z1"},
            "match_confidence": "strong",
            "notion": {"title": "Different Title", "zotero_key": "Z1"},
            "zotero": {"title": "Different Title", "zotero_key": "Z1"},
            "bibliographic_diffs": [],
        }
    ]
    with pytest.raises(ValueError, match="duplicates an existing Notion"):
        apply_sync_plan(
            plan,
            dry_run=True,
            include_reviewed_creates=True,
            notion_database_id="db-1",
        )


def test_create_blocked_by_normalized_title_variant():
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    with pytest.raises(ValueError, match="duplicates an existing Notion title"):
        apply_sync_plan(
            _create_plan(),
            dry_run=True,
            include_reviewed_creates=True,
            notion_database_id="db-1",
            existing_notion_titles={"  new   ZOTERO   paper "},
        )


def test_create_allowed_when_no_duplicate():
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    ops = apply_sync_plan(
        _create_plan(zotero_key="Z9", title="Unseen Paper"),
        dry_run=True,
        include_reviewed_creates=True,
        notion_database_id="db-1",
        existing_notion_keys={"z1"},
        existing_notion_titles={"new zotero paper"},
    )
    assert ops == ["[DRY-RUN] notion.create [db-1] 'Unseen Paper'"]


# --- T5.2: recovery-grade create write-log fields ---------------------------

def test_create_log_includes_zotero_key_and_properties(tmp_path):
    from notion_zotero.services.sync_plan_applier import apply_sync_plan
    from notion_zotero.writers.write_log import WriteLog

    mock_client = unittest.mock.MagicMock()
    mock_client.pages.create.return_value = {"id": "notion-page-new"}
    write_log = WriteLog(session_id="sess-create", log_dir=tmp_path)

    apply_sync_plan(
        _create_plan(),
        dry_run=False,
        notion_client=mock_client,
        write_log=write_log,
        include_reviewed_creates=True,
        notion_database_id="db-1",
        rate_limit_sleep=0,
    )

    entries = write_log.entries_for_session("sess-create")
    applied = entries[-1]
    assert applied["status"] == "applied"
    assert applied["entity_id"] == "notion-page-new"      # created page id
    assert applied["zotero_key"] == "Z1"                  # source zotero key
    assert isinstance(applied["properties"], dict)        # written properties
    assert applied["properties"].get("title") == "New Zotero Paper"


# --- T5.3: surface create outcomes in reports -------------------------------

def test_summarize_create_outcomes():
    from notion_zotero.services.sync_plan_applier import summarize_create_outcomes

    plan = {
        "version": 1,
        "operations": [],
        "review_actions": [
            {"operation": "create_notion_page_from_zotero_record",
             "status": "approved", "zotero_key": "Z1", "title": "Paper A"},
            {"operation": "create_notion_page_from_zotero_record",
             "status": "approved", "zotero_key": "Z2", "title": "Paper B"},
            {"operation": "create_notion_page_from_zotero_record",
             "status": "needs_review", "zotero_key": "Z3", "title": "Paper C"},
        ],
    }
    write_log_entries = [
        {"field": "__page_create__", "status": "applied",
         "entity_id": "page-A", "zotero_key": "Z1"},
        {"field": "__page_create__", "status": "failed",
         "zotero_key": "Z2", "error_message": "boom"},
        {"field": "title", "status": "applied"},  # not a create
    ]

    outcomes = summarize_create_outcomes(
        plan,
        write_log_entries=write_log_entries,
        existing_notion_titles={"paper b"},  # blocks Z2's create
    )

    assert outcomes["approved"] == 2
    assert outcomes["applied"] == 1
    assert outcomes["failed"] == 1
    assert outcomes["duplicate_blocked"] == 1


def test_health_report_includes_create_outcomes():
    from notion_zotero.analysis.mvp_health import build_health_report

    plan = {
        "version": 1,
        "operations": [],
        "review_actions": [
            {"operation": "create_notion_page_from_zotero_record",
             "status": "approved", "zotero_key": "Z1", "title": "Paper A"},
        ],
    }
    report = build_health_report(
        [],
        sync_plan=plan,
        write_log_entries=[
            {"field": "__page_create__", "status": "applied",
             "entity_id": "page-A", "zotero_key": "Z1"},
        ],
    )
    assert "create_outcomes" in report
    assert report["create_outcomes"]["approved"] == 1
    assert report["create_outcomes"]["applied"] == 1
