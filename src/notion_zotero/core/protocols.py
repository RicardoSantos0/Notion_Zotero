"""Structural Protocol contracts for injected writer clients.

These protocols use typing.Protocol (PEP 544) for structural subtyping —
no changes to the real Zotero or Notion client objects are required.
Protocols are checked statically by type-checkers; runtime behaviour is unchanged.
"""
from __future__ import annotations

from typing import Any, Protocol

__all__ = [
    "ZoteroClientProtocol",
    "NotionPagesProtocol",
    "NotionClientProtocol",
]


class ZoteroClientProtocol(Protocol):
    """Contract for the Zotero client injected into ZoteroWriter.

    ZoteroWriter calls exactly one method on the client:
        client.update_item(item_key: str, data: dict[str, Any], version: int | None = None) -> Any
    """

    def update_item(self, item_key: str, data: dict[str, Any], version: int | None = None) -> Any: ...


class NotionPagesProtocol(Protocol):
    """Contract for the ``client.pages`` sub-object used by NotionWriter.

    NotionWriter calls exactly one method on the sub-object:
        client.pages.update(page_id: str, *, properties: dict[str, Any]) -> Any
    """

    def update(self, page_id: str, **kwargs: Any) -> Any: ...


class NotionClientProtocol(Protocol):
    """Contract for the Notion client injected into NotionWriter.

    The client must expose a ``pages`` attribute satisfying NotionPagesProtocol.
    """

    pages: NotionPagesProtocol
