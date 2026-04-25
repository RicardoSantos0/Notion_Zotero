"""Smoke tests for previously-uncovered modules.

Goal: bring coverage above 85% so the pytest-cov gate passes.
These are minimal smoke tests — they verify imports and basic execution,
not exhaustive correctness.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_PROV = {
    "source_id": "test",
    "domain_pack_id": "test-pack",
    "domain_pack_version": "0.0.1",
}


# ---------------------------------------------------------------------------
# services/flattener.py
# ---------------------------------------------------------------------------

def test_flatten_bundles_empty_dir(tmp_path):
    from notion_zotero.services.flattener import flatten_bundles
    result = flatten_bundles(tmp_path)
    assert isinstance(result, dict)
    assert "references" in result


def test_flatten_bundles_with_fixture(tmp_path):
    from notion_zotero.services.flattener import flatten_bundles

    bundle = {
        "references": [
            {
                "id": "ref-001",
                "title": "Smoke Test Paper",
                "provenance": _PROV,
                "sync_metadata": {},
            }
        ]
    }
    fixture = tmp_path / "test.canonical.json"
    fixture.write_text(json.dumps(bundle), encoding="utf-8")

    result = flatten_bundles(tmp_path)
    assert len(result["references"]) == 1


def test_flatten_bundles_missing_dir():
    from notion_zotero.services.flattener import flatten_bundles
    with pytest.raises(FileNotFoundError):
        flatten_bundles("/nonexistent/path/xyz")


# ---------------------------------------------------------------------------
# services/migration_audit.py
# ---------------------------------------------------------------------------

def test_run_audit_empty_dirs(tmp_path):
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    report = run_audit(legacy_dir, canonical_dir)
    assert report.summary().startswith("Migration Audit Summary")
    assert report.missing_references == []


def test_run_audit_with_missing_reference(tmp_path):
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    # A legacy file with no matching canonical bundle
    legacy_page = {"properties": {"Title": "Some Paper"}}
    (legacy_dir / "page-abc.json").write_text(json.dumps(legacy_page), encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    assert len(report.missing_references) == 1
    assert report.missing_references[0]["page_id"] == "page-abc"


# ---------------------------------------------------------------------------
# services/qa_report.py
# ---------------------------------------------------------------------------

def test_run_qa_empty_dir(tmp_path):
    from notion_zotero.services.qa_report import run_qa

    report = run_qa(tmp_path)
    assert report.summary().startswith("QA Report Summary")
    assert report.malformed_extractions == []


def test_run_qa_with_bundle(tmp_path):
    from notion_zotero.services.qa_report import run_qa

    bundle = {
        "references": [
            {
                "id": "ref-qa",
                "title": None,  # triggers incomplete_references
                "doi": None,
                "zotero_key": None,
            }
        ],
        "workflow_states": [
            {"id": "ws-1", "state": "todo"}
        ],
        "task_extractions": [],
    }
    (tmp_path / "smoke.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")

    report = run_qa(tmp_path)
    # A reference with no title should appear in incomplete_references
    assert len(report.incomplete_references) >= 1


# ---------------------------------------------------------------------------
# core/citation.py
# ---------------------------------------------------------------------------

def test_citation_from_reference_basic():
    from notion_zotero.core.citation import citation_from_reference
    from notion_zotero.core.models import Reference

    ref = Reference(
        id="cite-001",
        title="Test Title",
        authors=["Smith, J.", "Doe, A."],
        year=2024,
        journal="Journal of Tests",
        provenance=_PROV,
        sync_metadata={},
    )
    result = citation_from_reference(ref)
    assert "Smith, J." in result
    assert "2024" in result
    assert "Test Title" in result


def test_citation_from_reference_no_authors():
    from notion_zotero.core.citation import citation_from_reference
    from notion_zotero.core.models import Reference

    ref = Reference(
        id="cite-002",
        title="Authorless Paper",
        provenance=_PROV,
        sync_metadata={},
    )
    result = citation_from_reference(ref)
    assert "Authorless Paper" in result


def test_citation_from_reference_many_authors():
    from notion_zotero.core.citation import citation_from_reference
    from notion_zotero.core.models import Reference

    ref = Reference(
        id="cite-003",
        title="Big Collaboration",
        authors=["A", "B", "C", "D"],
        year=2023,
        provenance=_PROV,
        sync_metadata={},
    )
    result = citation_from_reference(ref)
    assert "et al." in result


# ---------------------------------------------------------------------------
# analysis/__init__.py
# ---------------------------------------------------------------------------

def test_analysis_module_importable():
    import notion_zotero.analysis as analysis
    assert hasattr(analysis, "export_database_snapshot")


# ---------------------------------------------------------------------------
# core/normalize.py
# ---------------------------------------------------------------------------

def test_normalize_title_none():
    from notion_zotero.core.normalize import normalize_title
    assert normalize_title(None) == ""


def test_normalize_title_empty():
    from notion_zotero.core.normalize import normalize_title
    assert normalize_title("") == ""


def test_normalize_title_whitespace():
    from notion_zotero.core.normalize import normalize_title
    assert normalize_title("  hello   world  ") == "hello world"


def test_normalize_title_normal():
    from notion_zotero.core.normalize import normalize_title
    assert normalize_title("My Paper Title") == "My Paper Title"


def test_normalize_authors_none():
    from notion_zotero.core.normalize import normalize_authors
    assert normalize_authors(None) == ""


def test_normalize_authors_empty_string():
    from notion_zotero.core.normalize import normalize_authors
    assert normalize_authors("") == ""
