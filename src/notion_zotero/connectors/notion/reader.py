"""Read-only Notion connector. Requires NOTION_API_KEY env var."""
from __future__ import annotations

import os
import logging
from typing import Any

from notion_zotero.core.exceptions import NotionZoteroError
from notion_zotero.core.models import Reference

log = logging.getLogger(__name__)


class ConfigurationError(NotionZoteroError):
    """Raised when a required configuration value (e.g. env var) is missing."""


class NotionReader:
    """Read-only client for the Notion API.

    Instantiation raises ConfigurationError if NOTION_API_KEY is not available
    either as a constructor argument or as an environment variable.
    """

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("NOTION_API_KEY")
        if not resolved_key:
            raise ConfigurationError(
                "NOTION_API_KEY is required but was not provided and is not set "
                "in the environment."
            )
        try:
            from notion_client import Client  # type: ignore[import]
        except ImportError as exc:
            raise ConfigurationError(
                "notion-client package is required. Install it with: "
                "pip install notion-client"
            ) from exc

        self._client = Client(auth=resolved_key)
        log.debug("NotionReader initialised (read-only).")

    # ------------------------------------------------------------------
    # Public read methods
    # ------------------------------------------------------------------

    def get_page(self, page_id: str) -> dict:
        """Fetch a single raw Notion page by ID."""
        log.debug("Fetching Notion page %s", page_id)
        page: dict = self._client.pages.retrieve(page_id=page_id)  # type: ignore[assignment]
        return page

    def get_database_pages(self, database_id: str) -> list[dict]:
        """Paginate through all pages in a Notion database."""
        log.debug("Fetching all pages from Notion database %s", database_id)
        results: list[dict] = []
        has_more = True
        start_cursor: str | None = None

        while has_more:
            kwargs: dict[str, Any] = {"database_id": database_id, "page_size": 100}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor

            response: dict = self._client.databases.query(**kwargs)  # type: ignore[assignment]
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        log.debug("Retrieved %d pages from database %s", len(results), database_id)
        return results

    def to_reference(self, page: dict) -> Reference:
        """Map a raw Notion page dict to a canonical Reference model.

        Only Notion-side fields are extracted here.  Zotero-owned fields
        (title, authors, doi, …) may be populated if they are stored as
        Notion page properties, but their authoritative values come from
        Zotero during a full sync.
        """
        page_id: str = page.get("id", "")
        props: dict = page.get("properties", {})

        def _rich_text(prop: dict) -> str | None:
            items = prop.get("rich_text") or prop.get("title") or []
            return "".join(t.get("plain_text", "") for t in items) or None

        def _multi_select(prop: dict) -> list[str]:
            return [item.get("name", "") for item in prop.get("multi_select", [])]

        def _select(prop: dict) -> str | None:
            sel = prop.get("select")
            return sel.get("name") if sel else None

        def _number(prop: dict) -> int | None:
            val = prop.get("number")
            return int(val) if val is not None else None

        def _url(prop: dict) -> str | None:
            return prop.get("url") or None

        # Map well-known property names (case-insensitive best-effort)
        prop_lower = {k.lower(): v for k, v in props.items()}

        title_prop = (
            prop_lower.get("title")
            or prop_lower.get("name")
            or next(
                (v for v in props.values() if v.get("type") == "title"),
                {},
            )
        )
        title = _rich_text(title_prop) if title_prop else None

        authors_prop = prop_lower.get("authors") or prop_lower.get("author") or {}
        authors_raw = _rich_text(authors_prop) if authors_prop else None
        authors = [a.strip() for a in authors_raw.split(";") if a.strip()] if authors_raw else []

        year_prop = prop_lower.get("year") or prop_lower.get("publication year") or {}
        year = _number(year_prop) if year_prop else None

        journal_prop = prop_lower.get("journal") or prop_lower.get("publication") or {}
        journal = _rich_text(journal_prop) if journal_prop else None

        doi_prop = prop_lower.get("doi") or {}
        doi = _rich_text(doi_prop) or _url(doi_prop) if doi_prop else None

        url_prop = prop_lower.get("url") or prop_lower.get("link") or {}
        url = _url(url_prop) or _rich_text(url_prop) if url_prop else None

        zotero_key_prop = prop_lower.get("zotero_key") or prop_lower.get("zotero key") or {}
        zotero_key = _rich_text(zotero_key_prop) if zotero_key_prop else None

        abstract_prop = prop_lower.get("abstract") or {}
        abstract = _rich_text(abstract_prop) if abstract_prop else None

        item_type_prop = prop_lower.get("item_type") or prop_lower.get("type") or {}
        item_type = _select(item_type_prop) or _rich_text(item_type_prop) if item_type_prop else None

        tags_prop = prop_lower.get("tags") or prop_lower.get("keywords") or {}
        tags = _multi_select(tags_prop) if tags_prop else []

        ref_id = zotero_key or page_id

        return Reference(
            id=ref_id,
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            doi=doi,
            url=url,
            zotero_key=zotero_key,
            abstract=abstract,
            item_type=item_type,
            tags=tags,
            provenance={
                "source_id": page_id,
                "source_system": "notion",
                "domain_pack_id": "",
                "domain_pack_version": "",
            },
            sync_metadata={},
        )


__all__ = ["NotionReader", "ConfigurationError"]
