"""_parse.py — helpers for property and block parsing from Notion exports.

Copied to the `analysis` package to avoid cross-repo imports. Keep the API
stable and minimal; higher-level callers should rely on `pages_to_records` and
`extract_page_blocks`.
"""

from __future__ import annotations

from typing import Any


def _get_property_text(prop: dict[str, Any]) -> str:
    if not prop:
        return ""
    t = prop.get("type")
    val = prop.get(t)
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        if "text" in val:
            return val["text"][0].get("plain_text", "") if val["text"] else ""
    if isinstance(val, list):
        return " ".join(item.get("plain_text", "") for item in val)
    return str(val or "")


def pages_to_records(pages: list[dict]) -> list[dict]:
    records = []
    for p in pages:
        props = p.get("properties", {})
        record = {k: _get_property_text(v) for k, v in props.items()}
        record["id"] = p.get("id")
        records.append(record)
    return records


def extract_page_blocks(page: dict) -> list[dict]:
    blocks = page.get("blocks", [])
    # Flatten nested block children into a single list
    flat: list[dict] = []
    stack = list(blocks)
    while stack:
        b = stack.pop(0)
        flat.append(b)
        children = b.get("children") or []
        stack[0:0] = children
    return flat
