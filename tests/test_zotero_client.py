"""Tests for ZoteroClientAdapter."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests


def _make_response(status_code: int, json_body: dict | None = None, headers: dict | None = None):
    """Build a fake requests.Response with given status and optional JSON body."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    if json_body is not None:
        resp.json.return_value = json_body
    if status_code >= 400:
        http_err = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestZoteroClientAdapterUpdateItem:
    """Unit tests for ZoteroClientAdapter.update_item."""

    def test_happy_path_url_and_api_key_header(self):
        """200 response: URL contains library_id and item_key; Zotero-API-Key header set."""
        from notion_zotero.connectors.zotero.client import ZoteroClientAdapter

        adapter = ZoteroClientAdapter(api_key="zot-key", library_id="lib-999")
        ok_resp = _make_response(200, {"key": "ABCD1234"})

        with patch("requests.patch", return_value=ok_resp) as mock_patch:
            result = adapter.update_item("ABCD1234", {"title": "x"})

        mock_patch.assert_called_once()
        call_kwargs = mock_patch.call_args

        url = call_kwargs[0][0]
        assert "lib-999" in url
        assert "ABCD1234" in url

        headers = call_kwargs[1]["headers"]
        assert headers["Zotero-API-Key"] == "zot-key"

        assert result == {"key": "ABCD1234"}

    def test_version_guard_header_is_sent_when_provided(self):
        from notion_zotero.connectors.zotero.client import ZoteroClientAdapter

        adapter = ZoteroClientAdapter(api_key="zot-key", library_id="lib-999")
        ok_resp = _make_response(200, {"key": "ABCD1234"})

        with patch("requests.patch", return_value=ok_resp) as mock_patch:
            adapter.update_item("ABCD1234", {"title": "x"}, version=123)

        headers = mock_patch.call_args[1]["headers"]
        assert headers["If-Unmodified-Since-Version"] == "123"

    def test_429_with_backoff_header_retries_and_succeeds(self):
        """429 with Backoff: 0 header on first call, 200 on second — two total calls."""
        from notion_zotero.connectors.zotero.client import ZoteroClientAdapter

        adapter = ZoteroClientAdapter(api_key="zot-key", library_id="lib-999")
        retry_resp = _make_response(429, headers={"Backoff": "0"})
        ok_resp = _make_response(200, {"key": "ABCD1234"})

        with patch("requests.patch", side_effect=[retry_resp, ok_resp]) as mock_patch:
            result = adapter.update_item("ABCD1234", {"title": "retry"})

        assert mock_patch.call_count == 2
        assert result == {"key": "ABCD1234"}

    def test_400_raises_http_error(self):
        """400 response must ultimately raise HTTPError (tenacity exhausts retries)."""
        from notion_zotero.connectors.zotero.client import ZoteroClientAdapter

        adapter = ZoteroClientAdapter(api_key="zot-key", library_id="lib-999")
        # 400 triggers HTTPError which satisfies _is_requests_http_error=True,
        # so tenacity retries up to stop_after_attempt(4) then re-raises.
        bad_resp = _make_response(400, {"error": "bad request"})

        with patch("requests.patch", return_value=bad_resp) as mock_patch:
            with pytest.raises(requests.HTTPError):
                adapter.update_item("ABCD1234", {"title": "x"})

        assert mock_patch.call_count >= 1

    def test_protocol_satisfaction(self):
        """ZoteroClientAdapter must expose update_item callable."""
        from notion_zotero.connectors.zotero.client import ZoteroClientAdapter

        adapter = ZoteroClientAdapter(api_key="zot-key", library_id="lib-999")
        assert hasattr(adapter, "update_item")
        assert callable(adapter.update_item)
