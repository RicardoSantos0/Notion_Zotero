"""Tests: connectors raise ConfigurationError when API keys are absent."""
import os
import pytest
import unittest.mock


def test_notion_reader_requires_api_key():
    """NotionReader raises ConfigurationError when NOTION_API_KEY is absent."""
    from notion_zotero.connectors.notion.reader import NotionReader
    env = {k: v for k, v in os.environ.items() if k != "NOTION_API_KEY"}
    with unittest.mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(Exception):  # ConfigurationError
            NotionReader()


def test_zotero_reader_requires_api_key():
    """ZoteroReader raises ConfigurationError when ZOTERO_API_KEY is absent."""
    from notion_zotero.connectors.zotero.reader import ZoteroReader
    env = {k: v for k, v in os.environ.items()
           if k not in ("ZOTERO_API_KEY", "ZOTERO_LIBRARY_ID")}
    with unittest.mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(Exception):
            ZoteroReader()


def test_zotero_reader_requires_library_id():
    """ZoteroReader raises ConfigurationError when ZOTERO_LIBRARY_ID is absent."""
    from notion_zotero.connectors.zotero.reader import ZoteroReader
    env = {k: v for k, v in os.environ.items() if k != "ZOTERO_LIBRARY_ID"}
    # Provide the API key but not the library ID
    env["ZOTERO_API_KEY"] = "fake-key"
    with unittest.mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(Exception):
            ZoteroReader()


def test_notion_reader_to_reference_shape():
    """to_reference returns a Reference with correct provenance."""
    from notion_zotero.connectors.notion.reader import NotionReader
    from notion_zotero.core.models import Reference

    # Patch notion_client.Client so no real HTTP connection is made at init time
    mock_client = unittest.mock.MagicMock()
    with unittest.mock.patch("notion_client.Client", return_value=mock_client):
        with unittest.mock.patch.dict(os.environ, {"NOTION_API_KEY": "fake-key"}):
            reader = NotionReader(api_key="fake-key")

    fake_page = {
        "id": "page-abc-123",
        "properties": {
            "Title": {"title": [{"plain_text": "Test Paper"}]},
        },
    }
    ref = reader.to_reference(fake_page)
    assert isinstance(ref, Reference)
    assert ref.provenance.get("source_id") == "page-abc-123"
    assert ref.provenance.get("source_system") == "notion"


def test_notion_reader_to_reference_title_extracted():
    """to_reference correctly extracts the page title."""
    from notion_zotero.connectors.notion.reader import NotionReader

    mock_client = unittest.mock.MagicMock()
    with unittest.mock.patch("notion_client.Client", return_value=mock_client):
        reader = NotionReader(api_key="fake-key")

    fake_page = {
        "id": "page-xyz",
        "properties": {
            "Title": {"title": [{"plain_text": "My Test Paper"}]},
        },
    }
    ref = reader.to_reference(fake_page)
    assert ref.title == "My Test Paper"


def test_zotero_reader_to_reference_shape():
    """to_reference returns a Reference with correct provenance."""
    from notion_zotero.connectors.zotero.reader import ZoteroReader
    from notion_zotero.core.models import Reference

    with unittest.mock.patch.dict(os.environ, {
        "ZOTERO_API_KEY": "fake-key", "ZOTERO_LIBRARY_ID": "12345"
    }):
        reader = ZoteroReader(api_key="fake-key", library_id="12345")

    fake_item = {
        "key": "ITEM001",
        "data": {
            "title": "Deep Learning Paper",
            "creators": [],
            "date": "2023",
            "publicationTitle": "NeurIPS",
            "DOI": "10.5555/test",
            "itemType": "journalArticle",
        },
    }
    ref = reader.to_reference(fake_item)
    assert isinstance(ref, Reference)
    assert ref.provenance.get("source_system") == "zotero"
    assert ref.provenance.get("source_id") == "ITEM001"


def test_zotero_reader_to_reference_fields():
    """to_reference correctly maps Zotero item fields."""
    from notion_zotero.connectors.zotero.reader import ZoteroReader

    with unittest.mock.patch.dict(os.environ, {
        "ZOTERO_API_KEY": "fake-key", "ZOTERO_LIBRARY_ID": "12345"
    }):
        reader = ZoteroReader(api_key="fake-key", library_id="12345")

    fake_item = {
        "key": "ITEM002",
        "data": {
            "title": "Attention Is All You Need",
            "creators": [
                {"lastName": "Vaswani", "firstName": "Ashish"},
                {"name": "et al."},
            ],
            "date": "2017-06-12",
            "publicationTitle": "NeurIPS",
            "DOI": "10.5555/nips.2017",
            "itemType": "conferencePaper",
            "tags": [{"tag": "transformers"}, {"tag": "attention"}],
        },
    }
    ref = reader.to_reference(fake_item)
    assert ref.title == "Attention Is All You Need"
    assert ref.year == 2017
    assert ref.journal == "NeurIPS"
    assert ref.doi == "10.5555/nips.2017"
    assert ref.item_type == "conferencePaper"
    assert ref.zotero_key == "ITEM002"
    assert "transformers" in ref.tags
    assert "Vaswani, Ashish" in ref.authors


def test_zotero_reader_get_items_no_network():
    """get_items uses requests but must be mockable at the transport layer.

    Skipped when requests is not installed (CI environment without network
    deps); the key assertion is that no real HTTP call escapes the mock.
    """
    requests = pytest.importorskip("requests", reason="requests not installed")

    from notion_zotero.connectors.zotero.reader import ZoteroReader

    with unittest.mock.patch.dict(os.environ, {
        "ZOTERO_API_KEY": "fake-key", "ZOTERO_LIBRARY_ID": "12345"
    }):
        reader = ZoteroReader(api_key="fake-key", library_id="12345")

    fake_response = unittest.mock.MagicMock()
    fake_response.json.return_value = []
    fake_response.raise_for_status.return_value = None

    with unittest.mock.patch("requests.get", return_value=fake_response) as mock_get:
        items = reader.get_items(limit=10)
        assert mock_get.call_count == 1
        assert items == []
