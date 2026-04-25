"""T-010 — Unit tests for ZoteroReader (no real HTTP)."""
from __future__ import annotations

import logging
import unittest.mock
from unittest.mock import MagicMock, patch, call

import pytest
import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_zotero_reader(api_key="fake-key", library_id="12345"):
    from notion_zotero.connectors.zotero.reader import ZoteroReader
    return ZoteroReader(api_key=api_key, library_id=library_id)


def _mock_response(items, total=None, status_code=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = items
    headers = {}
    if total is not None:
        headers["Total-Results"] = str(total)
    resp.headers = headers
    resp.raise_for_status.return_value = None
    return resp


def _make_journal_article(key="ABC123"):
    return {
        "key": key,
        "data": {
            "key": key,
            "itemType": "journalArticle",
            "title": "Deep Learning for Graphs",
            "creators": [
                {"lastName": "Smith", "firstName": "Jane"},
                {"lastName": "Doe", "firstName": "Alan"},
            ],
            "date": "2021-05-10",
            "DOI": "10.1000/test",
            "url": "https://example.com/paper",
            "abstractNote": "A study of graph networks.",
            "publicationTitle": "Journal of AI Research",
            "tags": [{"tag": "machine learning"}, {"tag": "graphs"}],
        },
    }


# ---------------------------------------------------------------------------
# T-010-1: single page — Total-Results present, no second call needed
# ---------------------------------------------------------------------------

def test_get_items_single_page():
    reader = _make_zotero_reader()
    items = [{"key": f"item-{i}"} for i in range(50)]
    resp = _mock_response(items, total=50)

    with patch("requests.get", return_value=resp) as mock_get:
        result = reader.get_items(limit=100)

    assert len(result) == 50
    assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# T-010-2: multi-page — three fetches totalling 250 items
# ---------------------------------------------------------------------------

def test_get_items_multi_page():
    reader = _make_zotero_reader()
    page1 = [{"key": f"p1-{i}"} for i in range(100)]
    page2 = [{"key": f"p2-{i}"} for i in range(100)]
    page3 = [{"key": f"p3-{i}"} for i in range(50)]

    resp1 = _mock_response(page1, total=250)
    resp2 = _mock_response(page2, total=250)
    resp3 = _mock_response(page3, total=250)

    with patch("requests.get", side_effect=[resp1, resp2, resp3]) as mock_get:
        result = reader.get_items(limit=100)

    assert len(result) == 250
    assert mock_get.call_count == 3


# ---------------------------------------------------------------------------
# T-010-3: fallback termination — no Total-Results header
# ---------------------------------------------------------------------------

def test_get_items_fallback_termination():
    reader = _make_zotero_reader()
    page1 = [{"key": f"p1-{i}"} for i in range(100)]
    page2 = [{"key": f"p2-{i}"} for i in range(30)]

    resp1 = _mock_response(page1, total=None)
    resp2 = _mock_response(page2, total=None)

    with patch("requests.get", side_effect=[resp1, resp2]):
        result = reader.get_items(limit=100)

    assert len(result) == 130


# ---------------------------------------------------------------------------
# T-010-4: retry on 429 — recovers after one 429
# ---------------------------------------------------------------------------

def test_get_items_retry_on_429():
    reader = _make_zotero_reader()
    items = [{"key": "item-0"}]

    mock_bad_response = MagicMock(spec=requests.Response)
    mock_bad_response.headers = {"Backoff": "0.001"}
    mock_bad_response.status_code = 429

    http_error = requests.HTTPError(response=mock_bad_response)

    good_resp = _mock_response(items, total=1)

    call_count = {"n": 0}
    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise http_error
        return good_resp

    with patch("requests.get", side_effect=side_effect):
        with patch("notion_zotero.connectors.zotero.reader._zotero_retry_wait", return_value=0.001):
            result = reader.get_items(limit=100)

    assert len(result) == 1


# ---------------------------------------------------------------------------
# T-010-5: retry exhausted — re-raises after 3 attempts
# ---------------------------------------------------------------------------

def test_get_items_retry_exhausted():
    reader = _make_zotero_reader()

    mock_bad_response = MagicMock(spec=requests.Response)
    mock_bad_response.headers = {"Backoff": "0.001"}

    http_error = requests.HTTPError(response=mock_bad_response)

    with patch("requests.get", side_effect=http_error):
        with patch("notion_zotero.connectors.zotero.reader._zotero_retry_wait", return_value=0.001):
            with pytest.raises(requests.HTTPError):
                reader.get_items(limit=100)


# ---------------------------------------------------------------------------
# T-010-6: to_reference maps journalArticle fields correctly
# ---------------------------------------------------------------------------

def test_to_reference_maps_fields():
    reader = _make_zotero_reader()
    item = _make_journal_article("ABC123")

    ref = reader.to_reference(item)

    assert ref.title == "Deep Learning for Graphs"
    assert ref.year == 2021
    assert ref.doi == "10.1000/test"
    assert ref.journal == "Journal of AI Research"
    assert ref.url == "https://example.com/paper"
    assert ref.abstract == "A study of graph networks."
    assert ref.item_type == "journalArticle"
    assert "Smith, Jane" in ref.authors
    assert "Doe, Alan" in ref.authors
    assert "machine learning" in ref.tags
    assert ref.zotero_key == "ABC123"
    assert ref.provenance["source_system"] == "zotero"


# ---------------------------------------------------------------------------
# T-010-7: to_reference logs warning for unmapped fields
# ---------------------------------------------------------------------------

def test_to_reference_unmapped_field_warns(caplog):
    reader = _make_zotero_reader()
    item = {
        "key": "KEY1",
        "data": {
            "key": "KEY1",
            "itemType": "journalArticle",
            "title": "A Paper",
            "x_custom": "mystery_value",
            "creators": [],
            "tags": [],
        },
    }

    with caplog.at_level(logging.WARNING, logger="notion_zotero.connectors.zotero.reader"):
        reader.to_reference(item)

    assert any("x_custom" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# T-010-8: raises ConfigurationError without library ID
# ---------------------------------------------------------------------------

def test_zotero_reader_raises_without_library_id(monkeypatch):
    monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)
    monkeypatch.setenv("ZOTERO_API_KEY", "fake-key")

    from notion_zotero.connectors.zotero.reader import ZoteroReader
    from notion_zotero.core.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError) as exc_info:
        ZoteroReader()

    assert "zotero.org/settings/keys" in str(exc_info.value)
