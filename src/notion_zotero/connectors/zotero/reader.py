"""Read-only Zotero connector. Requires ZOTERO_API_KEY and ZOTERO_LIBRARY_ID env vars."""
from __future__ import annotations

import os
import logging

import requests
from tenacity import retry, stop_after_attempt, retry_if_exception
from tenacity.wait import wait_base

from notion_zotero.core.exceptions import ConfigurationError, NotionZoteroError  # noqa: F401
from notion_zotero.core.models import Reference

log = logging.getLogger(__name__)

_ZOTERO_BASE = "https://api.zotero.org"

_KNOWN_ZOTERO_FIELDS = {
    "key", "itemType", "title", "creators", "date", "DOI", "url",
    "abstractNote", "publicationTitle", "journalAbbreviation", "tags",
    "collections", "relations", "dateAdded", "dateModified", "version",
}


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


def _is_requests_http_error(exc):
    return isinstance(exc, requests.HTTPError)


class ZoteroReader:
    """Read-only HTTP client for the Zotero Web API.

    Instantiation raises ConfigurationError if ZOTERO_API_KEY or
    ZOTERO_LIBRARY_ID are not available either as constructor arguments or
    as environment variables.
    """

    def __init__(
        self,
        api_key: str | None = None,
        library_id: str | None = None,
        library_type: str = "user",
    ) -> None:
        resolved_key = api_key or os.environ.get("ZOTERO_API_KEY")
        if not resolved_key:
            raise ConfigurationError(
                "ZOTERO_API_KEY is required but was not provided and is not set "
                "in the environment."
            )
        resolved_lib = library_id or os.environ.get("ZOTERO_LIBRARY_ID")
        if not resolved_lib:
            raise ConfigurationError(
                "ZOTERO_LIBRARY_ID is required but was not set. "
                "Find your Zotero user ID at: https://www.zotero.org/settings/keys"
            )

        self._api_key = resolved_key
        self._library_id = resolved_lib
        self._library_type = library_type
        log.debug(
            "ZoteroReader initialised (read-only) for %s library %s.",
            library_type,
            resolved_lib,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {"Zotero-API-Key": self._api_key}

    def _base_url(self) -> str:
        return f"{_ZOTERO_BASE}/{self._library_type}s/{self._library_id}"

    # ------------------------------------------------------------------
    # Public read methods
    # ------------------------------------------------------------------

    def _fetch_page(self, url: str, params: dict) -> requests.Response:
        @retry(
            retry=retry_if_exception(_is_requests_http_error),
            stop=stop_after_attempt(3),
            wait=_zotero_retry_wait,
            reraise=True,
        )
        def _call():
            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
            return resp

        return _call()

    def get_items(self, limit: int = 100) -> list[dict]:
        """Fetch ALL items from the Zotero library, paginating with *limit* as page size."""
        url = f"{self._base_url()}/items"
        all_items: list[dict] = []
        start = 0

        while True:
            params = {"limit": limit, "start": start}
            log.debug("GET %s (start=%d, limit=%d)", url, start, limit)
            response = self._fetch_page(url, params)

            page_items: list[dict] = response.json()
            if not page_items:
                break

            all_items.extend(page_items)

            total_str = response.headers.get("Total-Results")
            if total_str is not None:
                try:
                    total = int(total_str)
                except ValueError:
                    total = None
            else:
                total = None

            start += len(page_items)

            if total is not None:
                if start >= total:
                    break
            else:
                # Fallback: stop when page returned fewer items than requested
                if len(page_items) < limit:
                    break

        log.debug("Retrieved %d items from Zotero library %s.", len(all_items), self._library_id)
        return all_items

    def to_reference(self, item: dict) -> Reference:
        """Map a raw Zotero item dict to a canonical Reference model."""
        item_key: str = item.get("key", "")
        data: dict = item.get("data", item)  # Zotero API wraps fields under "data"

        # Authors / creators
        creators = data.get("creators", [])
        authors: list[str] = []
        for creator in creators:
            last = creator.get("lastName", "")
            first = creator.get("firstName", "")
            name = creator.get("name", "")
            if name:
                authors.append(name)
            elif last or first:
                authors.append(f"{last}, {first}".strip(", "))

        # Year from date field (Zotero stores "2023-01-15", "2023", etc.)
        date_str: str = data.get("date", "") or ""
        year: int | None = None
        if date_str:
            try:
                year = int(date_str[:4])
            except (ValueError, IndexError):
                pass

        # Tags
        tags_raw = data.get("tags", [])
        tags = [t.get("tag", "") for t in tags_raw if t.get("tag")]

        for k in data:
            if k not in _KNOWN_ZOTERO_FIELDS:
                log.warning("ZoteroReader: unmapped field '%s' in item %s", k, item_key)

        return Reference(
            id=item_key or data.get("key", ""),
            title=data.get("title") or None,
            authors=authors,
            year=year,
            journal=data.get("publicationTitle") or data.get("journalAbbreviation") or None,
            doi=data.get("DOI") or None,
            url=data.get("url") or None,
            zotero_key=item_key or data.get("key") or None,
            abstract=data.get("abstractNote") or None,
            item_type=data.get("itemType") or None,
            tags=tags,
            provenance={
                "source_id": item_key,
                "source_system": "zotero",
                "domain_pack_id": "",
                "domain_pack_version": "",
            },
            sync_metadata={},
        )


__all__ = ["ZoteroReader", "ConfigurationError"]
