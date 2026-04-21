"""Zotero connector package for notion_zotero."""
from notion_zotero.connectors.zotero.reader import ZoteroReader, ConfigurationError

__all__ = ["ZoteroReader", "ConfigurationError"]
