"""Core package for notion_zotero canonical models and contracts."""

from notion_zotero.core.protocols import (
    NotionClientProtocol,
    NotionPagesProtocol,
    ZoteroClientProtocol,
)

__all__ = [
    "ZoteroClientProtocol",
    "NotionPagesProtocol",
    "NotionClientProtocol",
]
