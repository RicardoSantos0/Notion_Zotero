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
        r'CourseKata online textbook trace data',
        r'ITS logs',
        r'Mouse and Keyboard clicks',
        r'Learner-Activity Record',
        r"resource view",
        r"page view",
        r"video visit",
        r"video view",
        r"lesson",
        r"learning resource",
        r"content access",
        r"reading activity",
        r'Engagament Status',
        r'Learner-word session traces',
        r'Video Interactions',
        r'Video-Interactions',
        r'Code Traces',

    ],

    "MOOC platform logs": [
        r"\bmooc\b",
        r"massive open online course",
        r"edx",
        r"coursera",
        r"open edx",
        r'MoocRadar',
        r'Tomplay',
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
        r'Demographics',
        r'demographic data in enhanced versions',
        r"personal\s*family",
        r'LearnerProfile',
        r'Demographic Information',
        r'3. Financial Aspects',
        r'Demograhic Data',
        r'Vacation Information',
        r'Socio-Economic Data',
        r'Student and Family characteristics',
        r'Socio-Demographic Variables',
        r'Student Demograohics',

    ],

    "Academic background records": [
        r"academic background",
        r"prior academic",
        r"previous academic",
        r"entry qualification",
        r"admission",
        r"major",
        r'Academic Records',
        r'Academic Records in University',
        r'Academic History and Ratings',
        r'Academic Information',
        r'Academic History',
        r'Acdemic Background',
        r'Academic Spreadsheets',
        r'Highschool History and Characteristics',
        r'University student records',
        r'Pre-University Variables',
        r'School Characteristics', 
    ],

    "Professional background records": [
        r"Curriculum PDFs",
        r"Professional background",
        r"work experience",
        r"employment history",
        r"job history",
        r'5. Job Alternative/ Career',
        r"job alternative",
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
        r'Learner Results',
        r'Student Reports',
        r'Number of Credits Completed in First Year',

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
        r'MicroOERProfile',
        r'Student Infornation System',

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
        r'In-Question activities',  
    ],

    "Question/Answer Sequences": [
        r'Sequence of Questions',
        r'Answer of Sequences',
        r'Sequence of Answers',
        r'Sequences of Answers',
        r'ITS answers',
        r'Exercise Sequence',
        r'Question Sequences',

    ],

    "Learning Gains": [
        r'Learning Gains',
        r'Learning Gain',
        r'Learning Improvement',
        r'Pre-Test',
        r'Knowledge Topics',
        r'Math',
        r'Transfer Test',

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
        r'Difficulty',
        r'1',
        r'Exercise Sentences',
        r'Question Sentences',
        r'Question Attributes',
        r'Question Attribtutes',

    ],

    "Course/content metadata": [
        r"course catalog",
        r"course catalogue",
        r"course metadata",
        r"course description",
        r"lesson description",
        r'Course Information',
        r'chapter summaries',
        r'Course Semantic Information',
        r'Course and professor Metadata',
        r'Course Learning Outcomes',
        r'Course Descriptors',
        r'PLO Description',
        r'Learning Objects',
        r'e-Textbook',
        r'Module presentation',
        r'course2vec embeddings',

    ],

    "In-Class Behavior": [
        r"classroom",
        r"attendance",
        r"Attendance Records",
        r'Conversational transcripts',

    ],

    "Knowledge Components/Concepts": [
        r"knowledge component",
        r"\bkc\b",
        r"knowledge concept",
        r"knowledge component tagging",
        r'Knowledge Concepts',
        r'topic taxonom',
        r'Course Pre-Requisites embeddings',
        r'Association',
        r'Pre-requisite Concept Mapping',
        r'concept/outcome mappings',

    ],

    "Project/Code Assignments": [
        r'Code Submissions',
        r'Assignments',
        r'Programming submissions',
        r'Assignment submissions',
        r'Submission Records',
        r'Submissions',
        r'Term Paper Proposal',

    ],

    "Survey data": [
        r"survey",
        r'– Student DNU feedback logs',

    ],

    "Questionnaire/ Interview data": [
        r"questionnaire",
        r"self report",
        r"self reported",
        r"motivation",
        r"engagement scale",
        r'MSLQ',
        r'Interviews',
        r'Preferences',
        r'Perfect Solution for each task',
        r'4. Study Conditions',
        r'Contextual Information',
        r'– Student reflection texts (2 prompts per week)',
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
        r'ASSIST2009',
        r'Eedi',
    ],

    "Wearable Devices/ Sensors": [
        r"eye tracking",
        r"wearable",
        r"sensor",
        r"physiological",
        r"biometric",
        r'Eye-Tracking Data',
        r'Eye-Tracking',
        r'Eye-Tracker and Facial Expression',
        r'NIPS34',
        r'Observational Instrutments',
        r'Peripheral Data',
        r'Headset',
        r'Think-Aloud records',
    ],
    
    "In-Campus Behavioral Data": [
        r'In-Campus Behavioral Data',
        r'Library Visits',
        r'Campus Facility Usage',
        r'On-Campus Event Attendance',
        r'Library',
        r'Library Access Control'
        r'Consumption Data',
        r'Digital Card interactions with Campus Infrastructure',
        r'Once-Card Consumption',
    ],

    "Social Data/ Networks": [
        r"social network",
        r"social data",
        r"peer interaction",
        r"collaboration",
        r"social relationship",
        r'Peer Interactions',
        r'Social Networks',
        r'Collaborative Learning Data',
        r'Social tags',
        r'Social Networks',
    ],

    "External Websites/Apps usage": [
        r'Websites/App usage data',
        r'Web Browsing',
        r'GitLab commits',
        r'GitLab issues',
        r'Application data',
        r'Gateway Logins',
        r'Learning Tools',
        r'- Wikipedia Articles',
    ],

    "Instructor Behavior/Interventions": [
        r'Instructor Behavior/Interventions',
        r'Instructor Interventions',
        r'Feedback from Instructors',
        r'Course Instructor Behavior',
    ],

    "Others": [
        r"other",
        r"miscellaneous",
        r"various",
        r"multiple",
        r"mixed",
        r'There is no representation of the users. Instead it is solely based on the content provided.',
        r'Available Time',
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
