"""Domain pack for the education / learning-analytics review.

Defines canonical task ids, human-facing names, aliases, template mapping,
and the list of domain-specific Notion properties to extract beyond the
bibliographic canonical set.

Compliance: no imports from notion_zotero.core — this module is intentionally
kept free of core-model dependencies so it can be loaded before core models
are fully initialised.
"""
from __future__ import annotations

from typing import Dict, Any, Optional

# Module-level constants for external reference without loading the full dict.
DOMAIN_PACK_ID: str = "education_learning_analytics"
DOMAIN_PACK_VERSION: str = "1.0"

# Short label map used by task_label_fn — exported for notebook / analysis use.
_TASK_LABEL_MAP: dict[str, str] = {
    "performance_prediction": "PRED",
    "descriptive_modelling": "DESC",
    "recommender_systems": "REC",
    "knowledge_tracing": "KT",
}

# Notion property names to extract beyond the canonical bibliographic fields.
# Stored in sync_metadata["domain_properties"] in each canonical bundle.
# Groups:
#   reading_workflow  — checkbox fields tracking which sections have been read
#   domain_classification — domain-specific analytic tags for each paper
#   screening — review decision fields beyond Status / Status_1
DOMAIN_NOTION_PROPERTIES: list[str] = [
    # reading workflow (checkbox)
    "Introduction",
    "Related Work",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion",
    "Limitations",
    "Completed",
    # domain classification (select / multi_select)
    "Keywords/Type",
    "Learner Population",
    "Learner Representation",
    "Course-Agnostic Approach",
    "Deployed/ Deployable",
    "Work Nature",
    # screening (select / rich_text)
    "Motive For Exclusion",
]

domain_pack = {
    "id": "education_learning_analytics",
    "version": "1.1",
    "name": "Education / Learning Analytics",
    "tasks": {
        "descriptive_modelling": {
            "name": "Descriptive Modelling",
            "aliases": ["descriptive", "descriptive modelling", "descriptive analysis", "desc"],
            "template_id": "descriptive_analysis",
        },
        "performance_prediction": {
            "name": "Performance Prediction",
            "aliases": ["prediction", "performance prediction", "predictive", "pred"],
            "template_id": "prediction_modeling",
        },
        "recommender_systems": {
            "name": "Recommender Systems",
            "aliases": ["recommender", "recommendation", "recommender systems", "rec"],
            "template_id": "recommendation_system",
        },
        "knowledge_tracing": {
            "name": "Knowledge Tracing",
            "aliases": ["knowledge tracing", "kt", "tracing"],
            "template_id": "sequence_tracing",
        },
    },
    # Domain-specific Notion properties to extract (beyond canonical bibliographic set).
    # Importer reads this list and stores values in sync_metadata["domain_properties"].
    "notion_properties": DOMAIN_NOTION_PROPERTIES,
    # Short-label mapping for task names → analysis abbreviations.
    "task_labels": _TASK_LABEL_MAP,
}


def task_label_fn(task_name: str | None) -> str:
    """Map a full task name to its short analysis label (PRED / DESC / REC / KT).

    Falls back to the task name itself when no mapping is found.
    """
    key = (task_name or "").lower().replace(" ", "_").replace("-", "_")
    # exact match first
    if key in _TASK_LABEL_MAP:
        return _TASK_LABEL_MAP[key]
    # substring match for partial names
    for tid, label in _TASK_LABEL_MAP.items():
        if tid in key or key in tid:
            return label
    return task_name or ""


def list_tasks() -> Dict[str, Dict[str, Any]]:
    return domain_pack["tasks"]


def match_heading_to_task(heading: str | None) -> Optional[str]:
    if not heading:
        return None
    h = heading.lower()
    for tid, meta in domain_pack["tasks"].items():
        for a in meta.get("aliases", []):
            if a.lower() in h:
                return tid
    return None


__all__ = [
    "DOMAIN_PACK_ID",
    "DOMAIN_PACK_VERSION",
    "DOMAIN_NOTION_PROPERTIES",
    "domain_pack",
    "task_label_fn",
    "list_tasks",
    "match_heading_to_task",
]
