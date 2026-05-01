"""Tests for NotionClientAdapter and _NotionPagesAdapter."""
from __future__ import annotations

import unittest.mock
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


class TestNotionPagesAdapterUpdate:
    """Unit tests for _NotionPagesAdapter.update via NotionClientAdapter.pages."""

    def test_happy_path_patch_url_headers_body(self):
        """200 response: verify PATCH URL, Authorization header, and JSON body."""
        from notion_zotero.connectors.notion.client import NotionClientAdapter

        adapter = NotionClientAdapter("test-key")
        ok_resp = _make_response(200, {"id": "page-123", "object": "page"})

        with patch("requests.patch", return_value=ok_resp) as mock_patch:
            result = adapter.pages.update("page-123", properties={"Title": "x"})

        mock_patch.assert_called_once()
        call_kwargs = mock_patch.call_args

        url = call_kwargs[0][0]
        assert url == "https://api.notion.com/v1/pages/page-123"

        headers = call_kwargs[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Notion-Version"] == "2022-06-28"
        assert headers["Content-Type"] == "application/json"

        body = call_kwargs[1]["json"]
        assert body == {"properties": {"Title": "x"}}

        assert result == {"id": "page-123", "object": "page"}

    def test_429_retry_uses_retry_after_and_succeeds(self):
        """429 with retry_after=0 on first call, 200 on second — two total calls."""
        from notion_zotero.connectors.notion.client import NotionClientAdapter

        adapter = NotionClientAdapter("test-key")
        retry_resp = _make_response(429, {"retry_after": 0})
        ok_resp = _make_response(200, {"object": "page"})

        with patch("requests.patch", side_effect=[retry_resp, ok_resp]) as mock_patch:
            result = adapter.pages.update("page-abc", properties={"Title": "retry"})

        assert mock_patch.call_count == 2
        assert result == {"object": "page"}

    def test_400_raises_http_error(self):
        """400 response must ultimately raise HTTPError.

        The decorator uses retry_if_exception_type(requests.HTTPError) which
        matches ALL HTTPErrors, so tenacity exhausts stop_after_attempt(4)
        then re-raises.  The key contract is that HTTPError propagates to caller.
        """
        from notion_zotero.connectors.notion.client import NotionClientAdapter

        adapter = NotionClientAdapter("test-key")
        bad_resp = _make_response(400, {"message": "bad request"})

        with patch("requests.patch", return_value=bad_resp):
            with pytest.raises(requests.HTTPError):
                adapter.pages.update("page-bad", properties={"Title": "x"})

    def test_protocol_satisfaction(self):
        """NotionClientAdapter must expose pages attribute with update method."""
        from notion_zotero.connectors.notion.client import NotionClientAdapter

        adapter = NotionClientAdapter("any-key")
        assert hasattr(adapter, "pages")
        assert hasattr(adapter.pages, "update")
        assert callable(adapter.pages.update)
