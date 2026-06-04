"""Notion property serialization helpers for write paths."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


DEFAULT_NOTION_PROPERTY_SCHEMA: dict[str, dict[str, str]] = {
    "title": {"name": "title", "type": "title"},
    "authors": {"name": "authors", "type": "multi_select"},
    "year": {"name": "year", "type": "number"},
    "journal": {"name": "journal", "type": "rich_text"},
    "doi": {"name": "doi", "type": "rich_text"},
    "url": {"name": "url", "type": "url"},
    "zotero_key": {"name": "zotero_key", "type": "rich_text"},
    "abstract": {"name": "abstract", "type": "rich_text"},
    "item_type": {"name": "item_type", "type": "select"},
    "tags": {"name": "tags", "type": "multi_select"},
    "state": {"name": "state", "type": "status"},
    "workflow_state": {"name": "workflow_state", "type": "status"},
    "inclusion_decision_for_task": {"name": "inclusion_decision_for_task", "type": "select"},
    "extracted": {"name": "extracted", "type": "checkbox"},
    "relevance_notes": {"name": "relevance_notes", "type": "rich_text"},
    "kind": {"name": "kind", "type": "select"},
    "text": {"name": "text", "type": "rich_text"},
    "assignment_source": {"name": "assignment_source", "type": "select"},
}

CANONICAL_NOTION_PROPERTY_ALIASES: dict[str, str] = {
    "title": "title",
    "name": "title",
    "paper title": "title",
    "author": "authors",
    "authors": "authors",
    "year": "year",
    "publication year": "year",
    "journal": "journal",
    "publication": "journal",
    "doi": "doi",
    "url": "url",
    "link": "url",
    "zotero_key": "zotero_key",
    "zotero key": "zotero_key",
    "abstract": "abstract",
    "type": "item_type",
    "item_type": "item_type",
    "tags": "tags",
    "keywords": "tags",
    "search strategy": "search_terms",
    "search terms": "search_terms",
    "search_terms": "search_terms",
    "date of retrieval": "search_date",
    "search date": "search_date",
    "search_date": "search_date",
    "database": "database",
    "source database": "database",
    "search database": "database",
    "platform": "database",
    "quartile": "journal_quartile",
    "journal quartile": "journal_quartile",
    "sjr quartile": "journal_quartile",
    "journal_quartile": "journal_quartile",
    "article type": "journal_quartile",
}


def build_property_schema_from_notion_schema(
    notion_schema: Mapping[str, str | Mapping[str, Any]] | None,
) -> dict[str, dict[str, str]]:
    """Convert a Notion database schema into canonical-field property schema."""
    property_schema: dict[str, dict[str, str]] = {}
    for property_name, raw in (notion_schema or {}).items():
        canonical_field = CANONICAL_NOTION_PROPERTY_ALIASES.get(str(property_name).strip().casefold())
        if not canonical_field or canonical_field in property_schema:
            continue
        if isinstance(raw, Mapping):
            prop_type = str(raw.get("type") or "rich_text")
        else:
            prop_type = str(raw or "rich_text")
        property_schema[canonical_field] = {
            "name": str(property_name),
            "type": prop_type,
        }
    return property_schema


def _schema_entry(
    field_name: str,
    property_schema: Mapping[str, str | Mapping[str, str]] | None,
) -> dict[str, str]:
    raw = (property_schema or {}).get(field_name)
    if isinstance(raw, str):
        return {"name": field_name, "type": raw}
    if isinstance(raw, Mapping):
        name = str(raw.get("name") or field_name)
        typ = str(raw.get("type") or "rich_text")
        return {"name": name, "type": typ}
    return DEFAULT_NOTION_PROPERTY_SCHEMA.get(field_name, {"name": field_name, "type": "rich_text"})


def _text_objects(value: Any) -> list[dict[str, dict[str, str]]]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        content = "; ".join(str(item) for item in value if item is not None)
    else:
        content = str(value)
    return [{"text": {"content": content}}] if content else []


def _multi_select(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [{"name": str(item)} for item in value if str(item).strip()]
    text = str(value).strip()
    return [{"name": text}] if text else []


def serialize_notion_property(
    field_name: str,
    value: Any,
    property_schema: Mapping[str, str | Mapping[str, str]] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return ``(notion_property_name, typed_payload)`` for one canonical field."""
    entry = _schema_entry(field_name, property_schema)
    prop_name = entry["name"]
    prop_type = entry["type"]

    if prop_type == "title":
        return prop_name, {"title": _text_objects(value)}
    if prop_type == "rich_text":
        return prop_name, {"rich_text": _text_objects(value)}
    if prop_type == "number":
        return prop_name, {"number": value if value is not None else None}
    if prop_type == "url":
        return prop_name, {"url": str(value) if value else None}
    if prop_type == "checkbox":
        return prop_name, {"checkbox": bool(value)}
    if prop_type == "select":
        return prop_name, {"select": {"name": str(value)} if value else None}
    if prop_type == "status":
        return prop_name, {"status": {"name": str(value)} if value else None}
    if prop_type == "multi_select":
        return prop_name, {"multi_select": _multi_select(value)}
    if prop_type == "date":
        return prop_name, {"date": {"start": str(value)} if value else None}

    raise ValueError(f"Unsupported Notion property type for {field_name!r}: {prop_type!r}")


def serialize_notion_properties(
    updates: Mapping[str, Any],
    property_schema: Mapping[str, str | Mapping[str, str]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Serialize a mapping of canonical fields to Notion API property payloads."""
    payload: dict[str, dict[str, Any]] = {}
    for field_name, value in updates.items():
        notion_name, notion_value = serialize_notion_property(field_name, value, property_schema)
        payload[notion_name] = notion_value
    return payload


__all__ = [
    "CANONICAL_NOTION_PROPERTY_ALIASES",
    "DEFAULT_NOTION_PROPERTY_SCHEMA",
    "build_property_schema_from_notion_schema",
    "serialize_notion_property",
    "serialize_notion_properties",
]
