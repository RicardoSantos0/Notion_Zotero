"""Domain pack for the education / learning-analytics review.

Defines canonical task ids, human-facing names, aliases, and template mapping.
"""
from __future__ import annotations

from typing import Dict, Any, Optional

domain_pack = {
    "id": "education_learning_analytics",
    "name": "Education / Learning Analytics",
    "tasks": {
        "descriptive_modelling": {
            "name": "Descriptive Modelling",
            "aliases": ["descriptive", "descriptive modelling", "descriptive analysis"],
            "template_id": "descriptive_analysis",
        },
        "performance_prediction": {
            "name": "Performance Prediction",
            "aliases": ["prediction", "performance prediction", "predictive"],
            "template_id": "prediction_modeling",
        },
        "recommender_systems": {
            "name": "Recommender Systems",
            "aliases": ["recommender", "recommendation", "recommender systems"],
            "template_id": "recommendation_system",
        },
        "knowledge_tracing": {
            "name": "Knowledge Tracing",
            "aliases": ["knowledge tracing", "kt", "tracing"],
            "template_id": "sequence_tracing",
        },
    },
}


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


__all__ = ["domain_pack", "list_tasks", "match_heading_to_task"]
