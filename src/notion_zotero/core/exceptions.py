"""Typed exception hierarchy for notion_zotero."""
from __future__ import annotations


class NotionZoteroError(Exception):
    """Base exception for all notion_zotero errors."""


class ConfigurationError(NotionZoteroError):
    """Raised when a required configuration value (e.g. env var) is missing."""


class NotionImportError(NotionZoteroError):
    """Raised when importing/parsing a reading list page fails."""


class FieldMappingError(NotionImportError):
    """Raised when a required field cannot be mapped from the source."""

    def __init__(self, field: str, source: str | None = None) -> None:
        self.field = field
        self.source = source
        msg = f"Failed to map field '{field}'"
        if source:
            msg += f" from source '{source}'"
        super().__init__(msg)


class SchemaValidationError(NotionZoteroError):
    """Raised when a canonical object fails schema validation."""

    def __init__(self, model: str, details: str) -> None:
        self.model = model
        self.details = details
        super().__init__(f"Schema validation failed for {model}: {details}")


class DomainPackError(NotionZoteroError):
    """Raised when a domain pack cannot be loaded or resolved."""

    def __init__(self, pack_id: str, reason: str = "") -> None:
        self.pack_id = pack_id
        super().__init__(f"Domain pack '{pack_id}' error" + (f": {reason}" if reason else ""))


class TemplateError(NotionZoteroError):
    """Raised when a template is missing or invalid."""

    def __init__(self, template_id: str, reason: str = "") -> None:
        self.template_id = template_id
        super().__init__(f"Template '{template_id}' error" + (f": {reason}" if reason else ""))


class ProvenanceError(NotionZoteroError):
    """Raised when required provenance information is missing."""


__all__ = [
    "NotionZoteroError",
    "ConfigurationError",
    "NotionImportError",
    "FieldMappingError",
    "SchemaValidationError",
    "DomainPackError",
    "TemplateError",
    "ProvenanceError",
]
