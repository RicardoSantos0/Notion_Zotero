"""Prediction horizon/task summary helpers for manuscript tables."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from notion_zotero.analysis.cleaner import clean_table
from notion_zotero.analysis.original_db_summary import (
    GENERIC_VALUE_MAP,
    SEARCH_STRATEGY_COLUMNS,
    TYPO_FIXES,
)
from notion_zotero.analysis.summarizer import (
    build_summary_dataframes,
    is_accepted,
    load_canonical_records,
)
from notion_zotero.schemas.domain_packs.education_learning_analytics import (
    PREDICTION_HORIZON_ALIAS_PATTERNS,
    task_label_fn,
)

EARLY_ACTIONABLE_PATTERNS: list[str] = [
    r"before",
    r"pre.?course",
    r"at.*enroll",
    r"admission",
    r"registration",
    r"prior",
    r"start",
    r"beginning",
    r"first",
    r"early",
    r"week",
    r"month",
    r"semester",
    r"\byear\b",
    r"mid",
    r"half",
    r"during",
    r"every",
    r"ongoing",
    r"continuous",
    r"throughout",
    r"quarter",
    r"\b10%\b",
    r"\b25%\b",
    r"\b33%\b",
    r"\b50%\b",
]

POST_COURSE_PATTERNS: list[str] = [
    r"end\s*of\s*(the\s*)?course",
    r"post.?course",
    r"after\s*(the\s*)?course",
    r"final\s*(week|exam|assessment)",
    r"semester\s*end",
    r"course\s*complet",
    r"end\s*of\s*program",
    r"program\s*end",
    r"after\s*graduation",
]

DEPLOYED_IMPLEMENTED_PATTERNS: list[str] = [
    r"deployed\s*by\s*instructor",
    r"integrated\s*in\s*lms",
    r"classroom.*deploy",
    r"used\s*in\s*(production|practice)",
]

# Conservative Long-term patterns applied to supplementary fields (Courses, Students).
# These fields often mention 'university' or 'college' just as an institution name, so
# only unambiguously program-level vocabulary is matched here.
SUPPLEMENTARY_LONG_TERM_PATTERNS: list[str] = [
    r"\bprogram(me)?\b",      # program / programme
    r"\bdegree\b",
    r"\bbachelor",
    r"\bmaster",
    r"\bdoctoral",
    r"\bphd\b",
    r"\bmsc\b",
    r"\bbsc\b",
    r"\bmajor\b",             # college major
    r"graduat",
    r"persist",
    r"retention",
    r"first.?year\s*(student|cohort|engineering)",
    r"multi.?year",
    r"academic.?year",
    r"\d+\s*(cohort|academic\s*year)",  # e.g. "3 Cohorts of a Software Engineering Program"
]

# Moment of Prediction patterns that imply program-level scope (Long-term only).
# 'Before the course starts' is deliberately excluded — that is still Short-term
# (predicting a course outcome before the course). Only program/enrollment timing qualifies.
# Patterns are derived from actual values in the canonical data.
PROGRAM_MOMENT_LONG_TERM_PATTERNS: list[str] = [
    # Explicit program/degree framing
    r"(before|start|beginning)\s*(of\s*)?(the\s*)?program(me)?",
    r"end\s*of\s*(the\s*)?program(me)?",
    r"every\s*quarter\s*in\s*the\s*program(me)?",
    # Year-level milestones (multi-year = program-level)
    r"start\s*of\s*(the\s*)?first\s*year",          # 'Start of First Year'
    r"end\s*of\s*(the\s*)?first\s*year",            # 'End of First Year' (n=3)
    r"end\s*of\s*(second|2nd|third|3rd)\s*year",   # 'End of 2nd Year' (n=2)
    r"end\s*of\s*year\s*\d",                        # 'End of Year 2 (out of 4)'
    r"year\s*\d+\s*(of|out\s*of)\s*\d+",           # 'Year 2 (out of 4)'
    r"start\s*of\s*(new\s*)?academic\s*year",       # 'Start of New Academic Year' (n=3)
    r"end\s*of\s*(previous|prior)\s*semester",      # 'End of Previous Semester'
    r"before\s*start\s*of\s*next\s*semester",       # 'Before Start of Next Semester'
    # Admission / registration into a program
    r"time\s*of\s*admission",                       # 'Time of Admission at the MSc' (n=2)
    r"moment\s*of\s*(registration|admission)",      # 'Moment of Registration' (n=1)
    r"admission\s*of\s*student",                    # 'Admission of Student' (n=1)
    r"at\s*(enrollment|admission)\s*(into|to)?\s*(the\s*)?(program(me)?|degree|msc|bsc|university|college)",
    r"entering\s*(the\s*)?(program(me)?|degree|university|college)",
    r"first\s*(semester|year)\s*of\s*(the\s*)?(program(me)?|degree|study)",
]

# Context values that unambiguously imply item/session-level (Short-term) prediction.
# ITS platforms predict question correctness or session-level outcomes — never graduation.
CONTEXT_SHORT_TERM_PATTERNS: list[str] = [
    r"intelligent\s*tutoring",
    r"\bits\b",
    r"\bitss?\b",
]

# When these signals appear alongside Short-term matches, the row is Long-term only.
# Prevents incidental course-level vocabulary (e.g. the word "course") from
# overriding an explicitly program/graduation-level outcome.
STRONG_LONG_TERM_OVERRIDE_PATTERNS: list[str] = [
    r"graduat",
    r"\bdegree\b",
    r"persist",
    r"retention",
    r"\buniversity\b",
    r"\bcollege\b",
    r"\binstitution\b",
    r"academic.?year",
    r"multi.?year",
    r"transfer",
    r"first.?year",
]

REVIEWED_HORIZON_TITLE_PATTERNS: dict[str, list[str]] = {
    "Long-term": [
        r"multi-model heterogeneous ensemble",
        r"improved multi-view hypergraph",
        r"high-stakes examinations",
        r"early segmentation of students according to their academic performance",
        r"university student retention",
        r"university student dropout.*preference",
        r"mooc learner behavior prediction",
        r"master of data science program using admissions data",
        r"student achievement prediction using deep neural network from multi-source campus data",
    ],
    "Short-term": [
        r"academic performance of students with machine learning",
        r"time series interaction analysis",
        r"subscription-based online learning",
        r"deeplms",
        r"formative assessment.*learning outcomes",
        r"multimodal predictive student modeling",
        r"learning analytics should not promote one size fits all",
        r"estimate overall scores in tertiary preparatory general science",
        r"goal-based course recommendation",
        r"distance higher education using semi-supervised",
        r"ou analyse",
        r"supervised learning framework.*dropping out.*mooc",
        r"identifying at-risk students for early intervention",
        r"time-on-task estimation",
        r"evaluation of early student performance prediction",
        r"automl in educational data mining",
        r"small cohorts with minimal available attributes",
        r"delving deeper into mooc student dropout",
        r"enhancing educational evaluation",
    ],
}

REVIEWED_TARGET_OVERRIDE_RULES: list[tuple[str, list[str]]] = [
    ("Course Grade", [r"grade range.*a,\s*b,\s*c\s*and\s*f"]),
    ("AP Score", [r"\bap score\b"]),
    ("Graduation", [r"complete degree", r"graduates or drops out", r"graduation or dropout", r"graduation in expected time"]),
    ("Assessment", [r"upcoming assessment", r"next assessment"]),
    ("Delivery past the Deadline", [r"delay in submission", r"days of delay"]),
    ("GPA", [r"top\s*20%\s*gpa", r"bottom\s*20%\s*gpa", r"end of program mark", r"grade point average", r"to\s*x%\s*gpa"]),
    ("Exam Score", [r"performance groups.*low,\s*medium,\s*high"]),
    ("Course Grade", [r"being at risk of failing in a course", r"grades\s*\(weekly or final\)"]),
    ("Course Grade (High-Performing)", [r"high-performing student in a course"]),
    ("GPA trend", [r"trend of gpa"]),
    ("Dropout", [r"^dropout\b"]),
    ("Exam Grade", [r"summative assessment results"]),
    ("Course Grade", [r"academic performance.*grade"]),
    ("Assessment Grade", [r"post-test scores"]),
]

PRED_TARGET_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Dropout": [
        r"dropout",
        r"drop out",
        r"drop-out",
        r"withdraw",
        r"retention",
        r"persist",
        r"continue\s*\(1\)\s*vs",
        r"not\s*continue",
        r"\bcontinue\b.*\bnot\b",
    ],
    "GPA": [r"\bgpa\b", r"\bcgpa\b", r"grade point average"],
    "Graduation": [
        r"graduat",
        r"\bdegree\b",
    ],
    "Course Completion": [
        r"certificat",
        r"completion",
        r"complete",
    ],
    "Next Interaction / Question Outcome": [
        r"next.*interaction",
        r"quality of next interaction",
        r"next.*question",
        r"question.*correct",
        r"correctness",
    ],
}

AT_RISK_FRAMING_PATTERNS: list[str] = [
    r"at.?risk",
    r"risk of fail",
    r"risk of dropping",
    r"risk of dropout",
    r"low.perform",
    r"poor perform",
]

PASS_FAIL_PATTERNS: list[str] = [
    r"pass\s*(\(\d\))?\s*(vs|/|or)\s*fail",
    r"fail\s*(\(\d\))?\s*(vs|/|or)\s*pass",
    r"\bpass\b.*\bfail\b",
    r"\bfail\b.*\bpass\b",
    r"passed\s*\(?\d?\)?\s*(vs|/|or)\s*failed",
    r"success\s*\(?\d?\)?\s*(vs|/|or)\s*failure",
    r"succeeding\s*\(?\d?\)?\s*(vs|/|or)\s*failing",
    r"close\s*(to|of)\s*(fail|pass|passing|failing)",
    r"(near|almost|nearly)\s*(fail|pass)",
    r"delay.*vs.*timely|timely.*vs.*delay|late.*vs.*on.?time",
]

EXAM_PATTERNS: list[str] = [r"exam", r"cmbse"]
ASSESSMENT_PATTERNS: list[str] = [
    r"assessment",
    r"assignment",
    r"quiz",
    r"lab",
    r"submission",
    r"summative",
    r"formative",
]
COURSE_GRADE_PATTERNS: list[str] = [
    r"course.*grade",
    r"grade.*course",
    r"final.*grade",
    r"final.*mark",
    r"course.*score",
    r"course.*performance",
    r"end of course",
    r"student grade",
    r"grade letter",
    r"grade category",
    r"grade\s*\([a-f]",
    r"grade\s*(above|below)",
]
GENERIC_GRADE_SCORE_PATTERNS: list[str] = [
    r"grade",
    r"mark",
    r"score",
    r"performance",
    r"achievement",
]

AT_RISK_TIER_PATTERNS: list[str] = [
    r"at.?risk",
    r"\btop\s*\d+\s*%",
    r"\bbottom\s*\d+\s*%",
    r"(above|below)\s*(the\s*)?(median|mean|average)",
    r"performance\s*(tier|level|group|categor)",
    r"(low|high)\s*(perform|achiev)",
    r"sufficient\s*,\s*(average|good)",
    r"(exceptional|excellent|distinction)\s*,\s*(pass|fail)",
]

EMPTYISH_TEXT_PATTERNS: list[str] = [
    r"",
    r"n/?a",
    r"none",
    r"not\s*(reported|specified|stated|available)",
    r"unknown",
    r"-+",
]

LEARNING_OUTCOME_PATTERNS: list[str] = [
    r"cognitive",
    r"\bskill",
    r"learning.*(gain|outcome|result)",
    r"knowledge.*(gain|acqui)",
    r"recall\s*(rate|score)",
    r"competenc",
    r"academic\s*success",
]

TIME_TO_COMPLETION_PATTERNS: list[str] = [
    r"time.?(to|until|of).?(degree|graduat|complet|finish)",
    r"(years?|months?).?(to|until).?(degree|graduat|complet)",
    r"time.?to.?degree",
    r"years.?to.?degree",
]


def _require_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for PRED horizon summaries. "
            "Install the analysis extras with: pip install -e .[analysis]"
        ) from exc
    return pd


def _rows(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return [dict(row) for row in data if isinstance(row, Mapping)]
    if hasattr(data, "to_dict"):
        return data.to_dict("records")
    raise TypeError(f"Unsupported table input: {type(data)!r}")


def _as_text(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).lower()


def _has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value or "")


def _has_informative_text(value: Any) -> bool:
    text = _first_text(value).strip().lower()
    return bool(text) and not any(re.fullmatch(pattern, text) for pattern in EMPTYISH_TEXT_PATTERNS)


def classify_supervised_ml_task(value: Any) -> str | None:
    """Return ``Classification`` or ``Regression`` for supervised PRED rows."""
    text = str(value or "").strip().lower()
    if "classification" in text:
        return "Classification"
    if "regression" in text:
        return "Regression"
    return None


def classify_horizons(row: Mapping[str, Any]) -> list[str]:
    """Classify prediction horizon by outcome level.

    Short-term means course-level prediction. Long-term means program-level
    prediction. Generic dropout is not enough for long-term unless the row also
    signals a program, degree, institution, retention, persistence, enrollment,
    transfer, or graduation outcome.
    """
    return [horizon for horizon, _source in classify_horizons_with_source(row)]


def classify_horizons_with_source(row: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Classify prediction horizon and return the evidence source.

    Reviewed title overrides take precedence over aliases. This keeps generic
    terms such as dropout from becoming broad aliases while still recording
    manually reviewed paper-level decisions.
    """
    title_text = _as_text(
        row.get("source_title"),
        row.get("Paper title"),
        row.get("title"),
        row.get("Study"),
    )
    for horizon in ("Long-term", "Short-term"):
        if _has_any(title_text, REVIEWED_HORIZON_TITLE_PATTERNS[horizon]):
            return [(horizon, "reviewed paper-level override")]

    text = _as_text(row.get("Student Performance Definition"), row.get("Target"))
    labels: list[tuple[str, str]] = []
    if _has_any(text, PREDICTION_HORIZON_ALIAS_PATTERNS["Short-term"]):
        labels.append(("Short-term", "course-level alias"))
    if _has_any(text, PREDICTION_HORIZON_ALIAS_PATTERNS["Long-term"]):
        labels.append(("Long-term", "program-level alias"))

    # Supplementary Long-term signal from Courses / Students fields.
    # Scanned only against conservative program-level patterns to avoid false positives
    # from incidental institution names (e.g. "at University of X" in a course-grade study).
    supplementary_text = _as_text(row.get("Courses"), row.get("Students"))
    if supplementary_text.strip() and _has_any(supplementary_text, SUPPLEMENTARY_LONG_TERM_PATTERNS):
        if not any(h == "Long-term" for h, _ in labels):
            labels.append(("Long-term", "program-level context (Courses/Students)"))

    # Supplementary Long-term signal from Moment of Prediction.
    # Only specific program-level timing patterns qualify (e.g. "start of the program",
    # "at enrollment into the program"). Generic pre-course timing is excluded because
    # predicting a course outcome before the course starts is still Short-term.
    moment_text = _as_text(row.get("Moment of Prediction"))
    if moment_text.strip() and _has_any(moment_text, PROGRAM_MOMENT_LONG_TERM_PATTERNS):
        if not any(h == "Long-term" for h, _ in labels):
            labels.append(("Long-term", "program-level timing (Moment of Prediction)"))

    # ITS context overrides: Intelligent Tutoring Systems never predict program-level
    # outcomes. If an ITS context is present, demote any spurious Long-term label that
    # came only from supplementary fields (not from the primary target/definition text).
    context_text = _as_text(row.get("Context"))
    if context_text.strip() and _has_any(context_text, CONTEXT_SHORT_TERM_PATTERNS):
        # Remove Long-term labels sourced only from supplementary fields
        labels = [
            (h, src) for h, src in labels
            if h != "Long-term" or src == "program-level alias"
        ]
        # Add Short-term if still missing
        if not any(h == "Short-term" for h, _ in labels):
            labels.append(("Short-term", "ITS context (item/session-level)"))

    # Suppress incidental Short-term matches when strong Long-term signals dominate.
    # e.g. "graduation" or "degree" with an accidental "course" mention should be
    # Long-term only, not Both.
    if len(labels) > 1:
        horizons_found = {h for h, _ in labels}
        if "Long-term" in horizons_found and "Short-term" in horizons_found:
            if _has_any(text, STRONG_LONG_TERM_OVERRIDE_PATTERNS):
                labels = [(h, src) for h, src in labels if h != "Short-term"]

    # Final fallback: if no horizon found yet because Target / Student Performance
    # Definition are both empty, infer from the Courses field. If the field is
    # populated and lacks program-level vocabulary, treat it as course-level context.
    if not labels and not text.strip():
        courses_value = row.get("Courses")
        courses_text = _as_text(courses_value)
        if (
            _has_informative_text(courses_value)
            and not _has_any(courses_text, SUPPLEMENTARY_LONG_TERM_PATTERNS)
        ):
            labels.append(("Short-term", "course-level context (Courses field; empty primary fields)"))

    return labels


def classify_target_variable(row: Mapping[str, Any]) -> str:
    """Return the first obvious normalized target category for compatibility."""
    targets = classify_target_variables(row)
    return targets[0] if targets else "Other / ambiguous"


def classify_target_variables(row: Mapping[str, Any]) -> list[str]:
    """Return obvious normalized target categories.

    The aliases intentionally cover only clear cases. Ambiguous targets stay in
    ``Other / ambiguous`` so they can be reviewed manually.
    """
    target_text = _first_text(row.get("Target")).strip()
    if not target_text:
        target_text = _first_text(row.get("Student Performance Definition")).strip()
    text = _as_text(target_text)
    context_text = _as_text(row.get("Student Performance Definition"), target_text)
    targets: list[str] = []

    for target, patterns in REVIEWED_TARGET_OVERRIDE_RULES:
        if _has_any(context_text, patterns):
            targets.append(target)

    if _has_any(text, TIME_TO_COMPLETION_PATTERNS):
        targets.append("Time to completion")

    for target, patterns in PRED_TARGET_ALIAS_PATTERNS.items():
        if _has_any(context_text, patterns):
            targets.append(target)

    if _has_any(context_text, PASS_FAIL_PATTERNS):
        if _has_any(context_text, EXAM_PATTERNS):
            targets.append("Exam Grade")
        elif _has_any(context_text, ASSESSMENT_PATTERNS):
            targets.append("Assessment")
        else:
            targets.append("Course Grade")

    if _has_any(context_text, EXAM_PATTERNS) and _has_any(context_text, GENERIC_GRADE_SCORE_PATTERNS):
        if re.search(r"score", context_text):
            targets.append("Exam Score")
        else:
            targets.append("Exam Grade")
    elif _has_any(context_text, ASSESSMENT_PATTERNS) and _has_any(context_text, GENERIC_GRADE_SCORE_PATTERNS):
        targets.append("Assessment")
    elif _has_any(context_text, COURSE_GRADE_PATTERNS):
        targets.append("Course Grade")

    if "Time to completion" in targets:
        targets = [
            target
            for target in targets
            if target not in {"Graduation", "Course Completion"}
        ]
    if "Graduation" in targets:
        targets = [
            target
            for target in targets
            if target not in {"Dropout", "Course Completion"}
        ]
    elif "Dropout" in targets:
        targets = [target for target in targets if target != "Course Completion"]
    if any(target in {"Course Grade", "Exam Grade", "Exam Score", "Assessment"} for target in targets):
        targets = [
            target
            for target in targets
            if target
            not in {
                "GPA",
            }
        ]
    if not targets:
        if _has_any(text, LEARNING_OUTCOME_PATTERNS):
            targets.append("Learning outcome / skill")
    deduped = list(dict.fromkeys(targets))
    return deduped or ["Other / ambiguous"]


def has_at_risk_framing(row: Mapping[str, Any]) -> bool:
    """Return True when a target is framed as risk/performance-tier grouping."""
    return _has_any(
        _as_text(row.get("Student Performance Definition"), row.get("Target")),
        AT_RISK_FRAMING_PATTERNS + AT_RISK_TIER_PATTERNS,
    )


def raw_target_evidence(row: Mapping[str, Any]) -> str:
    """Return raw target text for audit/review columns."""
    values = [
        _first_text(row.get("Student Performance Definition")).strip(),
        _first_text(row.get("Target")).strip(),
    ]
    return " | ".join(dict.fromkeys(value for value in values if value))


def is_early_actionable_prediction(row: Mapping[str, Any]) -> bool:
    """Return True when prediction timing is before or during the course/program."""
    text = _as_text(row.get("Moment of Prediction"))
    if not text.strip():
        return False
    early = _has_any(text, EARLY_ACTIONABLE_PATTERNS)
    only_post_course = _has_any(text, POST_COURSE_PATTERNS) and not _has_any(
        text, [r"week", r"early", r"during", r"every", r"half", r"semester", r"\byear\b"]
    )
    return early and not only_post_course


def has_implemented_intervention_or_deployment(work_nature: Any, deployed: Any) -> bool:
    """Return True only for explicit deployment/integration evidence."""
    text = _as_text(_first_text(work_nature), _first_text(deployed))
    return _has_any(text, DEPLOYED_IMPLEMENTED_PATTERNS)


def build_pred_horizon_task_detail(dfs: Mapping[str, Any]):
    """Build paper-level rows behind the PRED horizon/task summary table."""
    pd = _require_pandas()
    pred_rows = _rows(dfs.get("PRED"))
    reading_rows = _rows(dfs.get("Reading List"))

    reading_by_id: dict[str, dict[str, Any]] = {}
    for row in reading_rows:
        paper_id = next(
            (str(row.get(col) or "") for col in ("page_id", "source_page_id", "id") if row.get(col)),
            "",
        )
        if paper_id:
            reading_by_id[paper_id] = row

    output_rows: list[dict[str, Any]] = []
    for row in pred_rows:
        task = classify_supervised_ml_task(row.get("Task"))
        if task is None:
            continue

        paper_id = str(row.get("source_page_id") or "")
        if not paper_id:
            continue

        reference = reading_by_id.get(paper_id, {})
        title = _first_text(reference.get("title") or row.get("source_title"))
        horizon_input = {**reference, **row, "Paper title": title}
        horizons = classify_horizons_with_source(horizon_input)
        if not horizons:
            continue

        implemented = has_implemented_intervention_or_deployment(
            reference.get("Work Nature"),
            reference.get("Deployed/ Deployable"),
        )
        for horizon, horizon_source in horizons:
            for target in classify_target_variables(row):
                output_rows.append(
                    {
                        "paper_id": paper_id,
                        "Paper title": title,
                        "Horizon": horizon,
                        "Horizon source": horizon_source,
                        "Supervised ML Task": task,
                        "Target Variable": target,
                        "Raw target evidence": raw_target_evidence(row),
                        "At-risk / tier framing": has_at_risk_framing(row),
                        "Early/actionable prediction": is_early_actionable_prediction(row),
                        "Implemented intervention or deployment": implemented,
                    }
                )

    if not output_rows:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "Paper title",
                "Horizon",
                "Horizon source",
                "Supervised ML Task",
                "Target Variable",
                "Raw target evidence",
                "At-risk / tier framing",
                "Early/actionable prediction",
                "Implemented intervention or deployment",
            ]
        )
    return pd.DataFrame(output_rows).drop_duplicates()


def find_unclassified_pred_horizon_rows(dfs: Mapping[str, Any]):
    """Return supervised PRED rows that still lack a horizon classification."""
    pd = _require_pandas()
    pred_rows = _rows(dfs.get("PRED"))
    reading_rows = _rows(dfs.get("Reading List"))

    reading_by_id: dict[str, dict[str, Any]] = {}
    for row in reading_rows:
        paper_id = next(
            (str(row.get(col) or "") for col in ("page_id", "source_page_id", "id") if row.get(col)),
            "",
        )
        if paper_id:
            reading_by_id[paper_id] = row

    output_rows: list[dict[str, Any]] = []
    for row in pred_rows:
        task = classify_supervised_ml_task(row.get("Task"))
        if task is None:
            continue

        paper_id = str(row.get("source_page_id") or "")
        if not paper_id:
            continue

        reference = reading_by_id.get(paper_id, {})
        title = _first_text(reference.get("title") or row.get("source_title"))
        horizon_input = {**reference, **row, "Paper title": title}
        if classify_horizons_with_source(horizon_input):
            continue

        output_rows.append(
            {
                "paper_id": paper_id,
                "Paper title": title,
                "Supervised ML Task": task,
                "Student Performance Definition": row.get("Student Performance Definition", ""),
                "Target": row.get("Target", ""),
                "Context": row.get("Context", ""),
                "Courses": row.get("Courses", ""),
                "Moment of Prediction": row.get("Moment of Prediction", ""),
            }
        )

    columns = [
        "paper_id",
        "Paper title",
        "Supervised ML Task",
        "Student Performance Definition",
        "Target",
        "Context",
        "Courses",
        "Moment of Prediction",
    ]
    if not output_rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(output_rows).drop_duplicates().reset_index(drop=True)


def _cleaned_summary_dataframes_from_canonical(
    canonical_dir: str | Path,
    *,
    accepted_only: bool,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    bundles = load_canonical_records(canonical_dir)
    if accepted_only:
        bundles = [bundle for bundle in bundles if is_accepted(bundle)]

    raw_dfs = build_summary_dataframes(bundles, task_label_fn=task_label_fn)
    cleaned_dfs: dict[str, Any] = {}
    clean_logs: dict[str, dict[str, Any]] = {}
    for name, df in raw_dfs.items():
        cleaned_dfs[name], clean_logs[name] = clean_table(
            df,
            typo_fixes=TYPO_FIXES,
            value_map=GENERIC_VALUE_MAP,
            search_strategy_columns=SEARCH_STRATEGY_COLUMNS,
        )
    return cleaned_dfs, clean_logs


def find_unclassified_pred_horizon_rows_from_canonical(
    canonical_dir: str | Path,
    *,
    accepted_only: bool = True,
):
    """Load canonical bundles and return supervised PRED rows lacking horizons."""
    cleaned_dfs, _logs = _cleaned_summary_dataframes_from_canonical(
        canonical_dir,
        accepted_only=accepted_only,
    )
    return find_unclassified_pred_horizon_rows(cleaned_dfs)


def build_pred_horizon_task_summary(dfs: Mapping[str, Any]):
    """Build the Horizon x supervised task x target manuscript table."""
    pd = _require_pandas()
    detail_df = build_pred_horizon_task_detail(dfs)
    summary_rows: list[dict[str, Any]] = []

    for horizon in ("Short-term", "Long-term"):
        for task in ("Classification", "Regression"):
            task_bucket = detail_df[
                (detail_df["Horizon"] == horizon)
                & (detail_df["Supervised ML Task"] == task)
            ]
            if task_bucket.empty:
                continue
            target_values = sorted(task_bucket["Target Variable"].dropna().unique())
            for target in target_values:
                bucket = task_bucket[task_bucket["Target Variable"] == target]
                raw_target_evidence = ""
                if not bucket.empty:
                    raw_target_evidence = " | ".join(
                        dict.fromkeys(
                            str(value)
                            for value in bucket["Raw target evidence"]
                            if str(value).strip()
                        )
                    )
                summary_rows.append(
                    {
                        "Horizon": horizon,
                        "Supervised ML Task": task,
                        "Target Variable": target,
                        "Number of Research Papers": bucket["paper_id"].nunique(),
                        "Papers with early/actionable prediction": bucket.loc[
                            bucket["Early/actionable prediction"], "paper_id"
                        ].nunique(),
                        "Papers with implemented intervention or deployment": bucket.loc[
                            bucket["Implemented intervention or deployment"], "paper_id"
                        ].nunique(),
                        "Papers with at-risk / tier framing": bucket.loc[
                            bucket["At-risk / tier framing"], "paper_id"
                        ].nunique(),
                        "Raw target evidence": raw_target_evidence,
                    }
                )

    return pd.DataFrame(summary_rows), detail_df


def build_pred_horizon_task_summary_from_canonical(
    canonical_dir: str | Path,
    *,
    accepted_only: bool = True,
):
    """Load canonical bundles, clean analysis tables, and build the PRED summary."""
    cleaned_dfs, clean_logs = _cleaned_summary_dataframes_from_canonical(
        canonical_dir,
        accepted_only=accepted_only,
    )

    summary_df, detail_df = build_pred_horizon_task_summary(cleaned_dfs)
    return summary_df, detail_df, clean_logs


def write_pred_horizon_task_summary_workbook(
    canonical_dir: str | Path = "data/pulled/notion/learning_analytics_review",
    output_path: str | Path = "data/analysis_outputs/pred_horizon_task_target_table.xlsx",
    *,
    accepted_only: bool = True,
) -> Path:
    """Write the PRED horizon/task summary workbook."""
    pd = _require_pandas()
    summary_df, detail_df, _logs = build_pred_horizon_task_summary_from_canonical(
        canonical_dir,
        accepted_only=accepted_only,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path) as writer:
        summary_df.to_excel(writer, sheet_name="target_table", index=False)
        detail_df.to_excel(writer, sheet_name="paper_level_detail", index=False)
    return path


__all__ = [
    "build_pred_horizon_task_detail",
    "build_pred_horizon_task_summary",
    "build_pred_horizon_task_summary_from_canonical",
    "classify_horizons",
    "classify_horizons_with_source",
    "classify_supervised_ml_task",
    "classify_target_variable",
    "classify_target_variables",
    "find_unclassified_pred_horizon_rows",
    "find_unclassified_pred_horizon_rows_from_canonical",
    "has_at_risk_framing",
    "has_implemented_intervention_or_deployment",
    "is_early_actionable_prediction",
    "raw_target_evidence",
    "write_pred_horizon_task_summary_workbook",
]
