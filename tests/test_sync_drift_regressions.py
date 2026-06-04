from __future__ import annotations

import json


def _bundle(reference: dict) -> dict:
    return {
        "bundle_id": reference["id"],
        "references": [reference],
        "tasks": [],
        "reference_tasks": [],
        "task_extractions": [],
        "workflow_states": [],
        "annotations": [],
    }


def _write_bundle(directory, name: str, reference: dict):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.canonical.json"
    path.write_text(json.dumps(_bundle(reference)), encoding="utf-8")
    return path


def test_drift_zotero_metadata_update_is_executable(tmp_path):
    from notion_zotero.services.sync_planner import build_sync_plan

    notion_dir = tmp_path / "notion"
    zotero_dir = tmp_path / "zotero"
    _write_bundle(
        notion_dir,
        "notion-paper",
        {
            "id": "notion-page-1",
            "title": "Learning Analytics Paper",
            "authors": ["A. Author"],
            "year": 2020,
            "doi": "10.1000/example",
            "zotero_key": "ZOT1",
        },
    )
    _write_bundle(
        zotero_dir,
        "zotero-paper",
        {
            "id": "zotero-item-1",
            "title": "Learning Analytics Paper",
            "authors": ["A. Author"],
            "year": 2021,
            "doi": "10.1000/example",
            "zotero_key": "ZOT1",
        },
    )

    plan = build_sync_plan(notion_dir, zotero_dir)

    assert plan["summary"]["matched"] == 1
    assert plan["summary"]["operations"] == 1
    assert plan["operations"][0]["operation"] == "update_notion_reference_field"
    assert plan["operations"][0]["field"] == "year"
    assert plan["operations"][0]["old_value"] == 2020
    assert plan["operations"][0]["new_value"] == 2021


def test_drift_zotero_only_record_stays_review_only(tmp_path):
    from notion_zotero.services.sync_planner import build_sync_plan

    notion_dir = tmp_path / "notion"
    zotero_dir = tmp_path / "zotero"
    _write_bundle(
        zotero_dir,
        "zotero-only",
        {
            "id": "zotero-item-2",
            "title": "Missing From Notion",
            "authors": ["B. Author"],
            "year": 2024,
            "zotero_key": "ZOT2",
        },
    )
    notion_dir.mkdir()

    plan = build_sync_plan(notion_dir, zotero_dir)

    assert plan["summary"]["operations"] == 0
    assert plan["summary"]["review_actions"] == 1
    action = plan["review_actions"][0]
    assert action["operation"] == "create_notion_page_from_zotero_record"
    assert action["status"] == "needs_review"
    assert action["reference"]["title"] == "Missing From Notion"


def test_drift_title_collision_is_ambiguous_not_executable(tmp_path):
    from notion_zotero.services.sync_planner import build_sync_plan

    notion_dir = tmp_path / "notion"
    zotero_dir = tmp_path / "zotero"
    _write_bundle(
        notion_dir,
        "notion-2020",
        {"id": "N1", "title": "Shared Title", "authors": ["A"], "year": 2020},
    )
    _write_bundle(
        notion_dir,
        "notion-2021",
        {"id": "N2", "title": "Shared Title", "authors": ["B"], "year": 2021},
    )
    _write_bundle(
        zotero_dir,
        "zotero",
        {"id": "Z1", "title": "Shared Title", "authors": ["C"], "year": 2022},
    )

    plan = build_sync_plan(notion_dir, zotero_dir)

    assert plan["summary"]["matched"] == 0
    assert plan["summary"]["operations"] == 0
    assert plan["summary"]["ambiguous"] == 1
    assert plan["ambiguous"][0]["reason"] == "title_year_conflict"
