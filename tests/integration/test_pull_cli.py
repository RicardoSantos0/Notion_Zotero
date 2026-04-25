"""T-011 — Integration tests for pull-notion and pull-zotero CLI commands."""
from __future__ import annotations

import json
import unittest.mock
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_reference(ref_id="REF001", zotero_key="REF001", title="Test Paper"):
    from notion_zotero.core.models import Reference

    return Reference(
        id=ref_id,
        title=title,
        zotero_key=zotero_key,
        provenance={
            "source_id": ref_id,
            "source_system": "test",
            "domain_pack_id": "",
            "domain_pack_version": "",
        },
        sync_metadata={},
    )


def _fake_notion_pages(n=3):
    return [{"id": f"page-{i:03d}", "properties": {}} for i in range(n)]


def _fake_zotero_items(n=2):
    return [
        {"key": f"KEY{i:03d}", "data": {"key": f"KEY{i:03d}", "itemType": "journalArticle",
                                          "title": f"Paper {i}", "creators": [], "tags": []}}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# T-011-1: pull-notion writes canonical files
# ---------------------------------------------------------------------------


def test_pull_notion_writes_canonical_files(monkeypatch, tmp_path):
    monkeypatch.setenv("NOTION_API_KEY", "fake-key")
    monkeypatch.setenv("NOTION_DATABASE_ID", "fake-db-id")

    pages = _fake_notion_pages(3)
    refs = [_fake_reference(ref_id=f"page-{i:03d}", zotero_key=None, title=f"Paper {i}") for i in range(3)]
    # Fix: refs with no zotero_key use id as key
    for i, ref in enumerate(refs):
        object.__setattr__(ref, "zotero_key", None)

    out_dir = tmp_path / "pulled" / "notion"

    with patch("dotenv.load_dotenv"):
        with patch("notion_zotero.connectors.notion.reader.NotionReader.__init__", return_value=None):
            with patch(
                "notion_zotero.connectors.notion.reader.NotionReader.get_database_pages",
                return_value=pages,
            ):
                with patch(
                    "notion_zotero.connectors.notion.reader.NotionReader.to_reference",
                    side_effect=refs,
                ):
                    from notion_zotero.cli import main
                    rc = main(["pull-notion", "--database-id", "fake-db", "--output", str(out_dir)])

    files = list(out_dir.glob("*.canonical.json"))
    assert len(files) == 3


# ---------------------------------------------------------------------------
# T-011-2: pull-notion atomic write — staging cleaned on exception
# ---------------------------------------------------------------------------


def test_pull_notion_atomic_write_on_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("NOTION_API_KEY", "fake-key")
    monkeypatch.setenv("NOTION_DATABASE_ID", "fake-db-id")

    out_dir = tmp_path / "pulled" / "notion"
    staging_dir = out_dir.parent / (out_dir.name + "_staging")

    with patch("dotenv.load_dotenv"):
        with patch("notion_zotero.connectors.notion.reader.NotionReader.__init__", return_value=None):
            with patch(
                "notion_zotero.connectors.notion.reader.NotionReader.get_database_pages",
                side_effect=RuntimeError("simulated failure"),
            ):
                from notion_zotero.cli import main
                with pytest.raises(SystemExit) as exc_info:
                    main(["pull-notion", "--database-id", "fake-db", "--output", str(out_dir)])
                assert exc_info.value.code != 0

    # Final output dir must not exist (was never created successfully)
    assert not out_dir.exists()
    # Staging dir must have been cleaned up
    assert not staging_dir.exists()


# ---------------------------------------------------------------------------
# T-011-3: pull-zotero writes canonical files
# ---------------------------------------------------------------------------


def test_pull_zotero_writes_canonical_files(monkeypatch, tmp_path):
    monkeypatch.setenv("ZOTERO_API_KEY", "fake-key")
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "12345")

    items = _fake_zotero_items(2)
    refs = [
        _fake_reference(ref_id="KEY000", zotero_key="KEY000", title="Paper 0"),
        _fake_reference(ref_id="KEY001", zotero_key="KEY001", title="Paper 1"),
    ]

    out_dir = tmp_path / "pulled" / "zotero"

    with patch("dotenv.load_dotenv"):
        with patch(
            "notion_zotero.connectors.zotero.reader.ZoteroReader.get_items",
            return_value=items,
        ):
            with patch(
                "notion_zotero.connectors.zotero.reader.ZoteroReader.to_reference",
                side_effect=refs,
            ):
                from notion_zotero.cli import main
                main(["pull-zotero", "--output", str(out_dir)])

    files = list(out_dir.glob("*.canonical.json"))
    assert len(files) == 2


# ---------------------------------------------------------------------------
# T-011-4: pull-zotero exits non-zero when ZOTERO_LIBRARY_ID not set
# ---------------------------------------------------------------------------


def test_pull_zotero_missing_library_id_exits(monkeypatch, tmp_path):
    monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)
    monkeypatch.setenv("ZOTERO_API_KEY", "fake-key")

    out_dir = tmp_path / "pulled" / "zotero"

    with patch("dotenv.load_dotenv"):
        from notion_zotero.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main(["pull-zotero", "--output", str(out_dir)])

    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# T-011-5: pull-notion exits non-zero when database ID not provided at all
# ---------------------------------------------------------------------------


def test_pull_notion_missing_database_id_exits(monkeypatch, tmp_path):
    monkeypatch.setenv("NOTION_API_KEY", "fake-key")
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    out_dir = tmp_path / "pulled" / "notion"

    with patch("dotenv.load_dotenv"):
        from notion_zotero.cli import main
        with pytest.raises(SystemExit) as exc_info:
            # No --database-id flag, no NOTION_DATABASE_ID env var
            main(["pull-notion", "--output", str(out_dir)])

    assert exc_info.value.code != 0
