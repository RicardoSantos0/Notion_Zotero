"""Smoke tests for pull-zotero, pull-notion, and status CLI commands.

These exercises mock external connectors and are considered integration/smoke.
"""
from __future__ import annotations

import json
import types
import unittest.mock
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs):
    """Build a simple namespace mirroring argparse output."""
    defaults = {
        "output": None,
        "limit": None,
        "database_id": None,
        "zotero_limit": None,
        "notion_database_id": None,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _fake_reference(ref_id="REF001", zotero_key="REF001", title="Test Paper"):
    from notion_zotero.core.models import Reference

    return Reference(
        id=ref_id,
        title=title,
        zotero_key=zotero_key,
        provenance={"source_id": ref_id, "source_system": "zotero", "domain_pack_id": "", "domain_pack_version": ""},
        sync_metadata={},
    )


# ---------------------------------------------------------------------------
# pull-zotero
# ---------------------------------------------------------------------------


def test_pull_zotero_no_api_key_raises(monkeypatch, tmp_path, capsys):
    """cmd_pull_zotero without env vars exits with an error message."""
    monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
    monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)

    # Prevent dotenv from loading a real .env
    with unittest.mock.patch("dotenv.load_dotenv"):
        from notion_zotero.cli import cmd_pull_zotero

        with pytest.raises(SystemExit):
            cmd_pull_zotero(_make_args(output=str(tmp_path)))

    captured = capsys.readouterr()
    assert "Error" in captured.err


def test_pull_zotero_saves_bundle_files(monkeypatch, tmp_path):
    """cmd_pull_zotero writes one .canonical.json per reference."""
    monkeypatch.setenv("ZOTERO_API_KEY", "fake-key")
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "12345")

    raw_item = {"key": "REF001", "data": {"title": "Test Paper", "creators": [], "tags": []}}
    fake_ref = _fake_reference()

    with unittest.mock.patch("dotenv.load_dotenv"):
        with unittest.mock.patch(
            "notion_zotero.connectors.zotero.reader.ZoteroReader.get_items",
            return_value=[raw_item],
        ):
            with unittest.mock.patch(
                "notion_zotero.connectors.zotero.reader.ZoteroReader.to_reference",
                return_value=fake_ref,
            ):
                from notion_zotero.cli import cmd_pull_zotero
                cmd_pull_zotero(_make_args(output=str(tmp_path), limit=10))

    files = list(tmp_path.glob("*.canonical.json"))
    assert len(files) == 1
    bundle = json.loads(files[0].read_text(encoding="utf-8"))
    assert "references" in bundle
    assert bundle["references"][0]["id"] == "REF001"
    assert bundle["tasks"] == []
    assert bundle["workflow_states"] == []


# ---------------------------------------------------------------------------
# pull-notion
# ---------------------------------------------------------------------------


def test_pull_notion_no_api_key_raises(monkeypatch, tmp_path, capsys):
    """cmd_pull_notion without env vars exits with an error message."""
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    with unittest.mock.patch("dotenv.load_dotenv"):
        from notion_zotero.cli import cmd_pull_notion

        with pytest.raises(SystemExit):
            cmd_pull_notion(_make_args(output=str(tmp_path), database_id="fake-db"))

    captured = capsys.readouterr()
    assert "Error" in captured.err


def test_pull_notion_saves_bundle_files(monkeypatch, tmp_path):
    """cmd_pull_notion writes one .canonical.json per reference."""
    monkeypatch.setenv("NOTION_API_KEY", "fake-key")
    monkeypatch.setenv("NOTION_DATABASE_ID", "fake-db-id")

    raw_page = {"id": "page-001", "properties": {}}
    fake_ref = _fake_reference(ref_id="page-001", zotero_key=None, title="Notion Paper")
    fake_ref = type(fake_ref)(
        id="page-001",
        title="Notion Paper",
        zotero_key=None,
        provenance={"source_id": "page-001", "source_system": "notion", "domain_pack_id": "", "domain_pack_version": ""},
        sync_metadata={},
    )

    with unittest.mock.patch("dotenv.load_dotenv"):
        with unittest.mock.patch(
            "notion_zotero.connectors.notion.reader.NotionReader.__init__",
            return_value=None,
        ):
            with unittest.mock.patch(
                "notion_zotero.connectors.notion.reader.NotionReader.get_database_pages",
                return_value=[raw_page],
            ):
                with unittest.mock.patch(
                    "notion_zotero.connectors.notion.reader.NotionReader.to_reference",
                    return_value=fake_ref,
                ):
                    from notion_zotero.cli import cmd_pull_notion
                    cmd_pull_notion(_make_args(output=str(tmp_path), database_id="fake-db-id"))

    files = list(tmp_path.glob("*.canonical.json"))
    assert len(files) == 1
    bundle = json.loads(files[0].read_text(encoding="utf-8"))
    assert bundle["references"][0]["id"] == "page-001"


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_no_api_key_raises(monkeypatch, capsys):
    """cmd_status with no env vars prints a warning but does not crash."""
    monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
    monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    with unittest.mock.patch("dotenv.load_dotenv"):
        from notion_zotero.cli import cmd_status
        # Should not raise — warns and prints partial status
        cmd_status(_make_args())

    captured = capsys.readouterr()
    # Should have printed something to stdout about Zotero/Notion
    assert "Zotero" in captured.out or "Warning" in captured.err
