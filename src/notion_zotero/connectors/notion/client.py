"""Notion write client adapter satisfying NotionClientProtocol."""
from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from tenacity.wait import wait_base

log = logging.getLogger(__name__)

_NOTION_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_RETRY_CODES = {429, 500, 502, 503, 504}

__all__ = ["NotionClientAdapter"]


class _NotionRetryWait(wait_base):
    """Use retry_after from Notion 429 JSON body, else 2s."""

    def __call__(self, retry_state) -> float:
        exc = retry_state.outcome.exception()
        if hasattr(exc, "response") and exc.response is not None:
            try:
                body = exc.response.json()
                return float(body.get("retry_after", 2))
            except Exception:
                pass
        return 2.0


_notion_retry_wait = _NotionRetryWait()


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, requests.HTTPError):
        resp = getattr(exc, "response", None)
        if resp is not None and resp.status_code in _RETRY_CODES:
            return True
    return False


class _NotionPagesAdapter:
    def __init__(self, headers: dict[str, str]) -> None:
        self._headers = headers

    @retry(
        retry=retry_if_exception_type(requests.HTTPError),
        wait=_notion_retry_wait,
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def update(self, page_id: str, *, properties: dict[str, Any]) -> dict:
        url = f"{_NOTION_BASE}/pages/{page_id}"
        resp = requests.patch(url, headers=self._headers, json={"properties": properties}, timeout=30)
        resp.raise_for_status()
        return resp.json()


class NotionClientAdapter:
    """Thin requests adapter for the Notion API satisfying NotionClientProtocol."""

    def __init__(self, api_key: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self.pages = _NotionPagesAdapter(self._headers)
