"""Manuscript table builders for the review pipeline (façade, T7.3).

Re-exports the stabilized Table 2-5 generators.
"""
from __future__ import annotations

from notion_zotero.analysis.paper_tables import (
    generate_table2,
    generate_table4,
    generate_table5,
)
from notion_zotero.analysis.predictive_problem_table import generate_table3

__all__ = ["generate_table2", "generate_table3", "generate_table4", "generate_table5"]
