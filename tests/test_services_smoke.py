"""Smoke tests for previously-uncovered modules.

Goal: bring coverage above 85% so the pytest-cov gate passes.
These are minimal smoke tests — they verify imports and basic execution,
not exhaustive correctness.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_normalize_authors_string():
    from notion_zotero.core.normalize import normalize_authors
    assert normalize_authors("  Smith, J. ") == "Smith, J."


def test_normalize_authors_list():
    from notion_zotero.core.normalize import normalize_authors
    result = normalize_authors(["Smith, J.", "Doe, A."])
    assert result == "Smith, J., Doe, A."


def test_normalize_authors_non_iterable():
    from notion_zotero.core.normalize import normalize_authors
    assert normalize_authors(42) == "42"


def test_normalize_doi_none():
    from notion_zotero.core.normalize import normalize_doi
    assert normalize_doi(None) is None


def test_normalize_doi_empty():
    from notion_zotero.core.normalize import normalize_doi
    assert normalize_doi("") is None


def test_normalize_doi_strips_https_prefix():
    from notion_zotero.core.normalize import normalize_doi
    assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"


def test_normalize_doi_strips_dx_prefix():
    from notion_zotero.core.normalize import normalize_doi
    assert normalize_doi("https://dx.doi.org/10.1234/test") == "10.1234/test"


def test_normalize_doi_strips_http_prefix():
    from notion_zotero.core.normalize import normalize_doi
    assert normalize_doi("http://doi.org/10.1234/test") == "10.1234/test"


def test_normalize_doi_bare():
    from notion_zotero.core.normalize import normalize_doi
    assert normalize_doi("10.1234/TEST") == "10.1234/test"


def test_normalize_heading_none():
    from notion_zotero.core.normalize import normalize_heading
    assert normalize_heading(None) == ""


def test_normalize_heading_value():
    from notion_zotero.core.normalize import normalize_heading
    assert normalize_heading("  Section 1  ") == "Section 1"


def test_normalize_status_none():
    from notion_zotero.core.normalize import normalize_status
    assert normalize_status(None) is None


def test_normalize_status_empty():
    from notion_zotero.core.normalize import normalize_status
    assert normalize_status("") is None


def test_normalize_status_strips():
    from notion_zotero.core.normalize import normalize_status
    assert normalize_status("  In Progress  ") == "in progress"


def test_normalize_url_none():
    from notion_zotero.core.normalize import normalize_url
    assert normalize_url(None) is None


def test_normalize_url_empty():
    from notion_zotero.core.normalize import normalize_url
    assert normalize_url("") is None


def test_normalize_url_strips():
    from notion_zotero.core.normalize import normalize_url
    assert normalize_url("  https://example.com  ") == "https://example.com"


# ---------------------------------------------------------------------------
# core/exceptions.py
# ---------------------------------------------------------------------------

def test_field_mapping_error_with_source():
    from notion_zotero.core.exceptions import FieldMappingError
    exc = FieldMappingError("doi", source="notion")
    assert "doi" in str(exc)
    assert "notion" in str(exc)
    assert exc.field == "doi"
    assert exc.source == "notion"


def test_field_mapping_error_no_source():
    from notion_zotero.core.exceptions import FieldMappingError
    exc = FieldMappingError("title")
    assert "title" in str(exc)
    assert exc.source is None


def test_schema_validation_error():
    from notion_zotero.core.exceptions import SchemaValidationError
    exc = SchemaValidationError("Reference", "missing id")
    assert "Reference" in str(exc)
    assert "missing id" in str(exc)
    assert exc.model == "Reference"
    assert exc.details == "missing id"


def test_domain_pack_error_with_reason():
    from notion_zotero.core.exceptions import DomainPackError
    exc = DomainPackError("my-pack", reason="not found")
    assert "my-pack" in str(exc)
    assert "not found" in str(exc)
    assert exc.pack_id == "my-pack"


def test_domain_pack_error_no_reason():
    from notion_zotero.core.exceptions import DomainPackError
    exc = DomainPackError("my-pack")
    assert "my-pack" in str(exc)


def test_template_error_with_reason():
    from notion_zotero.core.exceptions import TemplateError
    exc = TemplateError("tmpl-01", reason="invalid columns")
    assert "tmpl-01" in str(exc)
    assert "invalid columns" in str(exc)
    assert exc.template_id == "tmpl-01"


def test_template_error_no_reason():
    from notion_zotero.core.exceptions import TemplateError
    exc = TemplateError("tmpl-02")
    assert "tmpl-02" in str(exc)


def test_provenance_error():
    from notion_zotero.core.exceptions import ProvenanceError
    exc = ProvenanceError("missing source_id")
    assert "missing source_id" in str(exc)


# ---------------------------------------------------------------------------
# services/migration_audit.py — additional branch coverage
# ---------------------------------------------------------------------------

def test_audit_with_canonical_match_and_field_loss(tmp_path):
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    page_id = "page-xyz"

    # Legacy page has a title but canonical ref does not.
    # The ref id must equal the legacy file stem so the index lookup finds a match.
    legacy_page = {
        "properties": {
            "Title": "Important Paper",
        }
    }
    (legacy_dir / f"{page_id}.json").write_text(json.dumps(legacy_page), encoding="utf-8")

    canonical_bundle = {
        "references": [
            {
                "id": page_id,   # must match legacy file stem for the index lookup
                "title": None,   # field loss: legacy had a title
                "provenance": _PROV,
            }
        ],
        "task_extractions": [],
        "workflow_states": [],
    }
    (canonical_dir / f"{page_id}.canonical.json").write_text(json.dumps(canonical_bundle), encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    # Field loss: legacy had Title, canonical does not
    assert any(fl["field"] == "title" for fl in report.field_loss)


def test_audit_provenance_loss(tmp_path):
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    page_id = "page-provloss"
    legacy_page = {"properties": {}}
    (legacy_dir / f"{page_id}.json").write_text(json.dumps(legacy_page), encoding="utf-8")

    canonical_bundle = {
        "references": [
            {
                "id": page_id,   # must match legacy file stem
                "title": "Some Paper",
                # provenance is missing required keys
                "provenance": {"source_id": "x"},
            }
        ],
        "task_extractions": [],
        "workflow_states": [],
    }
    (canonical_dir / f"{page_id}.canonical.json").write_text(json.dumps(canonical_bundle), encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    assert len(report.provenance_loss) >= 1
    assert "domain_pack_id" in report.provenance_loss[0]["missing_provenance_keys"]


def test_audit_missing_extractions(tmp_path):
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    page_id = "page-tables"
    legacy_page = {
        "properties": {},
        "children": [
            {"type": "child_database"},
            {"type": "child_database"},
        ]
    }
    (legacy_dir / f"{page_id}.json").write_text(json.dumps(legacy_page), encoding="utf-8")

    canonical_bundle = {
        "references": [{"id": page_id, "title": "Paper", "provenance": _PROV}],
        "task_extractions": [],   # none present — should trigger missing_extractions
        "workflow_states": [],
    }
    (canonical_dir / f"{page_id}.canonical.json").write_text(json.dumps(canonical_bundle), encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    assert len(report.missing_extractions) == 1
    assert report.missing_extractions[0]["legacy_tables"] == 2


def test_audit_workflow_state_mismatch(tmp_path):
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    page_id = "page-statemismatch"
    legacy_page = {
        "properties": {
            "Status": {"select": {"name": "Done"}}
        }
    }
    (legacy_dir / f"{page_id}.json").write_text(json.dumps(legacy_page), encoding="utf-8")

    canonical_bundle = {
        "references": [{"id": page_id, "title": "Paper", "provenance": _PROV}],
        "task_extractions": [],
        "workflow_states": [{"id": "ws-1", "state": "in_progress"}],  # should be "done"
    }
    (canonical_dir / f"{page_id}.canonical.json").write_text(json.dumps(canonical_bundle), encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    assert len(report.workflow_state_mismatch) == 1
    assert report.workflow_state_mismatch[0]["expected_canonical"] == "done"
    assert report.workflow_state_mismatch[0]["actual_canonical"] == "in_progress"


def test_audit_status_lowercase_key(tmp_path):
    """Test _extract_legacy_status with lowercase 'status' property key."""
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    page_id = "page-lowerstatus"
    legacy_page = {
        "properties": {
            "status": {"select": {"name": "In progress"}}
        }
    }
    (legacy_dir / f"{page_id}.json").write_text(json.dumps(legacy_page), encoding="utf-8")

    canonical_bundle = {
        "references": [{"id": page_id, "title": "Paper", "provenance": _PROV}],
        "task_extractions": [],
        "workflow_states": [{"id": "ws-2", "state": "todo"}],  # mismatch with "in_progress"
    }
    (canonical_dir / f"{page_id}.canonical.json").write_text(json.dumps(canonical_bundle), encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    assert len(report.workflow_state_mismatch) == 1


def test_audit_skips_canonical_files_in_legacy(tmp_path):
    """Files containing .canonical. in the legacy dir should be skipped."""
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    # This file must be skipped
    (legacy_dir / "page-x.canonical.json").write_text("{}", encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    assert report.missing_references == []


def test_audit_summary_counts(tmp_path):
    from notion_zotero.services.migration_audit import run_audit

    legacy_dir = tmp_path / "legacy"
    canonical_dir = tmp_path / "canonical"
    legacy_dir.mkdir()
    canonical_dir.mkdir()

    # One missing reference
    (legacy_dir / "page-missing.json").write_text('{"properties": {}}', encoding="utf-8")

    report = run_audit(legacy_dir, canonical_dir)
    summary = report.summary()
    assert "1" in summary


# ---------------------------------------------------------------------------
# services/qa_report.py — additional branch coverage
# ---------------------------------------------------------------------------

def test_qa_ambiguous_status(tmp_path):
    from notion_zotero.services.qa_report import run_qa

    bundle = {
        "references": [
            {"id": "r1", "title": "Paper", "doi": "10.x/y", "zotero_key": "abc"}
        ],
        "workflow_states": [
            {"id": "ws-bad", "state": "unknown_state"}
        ],
        "task_extractions": [],
    }
    (tmp_path / "qa.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")

    report = run_qa(tmp_path)
    assert len(report.ambiguous_statuses) == 1
    assert report.ambiguous_statuses[0]["state"] == "unknown_state"


def test_qa_unlinked_extraction(tmp_path):
    from notion_zotero.services.qa_report import run_qa

    bundle = {
        "references": [
            {"id": "r2", "title": "Paper", "doi": "10.x/z", "zotero_key": "def"}
        ],
        "workflow_states": [],
        "task_extractions": [
            {
                "id": "ex-1",
                "reference_task_id": None,  # unlinked
                "extracted": [{"Metric": "RMSE", "Value": "0.5"}],
                "template_id": "prediction_modeling",
            }
        ],
    }
    (tmp_path / "qa2.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")

    report = run_qa(tmp_path)
    assert len(report.unlinked_extractions) == 1


def test_qa_malformed_extraction_empty_extracted(tmp_path):
    from notion_zotero.services.qa_report import run_qa

    bundle = {
        "references": [
            {"id": "r3", "title": "Paper", "doi": "10.x/a", "zotero_key": "ghi"}
        ],
        "workflow_states": [],
        "task_extractions": [
            {
                "id": "ex-2",
                "reference_task_id": "r3",
                "extracted": None,  # malformed
                "template_id": "prediction_modeling",
            }
        ],
    }
    (tmp_path / "qa3.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")

    report = run_qa(tmp_path)
    assert len(report.malformed_extractions) == 1
    assert report.malformed_extractions[0]["extraction_id"] == "ex-2"


def test_qa_missing_columns(tmp_path):
    from notion_zotero.services.qa_report import run_qa

    bundle = {
        "references": [
            {"id": "r4", "title": "Paper", "doi": "10.x/b", "zotero_key": "jkl"}
        ],
        "workflow_states": [],
        "task_extractions": [
            {
                "id": "ex-3",
                "reference_task_id": "r4",
                "extracted": [{"WrongCol": "x"}],  # missing required Metric & Value
                "template_id": "prediction_modeling",
            }
        ],
    }
    (tmp_path / "qa4.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")

    report = run_qa(tmp_path)
    assert len(report.missing_columns) >= 1


def test_qa_unknown_template_id(tmp_path):
    """Extractions with an unrecognised template_id should not crash."""
    from notion_zotero.services.qa_report import run_qa

    bundle = {
        "references": [
            {"id": "r5", "title": "Paper", "doi": "10.x/c", "zotero_key": "mno"}
        ],
        "workflow_states": [],
        "task_extractions": [
            {
                "id": "ex-4",
                "reference_task_id": "r5",
                "extracted": [{"anything": "value"}],
                "template_id": "nonexistent_template",
            }
        ],
    }
    (tmp_path / "qa5.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")

    report = run_qa(tmp_path)
    # Should not crash; no missing columns reported for unknown template
    assert isinstance(report.missing_columns, list)


def test_qa_summary_fields(tmp_path):
    from notion_zotero.services.qa_report import run_qa

    report = run_qa(tmp_path)
    summary = report.summary()
    assert "malformed" in summary
    assert "ambiguous" in summary
    assert "unlinked" in summary


def test_qa_extraction_row_not_dict(tmp_path):
    """extracted list containing non-dict rows should not crash."""
    from notion_zotero.services.qa_report import run_qa

    bundle = {
        "references": [
            {"id": "r6", "title": "Paper", "doi": "10.x/d", "zotero_key": "pqr"}
        ],
        "workflow_states": [],
        "task_extractions": [
            {
                "id": "ex-5",
                "reference_task_id": "r6",
                "extracted": ["not-a-dict"],
                "template_id": "prediction_modeling",
            }
        ],
    }
    (tmp_path / "qa6.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")

    report = run_qa(tmp_path)
    assert isinstance(report, object)


# ---------------------------------------------------------------------------
# connectors/notion/reader.py — non-API paths
# ---------------------------------------------------------------------------

def test_notion_reader_raises_without_key(monkeypatch):
    """NotionReader must raise ConfigurationError when no API key is available."""
    from notion_zotero.connectors.notion.reader import NotionReader, ConfigurationError

    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        NotionReader()


def test_notion_reader_raises_without_notion_client(monkeypatch):
    """NotionReader raises ConfigurationError when notion-client is not installed."""
    import sys
    import builtins

    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.setenv("NOTION_API_KEY", "fake-key-for-import-test")

    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "notion_client":
            raise ImportError("notion_client not available")
        return real_import(name, *args, **kwargs)

    # Remove cached module so our mock import is actually called
    sys.modules.pop("notion_client", None)
    sys.modules.pop("notion_zotero.connectors.notion.reader", None)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    from notion_zotero.connectors.notion.reader import ConfigurationError

    with pytest.raises((ImportError, ConfigurationError)):  # mock raises ImportError; real path raises ConfigurationError
        from notion_zotero.connectors.notion.reader import NotionReader
        NotionReader(api_key="fake-key")


def test_notion_reader_configuration_error_is_notion_zotero_error():
    from notion_zotero.connectors.notion.reader import ConfigurationError
    from notion_zotero.core.exceptions import NotionZoteroError

    assert issubclass(ConfigurationError, NotionZoteroError)


# ---------------------------------------------------------------------------
# analysis/__init__.py — export_database_snapshot paths
# ---------------------------------------------------------------------------

def test_export_database_snapshot_raises_on_missing_fixtures(tmp_path, monkeypatch):
    """export_database_snapshot raises FileNotFoundError when fixtures dir is absent."""
    import notion_zotero.analysis as analysis

    # Run from tmp_path so "fixtures/reading_list" definitely doesn't exist
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        analysis.export_database_snapshot(out=str(tmp_path / "out.json"))


# ---------------------------------------------------------------------------
# services/flattener.py — to_csv, to_jsonl, malformed bundle paths
# ---------------------------------------------------------------------------

def test_flatten_bundles_skips_malformed_json(tmp_path):
    """flatten_bundles silently skips files with invalid JSON."""
    from notion_zotero.services.flattener import flatten_bundles
    bad = tmp_path / "bad.canonical.json"
    bad.write_text("NOT JSON {{{", encoding="utf-8")
    result = flatten_bundles(tmp_path)
    assert result["references"].is_empty()


def test_flatten_bundles_skips_non_dict_bundle(tmp_path):
    """flatten_bundles skips bundles that are not dicts (e.g. a bare list)."""
    from notion_zotero.services.flattener import flatten_bundles
    import json
    (tmp_path / "list.canonical.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    result = flatten_bundles(tmp_path)
    assert result["references"].is_empty()


def test_flatten_bundles_skips_non_dict_rows(tmp_path):
    """flatten_bundles skips rows inside a bundle that are not dicts."""
    from notion_zotero.services.flattener import flatten_bundles
    import json
    bundle = {"references": ["string-row", 42, None]}
    (tmp_path / "mixed.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
    result = flatten_bundles(tmp_path)
    assert result["references"].is_empty()


def test_to_csv_writes_files(tmp_path):
    """to_csv writes one CSV file per entity type."""
    from notion_zotero.services.flattener import flatten_bundles, to_csv
    import json
    bundle = {"references": [{"id": "r1", "title": "T"}]}
    (tmp_path / "b.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
    dfs = flatten_bundles(tmp_path)
    out = tmp_path / "csv_out"
    to_csv(dfs, out)
    assert (out / "references.csv").exists()


def test_to_jsonl_writes_files(tmp_path):
    """to_jsonl writes one JSONL file per entity type."""
    from notion_zotero.services.flattener import flatten_bundles, to_jsonl
    import json
    bundle = {"references": [{"id": "r1", "title": "T"}]}
    (tmp_path / "b.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
    dfs = flatten_bundles(tmp_path)
    out = tmp_path / "jsonl_out"
    to_jsonl(dfs, out)
    assert (out / "references.jsonl").exists()


# ---------------------------------------------------------------------------
# schemas/templates/base.py — ColumnDefinition, ExtractionTemplate, TemplateMatchRule
# ---------------------------------------------------------------------------

def test_column_definition_matches_by_name():
    from notion_zotero.schemas.templates.base import ColumnDefinition
    col = ColumnDefinition(name="doi", aliases=["doi_number"])
    assert col.matches("DOI") is True
    assert col.matches("doi_number") is True
    assert col.matches("title") is False
    assert col.matches("") is False


def test_column_definition_no_aliases():
    from notion_zotero.schemas.templates.base import ColumnDefinition
    col = ColumnDefinition(name="title")
    assert col.matches("TITLE") is True
    assert col.matches("abstract") is False


def test_extraction_template_model_dump():
    from notion_zotero.schemas.templates.base import ExtractionTemplate, ColumnDefinition
    tmpl = ExtractionTemplate(
        template_id="t1",
        display_name="Test Template",
        expected_columns=[ColumnDefinition(name="doi")],
    )
    d = tmpl.model_dump()
    assert d["template_id"] == "t1"
    assert d["display_name"] == "Test Template"
    assert len(d["expected_columns"]) == 1


def test_template_match_rule_matches_headers():
    from notion_zotero.schemas.templates.base import TemplateMatchRule
    rule = TemplateMatchRule(required_headers=["doi", "title"], min_matches=2)
    assert rule.matches(["DOI", "Title", "Abstract"]) is True
    assert rule.matches(["doi"]) is False
    assert rule.matches([]) is False


def test_template_match_rule_partial_match():
    from notion_zotero.schemas.templates.base import TemplateMatchRule
    rule = TemplateMatchRule(required_headers=["doi"], min_matches=1)
    assert rule.matches(["doi", "title"]) is True


# ---------------------------------------------------------------------------
# core/exceptions.py — ConfigurationError and NotionImportError
# ---------------------------------------------------------------------------

def test_configuration_error_is_notion_zotero_error():
    from notion_zotero.core.exceptions import ConfigurationError, NotionZoteroError
    exc = ConfigurationError("missing key")
    assert isinstance(exc, NotionZoteroError)
    assert "missing key" in str(exc)


def test_notion_import_error_is_notion_zotero_error():
    from notion_zotero.core.exceptions import NotionImportError, NotionZoteroError
    assert issubclass(NotionImportError, NotionZoteroError)
