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

#------------------------------/------------------------------/------------------------------/
# Data Source Mappings
#------------------------------/------------------------------/------------------------------/
# Column candidates used in task extraction tables.
DATA_SOURCE_COLUMN_CANDIDATES: list[str] = [
    "Data sources",
    "Data source",
    "Dataset",
    "Datasets",
    "Data",
]

# Regexes are matched against a normalized lower-case key:
# e.g. "LMS logs" -> "lms logs"
#
# Keep this map deliberately conservative. Anything not matched will appear
# in the audit table and can be added later.
DATA_SOURCE_ALIAS_PATTERNS: dict[str, list[str]] = {
    "LMS/VLE logs": [
        r"\blms\b",
        r"\bvle\b",
        r"learning management system",
        r"virtual learning environment",
        r"moodle",
        r"blackboard",
        r"canvas",
        r"clickstream",
        r"click stream",
        r"event log",
        r"platform log",
        r"activity log",
        r"trace log",
        r'timestamps',
        r'course records',
        r'Learning resource/content interactions',
    ],

    "MOOC platform logs": [
        r"\bmooc\b",
        r"massive open online course",
        r"edx",
        r"coursera",
        r"open edx",
    ],

    "Student demographics/characteristics": [
        r"student demographic",
        r"learner demographic",
        r"student characteristic",
        r"learner characteristic",
        r"student profile",
        r"learner profile",
        r"gender",
        r"age",
        r"first generation",
        r"6. Personal/ Family Aspects",
        r'5. Job Alternative/ Career',
        r'Demographics',
        r'demographic data in enhanced versions',
    ],

    "Academic background records": [
        r"academic background",
        r"prior academic",
        r"previous academic",
        r"entry qualification",
        r"admission",
        r"specialization",
        r"major",
        r'Academic Records',
        r'Academic Records in University',
        r'Academic History and Ratings',
        r'Academic Information',
        r'Academic History',
        r'Acdemic Background',
        r'Academic Spreadsheets',
    ],

    "Assessment/performance records": [
        r"grade",
        r"grades",
        r"score",
        r"scores",
        r"mark",
        r"marks",
        r"gpa",
        r"assessment",
        r"exam",
        r"quiz",
        r"test result",
        r"performance",
        r"learner grade",
        r"student grade",
    ],

    "Administrative/SIS records": [
        r"student information system",
        r"\bsis\b",
        r"administrative",
        r"enrollment",
        r"enrolment",
        r"registration",
        r"course enrollment",
        r"course enrolment",
        r'Institutuional Data',
        r'Institutional Data',
        r'Enollment Data',
    ],

    "Forum/discussion data": [
        r"forum",
        r"discussion",
        r"post",
        r"reply",
        r"thread",
        r"message",
    ],

    "Exercise/question interactions": [
        r"student exercise interaction",
        r"exercise interaction",
        r"question interaction",
        r"answer sequence",
        r"answer sequences",
        r"response sequence",
        r"responses",
        r"transactions",
        r"user generated transaction",
        r"problem attempt",
        r"attempt data",
        r"option selected",
    ],

    "Question/Answer Sequences": [
        r'Sequence of Questions',
        r'Answer of Sequences',
        r'Sequence of Answers',
        r'Sequences of Answers',
        r'ITS answers',
        r'Exercise Sequence'
    ],

    "Learning Gains": [
        r'Learning Gains',
        r'Learning Gain',
        r'Learning Improvement',
        r'Pre-Test',
    ],


    "Exercise/question/Assignment metadata": [
        r'Question Text',
        r'Questions',
        r'Problem Difficulty',
        r'623 correct and 104',
        r'869',
        r'711 incorrect answers',
        r'Activity Metadata',
        r'Description of Activities Undertaken.',
        r'Activity Metadata',
        r"exercise metadata",
        r"question metadata",
        r'Answers',
        r'177',

    ],

    "Learning resource/content interactions": [
        r"resource view",
        r"page view",
        r"video visit",
        r"video view",
        r"lesson",
        r"learning resource",
        r"content access",
        r"reading activity",
    ],

    "Course/content metadata": [
        r"course catalog",
        r"course catalogue",
        r"course metadata",
        r"course description",
        r"lesson description",
        r'Course Information'

    ],

    "Knowledge Components/Concepts": [
        r"knowledge component",
        r"\bkc\b",
        r"knowledge concept",
        r"knowledge component tagging",
        r'Knowledge Concepts',
        r'topic taxonom',

    ],

    "Project/Code Assignments": [
        r'Code Submissions',
        r'Assignments',
        r'Programming submissions',

    ],

    "Survey data": [
        r"survey",
    ],

    "Questionnaire data": [
        r"questionnaire",
        r"self report",
        r"self reported",
        r"motivation",
        r"engagement scale",
        r'MSLQ',
    ],

    "External/Public datasets": [
        r"assistments",
        r'ASSIST17',
        r'ASSIST09',
        r'ASSIST12', 
        r"ednet",
        r"junyi",
        r"xes",
        r"open university learning analytics dataset",
        r"\boulad\b",
        r"public dataset",
        r"benchmark dataset",
        r'Algebra2005',
        r'ASSIST2009'
    ],
}

DATA_SOURCE_MISSING_VALUES: set[str] = {
    "",
    "None",
    "N/A",
    "NA",
    "Not Applicable",
    "None Specified",
    "Not Specified",
    "-",
}

TASK_DISPLAY_LABELS: dict[str, str] = {
    "PRED": "PRED",
    "DESC": "DESC",
    "KT": "KT",
    "REC": "ERS",
    "ERS": "ERS",
}

#------------------------------/------------------------------/------------------------------/
# Domain Pack Definition
#------------------------------/------------------------------/------------------------------/

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
    "DATA_SOURCE_COLUMN_CANDIDATES",
    "DATA_SOURCE_ALIAS_PATTERNS",
    "DATA_SOURCE_MISSING_VALUES",
    "TASK_DISPLAY_LABELS",
]
