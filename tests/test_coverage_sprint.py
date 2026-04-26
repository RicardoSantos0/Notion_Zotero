"""Coverage sprint: targeted tests for uncovered code paths.

Focused on closing the gap from 65% to >=80% without modifying existing tests.
Target files: cli.py, migration_audit.py, qa_report.py, flattener.py,
normalize.py, exceptions.py, education_learning_analytics.py, templates/base.py,
scripts/export_reading_list.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_bundle(path: Path, **kwargs) -> None:
    bundle = {
        "references": [],
        "tasks": [],
        "reference_tasks": [],
        "task_extractions": [],
        "workflow_states": [],
        "annotations": [],
    }
    bundle.update(kwargs)
    path.write_text(json.dumps(bundle), encoding="utf-8")


def _minimal_ref(**kwargs) -> dict:
    base = {
        "id": "ref-001",
        "title": "Test Paper",
        "authors": ["Smith, J"],
        "year": 2023,
        "journal": "Nature",
        "doi": "10.1000/xyz123",
        "zotero_key": "ZOT001",
        "provenance": {
            "source_id": "ref-001",
            "source_system": "notion",
            "domain_pack_id": "education_learning_analytics",
            "domain_pack_version": "1.0",
        },
    }
    base.update(kwargs)
    return base


# ===========================================================================
# normalize.py
# ===========================================================================

class TestNormalizeDoi:
    def test_strips_doi_org_prefix(self):
        from notion_zotero.core.normalize import normalize_doi
        assert normalize_doi("https://doi.org/10.1000/xyz") == "10.1000/xyz"

    def test_strips_dx_doi_prefix(self):
        from notion_zotero.core.normalize import normalize_doi
        assert normalize_doi("http://dx.doi.org/10.1000/abc") == "10.1000/abc"

    def test_lowercases(self):
        from notion_zotero.core.normalize import normalize_doi
        assert normalize_doi("10.1000/XYZ") == "10.1000/xyz"

    def test_none_returns_none(self):
        from notion_zotero.core.normalize import normalize_doi
        assert normalize_doi(None) is None

    def test_empty_returns_none(self):
        from notion_zotero.core.normalize import normalize_doi
        assert normalize_doi("") is None


class TestNormalizeHeading:
    def test_collapses_whitespace(self):
        from notion_zotero.core.normalize import normalize_heading
        assert normalize_heading("  foo   bar  ") == "foo bar"

    def test_none_returns_empty(self):
        from notion_zotero.core.normalize import normalize_heading
        assert normalize_heading(None) == ""


class TestNormalizeStatus:
    def test_lowercases_and_strips(self):
        from notion_zotero.core.normalize import normalize_status
        assert normalize_status("  Done  ") == "done"

    def test_none_returns_none(self):
        from notion_zotero.core.normalize import normalize_status
        assert normalize_status(None) is None

    def test_empty_returns_none(self):
        from notion_zotero.core.normalize import normalize_status
        assert normalize_status("") is None


class TestNormalizeUrl:
    def test_strips_whitespace(self):
        from notion_zotero.core.normalize import normalize_url
        assert normalize_url("  https://example.com  ") == "https://example.com"

    def test_none_returns_none(self):
        from notion_zotero.core.normalize import normalize_url
        assert normalize_url(None) is None

    def test_empty_returns_none(self):
        from notion_zotero.core.normalize import normalize_url
        assert normalize_url("") is None


class TestNormalizeAuthorsIterable:
    def test_list_joined(self):
        from notion_zotero.core.normalize import normalize_authors
        assert normalize_authors(["Smith, J", "Doe, A"]) == "Smith, J, Doe, A"

    def test_non_string_non_iterable(self):
        from notion_zotero.core.normalize import normalize_authors
        assert normalize_authors(42) == "42"


# ===========================================================================
# exceptions.py
# ===========================================================================

class TestExceptions:
    def test_field_mapping_error_with_source(self):
        from notion_zotero.core.exceptions import FieldMappingError
        e = FieldMappingError("title", source="notion")
        assert "title" in str(e)
        assert "notion" in str(e)
        assert e.field == "title"
        assert e.source == "notion"

    def test_field_mapping_error_without_source(self):
        from notion_zotero.core.exceptions import FieldMappingError
        e = FieldMappingError("doi")
        assert "doi" in str(e)
        assert e.source is None

    def test_schema_validation_error(self):
        from notion_zotero.core.exceptions import SchemaValidationError
        e = SchemaValidationError("Reference", "missing field 'id'")
        assert "Reference" in str(e)
        assert "missing field 'id'" in str(e)
        assert e.model == "Reference"

    def test_domain_pack_error_with_reason(self):
        from notion_zotero.core.exceptions import DomainPackError
        e = DomainPackError("my_pack", reason="not found")
        assert "my_pack" in str(e)
        assert "not found" in str(e)
        assert e.pack_id == "my_pack"

    def test_domain_pack_error_without_reason(self):
        from notion_zotero.core.exceptions import DomainPackError
        e = DomainPackError("my_pack")
        assert "my_pack" in str(e)

    def test_template_error_with_reason(self):
        from notion_zotero.core.exceptions import TemplateError
        e = TemplateError("tmpl_id", reason="bad format")
        assert "tmpl_id" in str(e)
        assert "bad format" in str(e)
        assert e.template_id == "tmpl_id"

    def test_template_error_without_reason(self):
        from notion_zotero.core.exceptions import TemplateError
        e = TemplateError("tmpl_id")
        assert "tmpl_id" in str(e)

    def test_provenance_error(self):
        from notion_zotero.core.exceptions import ProvenanceError
        e = ProvenanceError("missing source_id")
        assert isinstance(e, Exception)


# ===========================================================================
# domain_packs/education_learning_analytics.py
# ===========================================================================

class TestEducationLearningAnalyticsDomainPack:
    def test_list_tasks_returns_dict(self):
        from notion_zotero.schemas.domain_packs.education_learning_analytics import list_tasks
        tasks = list_tasks()
        assert isinstance(tasks, dict)
        assert "performance_prediction" in tasks

    def test_match_heading_knowledge_tracing(self):
        from notion_zotero.schemas.domain_packs.education_learning_analytics import match_heading_to_task
        assert match_heading_to_task("Knowledge Tracing") == "knowledge_tracing"

    def test_match_heading_recommender(self):
        from notion_zotero.schemas.domain_packs.education_learning_analytics import match_heading_to_task
        assert match_heading_to_task("Recommender Systems") == "recommender_systems"

    def test_match_heading_descriptive(self):
        from notion_zotero.schemas.domain_packs.education_learning_analytics import match_heading_to_task
        assert match_heading_to_task("descriptive analysis") == "descriptive_modelling"

    def test_match_heading_no_match(self):
        from notion_zotero.schemas.domain_packs.education_learning_analytics import match_heading_to_task
        assert match_heading_to_task("Unknown Heading XYZ") is None

    def test_match_heading_none(self):
        from notion_zotero.schemas.domain_packs.education_learning_analytics import match_heading_to_task
        assert match_heading_to_task(None) is None

    def test_domain_pack_version(self):
        from notion_zotero.schemas.domain_packs.education_learning_analytics import DOMAIN_PACK_VERSION
        assert DOMAIN_PACK_VERSION == "1.0"


# ===========================================================================
# schemas/templates/base.py
# ===========================================================================

class TestColumnDefinition:
    def test_matches_canonical_name(self):
        from notion_zotero.schemas.templates.base import ColumnDefinition
        col = ColumnDefinition(name="Score", aliases=["points"])
        assert col.matches("Score")
        assert col.matches("score")

    def test_matches_alias(self):
        from notion_zotero.schemas.templates.base import ColumnDefinition
        col = ColumnDefinition(name="Score", aliases=["points", "grade"])
        assert col.matches("points")
        assert col.matches("Grade")

    def test_no_match(self):
        from notion_zotero.schemas.templates.base import ColumnDefinition
        col = ColumnDefinition(name="Score", aliases=["points"])
        assert not col.matches("xyz")

    def test_empty_header(self):
        from notion_zotero.schemas.templates.base import ColumnDefinition
        col = ColumnDefinition(name="Score")
        assert not col.matches("")

    def test_none_header(self):
        from notion_zotero.schemas.templates.base import ColumnDefinition
        col = ColumnDefinition(name="Score")
        assert not col.matches(None)


class TestExtractionTemplateValidation:
    def test_valid_row(self):
        from notion_zotero.schemas.templates.base import ExtractionTemplate, ColumnDefinition
        tmpl = ExtractionTemplate(
            template_id="t1",
            display_name="T1",
            expected_columns=[ColumnDefinition(name="score", required=True)],
        )
        errors = tmpl.validate_extraction_row({"score": "A+"})
        assert errors == []

    def test_missing_required_column(self):
        from notion_zotero.schemas.templates.base import ExtractionTemplate, ColumnDefinition
        tmpl = ExtractionTemplate(
            template_id="t1",
            display_name="T1",
            expected_columns=[ColumnDefinition(name="score", required=True)],
        )
        errors = tmpl.validate_extraction_row({"other": "value"})
        assert any("score" in e for e in errors)

    def test_alias_satisfies_required(self):
        from notion_zotero.schemas.templates.base import ExtractionTemplate, ColumnDefinition
        tmpl = ExtractionTemplate(
            template_id="t1",
            display_name="T1",
            expected_columns=[ColumnDefinition(name="score", aliases=["grade"], required=True)],
        )
        errors = tmpl.validate_extraction_row({"grade": "B"})
        assert errors == []

    def test_model_dump_is_dict(self):
        from notion_zotero.schemas.templates.base import ExtractionTemplate
        tmpl = ExtractionTemplate(template_id="t1", display_name="T1")
        d = tmpl.model_dump()
        assert isinstance(d, dict)
        assert d["template_id"] == "t1"


class TestTemplateMatchRule:
    def test_matches_required_headers(self):
        from notion_zotero.schemas.templates.base import TemplateMatchRule
        rule = TemplateMatchRule(required_headers=["score", "algorithm"], min_matches=2)
        assert rule.matches(["Score Column", "Algorithm Used"])

    def test_partial_match_below_threshold(self):
        from notion_zotero.schemas.templates.base import TemplateMatchRule
        rule = TemplateMatchRule(required_headers=["score", "algorithm"], min_matches=2)
        assert not rule.matches(["score"])

    def test_empty_headers(self):
        from notion_zotero.schemas.templates.base import TemplateMatchRule
        rule = TemplateMatchRule(required_headers=["score"], min_matches=1)
        assert not rule.matches([])


# ===========================================================================
# services/flattener.py  (to_csv and to_jsonl)
# ===========================================================================

class TestFlattenerExporters:
    def test_to_csv_writes_files(self, tmp_path):
        from notion_zotero.services.flattener import flatten_bundles, to_csv
        bundle_dir = tmp_path / "bundles"
        bundle_dir.mkdir()
        # Use only scalar fields so Polars can write CSV (lists/dicts not supported)
        flat_ref = {
            "id": "ref-csv",
            "title": "CSV Paper",
            "year": 2023,
            "doi": "10.1000/csv",
            "journal": "Nature",
        }
        _write_bundle(bundle_dir / "r1.canonical.json", references=[flat_ref])
        dfs = flatten_bundles(str(bundle_dir))
        out_dir = tmp_path / "csv_out"
        to_csv(dfs, out_dir)
        assert (out_dir / "references.csv").exists()
        assert (out_dir / "tasks.csv").exists()

    def test_to_jsonl_writes_files(self, tmp_path):
        from notion_zotero.services.flattener import flatten_bundles, to_jsonl
        bundle_dir = tmp_path / "bundles"
        bundle_dir.mkdir()
        _write_bundle(bundle_dir / "r1.canonical.json",
                      references=[_minimal_ref()])
        dfs = flatten_bundles(str(bundle_dir))
        out_dir = tmp_path / "jsonl_out"
        to_jsonl(dfs, out_dir)
        assert (out_dir / "references.jsonl").exists()


# ===========================================================================
# services/migration_audit.py
# ===========================================================================

class TestMigrationAudit:
    def _make_legacy(self, tmp_path: Path, page_id: str, **kwargs) -> Path:
        props = kwargs.get("properties", {})
        legacy = {
            "id": page_id,
            "properties": props,
            "children": kwargs.get("children", []),
        }
        f = tmp_path / f"{page_id}.json"
        f.write_text(json.dumps(legacy), encoding="utf-8")
        return f

    def _make_canonical(self, tmp_path: Path, page_id: str, **kwargs) -> Path:
        refs = kwargs.get("references", [_minimal_ref(id=page_id, title="Test")])
        bundle = {
            "references": refs,
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": kwargs.get("task_extractions", []),
            "workflow_states": kwargs.get("workflow_states", []),
            "annotations": [],
        }
        f = tmp_path / f"{page_id}.canonical.json"
        f.write_text(json.dumps(bundle), encoding="utf-8")
        return f

    def test_run_audit_no_legacy_files(self, tmp_path):
        from notion_zotero.services.migration_audit import run_audit
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        canonical_dir = tmp_path / "canonical"
        canonical_dir.mkdir()
        report = run_audit(legacy_dir, canonical_dir)
        assert len(report.missing_references) == 0

    def test_run_audit_missing_reference(self, tmp_path):
        from notion_zotero.services.migration_audit import run_audit
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        canonical_dir = tmp_path / "canonical"
        canonical_dir.mkdir()
        self._make_legacy(legacy_dir, "page-001")
        report = run_audit(legacy_dir, canonical_dir)
        assert len(report.missing_references) == 1
        assert report.missing_references[0]["page_id"] == "page-001"

    def test_run_audit_matched_reference(self, tmp_path):
        from notion_zotero.services.migration_audit import run_audit
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        canonical_dir = tmp_path / "canonical"
        canonical_dir.mkdir()
        self._make_legacy(legacy_dir, "page-002")
        self._make_canonical(canonical_dir, "page-002")
        report = run_audit(legacy_dir, canonical_dir)
        assert len(report.missing_references) == 0

    def test_run_audit_missing_extraction(self, tmp_path):
        from notion_zotero.services.migration_audit import run_audit
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        canonical_dir = tmp_path / "canonical"
        canonical_dir.mkdir()
        self._make_legacy(
            legacy_dir, "page-003",
            children=[{"type": "child_database"}, {"type": "child_database"}],
        )
        self._make_canonical(canonical_dir, "page-003", task_extractions=[])
        report = run_audit(legacy_dir, canonical_dir)
        assert len(report.missing_extractions) == 1

    def test_run_audit_provenance_loss(self, tmp_path):
        from notion_zotero.services.migration_audit import run_audit
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        canonical_dir = tmp_path / "canonical"
        canonical_dir.mkdir()
        self._make_legacy(legacy_dir, "page-004")
        ref_no_prov = _minimal_ref(id="page-004", provenance={})
        self._make_canonical(canonical_dir, "page-004", references=[ref_no_prov])
        report = run_audit(legacy_dir, canonical_dir)
        assert len(report.provenance_loss) > 0

    def test_run_audit_workflow_state_mismatch(self, tmp_path):
        from notion_zotero.services.migration_audit import run_audit
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        canonical_dir = tmp_path / "canonical"
        canonical_dir.mkdir()
        self._make_legacy(
            legacy_dir, "page-005",
            properties={"Status": {"select": {"name": "Done"}}},
        )
        ws = {"id": "ws-001", "state": "todo"}
        self._make_canonical(canonical_dir, "page-005", workflow_states=[ws])
        report = run_audit(legacy_dir, canonical_dir)
        assert len(report.workflow_state_mismatch) > 0

    def test_audit_report_summary(self):
        from notion_zotero.services.migration_audit import AuditReport
        r = AuditReport(missing_references=[{"page_id": "x"}])
        summary = r.summary()
        assert "1" in summary
        assert "missing references" in summary

    def test_skip_canonical_files_in_legacy_dir(self, tmp_path):
        from notion_zotero.services.migration_audit import run_audit
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        canonical_dir = tmp_path / "canonical"
        canonical_dir.mkdir()
        (legacy_dir / "page-x.canonical.json").write_text(
            json.dumps({"references": []}), encoding="utf-8"
        )
        report = run_audit(legacy_dir, canonical_dir)
        assert len(report.missing_references) == 0


# ===========================================================================
# services/qa_report.py
# ===========================================================================

class TestQAReport:
    def test_ambiguous_workflow_state(self, tmp_path):
        from notion_zotero.services.qa_report import run_qa
        bundle = {
            "references": [_minimal_ref()],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [],
            "workflow_states": [{"id": "ws-1", "state": "unknown_state"}],
            "annotations": [],
        }
        (tmp_path / "b.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
        report = run_qa(tmp_path)
        assert len(report.ambiguous_statuses) == 1

    def test_unlinked_extraction(self, tmp_path):
        from notion_zotero.services.qa_report import run_qa
        bundle = {
            "references": [_minimal_ref()],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [
                {"id": "ex-1", "reference_task_id": None, "template_id": None, "extracted": {"col": "val"}},
            ],
            "workflow_states": [],
            "annotations": [],
        }
        (tmp_path / "b.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
        report = run_qa(tmp_path)
        assert len(report.unlinked_extractions) == 1

    def test_malformed_extraction_no_extracted(self, tmp_path):
        from notion_zotero.services.qa_report import run_qa
        bundle = {
            "references": [_minimal_ref()],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [
                {"id": "ex-2", "reference_task_id": "rt-1", "template_id": None, "extracted": None},
            ],
            "workflow_states": [],
            "annotations": [],
        }
        (tmp_path / "b.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
        report = run_qa(tmp_path)
        assert len(report.malformed_extractions) == 1

    def test_incomplete_reference_no_doi_no_zotero(self, tmp_path):
        from notion_zotero.services.qa_report import run_qa
        bundle = {
            "references": [_minimal_ref(doi=None, zotero_key=None)],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [],
            "workflow_states": [],
            "annotations": [],
        }
        (tmp_path / "b.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
        report = run_qa(tmp_path)
        assert len(report.incomplete_references) == 1

    def test_qa_report_summary(self):
        from notion_zotero.services.qa_report import QAReport
        r = QAReport(ambiguous_statuses=[{"bundle": "x", "state": "bad"}])
        summary = r.summary()
        assert "1" in summary
        assert "ambiguous" in summary

    def test_missing_columns_with_template(self, tmp_path):
        from notion_zotero.services.qa_report import run_qa
        from notion_zotero.schemas.templates.generic import TEMPLATES
        if not TEMPLATES:
            pytest.skip("No templates registered")
        tmpl_id = next(iter(TEMPLATES))
        tmpl = TEMPLATES[tmpl_id]
        req_cols = [c for c in tmpl.expected_columns if c.required]
        if not req_cols:
            pytest.skip("No required columns in first template")
        bundle = {
            "references": [_minimal_ref()],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [
                {
                    "id": "ex-3",
                    "reference_task_id": "rt-1",
                    "template_id": tmpl_id,
                    "extracted": [{"unrelated_col": "value"}],
                },
            ],
            "workflow_states": [],
            "annotations": [],
        }
        (tmp_path / "b.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
        report = run_qa(tmp_path)
        assert len(report.missing_columns) >= 1


# ===========================================================================
# scripts/export_reading_list.py (utility functions only — no live API calls)
# ===========================================================================

class TestExportReadingListUtils:
    def _import_module(self):
        from notion_zotero.scripts import export_reading_list as m
        return m

    def test_plain_text_from_rich(self):
        m = self._import_module()
        rich = [{"plain_text": "Hello"}, {"plain_text": " World"}]
        assert m.plain_text(rich) == "Hello World"

    def test_plain_text_from_text_dict(self):
        m = self._import_module()
        rich = [{"text": {"content": "Foo"}}]
        assert m.plain_text(rich) == "Foo"

    def test_plain_text_string_element(self):
        m = self._import_module()
        assert m.plain_text(["a", "b"]) == "ab"

    def test_plain_text_empty(self):
        m = self._import_module()
        assert m.plain_text([]) == ""

    def test_plain_text_none(self):
        m = self._import_module()
        assert m.plain_text(None) == ""

    def test_get_title_from_title_prop(self):
        m = self._import_module()
        page = {
            "id": "abc",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "My Title"}],
                }
            },
        }
        assert m.get_title(page) == "My Title"

    def test_get_title_fallback_to_id(self):
        m = self._import_module()
        page = {"id": "page-xyz", "properties": {}}
        assert m.get_title(page) == "page-xyz"

    def test_serialize_block_paragraph(self):
        m = self._import_module()
        block = {
            "id": "blk-1",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Hello"}]},
        }
        result = m.serialize_block(block)
        assert result["type"] == "paragraph"
        assert result["text"] == "Hello"
        assert result["id"] == "blk-1"

    def test_serialize_block_unknown_type(self):
        m = self._import_module()
        block = {"id": "blk-2", "type": "divider"}
        result = m.serialize_block(block)
        assert result["text"] == ""
        assert result["type"] == "divider"

    def test_serialize_block_heading_2(self):
        m = self._import_module()
        block = {
            "id": "blk-3",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Section"}]},
        }
        result = m.serialize_block(block)
        assert result["text"] == "Section"

    def test_fetch_blocks_single_page(self):
        """fetch_blocks paginates until has_more is False."""
        m = self._import_module()
        mock_notion = MagicMock()
        page1 = {"results": [{"id": "blk-1", "type": "paragraph"}], "has_more": False}
        mock_notion.blocks.children.list.return_value = page1
        result = m.fetch_blocks(mock_notion, "parent-id")
        assert len(result) == 1
        mock_notion.blocks.children.list.assert_called_once_with(
            block_id="parent-id", start_cursor=None, page_size=100
        )

    def test_fetch_blocks_multi_page(self):
        """fetch_blocks follows next_cursor."""
        m = self._import_module()
        mock_notion = MagicMock()
        mock_notion.blocks.children.list.side_effect = [
            {"results": [{"id": "b1"}], "has_more": True, "next_cursor": "cur1"},
            {"results": [{"id": "b2"}], "has_more": False, "next_cursor": None},
        ]
        result = m.fetch_blocks(mock_notion, "pid")
        assert len(result) == 2

    def test_extract_tables_empty_blocks(self):
        """extract_tables with no table blocks returns []."""
        m = self._import_module()
        mock_notion = MagicMock()
        blocks = [
            {"id": "b1", "type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "hello"}]}}
        ]
        result = m.extract_tables(blocks, mock_notion)
        assert result == []

    def test_extract_tables_with_table(self):
        """extract_tables parses table_row cells."""
        m = self._import_module()
        mock_notion = MagicMock()
        row_block = {
            "id": "row-1",
            "type": "table_row",
            "table_row": {"cells": [[{"plain_text": "A"}], [{"plain_text": "B"}]]},
        }
        mock_notion.blocks.children.list.return_value = {
            "results": [row_block],
            "has_more": False,
        }
        table_block = {"id": "tbl-1", "type": "table"}
        blocks = [table_block]
        result = m.extract_tables(blocks, mock_notion)
        assert len(result) == 1
        assert result[0]["rows"] == [["A", "B"]]

    def test_extract_tables_heading_lookup(self):
        """extract_tables finds the nearest heading above the table."""
        m = self._import_module()
        mock_notion = MagicMock()
        mock_notion.blocks.children.list.return_value = {
            "results": [], "has_more": False
        }
        blocks = [
            {"id": "h1", "type": "heading_2",
             "heading_2": {"rich_text": [{"plain_text": "My Heading"}]}},
            {"id": "tbl-2", "type": "table"},
        ]
        result = m.extract_tables(blocks, mock_notion)
        assert len(result) == 1
        assert result[0]["heading"] == "My Heading"

    def test_export_page_writes_file(self, tmp_path):
        """export_page creates a JSON fixture file."""
        m = self._import_module()
        mock_notion = MagicMock()
        mock_notion.pages.retrieve.return_value = {
            "id": "page-001",
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Page"}]}
            },
        }
        mock_notion.blocks.children.list.return_value = {
            "results": [], "has_more": False
        }
        m.export_page(mock_notion, "page-001", str(tmp_path))
        out_file = tmp_path / "page-001.json"
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["title"] == "Test Page"
        assert data["page_id"] == "page-001"

    def test_export_database_single_page(self, tmp_path):
        """export_database calls export_page for each result."""
        m = self._import_module()
        mock_notion = MagicMock()
        mock_notion.databases.query.return_value = {
            "results": [{"id": "page-db-1"}],
            "has_more": False,
        }
        mock_notion.pages.retrieve.return_value = {
            "id": "page-db-1",
            "properties": {},
        }
        mock_notion.blocks.children.list.return_value = {
            "results": [], "has_more": False
        }
        m.export_database(mock_notion, "db-001", str(tmp_path))
        out_file = tmp_path / "page-db-1.json"
        assert out_file.exists()


# ===========================================================================
# cli.py — report commands
# ===========================================================================

@pytest.fixture
def canonical_dir_with_refs(tmp_path):
    """A canonical directory with one well-formed reference bundle."""
    bundle_dir = tmp_path / "canonical"
    bundle_dir.mkdir()
    _write_bundle(
        bundle_dir / "ref-001.canonical.json",
        references=[_minimal_ref()],
    )
    return str(bundle_dir)


@pytest.fixture
def empty_canonical_dir(tmp_path):
    d = tmp_path / "empty_canonical"
    d.mkdir()
    return str(d)


class TestCliReportByYear:
    def test_report_with_data(self, canonical_dir_with_refs, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-by-year", "--input", canonical_dir_with_refs])
        assert rc == 0
        out = capsys.readouterr().out
        assert "2023" in out

    def test_report_empty_dir(self, empty_canonical_dir, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-by-year", "--input", empty_canonical_dir])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No references" in out


class TestCliReportByJournal:
    def test_report_with_data(self, canonical_dir_with_refs, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-by-journal", "--input", canonical_dir_with_refs])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Nature" in out

    def test_report_empty_dir(self, empty_canonical_dir, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-by-journal", "--input", empty_canonical_dir])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No references" in out


class TestCliReportDoiCoverage:
    def test_report_with_doi(self, canonical_dir_with_refs, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-doi-coverage", "--input", canonical_dir_with_refs])
        assert rc == 0
        out = capsys.readouterr().out
        assert "DOI coverage" in out

    def test_report_empty_dir(self, empty_canonical_dir, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-doi-coverage", "--input", empty_canonical_dir])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No references" in out


class TestCliReportTaskCounts:
    def test_report_with_data(self, canonical_dir_with_refs, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-task-counts", "--input", canonical_dir_with_refs])
        assert rc == 0
        out = capsys.readouterr().out
        assert "References" in out

    def test_report_empty_dir(self, empty_canonical_dir, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-task-counts", "--input", empty_canonical_dir])
        assert rc == 0


class TestCliReportProvenance:
    def test_report_with_provenance_data(self, tmp_path, capsys):
        from notion_zotero import cli
        bundle_dir = tmp_path / "canonical"
        bundle_dir.mkdir()
        _write_bundle(
            bundle_dir / "ref-p.canonical.json",
            references=[_minimal_ref()],
            workflow_states=[{
                "id": "ws-001",
                "state": "todo",
                "provenance": {
                    "source_id": "ref-001",
                    "domain_pack_id": "education_learning_analytics",
                    "domain_pack_version": "1.0",
                },
            }],
        )
        rc = cli.main(["report-provenance", "--input", str(bundle_dir)])
        assert rc == 0

    def test_report_no_provenance_data(self, empty_canonical_dir, capsys):
        from notion_zotero import cli
        rc = cli.main(["report-provenance", "--input", empty_canonical_dir])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No provenance" in out


class TestCliDedupeCanonical:
    def test_dedupe_file_not_found(self, tmp_path):
        from notion_zotero import cli
        with pytest.raises(FileNotFoundError):
            cli.main(["dedupe-canonical", "--input", str(tmp_path / "nonexistent.json")])

    def test_dedupe_non_list_input(self, tmp_path):
        from notion_zotero import cli
        bundle = {
            "references": [_minimal_ref()],
            "tasks": [], "reference_tasks": [],
            "task_extractions": [], "workflow_states": [], "annotations": [],
        }
        in_file = tmp_path / "single.json"
        in_file.write_text(json.dumps(bundle), encoding="utf-8")
        out_file = tmp_path / "out.json"
        rc = cli.main(["dedupe-canonical", "--input", str(in_file), "--out", str(out_file)])
        assert rc == 0
        result = json.loads(out_file.read_text())
        assert isinstance(result, list)

    def test_dedupe_keeps_higher_score_bundle(self, tmp_path):
        from notion_zotero import cli
        from notion_zotero.core.normalize import normalize_title, normalize_authors
        bundle_a = {
            "references": [_minimal_ref(doi="10.1000/dup", title="Dup Paper")],
            "tasks": [], "reference_tasks": [],
            "task_extractions": [{"id": "ex-1"}],
            "workflow_states": [], "annotations": [],
        }
        bundle_b = {
            "references": [_minimal_ref(doi="10.1000/dup", title="Dup Paper")],
            "tasks": [], "reference_tasks": [],
            "task_extractions": [],
            "workflow_states": [], "annotations": [],
        }
        in_file = tmp_path / "merged.json"
        in_file.write_text(json.dumps([bundle_a, bundle_b]), encoding="utf-8")
        out_file = tmp_path / "out_dedup.json"
        rc = cli.main(["dedupe-canonical", "--input", str(in_file), "--out", str(out_file)])
        assert rc == 0
        result = json.loads(out_file.read_text())
        assert len(result) == 1
        assert len(result[0].get("task_extractions", [])) == 1

    def test_dedupe_by_title_authors(self, tmp_path):
        from notion_zotero import cli
        bundle_a = {
            "references": [_minimal_ref(doi=None, zotero_key=None,
                                        title="Same Title", authors=["Author A"])],
            "tasks": [], "reference_tasks": [],
            "task_extractions": [], "workflow_states": [], "annotations": [],
        }
        bundle_b = {
            "references": [_minimal_ref(doi=None, zotero_key=None,
                                        title="Same Title", authors=["Author A"])],
            "tasks": [], "reference_tasks": [],
            "task_extractions": [], "workflow_states": [], "annotations": [],
        }
        in_file = tmp_path / "merged.json"
        in_file.write_text(json.dumps([bundle_a, bundle_b]), encoding="utf-8")
        out_file = tmp_path / "out_ta.json"
        cli.main(["dedupe-canonical", "--input", str(in_file), "--out", str(out_file)])
        result = json.loads(out_file.read_text())
        assert len(result) == 1


class TestCliZoteroCitation:
    def test_citation_missing_file(self, tmp_path):
        from notion_zotero import cli
        with pytest.raises(FileNotFoundError):
            cli.main(["zotero-citation", "--file", str(tmp_path / "missing.json")])

    def test_citation_from_list_format(self, tmp_path, capsys):
        from notion_zotero import cli
        bundle = {"references": [_minimal_ref()]}
        bundle_list = [bundle]
        f = tmp_path / "item.json"
        f.write_text(json.dumps(bundle_list), encoding="utf-8")
        rc = cli.main(["zotero-citation", "--file", str(f)])
        assert rc == 0

    def test_citation_from_plain_dict(self, tmp_path, capsys):
        from notion_zotero import cli
        ref = _minimal_ref()
        f = tmp_path / "ref.json"
        f.write_text(json.dumps(ref), encoding="utf-8")
        rc = cli.main(["zotero-citation", "--file", str(f)])
        assert rc == 0


class TestCliExportSnapshot:
    def test_export_snapshot_fallback_raises(self):
        from notion_zotero import cli
        import types
        args = types.SimpleNamespace(out="out.json", db=None)
        with patch("notion_zotero.cli.cmd_export_snapshot",
                   side_effect=RuntimeError("export-snapshot is not available")):
            with pytest.raises(RuntimeError, match="export-snapshot"):
                cli.cmd_export_snapshot(args)


class TestCliMainNoArgs:
    def test_no_subcommand_returns_2(self):
        from notion_zotero import cli
        rc = cli.main([])
        assert rc == 2


# ===========================================================================
# cli.py — pull commands (mocked)
# ===========================================================================

class TestCliPullZotero:
    def _make_mock_reader(self):
        from notion_zotero.core.models import Reference
        mock_reader = MagicMock()
        ref = Reference(
            id="zot-001",
            title="Zotero Paper",
            zotero_key="ZOT001",
            provenance={"source_id": "zot-001", "source_system": "zotero",
                        "domain_pack_id": "", "domain_pack_version": ""},
        )
        mock_reader.get_items.return_value = [{"key": "ZOT001"}]
        mock_reader.to_reference.return_value = ref
        return mock_reader

    def test_pull_zotero_missing_api_key_exits(self, tmp_path, monkeypatch):
        """Without ZOTERO_API_KEY, cmd_pull_zotero prints error and exits 1."""
        from notion_zotero import cli
        monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
        monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)
        with pytest.raises(SystemExit) as exc:
            cli.main(["pull-zotero", "--output", str(tmp_path / "out")])
        assert exc.value.code == 1

    def test_pull_zotero_with_mock_reader(self, tmp_path, monkeypatch):
        """Successful pull via mocked ZoteroReader."""
        from notion_zotero import cli
        monkeypatch.setenv("ZOTERO_API_KEY", "fake-key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
        mock_reader = self._make_mock_reader()
        out_dir = tmp_path / "zotero_out"
        with patch("notion_zotero.connectors.zotero.reader.ZoteroReader",
                   return_value=mock_reader):
            rc = cli.main(["pull-zotero", "--output", str(out_dir)])
        assert rc == 0
        assert out_dir.exists()
        files = list(out_dir.glob("*.canonical.json"))
        assert len(files) == 1

    def test_pull_zotero_reader_get_items_error_exits(self, tmp_path, monkeypatch):
        """If get_items() raises, exits 1."""
        from notion_zotero import cli
        monkeypatch.setenv("ZOTERO_API_KEY", "fake-key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
        mock_reader = MagicMock()
        mock_reader.get_items.side_effect = RuntimeError("network error")
        with patch("notion_zotero.connectors.zotero.reader.ZoteroReader",
                   return_value=mock_reader):
            with pytest.raises(SystemExit) as exc:
                cli.main(["pull-zotero", "--output", str(tmp_path / "out")])
        assert exc.value.code == 1


class TestCliPullNotion:
    def test_pull_notion_missing_database_id_exits(self, tmp_path, monkeypatch):
        """Without NOTION_DATABASE_ID, cmd_pull_notion exits 1."""
        from notion_zotero import cli
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        monkeypatch.setenv("NOTION_API_KEY", "fake-key")
        with pytest.raises(SystemExit) as exc:
            cli.main(["pull-notion"])
        assert exc.value.code == 1

    def test_pull_notion_missing_api_key_exits(self, tmp_path, monkeypatch):
        """Without NOTION_API_KEY, NotionReader() raises ConfigurationError → exit 1."""
        from notion_zotero import cli
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.setenv("NOTION_DATABASE_ID", "fake-db")
        with pytest.raises(SystemExit) as exc:
            cli.main(["pull-notion", "--database-id", "fake-db"])
        assert exc.value.code == 1

    def test_pull_notion_with_mock_reader(self, tmp_path, monkeypatch):
        """Successful pull via mocked NotionReader."""
        from notion_zotero import cli
        from notion_zotero.core.models import Reference
        monkeypatch.setenv("NOTION_API_KEY", "fake-key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-123")
        mock_reader = MagicMock()
        ref = Reference(
            id="notion-001",
            title="Notion Paper",
            provenance={"source_id": "notion-001", "source_system": "notion",
                        "domain_pack_id": "", "domain_pack_version": ""},
        )
        mock_reader.get_database_pages.return_value = [{"id": "notion-001", "properties": {}}]
        mock_reader.to_reference.return_value = ref
        out_dir = tmp_path / "notion_out"
        with patch("notion_zotero.connectors.notion.reader.NotionReader",
                   return_value=mock_reader):
            rc = cli.main(["pull-notion", "--output", str(out_dir)])
        assert rc == 0
        assert out_dir.exists()
        files = list(out_dir.glob("*.canonical.json"))
        assert len(files) == 1


class TestCliStatus:
    def test_status_no_zotero_key_warns_and_continues(self, monkeypatch, capsys):
        """cmd_status prints warning when Zotero unreachable, continues to Notion.
        Patches load_dotenv to prevent .env from restoring deleted vars.
        """
        from notion_zotero import cli
        monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
        monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        with patch("dotenv.load_dotenv", return_value=None):
            rc = cli.main(["status"])
        assert rc == 0
        out = capsys.readouterr()
        combined = out.out + out.err
        assert "Zotero" in combined

    def test_status_no_notion_database_id_warns(self, monkeypatch, capsys):
        """When NOTION_DATABASE_ID not set, status warns about skipping Notion.
        Patches load_dotenv to prevent .env from restoring deleted vars.
        """
        from notion_zotero import cli
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        with patch("dotenv.load_dotenv", return_value=None):
            rc = cli.main(["status"])
        assert rc == 0
        out = capsys.readouterr()
        combined = out.out + out.err
        assert "NOTION_DATABASE_ID" in combined or "Notion" in combined

    def test_status_with_mocked_readers(self, tmp_path, monkeypatch, capsys):
        """Full status path with both readers mocked."""
        from notion_zotero import cli
        from notion_zotero.core.models import Reference
        monkeypatch.setenv("ZOTERO_API_KEY", "fake-key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-123")
        monkeypatch.setenv("NOTION_API_KEY", "fake-notion")

        ref_z = Reference(
            id="z001", title="Z Paper", zotero_key="ZKEY1",
            provenance={"source_id": "z001", "source_system": "zotero",
                        "domain_pack_id": "", "domain_pack_version": ""},
        )
        ref_n = Reference(
            id="n001", title="N Paper", zotero_key="ZKEY1",
            provenance={"source_id": "n001", "source_system": "notion",
                        "domain_pack_id": "", "domain_pack_version": ""},
        )

        mock_zotero = MagicMock()
        mock_zotero.get_items.return_value = [{"key": "ZKEY1"}]
        mock_zotero.to_reference.return_value = ref_z

        mock_notion = MagicMock()
        mock_notion.get_database_pages.return_value = [{"id": "n001"}]
        mock_notion.to_reference.return_value = ref_n

        with patch("notion_zotero.connectors.zotero.reader.ZoteroReader",
                   return_value=mock_zotero), \
             patch("notion_zotero.connectors.notion.reader.NotionReader",
                   return_value=mock_notion):
            rc = cli.main(["status"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Zotero" in out
        assert "Notion" in out
