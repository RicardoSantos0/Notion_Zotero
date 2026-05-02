"""Zotero write client adapter satisfying ZoteroClientProtocol."""
from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, retry_if_exception
from tenacity.wait import wait_base

log = logging.getLogger(__name__)

_ZOTERO_BASE = "https://api.zotero.org"

__all__ = ["ZoteroClientAdapter"]


class _ZoteroRetryWait(wait_base):
    def __call__(self, retry_state) -> float:
        exc = retry_state.outcome.exception()
        if hasattr(exc, "response") and exc.response is not None:
            try:
                return float(exc.response.headers.get("Backoff", 2))
            except Exception:
                pass
        return 2.0


_zotero_retry_wait = _ZoteroRetryWait()


def _is_requests_http_error(exc: BaseException) -> bool:
    return isinstance(exc, requests.HTTPError)


class ZoteroClientAdapter:
    """Thin requests adapter for the Zotero Web API satisfying ZoteroClientProtocol."""

    def __init__(self, api_key: str, library_id: str) -> None:
        self._api_key = api_key
        self._library_id = library_id
        self._headers = {
            "Zotero-API-Key": api_key,
            "Content-Type": "application/json",
        }

    @retry(
        retry=retry_if_exception(_is_requests_http_error),
        wait=_zotero_retry_wait,
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def update_item(self, item_key: str, data: dict[str, Any], version: int | None = None) -> Any:
        url = f"{_ZOTERO_BASE}/users/{self._library_id}/items/{item_key}"
        headers = dict(self._headers)
        if version is not None:
            headers["If-Unmodified-Since-Version"] = str(version)
        resp = requests.patch(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
