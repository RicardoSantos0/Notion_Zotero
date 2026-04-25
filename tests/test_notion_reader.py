"""T-009 — Unit tests for NotionReader (no real HTTP)."""
from __future__ import annotations

import os
import unittest.mock
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_notion_reader(api_key="fake-key"):
    """Construct NotionReader with a patched notion_client.Client."""
    with patch("notion_client.Client"):
        from notion_zotero.connectors.notion.reader import NotionReader
        return NotionReader(api_key=api_key)


def _make_page(page_id="page-001", zotero_key=None, title="Test Paper"):
    props = {
        "Title": {
            "type": "title",
            "title": [{"plain_text": title}],
        },
        "Authors": {
            "rich_text": [{"plain_text": "Smith, J; Doe, A"}],
        },
        "Year": {
            "number": 2023,
        },
        "Journal": {
            "rich_text": [{"plain_text": "Nature"}],
        },
        "DOI": {
            "rich_text": [{"plain_text": "10.1000/xyz"}],
        },
    }
    if zotero_key:
        props["Zotero_key"] = {"rich_text": [{"plain_text": zotero_key}]}
    return {"id": page_id, "properties": props}


# ---------------------------------------------------------------------------
# T-009-1: single page (no pagination)
# ---------------------------------------------------------------------------

def test_get_database_pages_single_page():
    reader = _make_notion_reader()
    fake_pages = [{"id": f"page-{i}"} for i in range(10)]
    reader._client.databases.query.return_value = {
        "results": fake_pages,
        "has_more": False,
        "next_cursor": None,
    }

    result = reader.get_database_pages("db-id")

    assert len(result) == 10
    reader._client.databases.query.assert_called_once_with(
        database_id="db-id", page_size=100
    )


# ---------------------------------------------------------------------------
# T-009-2: multi-page pagination
# ---------------------------------------------------------------------------

def test_get_database_pages_multi_page():
    reader = _make_notion_reader()
    page1_items = [{"id": f"p1-{i}"} for i in range(5)]
    page2_items = [{"id": f"p2-{i}"} for i in range(3)]

    reader._client.databases.query.side_effect = [
        {"results": page1_items, "has_more": True, "next_cursor": "cursor1"},
        {"results": page2_items, "has_more": False, "next_cursor": None},
    ]

    result = reader.get_database_pages("db-id")

    assert len(result) == 8
    assert result[:5] == page1_items
    assert result[5:] == page2_items

    calls = reader._client.databases.query.call_args_list
    assert calls[0] == call(database_id="db-id", page_size=100)
    assert calls[1] == call(database_id="db-id", page_size=100, start_cursor="cursor1")


# ---------------------------------------------------------------------------
# T-009-3: retry on 429
# ---------------------------------------------------------------------------

def test_get_database_pages_retry_on_429():
    """First call raises APIResponseError(429), second succeeds."""
    from notion_zotero.connectors.notion.reader import NotionReader

    mock_response = MagicMock()
    mock_response.json.return_value = {"retry_after": 0.001}

    try:
        from notion_client.errors import APIResponseError
        exc_429 = APIResponseError.__new__(APIResponseError)
        exc_429.status = 429
        exc_429.response = mock_response
    except Exception:
        # Fallback: build a duck-typed exception
        class _FakeAPIError(Exception):
            pass
        exc_429 = _FakeAPIError()
        exc_429.status = 429
        exc_429.response = mock_response
        APIResponseError = _FakeAPIError

    fake_pages = [{"id": "page-1"}]

    # Patch at the client level inside a fresh reader to avoid import ordering issues
    with patch("notion_client.Client"):
        reader = NotionReader(api_key="fake-key")

    reader._client.databases.query.side_effect = [
        exc_429,
        {"results": fake_pages, "has_more": False, "next_cursor": None},
    ]

    # Patch wait to near-zero so the test is fast
    with patch("notion_zotero.connectors.notion.reader._notion_retry_wait", return_value=0.001):
        with patch("notion_client.errors.APIResponseError", APIResponseError):
            # Rebuild with patched error class
            try:
                result = reader.get_database_pages("db-id")
            except Exception:
                # If retry config uses the patched class, re-import and rerun
                reader._client.databases.query.side_effect = [
                    exc_429,
                    {"results": fake_pages, "has_more": False, "next_cursor": None},
                ]
                result = reader.get_database_pages("db-id")

    assert len(result) == 1


# ---------------------------------------------------------------------------
# T-009-4: get_page returns dict
# ---------------------------------------------------------------------------

def test_get_page_returns_dict():
    reader = _make_notion_reader()
    expected = {"id": "page-abc", "properties": {}}
    reader._client.pages.retrieve.return_value = expected

    result = reader.get_page("page-abc")

    assert result == expected
    reader._client.pages.retrieve.assert_called_once_with(page_id="page-abc")


# ---------------------------------------------------------------------------
# T-009-5: raises ConfigurationError without API key
# ---------------------------------------------------------------------------

def test_notion_reader_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    from notion_zotero.connectors.notion.reader import NotionReader
    from notion_zotero.core.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="NOTION_API_KEY"):
        NotionReader()


# ---------------------------------------------------------------------------
# T-009-6: to_reference field mapping
# ---------------------------------------------------------------------------

def test_to_reference_maps_fields():
    reader = _make_notion_reader()
    page = _make_page(page_id="page-xyz", title="My Paper")

    ref = reader.to_reference(page)

    assert ref.title == "My Paper"
    assert ref.year == 2023
    assert ref.journal == "Nature"
    assert ref.doi == "10.1000/xyz"
    assert "Smith" in ref.authors[0]
    assert "Doe" in ref.authors[1]
    assert ref.provenance["source_id"] == "page-xyz"
    assert ref.provenance["source_system"] == "notion"
