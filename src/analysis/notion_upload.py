"""notion_upload.py — upload helpers for creating pages and blocks in Notion.

These helpers intentionally keep the API minimal and synchronous to make unit
testing straightforward in the Notion_Zotero project.
"""

from __future__ import annotations

from typing import Any

from ._client import get_notion_client, get_page_id


def create_page(parent_page_id: str | None, properties: dict[str, Any], children: list[dict] | None = None) -> dict[str, Any]:
    client = get_notion_client()
    parent = {"type": "page_id", "page_id": get_page_id(parent_page_id)}
    payload = {"parent": parent, "properties": properties}
    if children:
        payload["children"] = children
    return client.pages.create(**payload)


def append_block(parent_block_id: str, block: dict[str, Any]) -> dict[str, Any]:
    client = get_notion_client()
    return client.blocks.children.append(block_id=get_page_id(parent_block_id), children=[block])
    
