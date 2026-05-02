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


def test_build_sync_plan_matches_by_zotero_key_and_plans_zotero_owned_update(tmp_path):
    from notion_zotero.services.sync_planner import build_sync_plan

    notion_dir = tmp_path / "notion"
    zotero_dir = tmp_path / "zotero"
    _write_bundle(
        notion_dir,
        "notion-ref",
        {
            "id": "notion-page-1",
            "title": "Old title",
            "authors": ["A. Researcher"],
            "year": 2020,
            "doi": "10.1000/example",
            "zotero_key": "ZOT1",
        },
    )
    _write_bundle(
        zotero_dir,
        "zotero-ref",
        {
            "id": "zotero-item-1",
            "title": "New title",
            "authors": ["A. Researcher"],
            "year": 2020,
            "doi": "10.1000/example",
            "zotero_key": "ZOT1",
        },
    )

    plan = build_sync_plan(notion_dir, zotero_dir, generated_at="2026-05-02T00:00:00Z")

    assert plan["summary"]["matched"] == 1
    assert plan["summary"]["operations"] == 1
    assert plan["matches"][0]["match_key"] == {"type": "zotero_key", "value": "zot1"}
    assert plan["operations"][0]["target"] == "notion"
    assert plan["operations"][0]["source"] == "zotero"
    assert plan["operations"][0]["field"] == "title"
    assert plan["operations"][0]["old_value"] == "Old title"
    assert plan["operations"][0]["new_value"] == "New title"


def test_build_sync_plan_reports_records_only_present_in_one_source(tmp_path):
    from notion_zotero.services.sync_planner import build_sync_plan

    notion_dir = tmp_path / "notion"
    zotero_dir = tmp_path / "zotero"
    _write_bundle(notion_dir, "notion-only", {"id": "N1", "title": "Only Notion"})
    _write_bundle(zotero_dir, "zotero-only", {"id": "Z1", "title": "Only Zotero"})

    plan = build_sync_plan(notion_dir, zotero_dir)

    assert plan["summary"]["matched"] == 0
    assert plan["summary"]["operations"] == 0
    assert plan["summary"]["only_notion"] == 1
    assert plan["summary"]["only_zotero"] == 1
    assert plan["summary"]["review_actions"] == 1
    assert plan["only_notion"][0]["reference_id"] == "N1"
    assert plan["only_zotero"][0]["reference_id"] == "Z1"
    assert plan["review_actions"][0]["operation"] == "create_notion_page_from_zotero_record"
    assert plan["review_actions"][0]["status"] == "needs_review"


def test_build_sync_plan_marks_multiple_notion_candidates_as_ambiguous(tmp_path):
    from notion_zotero.services.sync_planner import build_sync_plan

    notion_dir = tmp_path / "notion"
    zotero_dir = tmp_path / "zotero"
    shared = {
        "title": "Shared paper",
        "authors": ["A. Researcher"],
        "year": 2021,
        "doi": "10.1000/shared",
        "zotero_key": "DUP1",
    }
    _write_bundle(notion_dir, "notion-a", {"id": "N1", **shared})
    _write_bundle(notion_dir, "notion-b", {"id": "N2", **shared})
    _write_bundle(zotero_dir, "zotero", {"id": "Z1", **shared})

    plan = build_sync_plan(notion_dir, zotero_dir)

    assert plan["summary"]["matched"] == 0
    assert plan["summary"]["ambiguous"] == 1
    assert plan["summary"]["only_notion"] == 0
    assert plan["ambiguous"][0]["reason"] == "multiple_candidates"
    assert {candidate["notion"]["reference_id"] for candidate in plan["ambiguous"][0]["candidates"]} == {
        "N1",
        "N2",
    }


def test_write_sync_plan_creates_parent_directory(tmp_path):
    from notion_zotero.services.sync_planner import write_sync_plan

    out = tmp_path / "nested" / "plan.json"
    written = write_sync_plan({"version": 1, "summary": {}}, out)

    assert written == out
    assert json.loads(out.read_text(encoding="utf-8"))["version"] == 1
