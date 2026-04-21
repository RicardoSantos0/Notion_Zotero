"""Tests for the dry-run diff engine."""
from notion_zotero.services.diff_engine import diff_bundles, DiffReport, DiffEntry


def _make_bundle(ref_id, title, state="todo", extra_refs=None):
    return {
        "references": [
            {
                "id": ref_id,
                "title": title,
                "authors": [],
                "year": None,
                "journal": None,
                "doi": None,
                "url": None,
                "zotero_key": None,
                "abstract": None,
                "item_type": None,
                "tags": [],
                "provenance": {},
                "validation_status": "unknown",
                "sync_metadata": {},
            }
        ] + (extra_refs or []),
        "tasks": [],
        "reference_tasks": [],
        "task_extractions": [],
        "workflow_states": [
            {
                "id": f"ws_{ref_id}",
                "reference_id": ref_id,
                "state": state,
                "source_field": "Status",
                "provenance": {},
                "validation_status": "unknown",
                "sync_metadata": {},
            }
        ],
        "annotations": [],
    }


def test_no_changes_produces_empty_diff():
    bundle = _make_bundle("ref-001", "Same Title")
    report = diff_bundles(bundle, bundle)
    assert report.entries == []


def test_changed_field_detected():
    baseline = _make_bundle("ref-001", "Old Title")
    updated = _make_bundle("ref-001", "New Title")
    report = diff_bundles(baseline, updated)
    changed = [e for e in report.entries if e.field == "title" and e.change_type == "changed"]
    assert len(changed) == 1
    assert changed[0].old_value == "Old Title"
    assert changed[0].new_value == "New Title"


def test_added_entity_detected():
    baseline = _make_bundle("ref-001", "Paper A")
    updated = _make_bundle("ref-001", "Paper A", extra_refs=[
        {
            "id": "ref-002",
            "title": "Paper B",
            "authors": [],
            "year": None,
            "journal": None,
            "doi": None,
            "url": None,
            "zotero_key": None,
            "abstract": None,
            "item_type": None,
            "tags": [],
            "provenance": {},
            "validation_status": "unknown",
            "sync_metadata": {},
        }
    ])
    report = diff_bundles(baseline, updated)
    added = [e for e in report.entries if e.change_type == "added"]
    assert any(e.entity_id == "ref-002" for e in added)


def test_removed_entity_detected():
    baseline = _make_bundle("ref-001", "Paper A", extra_refs=[
        {
            "id": "ref-003",
            "title": "Paper C",
            "authors": [],
            "year": None,
            "journal": None,
            "doi": None,
            "url": None,
            "zotero_key": None,
            "abstract": None,
            "item_type": None,
            "tags": [],
            "provenance": {},
            "validation_status": "unknown",
            "sync_metadata": {},
        }
    ])
    updated = _make_bundle("ref-001", "Paper A")
    report = diff_bundles(baseline, updated)
    removed = [e for e in report.entries if e.change_type == "removed"]
    assert any(e.entity_id == "ref-003" for e in removed)


def test_diff_report_summary():
    baseline = _make_bundle("ref-001", "Old Title")
    updated = _make_bundle("ref-001", "New Title")
    report = diff_bundles(baseline, updated)
    summary = report.summary()
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_diff_report_summary_no_changes():
    bundle = _make_bundle("ref-001", "Same Title")
    report = diff_bundles(bundle, bundle)
    summary = report.summary()
    assert "No differences" in summary


def test_diff_entry_fields():
    """DiffEntry carries all required fields."""
    entry = DiffEntry(
        entity_type="references",
        entity_id="ref-X",
        field="title",
        old_value="A",
        new_value="B",
        change_type="changed",
    )
    assert entry.entity_type == "references"
    assert entry.entity_id == "ref-X"
    assert entry.field == "title"
    assert entry.old_value == "A"
    assert entry.new_value == "B"
    assert entry.change_type == "changed"


def test_workflow_state_change_detected():
    baseline = _make_bundle("ref-001", "Paper", state="todo")
    updated = _make_bundle("ref-001", "Paper", state="done")
    report = diff_bundles(baseline, updated)
    changed = [e for e in report.entries if e.field == "state" and e.change_type == "changed"]
    assert len(changed) == 1
    assert changed[0].old_value == "todo"
    assert changed[0].new_value == "done"


def test_diff_report_bundle_id_propagated():
    baseline = {"bundle_id": "my-bundle", "references": [], "tasks": [],
                "reference_tasks": [], "task_extractions": [], "workflow_states": [],
                "annotations": []}
    updated = {"bundle_id": "my-bundle", "references": [], "tasks": [],
               "reference_tasks": [], "task_extractions": [], "workflow_states": [],
               "annotations": []}
    report = diff_bundles(baseline, updated)
    assert report.bundle_id == "my-bundle"


def test_diff_dirs(tmp_path):
    """diff_dirs correctly processes a directory of bundle JSON files."""
    import json

    baseline_dir = tmp_path / "baseline"
    updated_dir = tmp_path / "updated"
    baseline_dir.mkdir()
    updated_dir.mkdir()

    bundle_a_base = _make_bundle("ref-001", "Old Title")
    bundle_a_upd = _make_bundle("ref-001", "New Title")
    bundle_a_base["bundle_id"] = "bundle-a"
    bundle_a_upd["bundle_id"] = "bundle-a"

    (baseline_dir / "bundle-a.json").write_text(json.dumps(bundle_a_base), encoding="utf-8")
    (updated_dir / "bundle-a.json").write_text(json.dumps(bundle_a_upd), encoding="utf-8")

    from notion_zotero.services.diff_engine import diff_dirs
    reports = diff_dirs(baseline_dir, updated_dir)
    assert len(reports) == 1
    changed = [e for e in reports[0].entries if e.field == "title" and e.change_type == "changed"]
    assert len(changed) == 1
