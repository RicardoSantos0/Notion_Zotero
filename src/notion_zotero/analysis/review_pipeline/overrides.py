"""Override application for the review pipeline.

WP1 implementation: applies manual overrides from manual_overrides.yaml to
classified contribution rows AFTER the rule-based classifier runs.

This module re-exports ``apply_overrides`` from the lightweight
``notion_zotero.analysis.overrides`` module, which has no heavy dependencies.

Full review_pipeline integration (contribution_rows, normalizers, etc.) will
be added in WP2-WP4 per d-012.
"""
from __future__ import annotations

from notion_zotero.analysis.overrides import apply_overrides

__all__ = ["apply_overrides"]
