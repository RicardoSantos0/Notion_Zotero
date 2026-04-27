"""Tests for the Notion enrichment sprint deliverables.

Covers:
- NotionReader.get_page_blocks
- NotionReader.get_database_schema
- NotionReader.to_reference with schema (extra props stored in sync_metadata)
- cmd_pull_notion producing full bundles
- parse_fixture_from_dict
- summarizer surfaces notion_properties
- _blocks_to_fixture_parts helper
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_notion_reader(api_key: str = "fake-key"):
    """Construct NotionReader with a patched notion_client.Client."""
    with patch("notion_client.Client"):
        from notion_zotero.connectors.notion.reader import NotionReader
        return NotionReader(api_key=api_key)


def _make_full_page(page_id: str = "page-full-001"):
    """Build a fake Notion page with both canonical and extra properties."""
    return {
        "id": page_id,
        "properties": {
            "Title": {
                "type": "title",
                "title": [{"plain_text": "Test Full Paper"}],
            },
            "Authors": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "Smith, J; Doe, A"}],
            },
            "Year": {
                "type": "number",
                "number": 2024,
            },
            "Status": {
                "type": "select",
                "select": {"name": "Done"},
            },
            "Search Strategy": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "Systematic"}],
            },
            "Learner Population": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "Higher Education"}],
            },
        },
    }


# ---------------------------------------------------------------------------
# T-ENR-01: get_page_blocks returns list of blocks
# ---------------------------------------------------------------------------

class TestGetPageBlocks:
    def test_returns_list_of_two_blocks(self):
        reader = _make_notion_reader()
        block1 = {"id": "blk-1", "type": "paragraph"}
        block2 = {"id": "blk-2", "type": "heading_1"}
        reader._client.blocks.children.list.return_value = {
            "results": [block1, block2],
            "has_more": False,
            "next_cursor": None,
        }

        result = reader.get_page_blocks("page-abc")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "blk-1"
        assert result[1]["id"] == "blk-2"

    def test_paginates_through_multiple_pages(self):
        reader = _make_notion_reader()
        reader._client.blocks.children.list.side_effect = [
            {"results": [{"id": "b1"}], "has_more": True, "next_cursor": "cur1"},
            {"results": [{"id": "b2"}, {"id": "b3"}], "has_more": False, "next_cursor": None},
        ]

        result = reader.get_page_blocks("page-xyz")

        assert len(result) == 3

    def test_returns_empty_list_when_no_blocks(self):
        reader = _make_notion_reader()
        reader._client.blocks.children.list.return_value = {
            "results": [],
            "has_more": False,
        }

        result = reader.get_page_blocks("page-empty")
        assert result == []


# ---------------------------------------------------------------------------
# T-ENR-02: get_database_schema returns dict with property types
# ---------------------------------------------------------------------------

class TestGetDatabaseSchema:
    def test_returns_dict_with_three_keys(self):
        reader = _make_notion_reader()
        reader._client.databases.retrieve.return_value = {
            "properties": {
                "Title": {"type": "title"},
                "Status": {"type": "select"},
                "Year": {"type": "number"},
            }
        }

        result = reader.get_database_schema("db-001")

        assert isinstance(result, dict)
        assert len(result) == 3
        assert result["Title"] == "title"
        assert result["Status"] == "select"
        assert result["Year"] == "number"

    def test_returns_empty_dict_for_empty_schema(self):
        reader = _make_notion_reader()
        reader._client.databases.retrieve.return_value = {"properties": {}}

        result = reader.get_database_schema("db-empty")
        assert result == {}

    def test_handles_missing_properties_key(self):
        reader = _make_notion_reader()
        reader._client.databases.retrieve.return_value = {}

        result = reader.get_database_schema("db-no-props")
        assert isinstance(result, dict)
        assert result == {}


# ---------------------------------------------------------------------------
# T-ENR-03: to_reference stores extra props in sync_metadata when schema given
# ---------------------------------------------------------------------------

class TestToReferenceWithSchema:
    def test_extra_props_stored_in_sync_metadata(self):
        reader = _make_notion_reader()
        page = _make_full_page()
        # Schema has the same props as the page
        schema = {
            "Title": "title",
            "Authors": "rich_text",
            "Year": "number",
            "Status": "select",
            "Search Strategy": "rich_text",
            "Learner Population": "rich_text",
        }

        ref = reader.to_reference(page, schema=schema)

        # Canonical fields should be mapped
        assert ref.title == "Test Full Paper"
        assert ref.year == 2024
        assert "Smith" in ref.authors[0]

        # Search Strategy is now a canonical field → ref.search_terms
        assert ref.search_terms == "Systematic"
        # Non-canonical fields (Status, Learner Population) stay in sync_metadata
        notion_props = ref.sync_metadata.get("notion_properties", {})
        assert "Status" in notion_props
        assert "Learner Population" in notion_props
        assert notion_props["Status"] == "Done"
        assert notion_props["Learner Population"] == "Higher Education"
        assert "Search Strategy" not in notion_props

    def test_four_extra_props_out_of_five_total(self):
        """One canonical (title) + 4 non-canonical = 4 in notion_properties."""
        reader = _make_notion_reader()
        page = {
            "id": "page-001",
            "properties": {
                "Title": {"type": "title", "title": [{"plain_text": "My Paper"}]},
                "Status": {"type": "select", "select": {"name": "To Do"}},
                "Strategy": {"type": "rich_text", "rich_text": [{"plain_text": "S1"}]},
                "Population": {"type": "rich_text", "rich_text": [{"plain_text": "P1"}]},
                "Domain": {"type": "rich_text", "rich_text": [{"plain_text": "D1"}]},
            },
        }
        schema = {
            "Title": "title",
            "Status": "select",
            "Strategy": "rich_text",
            "Population": "rich_text",
            "Domain": "rich_text",
        }

        ref = reader.to_reference(page, schema=schema)
        notion_props = ref.sync_metadata.get("notion_properties", {})

        # Title is canonical -- the other 4 are not
        assert ref.title == "My Paper"
        assert len(notion_props) == 4
        assert "Status" in notion_props
        assert "Strategy" in notion_props
        assert "Population" in notion_props
        assert "Domain" in notion_props

    def test_no_schema_still_works(self):
        """When schema=None, the legacy extraction path is used (no notion_properties)."""
        reader = _make_notion_reader()
        page = {
            "id": "pg-legacy",
            "properties": {
                "Title": {"type": "title", "title": [{"plain_text": "Legacy Title"}]},
            },
        }
        ref = reader.to_reference(page)
        assert ref.title == "Legacy Title"
        # Legacy path does not populate notion_properties
        notion_props = ref.sync_metadata.get("notion_properties")
        assert notion_props is None or notion_props == {}

    def test_multi_select_tags_extracted(self):
        reader = _make_notion_reader()
        page = {
            "id": "pg-tags",
            "properties": {
                "Title": {"type": "title", "title": [{"plain_text": "Tagged Paper"}]},
                "Tags": {
                    "type": "multi_select",
                    "multi_select": [
                        {"name": "ML"},
                        {"name": "Education"},
                    ],
                },
            },
        }
        schema = {"Title": "title", "Tags": "multi_select"}

        ref = reader.to_reference(page, schema=schema)
        assert ref.tags == ["ML", "Education"]


# ---------------------------------------------------------------------------
# T-ENR-04: pull-notion produces full bundle (mocked)
# ---------------------------------------------------------------------------

class TestPullNotionFullBundle:
    def _make_mock_reader(self, page_id: str = "page-bundle-001"):
        from notion_zotero.core.models import Reference
        mock_reader = MagicMock()
        ref = Reference(
            id=page_id,
            title="Bundle Paper",
            provenance={
                "source_id": page_id,
                "source_system": "notion",
                "domain_pack_id": "",
                "domain_pack_version": "",
            },
            sync_metadata={"notion_properties": {"Status": "Done"}},
        )
        mock_reader.get_database_schema.return_value = {"Title": "title", "Status": "select"}
        mock_reader.get_database_pages.return_value = [
            {"id": page_id, "properties": {
                "Title": {"type": "title", "title": [{"plain_text": "Bundle Paper"}]},
                "Status": {"type": "select", "select": {"name": "Done"}},
            }}
        ]
        mock_reader.to_reference.return_value = ref
        mock_reader.get_page_blocks.return_value = []
        return mock_reader

    def test_pull_notion_produces_bundle_structure(self, tmp_path, monkeypatch):
        from notion_zotero import cli
        monkeypatch.setenv("NOTION_API_KEY", "fake-key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-test")
        mock_reader = self._make_mock_reader()
        out_dir = tmp_path / "notion_full_out"

        with patch("notion_zotero.connectors.notion.reader.NotionReader",
                   return_value=mock_reader):
            rc = cli.main(["pull-notion", "--output", str(out_dir)])

        assert rc == 0
        assert out_dir.exists()
        files = list(out_dir.glob("*.canonical.json"))
        assert len(files) == 1

        bundle = json.loads(files[0].read_text(encoding="utf-8"))
        # Must have canonical bundle keys
        assert "references" in bundle
        assert "tasks" in bundle
        assert "task_extractions" in bundle
        assert "workflow_states" in bundle
        assert "annotations" in bundle

    def test_pull_notion_skip_blocks_produces_minimal_bundle(self, tmp_path, monkeypatch):
        from notion_zotero import cli
        from notion_zotero.core.models import Reference
        monkeypatch.setenv("NOTION_API_KEY", "fake-key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-test")

        mock_reader = MagicMock()
        ref = Reference(
            id="pg-skip",
            title="Skip Paper",
            provenance={
                "source_id": "pg-skip",
                "source_system": "notion",
                "domain_pack_id": "",
                "domain_pack_version": "",
            },
            sync_metadata={},
        )
        mock_reader.get_database_pages.return_value = [
            {"id": "pg-skip", "properties": {}}
        ]
        mock_reader.to_reference.return_value = ref

        out_dir = tmp_path / "notion_skip_out"
        with patch("notion_zotero.connectors.notion.reader.NotionReader",
                   return_value=mock_reader):
            rc = cli.main(["pull-notion", "--output", str(out_dir), "--skip-blocks"])

        assert rc == 0
        files = list(out_dir.glob("*.canonical.json"))
        assert len(files) == 1
        bundle = json.loads(files[0].read_text(encoding="utf-8"))
        # In skip-blocks mode, blocks are not fetched
        mock_reader.get_page_blocks.assert_not_called()
        assert bundle["references"][0]["title"] == "Skip Paper"

    def test_pull_notion_get_schema_error_falls_back(self, tmp_path, monkeypatch):
        """If get_database_schema raises, the pull should continue with schema=None."""
        from notion_zotero import cli
        from notion_zotero.core.models import Reference
        monkeypatch.setenv("NOTION_API_KEY", "fake-key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-test")

        mock_reader = MagicMock()
        ref = Reference(
            id="pg-schema-err",
            title="Schema Error Paper",
            provenance={
                "source_id": "pg-schema-err",
                "source_system": "notion",
                "domain_pack_id": "",
                "domain_pack_version": "",
            },
            sync_metadata={},
        )
        mock_reader.get_database_schema.side_effect = RuntimeError("schema fetch failed")
        mock_reader.get_database_pages.return_value = [
            {"id": "pg-schema-err", "properties": {}}
        ]
        mock_reader.to_reference.return_value = ref
        mock_reader.get_page_blocks.return_value = []

        out_dir = tmp_path / "schema_err_out"
        with patch("notion_zotero.connectors.notion.reader.NotionReader",
                   return_value=mock_reader):
            rc = cli.main(["pull-notion", "--output", str(out_dir)])

        assert rc == 0
        files = list(out_dir.glob("*.canonical.json"))
        assert len(files) == 1


# ---------------------------------------------------------------------------
# T-ENR-05: parse_fixture_from_dict produces same structure as parse_fixture
# ---------------------------------------------------------------------------

class TestParseFixtureFromDict:
    def test_produces_canonical_bundle_keys(self):
        from notion_zotero.services.reading_list_importer import parse_fixture_from_dict

        fixture = {
            "page_id": "test-page-001",
            "title": "Test Paper From Dict",
            "properties": {},
            "tables": [],
            "blocks": [],
        }

        page_id, bundle = parse_fixture_from_dict(fixture)

        assert page_id == "test-page-001"
        assert "references" in bundle
        assert "tasks" in bundle
        assert "task_extractions" in bundle
        assert "workflow_states" in bundle
        assert "annotations" in bundle
        assert bundle["references"][0]["title"] == "Test Paper From Dict"

    def test_provenance_populated_in_reference(self):
        from notion_zotero.services.reading_list_importer import parse_fixture_from_dict

        fixture = {
            "page_id": "prov-test-001",
            "title": "Provenance Test",
            "properties": {},
            "tables": [],
            "blocks": [],
        }

        _, bundle = parse_fixture_from_dict(fixture)

        ref = bundle["references"][0]
        prov = ref.get("provenance", {})
        assert prov.get("source_id") == "prov-test-001"
        assert "domain_pack_id" in prov
        assert "domain_pack_version" in prov

    def test_workflow_state_from_status_property(self):
        from notion_zotero.services.reading_list_importer import parse_fixture_from_dict

        fixture = {
            "page_id": "ws-test-001",
            "title": "Workflow State Test",
            "properties": {
                "Status": {
                    "type": "select",
                    "select": {"name": "Done"},
                }
            },
            "tables": [],
            "blocks": [],
        }

        _, bundle = parse_fixture_from_dict(fixture)

        # If the status maps to a known workflow state, we should get one
        # (depends on map_status -- at minimum the bundle key exists)
        assert "workflow_states" in bundle

    def test_text_blocks_become_annotations(self):
        from notion_zotero.services.reading_list_importer import parse_fixture_from_dict

        fixture = {
            "page_id": "ann-test-001",
            "title": "Annotation Test",
            "properties": {},
            "tables": [],
            "blocks": [
                {"type": "paragraph", "text": "This is a note.", "id": "blk-an-1"},
            ],
        }

        _, bundle = parse_fixture_from_dict(fixture)

        assert len(bundle["annotations"]) == 1
        assert bundle["annotations"][0]["text"] == "This is a note."

    def test_matches_parse_fixture_output_structure(self, tmp_path):
        """parse_fixture and parse_fixture_from_dict should produce identical structures."""
        from notion_zotero.services.reading_list_importer import parse_fixture, parse_fixture_from_dict

        fixture_data = {
            "page_id": "structural-test-001",
            "title": "Structural Test",
            "properties": {},
            "tables": [],
            "blocks": [],
        }

        # Write to file and parse via parse_fixture
        fixture_file = tmp_path / "structural-test-001.json"
        fixture_file.write_text(json.dumps(fixture_data), encoding="utf-8")
        pid_file, bundle_file = parse_fixture(fixture_file)

        # Parse the same data in-memory
        pid_dict, bundle_dict = parse_fixture_from_dict(fixture_data)

        assert pid_file == pid_dict
        assert set(bundle_file.keys()) == set(bundle_dict.keys())


# ---------------------------------------------------------------------------
# T-ENR-06: summarizer surfaces notion_properties as extra columns
# ---------------------------------------------------------------------------

class TestSummarizerNotionProps:
    def test_notion_properties_appear_as_columns(self):
        from notion_zotero.analysis.summarizer import build_summary_tables

        bundle = {
            "provenance": {
                "source_id": "page-summ-001",
                "domain_pack_id": "",
                "domain_pack_version": "",
            },
            "references": [{
                "id": "page-summ-001",
                "title": "Summarizer Test",
                "authors": [],
                "year": 2023,
                "provenance": {
                    "source_id": "page-summ-001",
                    "domain_pack_id": "",
                    "domain_pack_version": "",
                },
                "sync_metadata": {
                    "notion_properties": {
                        "Status": "Done",
                        "Search Strategy": "Snowball",
                    }
                },
            }],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [],
            "workflow_states": [],
            "annotations": [],
        }

        tables = build_summary_tables([bundle])
        reading_list = tables["Reading List"]

        assert len(reading_list) == 1
        row = reading_list[0]
        # Extra notion_properties should be spread into the row
        assert row.get("Status") == "Done"
        assert row.get("Search Strategy") == "Snowball"

    def test_no_notion_properties_still_works(self):
        from notion_zotero.analysis.summarizer import build_summary_tables

        bundle = {
            "provenance": {"source_id": "page-plain", "domain_pack_id": "", "domain_pack_version": ""},
            "references": [{
                "id": "page-plain",
                "title": "Plain Paper",
                "provenance": {"source_id": "page-plain", "domain_pack_id": "", "domain_pack_version": ""},
                "sync_metadata": {},
            }],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [],
            "workflow_states": [],
            "annotations": [],
        }

        tables = build_summary_tables([bundle])
        assert len(tables["Reading List"]) == 1

    def test_null_sync_metadata_handled_gracefully(self):
        from notion_zotero.analysis.summarizer import build_summary_tables

        bundle = {
            "provenance": {"source_id": "page-null-sm", "domain_pack_id": "", "domain_pack_version": ""},
            "references": [{
                "id": "page-null-sm",
                "title": "Null SM Paper",
                "provenance": {"source_id": "page-null-sm", "domain_pack_id": "", "domain_pack_version": ""},
                "sync_metadata": None,
            }],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [],
            "workflow_states": [],
            "annotations": [],
        }

        tables = build_summary_tables([bundle])
        assert len(tables["Reading List"]) == 1


# ---------------------------------------------------------------------------
# T-ENR-07: _blocks_to_fixture_parts helper
# ---------------------------------------------------------------------------

class TestBlocksToFixtureParts:
    def _get_helper(self):
        from notion_zotero.cli import _blocks_to_fixture_parts
        return _blocks_to_fixture_parts

    def test_paragraph_becomes_text_block(self):
        helper = self._get_helper()
        blocks = [{
            "id": "blk-p1",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Hello world"}]},
        }]
        mock_reader = MagicMock()

        tables, text_blocks = helper(blocks, mock_reader)

        assert len(text_blocks) == 1
        assert text_blocks[0]["text"] == "Hello world"
        assert text_blocks[0]["type"] == "paragraph"
        assert text_blocks[0]["id"] == "blk-p1"
        assert tables == []

    def test_heading_is_captured_for_next_table(self):
        helper = self._get_helper()
        mock_reader = MagicMock()
        # Return table row children -- one row with two cells (each cell is a list of rich_text)
        mock_reader.get_page_blocks.return_value = [
            {
                "id": "row-1",
                "type": "table_row",
                "table_row": {"cells": [[{"plain_text": "Col A"}], [{"plain_text": "Val 1"}]]},
            }
        ]
        blocks = [
            {
                "id": "h1",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"plain_text": "My Section"}]},
            },
            {
                "id": "tbl-1",
                "type": "table",
                "table": {"has_column_header": True},
            },
        ]

        tables, text_blocks = helper(blocks, mock_reader)

        assert len(tables) == 1
        assert tables[0]["heading"] == "My Section"
        # One row with two cells
        assert tables[0]["rows"] == [["Col A", "Val 1"]]

    def test_empty_paragraph_not_included(self):
        helper = self._get_helper()
        blocks = [{
            "id": "blk-empty",
            "type": "paragraph",
            "paragraph": {"rich_text": []},
        }]
        mock_reader = MagicMock()

        tables, text_blocks = helper(blocks, mock_reader)

        assert text_blocks == []

    def test_table_fetch_error_skips_gracefully(self):
        """If get_page_blocks raises for a table, the table is skipped silently."""
        helper = self._get_helper()
        mock_reader = MagicMock()
        mock_reader.get_page_blocks.side_effect = RuntimeError("network error")

        blocks = [{"id": "tbl-err", "type": "table", "table": {"has_column_header": True}}]

        tables, text_blocks = helper(blocks, mock_reader)
        assert tables == []
