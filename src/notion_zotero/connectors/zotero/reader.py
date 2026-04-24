"""Read-only Zotero connector. Requires ZOTERO_API_KEY and ZOTERO_LIBRARY_ID env vars."""
from __future__ import annotations

import os
import logging

from notion_zotero.core.exceptions import ConfigurationError, NotionZoteroError  # noqa: F401
from notion_zotero.core.models import Reference

log = logging.getLogger(__name__)

_ZOTERO_BASE = "https://api.zotero.org"


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
                "ZOTERO_LIBRARY_ID is required but was not provided and is not set "
                "in the environment."
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

    def get_items(self, limit: int = 100) -> list[dict]:
        """Fetch up to *limit* items from the Zotero library."""
        try:
            import requests  # type: ignore[import]
        except ImportError as exc:
            raise ConfigurationError(
                "requests package is required. Install it with: pip install requests"
            ) from exc

        url = f"{self._base_url()}/items"
        params = {"limit": limit}
        log.debug("GET %s (limit=%d)", url, limit)
        response = requests.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()
        items: list[dict] = response.json()
        log.debug("Retrieved %d items from Zotero library %s.", len(items), self._library_id)
        return items

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
