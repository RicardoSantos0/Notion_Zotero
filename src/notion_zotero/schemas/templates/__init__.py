"""Template registry convenience exports."""
from __future__ import annotations

from .generic import TEMPLATES


def get_template(template_id: str):
    return TEMPLATES.get(template_id)


__all__ = ["TEMPLATES", "get_template"]
"""Template library package placeholder for notion_zotero.schemas.templates."""

__all__ = []
