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
    "DEFAULT_NOTION_PROPERTY_SCHEMA",
    "serialize_notion_property",
    "serialize_notion_properties",
]
