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


# Re-export apply_overrides from the lightweight overrides module so callers that
# import directly from pred_horizon_summary still get the function.
from notion_zotero.analysis.overrides import apply_overrides  # noqa: E402

# ---------------------------------------------------------------------------
# 10-dimension taxonomy classifier (STEP 2 — T3.3)
# classify_contribution() returns per-dimension DimensionResult dicts.
# Binding schema: docs/classify_contribution_schema.md v1.0 (d-032 approved).
# Primary signal: raw_evidence. Falls back to Title-Case and snake_case field
# aliases gracefully (d-032 constraint).
# ---------------------------------------------------------------------------

# --- Vocabulary tables ---

_VOCAB: dict[str, list[str]] = {
    "supervised_ml_task": [
        "classification", "regression", "survival", "ranking",
        "sequence_forecast", "other",
    ],
    "outcome_scope": [
        "interaction_or_item", "assessment", "course_or_module",
        "term_or_semester", "program_or_degree", "institution_or_system",
        "mixed_or_multiple", "unclear",
    ],
    "unit_of_analysis": [
        "learner_item_interaction", "learner_assessment", "learner_course",
        "learner_term", "learner_program", "learner_institution",
        "cohort_or_group", "unclear",
    ],
    "target_construct": [
        "grade_or_score", "pass_fail_or_success_failure",
        "at_risk_or_performance_tier", "dropout_or_withdrawal",
        "retention_or_persistence", "completion_or_certification",
        "graduation_or_degree_completion", "gpa_or_cumulative_performance",
        "next_interaction_correctness", "submission_timing_or_delay",
        "learning_gain_or_skill_mastery", "enrolment_or_course_selection",
        "time_to_completion", "other_or_unclear",
    ],
    "prediction_timing": [
        "before_course_or_at_course_enrolment", "early_course",
        "mid_course", "late_course", "end_of_course_or_post_course",
        "before_program_or_at_admission", "program_milestone",
        "continuous_or_repeated", "unclear",
    ],
    "actionability_status": [
        "retrospective_only", "early_backtest_only", "tested_on_new_students",
        "deployed_or_deployable", "deployed_with_intervention_evaluation",
        "unclear",
    ],
    "risk_framing": ["yes", "no", "unclear"],
    "evidence_quality": ["high", "medium", "low"],
    "cv_design": ["random_fold", "temporal_or_prospective", "unclear"],
    "context_type": ["HEI", "MOOC", "ITS", "mixed", "unclear"],
    "outcome_horizon": ["short_term", "long_term", "mixed", "unclear"],
    "outcome_basis": [
        "assessment_grade", "assessment_pass_fail",
        "course_final_grade", "course_pass_fail", "performance_tier",
        "course_completion_or_dropout",
        "graduation_or_degree_completion", "program_dropout_or_withdrawal",
        "retention_or_persistence", "time_to_degree", "cumulative_gpa",
        "program_milestone_exam",
        "not_applicable", "unclear",
    ],
}

# Mapping outcome_scope -> outcome_horizon by the semester boundary (d-043):
# within current semester => short_term; beyond one semester => long_term.
_HORIZON_BY_SCOPE = {
    "interaction_or_item": "short_term",
    "assessment": "short_term",
    "course_or_module": "short_term",
    "term_or_semester": "short_term",
    "program_or_degree": "long_term",
    "institution_or_system": "long_term",
    "mixed_or_multiple": "mixed",
    "unclear": "unclear",
}

# --- Field-alias helpers ---

def _get_field(row: Mapping[str, Any], *keys: str) -> str:
    """Return the first non-empty value among the given keys (case-insensitive lookup)."""
    for key in keys:
        val = row.get(key)
        if val is None:
            # Title-Case variant
            title_key = key.replace("_", " ").title()
            val = row.get(title_key)
        if val is not None:
            text = str(val).strip()
            if text:
                return text
    return ""


def _text(*parts: str) -> str:
    """Concatenate parts, lowercased."""
    return " ".join(p.lower() for p in parts if p)


def _matches(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, re.IGNORECASE))


def _any_match(patterns: list[str], text: str) -> bool:
    return any(_matches(p, text) for p in patterns)


# --- DimensionResult factory ---

def _ok(label: str, confidence: str, evidence: str) -> dict[str, Any]:
    return {"label": label, "confidence": confidence, "evidence": evidence}


def _conflict(candidates: list[str], evidence_span: str) -> dict[str, Any]:
    cand_str = " vs ".join(candidates)
    return {
        "label": "unclear",
        "confidence": "low",
        "evidence": f"CONFLICT: {cand_str} — {evidence_span}; routed to audit",
        "conflict_flag": True,
    }


# --- Per-dimension classifiers ---

def _classify_supervised_ml_task(row: Mapping[str, Any]) -> dict[str, Any]:
    raw_task = _get_field(row, "raw_task", "Task")
    raw_task_l = raw_task.lower()
    evidence_text = _get_field(row, "raw_evidence", "raw_models", "Models")

    if "classification" in raw_task_l:
        return _ok("classification", "high", f"raw_task='{raw_task}'")
    if "regression" in raw_task_l:
        return _ok("regression", "high", f"raw_task='{raw_task}'")
    if "clustering" in raw_task_l:
        return _ok("other", "high", f"raw_task='{raw_task}' (clustering -> other)")

    # Infer from raw_evidence / models
    ev = _text(evidence_text)
    if _any_match([r"cox\s*regression", r"survival\s*anal", r"kaplan", r"time.to.event"], ev):
        return _ok("survival", "medium", f"inferred from models: '{evidence_text}'")
    if _any_match([r"knowledge\s*trac", r"\bdkt\b", r"deep\s*knowledge", r"next.{0,10}(question|item|interact)"], ev):
        return _ok("sequence_forecast", "medium", f"inferred from models: '{evidence_text}'")
    if _any_match([r"classif"], ev):
        return _ok("classification", "medium", f"inferred from evidence: '{evidence_text}'")
    if _any_match([r"regress"], ev):
        return _ok("regression", "medium", f"inferred from evidence: '{evidence_text}'")

    if raw_task:
        return _ok("other", "low", f"raw_task='{raw_task}' not mapped to standard vocab")
    return _ok("other", "low", "no raw_task field; could not infer from evidence")


def _classify_context_type(row: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic gazetteer on raw_context (+ raw_evidence fallback)."""
    raw_ctx = _get_field(row, "raw_context", "Context")
    ev = _get_field(row, "raw_evidence")
    combined = _text(raw_ctx, ev)

    mooc_pats = [
        r"\bmooc\b", r"\bedx\b", r"coursera", r"futurelearn", r"udemy",
        r"open\s*enrollment", r"massive\s*open", r"online\s*course",
    ]
    its_pats = [
        r"intelligent\s*tutor", r"\bits\b", r"assistments", r"khan\s*academy",
        r"tutoring\s*system", r"adaptive\s*exercise",
    ]
    hei_pats = [
        r"higher\s*education", r"\buniversity\b", r"\bcollege\b",
        r"undergraduate", r"\bhei\b", r"degree\s*program",
        r"social\s*networks\s*in\s*higher",
    ]

    hits: list[str] = []
    if _any_match(mooc_pats, combined):
        hits.append("MOOC")
    if _any_match(its_pats, combined):
        hits.append("ITS")
    if _any_match(hei_pats, combined):
        hits.append("HEI")

    if len(hits) > 1:
        return _ok("mixed", "medium", f"multiple context signals: {hits} in '{raw_ctx}'")
    if len(hits) == 1:
        return _ok(hits[0], "high", f"gazetteer match '{hits[0]}' in raw_context='{raw_ctx}'")
    if raw_ctx:
        return _ok("unclear", "low", f"raw_context='{raw_ctx}' not mapped; full-text review needed")
    return _ok("unclear", "low", "raw_context field absent")


def _classify_outcome_scope(row: Mapping[str, Any], ctx_label: str) -> dict[str, Any]:
    """Hybrid: rules on raw_evidence + MOOC-dropout disambiguation rule.

    Consults the exported "Learner Population" description (d-043 review) to
    disambiguate institutional/program-level dropout from course-level dropout.
    """
    spd = _get_field(row, "raw_student_performance_definition", "Student Performance Definition")
    tgt = _get_field(row, "raw_target", "Target")
    ev = _get_field(row, "raw_evidence")
    moment = _get_field(row, "raw_moment_of_prediction", "Moment of Prediction")
    combined = _text(spd, tgt, ev)
    # Exported Notion descriptions — high-signal for HEI/program vs course scope.
    lp = _get_field(row, "raw_learner_population", "Learner Population")
    sample = _get_field(row, "raw_sample_setting")
    desc = _text(lp, sample)

    # Interaction/item level — must check before course patterns
    if _any_match([
        r"next.{0,10}(question|item|attempt|interact)",
        r"question\s*correct",
        r"correctness",
        r"knowledge\s*trac",
        r"\bitem\b",
    ], combined):
        return _ok("interaction_or_item", "high",
                   f"item-level signal in '{combined[:80]}'")

    # Assessment level
    if _any_match([
        r"\bassignment\b", r"\bquiz\b", r"\blab\b",
        r"assessment\s*(score|mark|grade|result)",
        r"submission\s*(timing|delay|deadline)",
    ], combined) and not _any_match([r"final\s*(grade|mark|exam)", r"course\s*grade"], combined):
        return _ok("assessment", "high", f"assessment-level signal in '{combined[:80]}'")

    # Program/degree level signals (checked before course to avoid "course in program" confusion)
    prog_pats = [
        r"graduat", r"\bdegree\b", r"retention", r"persist",
        r"years?\s*to\s*(degree|graduat|complet)", r"time\s*to\s*degree",
        r"program(me)?\s*(complet|level|outcome)",
        r"end\s*of\s*program(me)?",
        r"first.?year\s*(student|retention|survival)",
        r"dropout.*program|program.*dropout",
    ]
    # Graduation-level moment of prediction
    moment_prog = _any_match([
        r"end\s*of\s*(the\s*)?program(me)?",
        r"(start|beginning)\s*(of\s*)?(the\s*)?program(me)?",
        r"time\s*of\s*admission", r"admission\s*of\s*student",
        r"end\s*of\s*(first|1st|second|2nd|third|3rd)\s*year",
    ], _text(moment))

    if _any_match(prog_pats, combined) and not _any_match([r"course\s*(grade|complet|pass)", r"mooc.*dropout", r"dropout.*mooc"], combined):
        return _ok("program_or_degree", "high", f"program-level signal in '{combined[:80]}'")

    # MOOC dropout rule: if context=MOOC and dropout/completion -> course_or_module
    if ctx_label == "MOOC" and _any_match([r"dropout", r"drop.out", r"complet", r"certif", r"withdraw"], combined):
        return _ok("course_or_module", "high",
                   "MOOC dropout disambiguation rule: context_type=MOOC => outcome_scope=course_or_module")

    # Term/semester GPA (end-of-semester GPA, not cumulative)
    if _any_match([r"semester\s*gpa", r"term\s*gpa", r"end.of.semester\s*gpa"], combined):
        return _ok("term_or_semester", "high", f"semester GPA signal in '{combined[:80]}'")

    # Program-level dropout/withdrawal disambiguation (d-043 review): institutional /
    # degree dropout is LONG-TERM and must be caught BEFORE the bare-dropout course
    # rule below (which would otherwise force course_or_module). Uses the exported
    # "Learner Population" description + program-level moment signals. MOOC/course-
    # explicit dropout is excluded and stays course_or_module.
    if _any_match([r"dropout", r"drop.out", r"withdraw", r"attrition",
                   r"not\s*(re)?registr", r"not\s*continu"], combined) \
            and ctx_label != "MOOC" \
            and not _any_match([r"course\s*dropout", r"\bmooc\b"], _text(combined, desc)):
        _prog_signal = moment_prog or _any_match([
            r"\bdegree\b", r"\bprogram(me)?\b", r"institution",
            r"first.?year", r"second.?year", r"third.?year", r"\d(st|nd|rd|th)\s*year",
            r"undergraduate", r"freshman", r"retention", r"persist",
        ], _text(combined, desc, moment))
        if _prog_signal:
            return _ok("program_or_degree", "high",
                       "institutional/program dropout (learner_population/moment) -> "
                       f"program_or_degree; lp='{lp[:60]}' moment='{moment[:40]}'")

    # Course-level patterns
    course_pats = [
        r"course\s*(grade|pass|fail|score|performance|complet|dropout)",
        r"final\s*(grade|mark|exam|score)",
        r"mooc", r"module", r"pass\s*(vs|/|or)\s*fail",
        r"end\s*of\s*course", r"course.level",
        r"dropout", r"drop.out", r"withdraw",
    ]
    if _any_match(course_pats, combined):
        return _ok("course_or_module", "high", f"course-level signal in '{combined[:80]}'")

    # Program level with moment signals
    if moment_prog or _any_match(prog_pats, combined):
        return _ok("program_or_degree", "medium",
                   f"program-level timing/signal in moment='{moment}' or text")

    # Generic grade/score without course or program context
    if _any_match([r"\bgpa\b", r"\bcgpa\b", r"grade\s*point\s*average", r"cumulative.*grade"], combined):
        return _ok("program_or_degree", "medium", "cumulative GPA signal -> likely program scope")

    if _any_match([r"\bgrade\b", r"\bscore\b", r"\bmark\b", r"performance"], combined):
        return _ok("course_or_module", "medium", "generic grade signal, defaulting to course_or_module")

    if combined.strip():
        return _ok("unclear", "low", f"no scope signal found in '{combined[:80]}'")
    return _ok("unclear", "low", "evidence fields empty")


def _classify_target_construct(row: Mapping[str, Any]) -> dict[str, Any]:
    """Gazetteer + conflict detection."""
    spd = _get_field(row, "raw_student_performance_definition", "Student Performance Definition")
    tgt = _get_field(row, "raw_target", "Target")
    ev = _get_field(row, "raw_evidence")
    combined = _text(spd, tgt, ev)

    # --- Stage 1: Unambiguous high-priority patterns ---

    # Next interaction correctness (highest priority — very specific)
    if _any_match([
        r"next.{0,10}(question|item|attempt).{0,10}correct",
        r"next.{0,10}interact",
        r"question\s*correctness",
        r"\bcorrectness\b",
        r"knowledge\s*trac",
    ], combined):
        return _ok("next_interaction_correctness", "high",
                   f"next-interaction correctness pattern in '{combined[:80]}'")

    # Time to completion
    if _any_match([
        r"time.{0,5}to.{0,5}(degree|graduat|complet|finish)",
        r"years?.{0,5}to.{0,5}(degree|graduat|complet)",
        r"\btime.to.degree\b",
    ], combined):
        return _ok("time_to_completion", "high", f"time-to-completion pattern in '{combined[:80]}'")

    # Submission timing / delay
    if _any_match([
        r"submission.{0,10}(delay|timing|late|deadline)",
        r"delay.{0,10}submission",
        r"delivery.{0,10}past.*deadline",
        r"days?\s*of\s*delay",
    ], combined):
        return _ok("submission_timing_or_delay", "high",
                   f"submission timing/delay pattern in '{combined[:80]}'")

    # GPA / cumulative performance — checked BEFORE graduation (disambiguation rule:
    # "GPA at graduation" = gpa_or_cumulative_performance, not graduation_or_degree_completion).
    if _any_match([r"\bgpa\b", r"\bcgpa\b", r"grade\s*point\s*average",
                   r"end\s*of\s*program\s*mark", r"top\s*\d+\s*%\s*gpa",
                   r"bottom\s*\d+\s*%\s*gpa", r"gpa\s*trend"], combined):
        return _ok("gpa_or_cumulative_performance", "high",
                   f"GPA pattern in '{combined[:80]}'")

    # Graduation / degree completion.
    # Precision fix (Change B): exclude "undergraduate" — the word "graduat" appears
    # inside "undergraduate" but refers to a student level, not a graduation outcome.
    # Pattern uses negative lookbehind for "under" so "undergraduate course" does not
    # erroneously trigger graduation_or_degree_completion.
    if _any_match([
        r"(?<!under)graduat(?!ion.{0,5}(risk|course))",
        r"complete\s*degree",
        r"graduates?\s*(or|vs)\s*drops?\s*out",
        r"graduation\s*(or|vs|in)\s*(dropout|expected|time)",
    ], combined) and not _any_match([r"dropout.*graduat|graduat.*dropout.*course"], combined):
        return _ok("graduation_or_degree_completion", "high",
                   f"graduation/degree pattern in '{combined[:80]}'")

    # Retention / persistence
    if _any_match([r"retention", r"\bpersist", r"continue.*enrol", r"first.?year.*surviv"], combined) \
            and not _any_match([r"at.risk", r"risk\s*of\s*fail"], combined):
        return _ok("retention_or_persistence", "high",
                   f"retention/persistence pattern in '{combined[:80]}'")

    # Enrolment / course selection
    if _any_match([r"\benrol", r"course\s*selection", r"recommendation\s*system",
                   r"continue.*post.grad", r"post.graduate\s*studies"], combined):
        return _ok("enrolment_or_course_selection", "medium",
                   f"enrolment/course-selection pattern in '{combined[:80]}'")

    # Learning gain / skill mastery
    if _any_match([
        r"learning\s*gain", r"skill\s*master", r"knowledge\s*(gain|acqui)",
        r"cognitive\s*(skill|level)", r"competenc",
    ], combined):
        return _ok("learning_gain_or_skill_mastery", "high",
                   f"learning gain/skill mastery pattern in '{combined[:80]}'")

    # Dropout / withdrawal (standalone)
    if _any_match([
        r"\bdropout\b", r"\bdrop.out\b", r"\bwithdraw", r"\battrition\b",
        r"continue\s*\(?1\)?\s*(vs|or)\s*not", r"not\s*continue",
    ], combined):
        # Check conflict with completion
        if _any_match([r"\bcompletion\b", r"\bcomplete\b", r"\bcertif"], combined):
            # Could be dropout vs completion phrasing — check for "or"
            if _any_match([r"dropout\s*or\s*complet|complet\s*or\s*dropout",
                           r"dropout.*vs.*complet|complet.*vs.*dropout"], combined):
                return _conflict(
                    ["dropout_or_withdrawal", "completion_or_certification"],
                    f"dropout vs completion ambiguity in '{combined[:80]}'"
                )
        return _ok("dropout_or_withdrawal", "high",
                   f"dropout/withdrawal pattern in '{combined[:80]}'")

    # Conflict check: "grade or completion" / "Course Grade or Completion" patterns.
    # This MUST run before the simple completion_or_certification return below to ensure
    # "Course Grade or Completion" is flagged as a CONFLICT (test-R-004-002).
    if _any_match([
        r"\bgrade\b.{0,10}\bor\b.{0,10}\bcomplet",
        r"\bcomplet.{0,10}\bor\b.{0,10}\bgrade\b",
    ], combined):
        return _conflict(
            ["grade_or_score", "completion_or_certification"],
            f"'grade or completion' ambiguity in '{combined[:80]}'",
        )

    # Completion / certification (after dropout and conflict checks)
    if _any_match([r"\bcompletion\b", r"\bcomplete\b", r"\bcertif", r"certificat"], combined):
        return _ok("completion_or_certification", "high",
                   f"completion/certification pattern in '{combined[:80]}'")

    # Completion / certification via "completed vs abandoned" or similar binary outcome
    # framing (must run before Stage 2 pass/fail to catch "Completed (0) vs Abandoned (1)").
    if _any_match([
        r"completed\s*\(?\d?\)?\s*(vs|/|or)\s*abandoned",
        r"abandoned\s*\(?\d?\)?\s*(vs|/|or)\s*completed",
        r"completing\s*(their|the)\s*(program|course|degree|studies)",
    ], combined) and not _any_match([r"\bdropout\b", r"\bdrop.out\b"], combined):
        return _ok("completion_or_certification", "high",
                   f"completed-vs-abandoned or 'completing their program' pattern in '{combined[:80]}'")

    # --- Stage 2: Performance disambiguation ---
    # Collect candidates for potential conflict detection

    candidates: list[str] = []

    # At-risk / performance tier (risk label is the actual outcome variable)
    if _any_match([
        r"at.?risk\s*(tier|group|label|score|flag|categor)",
        r"performance\s*(tier|level|group|cluster|category)",
        r"top\s*\d+\s*%", r"bottom\s*\d+\s*%",
        r"(above|below)\s*(the\s*)?(median|mean|average)",
        r"(low|high).perform\w*\s+student",  # "low-performing student" as outcome
        r"risk\s*score", r"risk\s*label",
    ], combined):
        candidates.append("at_risk_or_performance_tier")

    # Pass/fail — extended patterns to cover all binary outcome phrasings
    pf_pats = [
        r"pass\s*(\([^)]{0,10}\))?\s*(vs|/|or)\s*fail",   # Pass (>=5) vs Fail, Pass (1) vs Fail
        r"fail\s*(\([^)]{0,10}\))?\s*(vs|/|or)\s*pass",   # Fail (<5) vs Pass
        r"\bpass\b.{0,15}\bfail\b",                        # pass ... fail (up to 15 chars)
        r"\(pass\).{0,15}\(fail\)",                        # (Pass) ... (Fail)
        r"\(fail\).{0,15}\(pass\)",                        # (Fail) ... (Pass)
        r">?\s*\d+\s*\(pass\)\s*(vs|/|or)\s*>?\s*\d+\s*\(fail\)",  # >40 (Pass) vs >40 (Fail)
        r"\(?pass\)?\s*(vs|/|or)\s*\(?fail\)?",            # Pass vs Fail, (pass) vs (fail)
        r"success\s*(\([^)]{0,10}\))?\s*(vs|/|or)\s*failure",  # Success (1) vs Failure (0)
        r"failure\s*(\([^)]{0,10}\))?\s*(vs|/|or)\s*success",  # Failure (0) vs Success (1)
        r"succeeding\s*(vs|/|or)\s*failing",
        r"failing\s*(vs|/|or)\s*succeeding",               # Failing (1) vs Succeeding (0)
        r"\bfailing\b.{0,10}\bsucceeding\b",               # failing ... succeeding
        r"\bsucceeding\b.{0,10}\bfailing\b",
        r"close\s*(to|of)\s*(fail|pass)",
        r"being\s*at\s*risk\s*of\s*failing",
        r"risk\s*of\s*fail",
        r"safe\s*\)?\s*(vs|/|or)\s*at.risk",              # Safe vs At-risk (binary pass/fail framing)
    ]
    if _any_match(pf_pats, combined):
        candidates.append("pass_fail_or_success_failure")

    # Grade or score (continuous) — only match when binary pass/fail is NOT present
    # to prevent grade-context words ("student grade") from overriding explicit binary outcomes
    grade_pats = [
        r"final\s*(grade|mark|score|exam\s*score)",
        r"course\s*(grade|mark|score|performance)",
        r"exam\s*(grade|score|result|mark)",
        r"assessment\s*(grade|score|mark|result)",
        r"grades?\s*(range|letter|category|group|level|above|below|from\s*[a-f])",
        r"grade\s*\(?[a-f]\)?",
        r"performance\s*(group|level)\s*(low|med|high)",
        r"academic\s*performance",
        r"student\s*grades?",
        r"ap\s*score",
        r"post.test\s*score",
        r"\bmark\b",
        # Ordinal grade category lists (e.g. "Exceptional, Excellent, Distinction, Pass, Fail")
        r"(distinction|excellent|exceptional).{0,30}(pass|fail)",
        r"grades?\s*categor",
        # Ordinal letter-grade classification (e.g. "A vs B or C", "weekly or final" grades)
        r"\b[a-f]\s*(vs|/|or)\s*[a-f]\b",              # A vs B or C
        r"grades?\s*\(weekly\s*or\s*final\)",
        r"(weekly|final)\s*grades?",
    ]
    if _any_match(grade_pats, combined):
        candidates.append("grade_or_score")

    # Conflict check: "Course Grade or Completion" pattern and similar
    # If both grade/score and completion/certification appear explicitly
    if _any_match([r"\bgrade\b.{0,10}\bor\b.{0,10}\bcomplet",
                   r"\bcomplet.{0,10}\bor\b.{0,10}\bgrade\b"], combined):
        cands_named = []
        if "grade_or_score" not in candidates:
            candidates.append("grade_or_score")
        cands_named = ["grade_or_score", "completion_or_certification"]
        return _conflict(cands_named,
                         f"'grade or completion' ambiguity in '{combined[:80]}'")

    # Deduplicate preserving order; if exactly one candidate, return it
    seen: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.append(c)

    if len(seen) == 1:
        return _ok(seen[0], "high", f"performance pattern -> '{seen[0]}' in '{combined[:80]}'")

    if len(seen) > 1:
        # Multiple candidates -> conflict if they're genuinely incompatible
        # pass_fail and at_risk_or_performance_tier can coexist (at-risk framing of pass/fail);
        # in that case prefer pass_fail_or_success_failure (risk_framing handles the at-risk part)
        if set(seen) == {"at_risk_or_performance_tier", "pass_fail_or_success_failure"}:
            return _ok("pass_fail_or_success_failure", "medium",
                       f"at-risk framing of pass/fail -> pass_fail (risk_framing handles at-risk); '{combined[:80]}'")
        # grade_or_score + at_risk = at-risk threshold on a score -> grade_or_score
        if set(seen) == {"at_risk_or_performance_tier", "grade_or_score"}:
            return _ok("grade_or_score", "medium",
                       f"at-risk framing of score -> grade_or_score; risk_framing covers at-risk; '{combined[:80]}'")
        # pass_fail + grade_or_score: explicit binary outcome takes precedence over generic
        # grade context in SPD field (e.g. "Student Grade | Pass (1) vs Fail (0)").
        # The raw_target's binary framing is more specific than the SPD's category label.
        if "pass_fail_or_success_failure" in seen and "grade_or_score" in seen:
            if "at_risk_or_performance_tier" not in seen:
                return _ok("pass_fail_or_success_failure", "medium",
                           f"explicit binary pass/fail overrides generic grade context; '{combined[:80]}'")
        return _conflict(seen, f"multiple target constructs in '{combined[:80]}'")

    # Fallback: generic grade/score/performance not already caught
    if _any_match([r"\bgrades?\b", r"\bscore\b", r"\bmark\b", r"\bperformance\b",
                   r"\bachievement\b"], combined):
        return _ok("grade_or_score", "medium",
                   f"generic grade/score signal in '{combined[:80]}'")

    if combined.strip():
        return _ok("other_or_unclear", "low",
                   f"no recognizable target construct in '{combined[:80]}'")
    return _ok("other_or_unclear", "low", "evidence fields empty")


def _classify_outcome_horizon(outcome_scope_label: str) -> dict[str, Any]:
    """Short- vs long-term horizon of the predicted outcome, by the semester
    boundary (d-043). Deterministic coarsening of outcome_scope: within the
    current semester => short_term; beyond one semester => long_term.

    Used as a Table III counts grouping column. Never routes to audit (it is a
    deterministic function of outcome_scope).
    """
    label = _HORIZON_BY_SCOPE.get(outcome_scope_label, "unclear")
    return _ok(label, "high",
               f"semester-boundary horizon: outcome_scope='{outcome_scope_label}' -> {label}")


def _classify_outcome_basis(
    row: Mapping[str, Any],
    target_construct_label: str,
    outcome_scope_label: str,
) -> dict[str, Any]:
    """Unified outcome-definition dimension with level-appropriate classes (d-043).

    Refines the predicted outcome into a concrete definition at the assessment,
    course, or program level (supersedes the grade-only score_basis). ``unclear``
    only for grade/completion-family rows whose definition cannot be determined;
    ``not_applicable`` for constructs with no grade/completion definition.

    By design NEVER returns ``confidence="low"`` and NEVER sets ``conflict_flag``
    — an orthogonal detail annotation, so it does not change ``route_to_audit`` or
    the Table III count totals (it surfaces in the table_3_detail sheet).
    """
    spd = _get_field(row, "raw_student_performance_definition", "Student Performance Definition")
    tgt = _get_field(row, "raw_target", "Target")
    ev = _get_field(row, "raw_evidence")
    combined = _text(spd, tgt, ev)
    is_assessment = outcome_scope_label == "assessment"
    is_program = outcome_scope_label in ("program_or_degree", "institution_or_system")

    tc = target_construct_label

    # National/licensing/board or qualifying milestone exam embedded in a program
    # (e.g. CMBSE) — a program-level milestone, not a course grade (d-046).
    if _any_match([
        r"\bcmbse\b", r"board\s*(skill\s*)?exam", r"licens(ing|ure)\s*exam",
        r"national\s*\w{0,15}\s*exam", r"qualifying\s*exam", r"comprehensive\s*exam",
        r"licensing\s*board",
    ], combined):
        return _ok("program_milestone_exam", "high",
                   f"national/licensing/board milestone exam in '{combined[:80]}'")

    # --- Grade/score family ---
    if tc == "grade_or_score":
        tier_pats = [
            r"performance\s*(tier|level|group|cluster|category|band)",
            r"(low|high|medium|mid).?perform\w*\s+student",
            r"top\s*\d+\s*%", r"bottom\s*\d+\s*%",
            r"(above|below)\s*(the\s*)?(median|mean|average)",
            r"\btier\b", r"\bquartile\b", r"percentile\s*(rank|group)",
            r"(high|medium|low)\s*/\s*(high|medium|low)",
        ]
        if _any_match(tier_pats, combined):
            return _ok("performance_tier", "high",
                       f"binned performance tier (not a real grade) in '{combined[:80]}'")
        if is_assessment:
            return _ok("assessment_grade", "high",
                       f"assessment-level grade in '{combined[:80]}'")
        return _ok("course_final_grade", "high",
                   f"course-level grade in '{combined[:80]}'")

    if tc == "at_risk_or_performance_tier":
        return _ok("performance_tier", "high",
                   f"performance tier (not a real grade) in '{combined[:80]}'")

    # --- Pass/fail family ---
    if tc == "pass_fail_or_success_failure":
        if is_assessment:
            return _ok("assessment_pass_fail", "high",
                       f"assessment-level pass/fail in '{combined[:80]}'")
        return _ok("course_pass_fail", "high",
                   f"course-level pass/fail in '{combined[:80]}'")

    # --- Completion / dropout (course vs program by horizon) ---
    if tc == "dropout_or_withdrawal":
        if is_program:
            return _ok("program_dropout_or_withdrawal", "high",
                       f"program/institution dropout in '{combined[:80]}'")
        return _ok("course_completion_or_dropout", "high",
                   f"course-level dropout in '{combined[:80]}'")
    if tc == "completion_or_certification":
        if is_program:
            return _ok("graduation_or_degree_completion", "high",
                       f"program completion/certification in '{combined[:80]}'")
        return _ok("course_completion_or_dropout", "high",
                   f"course completion/certification in '{combined[:80]}'")

    # --- Program-level constructs (near 1:1 with target_construct) ---
    if tc == "graduation_or_degree_completion":
        return _ok("graduation_or_degree_completion", "high",
                   f"graduation/degree completion in '{combined[:80]}'")
    if tc == "retention_or_persistence":
        return _ok("retention_or_persistence", "high",
                   f"retention/persistence in '{combined[:80]}'")
    if tc == "time_to_completion":
        return _ok("time_to_degree", "high", f"time-to-degree in '{combined[:80]}'")
    if tc == "gpa_or_cumulative_performance":
        return _ok("cumulative_gpa", "high", f"cumulative GPA / standing in '{combined[:80]}'")

    # --- Constructs with no grade/completion definition ---
    if tc in ("next_interaction_correctness", "submission_timing_or_delay",
              "learning_gain_or_skill_mastery", "enrolment_or_course_selection"):
        return _ok("not_applicable", "high",
                   f"target_construct='{tc}' has no grade/completion definition")

    # --- Unclear / other target construct ---
    return _ok("unclear", "medium",
               f"outcome definition undeterminable for target_construct='{tc}'")


def _classify_prediction_timing(row: Mapping[str, Any]) -> dict[str, Any]:
    """Anchored to feature-extraction cutoff (d-011). Primary: raw_moment_of_prediction."""
    moment = _get_field(row, "raw_moment_of_prediction", "Moment of Prediction")
    ev = _get_field(row, "raw_evidence")
    combined = _text(moment, ev)

    # Order matters: more specific patterns first.

    # Program milestone (multi-year or cross-semester program boundary)
    if _any_match([
        r"end\s*of\s*(the\s*)?(first|1st|second|2nd|third|3rd)\s*(year|semester|quarter)",
        r"end\s*of\s*year\s*\d",
        r"end\s*of\s*(the\s*)?first\s*(academic\s*)?year",
        r"(start|beginning)\s*(of\s*)?(the\s*)?program(me)?",
        r"end\s*of\s*(the\s*)?program(me)?",
        r"time\s*of\s*admission",
        r"moment\s*of\s*(registration|admission)",
        r"admission\s*of\s*student",
        r"every\s*quarter\s*(in\s*)?(the\s*)?program(me)?",
        r"every\s*semester\s*(across|throughout|in)\s*(the\s*)?(degree|program)",
        r"8\s*stages\s*(of\s*)?(the\s*)?academic\s*year",
        r"\d+\s*stages\s*(of\s*)?(the\s*)?academic\s*year",
    ], combined):
        return _ok("program_milestone", "high",
                   f"program milestone timing in moment='{moment}'")

    # Before program / at admission
    if _any_match([
        r"at\s*(enroll|admission)\s*(into|to)?\s*(the\s*)?(program|degree|msc|bsc|university|college)",
        r"entering\s*(the\s*)?(program|degree|university|college)",
        r"before.{0,10}(program|degree|university)\s*(start|begins?)",
        r"start\s*of\s*(the\s*)?first\s*year",          # "Start of First Year"
        r"start\s*of\s*first\s*year",
    ], combined):
        return _ok("before_program_or_at_admission", "high",
                   f"pre-program/admission timing in moment='{moment}'")

    # End of course / post-course (including end of semester, after final exam)
    if _any_match([
        r"end\s*of\s*(the\s*)?course",
        r"post.?course",
        r"after\s*(the\s*)?course",
        r"final\s*(week|exam|assessment)$",
        r"course\s*complet",
        r"after\s*(the\s*)?final\s*exam",               # After Final Exam
        r"end\s*of\s*(the\s*)?semester\b",              # End of Semester (course-level)
        r"end\s*of\s*(the\s*)?term\b",
    ], combined):
        return _ok("end_of_course_or_post_course", "high",
                   f"end-of-course timing in moment='{moment}'")

    # Continuous / repeated (covers per-assessment, per-assignment, inter-session)
    if _any_match([
        r"every\s*(week|month|session|step|quarter|20\%|assessment|exam|assignment)",
        r"continuous",
        r"each\s*(week|step|session|day|assessment)",
        r"repeated",
        r"snapshot",
        r"cumulative\s*snapshot",
        r"throughout",
        r"\d+\%.*\d+\%.*\d+\%",  # multiple percentage points (10%, 25%, 33%, 50%)
        r"after\s*every\s*moment",                      # After every moment of evaluation
        r"every\s*moment\s*(of|for)\s*(evaluation|assessment)",
        r"between\s*assignment",                         # Between Assignments
        r"before\s*(every|each)\s*(assignment|exam|assessment)",
        r"before\s*each\s*(exam|assessment|quiz)",
        r"at\s*different\s*stages",
        r"different\s*stages\s*of\s*(the\s*)?module",
        r"after\s*specific\s*tma",
        r"multiple\s*time\s*points",
        r"every\s*2\s*minutes",
        r"mid.semester\s*(and|;)\s*end.of.semester",
    ], combined):
        return _ok("continuous_or_repeated", "high",
                   f"continuous/repeated timing in moment='{moment}'")

    # Before course / at course enrolment (including "Start of Term", "Start of Spring Semester")
    if _any_match([
        r"before\s*(the\s*)?course\s*start",
        r"(start|beginning)\s*(of\s*)?(the\s*)?(course|semester|term|spring|fall|autumn|winter|summer)\b",
        r"start\s*of\s*(the\s*)?(spring|fall|autumn|winter|summer)\s*semester",
        r"start\s*of\s*(the\s*)?term\b",               # Start of Term
        r"start\s*of\s*(the\s*)?(next\s*)?(course|semester)",   # Start of Next Semester
        r"before\s*(the\s*)?(start\s*of\s*)?(the\s*)?(next\s*)?(semester|course|term)\b",
        r"start\s*of\s*semester",
        r"week\s*0\b",
        r"before\s*(enroll|regist)",
        r"at\s*(course\s*)?(enroll|regist|start)",
    ], combined):
        return _ok("before_course_or_at_course_enrolment", "high",
                   f"pre-course/at-enrolment timing in moment='{moment}'")

    # Week-based: early (weeks 1-4 or first few weeks)
    week_match = re.search(r"week\s*(\d+)", combined, re.IGNORECASE)
    if week_match:
        wnum = int(week_match.group(1))
        if 1 <= wnum <= 4:
            return _ok("early_course", "high",
                       f"week {wnum} feature cutoff => early_course (d-011)")
        if 5 <= wnum <= 8:
            return _ok("mid_course", "high",
                       f"week {wnum} feature cutoff => mid_course (d-011)")
        if wnum >= 9:
            return _ok("late_course", "high",
                       f"week {wnum} feature cutoff => late_course (d-011)")

    # Percentage-based single cutoff
    pct_match = re.search(r"\b(10|25|33|50|60|75|80|90)\s*%", combined, re.IGNORECASE)
    if pct_match:
        pct = int(pct_match.group(1))
        if pct <= 33:
            return _ok("early_course", "medium",
                       f"{pct}% course duration => early_course")
        if pct <= 60:
            return _ok("mid_course", "medium",
                       f"{pct}% course duration => mid_course")
        return _ok("late_course", "medium",
                   f"{pct}% course duration => late_course")

    # Half-way / mid-course
    if _any_match([r"halfway", r"half.?way", r"mid.?course", r"course.?half", r"half\s*point",
                   r"mid.?semester", r"after\s*midterm",
                   r"during\s*(the\s*)?first\s*(semester|term|quarter)"], combined):
        return _ok("mid_course", "high", f"halfway/mid-course in moment='{moment}'")

    # Day-based: first N days of a course
    day_match = re.search(r"first\s+(\d+)\s*days?\s*(of\s*)?(the\s*)?course", combined, re.IGNORECASE)
    if day_match:
        ndays = int(day_match.group(1))
        if ndays <= 35:
            return _ok("early_course", "medium",
                       f"first {ndays} days of course => early_course")
        if ndays <= 70:
            return _ok("mid_course", "medium",
                       f"first {ndays} days of course => mid_course")
        return _ok("late_course", "medium",
                   f"first {ndays} days of course => late_course")

    # Lab/session-based early signal (e.g. "After 6 lab sessions")
    if _any_match([r"after\s*\d+\s*(lab|session|lecture|class)(es|s)?\b",
                   r"first\s*\d+\s*(lab|session|lecture)(es|s)?\b"], combined):
        return _ok("early_course", "medium",
                   f"lab/session-based early signal in moment='{moment}'")

    # Assignment subset: "Assignments 1 to N (out of M)" -> early if N/M <= 0.4
    asgn_match = re.search(
        r"assignment[s]?\s*1\s*to\s*(\d+)\s*\(?out\s*of\s*(\d+)\)?",
        combined, re.IGNORECASE
    )
    if asgn_match:
        n_done = int(asgn_match.group(1))
        n_total = int(asgn_match.group(2))
        frac = n_done / n_total if n_total else 0
        if frac <= 0.40:
            return _ok("early_course", "medium",
                       f"assignments {n_done}/{n_total} ({frac:.0%}) => early_course")
        if frac <= 0.65:
            return _ok("mid_course", "medium",
                       f"assignments {n_done}/{n_total} ({frac:.0%}) => mid_course")
        return _ok("late_course", "medium",
                   f"assignments {n_done}/{n_total} ({frac:.0%}) => late_course")

    # "Before Last Quarter of Course" -> late_course
    if _any_match([r"before\s*(the\s*)?last\s*(quarter|third|week|20%|25%)",
                   r"last\s*(quarter|third)\s*of\s*(the\s*)?course"], combined):
        return _ok("late_course", "medium",
                   f"before last quarter/third of course in moment='{moment}'")

    # First N weeks as a phrase (e.g. "First 2 weeks", "First half of course / first 5 weeks")
    first_weeks_match = re.search(r"first\s+(\d+)\s*weeks?", combined, re.IGNORECASE)
    if first_weeks_match:
        wnum = int(first_weeks_match.group(1))
        if 1 <= wnum <= 4:
            return _ok("early_course", "medium",
                       f"first {wnum} weeks => early_course")
        if 5 <= wnum <= 8:
            return _ok("mid_course", "medium",
                       f"first {wnum} weeks => mid_course")
        return _ok("late_course", "medium",
                   f"first {wnum} weeks => late_course")

    # "Previous Month" — treated as continuous/rolling window
    if _any_match([r"previous\s*month", r"past\s*month", r"monthly"], combined):
        return _ok("continuous_or_repeated", "medium",
                   f"monthly/rolling window timing in moment='{moment}'")

    # Generic "monthly" or "semester" snapshots during semester
    if _any_match([r"monthly.*(semester|course|prediction)",
                   r"(semester|course).*monthly"], combined):
        return _ok("continuous_or_repeated", "medium",
                   f"monthly snapshot timing in moment='{moment}'")

    # Start of academic year (multi-year milestone)
    if _any_match([r"start\s*of\s*(new\s*)?academic\s*year"], combined):
        return _ok("program_milestone", "medium",
                   f"academic year start in moment='{moment}'")

    # Before assignment submission / at each assessment
    if _any_match([r"before\s*assignment\s*submission",
                   r"at\s*each\s*assessment",
                   r"each\s*assessment"], combined):
        return _ok("continuous_or_repeated", "medium",
                   f"per-assessment timing in moment='{moment}'")

    # Early course signals — "early prediction", "during first semester", etc.
    if _any_match([r"\bearly\s*(prediction|indicator|warning)\b",
                   r"during\s*(the\s*)?first\s*(week|month)"], combined):
        return _ok("early_course", "medium",
                   f"early-prediction signal in moment='{moment}'")

    if moment.strip() and moment.strip().lower() not in ("nan", "n/a", "not applicable", "none"):
        return _ok("unclear", "low",
                   f"moment='{moment}' not matched to any timing rule")
    return _ok("unclear", "low", "raw_moment_of_prediction field absent")


def _classify_cv_design(row: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic rules on raw_assessment_strategy. Full-text required by guardrail 8."""
    strat = _get_field(row, "raw_assessment_strategy", "Assessment Strategy")
    ev = _get_field(row, "raw_evidence")
    combined = _text(strat, ev)

    # Temporal / prospective
    if _any_match([
        r"temporal\s*valid",
        r"prospective",
        r"train.*20[0-9]{2}.*test.*20[0-9]{2}",
        r"leave.last.semester",
        r"chronological",
        r"leave.one.semester",
    ], combined):
        return _ok("temporal_or_prospective", "high",
                   f"temporal validation pattern in '{strat}'")

    # Random fold (k-fold, stratified, repeated holdout, LOO)
    if _any_match([
        r"\d+.fold\s*(cross.valid|cv)",
        r"cross.valid",
        r"stratified\s*(k.fold|cross)",
        r"leave.one.out",
        r"repeated\s*holdout",
        r"k.fold",
    ], combined):
        return _ok("random_fold", "high", f"k-fold/cross-validation in '{strat}'")

    # Holdout (without temporal context -> random_fold, medium confidence)
    if _any_match([r"\bholdout\b", r"hold.out", r"\d+/\d+\s*split",
                   r"\d+%.*\d+%", r"train.test\s*split"], combined):
        return _ok("random_fold", "medium",
                   f"holdout (no temporal context) in '{strat}'; full-text confirmation needed")

    # None / unspecified
    if _any_match([r"none\s*specified", r"\bnone\b", r"no\s*assessment",
                   r"unspecified", r"not\s*specified", r"^-+$"], combined):
        return _ok("unclear", "low", f"no assessment strategy reported: '{strat}'")

    if strat.strip():
        return _ok("unclear", "low", f"assessment strategy '{strat}' not mapped; full-text review needed")
    return _ok("unclear", "low", "raw_assessment_strategy field absent")


def _classify_risk_framing(row: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic regex on raw_student_performance_definition, raw_target, raw_evidence."""
    spd = _get_field(row, "raw_student_performance_definition", "Student Performance Definition")
    tgt = _get_field(row, "raw_target", "Target")
    ev = _get_field(row, "raw_evidence")
    combined = _text(spd, tgt, ev)

    strong_yes = [
        r"at.?risk",
        r"risk\s*of\s*(fail|drop|withdraw|low)",
        r"low.?perform\w*\s+student",
        r"poor.?perform\w*\s+student",
        r"(bottom|low)\s*\d+\s*%",
        r"risk\s*(score|label|flag|tier|group)",
        r"performance\s*(tier|group|cluster|category|level)\s*(low|medium|high|good|bad)",
        r"identify.*at.risk",
    ]
    if _any_match(strong_yes, combined):
        return _ok("yes", "high",
                   f"at-risk/tier framing detected in '{combined[:80]}'")

    # Softer signals
    soft_yes = [
        r"above.*(median|mean|average)",
        r"below.*(median|mean|average)",
        r"top\s*\d+\s*%",
        r"sufficient.{0,10}average.{0,10}good",
        r"exceptional.{0,10}pass.{0,10}fail",
    ]
    if _any_match(soft_yes, combined):
        return _ok("yes", "medium",
                   f"soft risk-tier framing in '{combined[:80]}'")

    return _ok("no", "high", "no at-risk framing signals in available text")


def _is_lms_as_data_source_only(ev_text: str) -> bool:
    """Return True when an LMS name appears ONLY as a data-collection platform.

    The precision guard (Change A) prevents raw evidence that merely names
    Moodle/Blackboard/Canvas/DeepLMS as the data source from being treated as
    evidence of deployment.  Triggers only when no deployment/integration verb
    accompanies the LMS reference.
    """
    lms_only_pats = [
        r"web\s*usage\s*mining.*moodle",
        r"moodle.*web\s*usage\s*mining",
        r"\bdeeplms\b",
        r"(moodle|blackboard|canvas)\s*(log|data|course|platform|lms)?\s*(for\s*(predict|analyz|mining)|data)",
        r"using\s*(moodle|blackboard|canvas)\s*(course|data|log)",
    ]
    deploy_verb_pats = [
        r"integrat",
        r"deploy",
        r"embed",
        r"plug.?in",
        r"dashboard.*instructor",
        r"instructor.*dashboard",
        r"alert.*instructor",
        r"in\s*production",
        r"real.time.*system",
    ]
    if not _any_match(lms_only_pats, ev_text):
        return False
    # If deployment verbs are also present, don't suppress
    return not _any_match(deploy_verb_pats, ev_text)


def _classify_actionability_status(row: Mapping[str, Any]) -> dict[str, Any]:
    """Rules on raw_assessment_strategy + raw_evidence + raw_deployed_deployable.

    3-level gradient (ho-018 refined by author, 2026-06-07):

    Tier 1 — deployed_with_intervention_evaluation:
      * Canonical Deployed/Deployable = 'Deployed by Instructor' or
        'Integrated in LMS' (author counts instructor/LMS deployment as a
        delivered intervention).
      * OR intervention-evaluation phrasing in raw text (RCT, A/B test, etc.).

    Tier 2 — deployed_or_deployable:
      * Canonical Deployed/Deployable = 'Deployable'.
      * OR deployment phrasing in raw evidence / assessment strategy.

    Tier 3 — fall-through (no canonical tier 1/2 value):
      * Canonical values 'Prototype', 'Not Ready', 'Out of Scope' → do NOT
        force a label; continue to validation-based logic so a Prototype paper
        with temporal validation can still reach early_backtest_only, and a
        paper tested on new students can reach tested_on_new_students.

    Precision guard: LMS names that appear only as data-collection platforms do
    NOT trigger deployment labels.
    """
    strat = _get_field(row, "raw_assessment_strategy", "Assessment Strategy")
    ev = _get_field(row, "raw_evidence")
    deployed_field = _get_field(row, "raw_deployed_deployable", "Deployed/ Deployable",
                                "Deployed_Deployable")
    work_nature = _get_field(row, "raw_work_nature", "Work Nature")
    combined = _text(strat, ev, deployed_field, work_nature)

    # --- Precision guard: LMS-as-data-source rows must not be mis-classified ---
    # Check against ev only (strat field never contains LMS data-source phrases).
    if _is_lms_as_data_source_only(_text(ev)):
        # Skip deployment detection; fall through to CV-based retrospective logic.
        pass
    else:
        deployed_field_l = deployed_field.lower().strip()

        # --- Tier 1: Deployed with intervention evaluation (highest specificity) ---

        # 1a. Canonical field: Deployed by Instructor or Integrated in LMS.
        #     Author confirmed: instructor/LMS deployment = delivered intervention.
        canonical_intervention_vals = [
            "deployed by instructor",
            "integrated in lms",
        ]
        if any(val in deployed_field_l for val in canonical_intervention_vals):
            return _ok("deployed_with_intervention_evaluation", "high",
                       f"canonical Deployed/Deployable='{deployed_field}' — "
                       "instructor/LMS deployment counts as delivered intervention (ho-018)")

        # 1b. Intervention-evaluation phrasing in raw text (RCT, A/B test, etc.)
        intervention_eval_pats = [
            r"intervention.*evaluat",
            r"evaluat.*intervention",
            r"randomized.*(trial|controlled|experiment)",
            r"(random(ly)?|randomly)\s*assign",
            r"a/b.*test",
            r"treatment.*control",
            r"control.*treatment",
            r"quasi.experiment",
            r"experimental.*group",
        ]
        if _any_match(intervention_eval_pats, combined):
            return _ok("deployed_with_intervention_evaluation", "high",
                       f"intervention evaluation signal in '{combined[:80]}'")

        # --- Tier 2: Deployed or deployable (capability/deployable tier) ---

        # 2a. Canonical field: Deployable.
        if "deployable" in deployed_field_l and "not" not in deployed_field_l:
            return _ok("deployed_or_deployable", "high",
                       f"canonical Deployed/Deployable='{deployed_field}' (ho-018 tier 2)")

        # 2b. Deployment phrasing in raw_evidence / raw_assessment_strategy
        deployment_phrase_pats = [
            r"integrated\s*(into|in)\s*(the\s*)?(lms|moodle|blackboard|canvas|vle|system|platform)",
            r"deployed\s*(in|into|by|to|for)\s*(the\s*)?(lms|instructor|teacher|advisor|system|course)",
            r"embedded\s*(in|into)\s*(the\s*)?(lms|system|course|platform)",
            r"in\s*production",
            r"real.?time\s*(system|predict|alert|notif)",
            r"early.?warning\s*system\s*(used|deployed|accessed|provided|integrat)",
            r"dashboard\s*(provided|sent|given|accessed|used)\s*(to|by)\s*(instructor|teacher|advisor|student)",
            r"(instructor|teacher|advisor)\s*(receiv|access|us|view)\s*(the\s*)?(dashboard|alert|notif|result|output|predict)",
            r"alert.*send.*instructor|alert.*instructor",
            r"intervention\s*(delivered|provided|conducted|implemented)",
            r"pilot\s*(test|study|deploy)\s*(on\s*)?(new|live|real|current)\s*student",
        ]
        if _any_match(deployment_phrase_pats, combined):
            return _ok("deployed_or_deployable", "high",
                       f"deployment phrase in evidence/strategy: '{combined[:80]}'")

        # --- Tier 3: Prototype / Not Ready / Out of Scope → fall through ---
        # No explicit return here; canonical non-deployed values do not force a label.
        # The row continues to the validation-based logic below so temporal/prospective
        # validation can still yield early_backtest_only or tested_on_new_students.

    # --- Temporal validation -> early_backtest_only ---
    if _any_match([
        r"temporal\s*valid",
        r"prospective.*valid",
        r"train.*20[0-9]{2}.*test.*20[0-9]{2}",
        r"leave.last.semester",
    ], combined):
        return _ok("early_backtest_only", "medium",
                   f"temporal validation -> early_backtest_only in '{combined[:80]}'")

    # --- Historical/retrospective only ---
    if _any_match([
        r"retrospective",
        r"historical\s*data\s*only",
        r"past\s*data",
    ], combined):
        return _ok("retrospective_only", "medium",
                   f"retrospective signal in '{combined[:80]}'")

    # Most studies are tested on held-out data from same dataset = retrospective_only
    if _any_match([
        r"\bholdout\b", r"k.fold", r"cross.valid",
        r"\d+.fold", r"hold.out",
        r"leave.one.out",
    ], combined):
        return _ok("retrospective_only", "medium",
                   f"holdout/CV without deployment evidence -> retrospective_only; '{combined[:80]}'")

    # Genuinely unclear
    return _ok("unclear", "low",
               f"insufficient actionability signal in assessment strategy='{strat}'")


def _classify_evidence_quality(row: Mapping[str, Any]) -> dict[str, Any]:
    """Heuristic scoring: sample size + assessment strategy + model count."""
    sample = _get_field(row, "raw_sample_setting", "Students")
    strat = _get_field(row, "raw_assessment_strategy", "Assessment Strategy")
    models = _get_field(row, "raw_models", "Models")
    ev = _get_field(row, "raw_evidence")
    combined = _text(sample, strat, models, ev)
    score = 0
    evidence_parts: list[str] = []

    # Sample size
    nums = re.findall(r"[\d,\xa0]+", sample.replace(",", "").replace("\xa0", ""))
    max_n = 0
    for n_str in nums:
        try:
            n = int(n_str.replace(",", "").replace("\xa0", ""))
            max_n = max(max_n, n)
        except ValueError:
            pass
    if max_n > 1000:
        score += 2
        evidence_parts.append(f"n>{max_n} (+2)")
    elif max_n >= 100:
        score += 1
        evidence_parts.append(f"n={max_n} (+1)")
    else:
        evidence_parts.append(f"n={max_n} (+0)")

    # Assessment strategy
    strat_l = strat.lower()
    if _any_match([r"temporal", r"prospective", r"leave.last.semester"], strat_l):
        score += 2
        evidence_parts.append("temporal_valid (+2)")
    elif _any_match([r"k.fold", r"cross.valid", r"\d+.fold", r"holdout", r"leave.one"], strat_l):
        score += 1
        evidence_parts.append("cv/holdout (+1)")
    else:
        evidence_parts.append("no_valid (+0)")

    # Public datasets / replication signal
    if _any_match([r"oulad", r"open\s*universit", r"assistments",
                   r"kdd\s*cup", r"public\s*dataset", r"replicated"], combined):
        score += 1
        evidence_parts.append("public_dataset (+1)")

    # Multiple models compared
    if models:
        model_count = len([m.strip() for m in re.split(r"[,;]+", models) if m.strip()])
        if model_count >= 3:
            score += 1
            evidence_parts.append(f"{model_count}_models (+1)")

    ev_str = "; ".join(evidence_parts) + f" => total={score}"
    if score >= 5:
        return _ok("high", "high", ev_str)
    if score >= 3:
        return _ok("medium", "medium", ev_str)
    return _ok("low", "medium", ev_str)


def _infer_unit_of_analysis(outcome_scope_label: str, combined: str) -> dict[str, Any]:
    """Infer unit_of_analysis from outcome_scope as primary signal."""
    scope_map = {
        "interaction_or_item": "learner_item_interaction",
        "assessment": "learner_assessment",
        "course_or_module": "learner_course",
        "term_or_semester": "learner_term",
        "program_or_degree": "learner_program",
        "institution_or_system": "learner_institution",
    }
    if outcome_scope_label in scope_map:
        unit = scope_map[outcome_scope_label]
        return _ok(unit, "medium",
                   f"inferred from outcome_scope='{outcome_scope_label}'")

    # Cohort signal
    if _any_match([r"\bcohort\b", r"\bgroup\b.*predict", r"class.level"], combined):
        return _ok("cohort_or_group", "medium", "cohort/group signal in evidence")

    return _ok("unclear", "low", "unit_of_analysis could not be inferred")


# --- Main classify_contribution entry point ---

def classify_contribution(row: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one predictive-modelling contribution across the 10-dimension taxonomy.

    Primary signal: ``raw_evidence`` (d-032). Falls back to Title-Case keys
    (``"Student Performance Definition"``, ``"Moment of Prediction"``, ``"Context"``,
    ``"Target"``) and snake_case ``raw_*`` fields; handles both gracefully.

    Returns a dict with one ``DimensionResult`` entry per dimension plus top-level
    ``route_to_audit`` and ``manual_override_applied`` flags.

    Schema: ``docs/classify_contribution_schema.md`` v1.0 (d-032 approved).
    Guardrails: every result carries label + confidence + evidence; low-confidence
    and conflict rows are flagged; no silent assignment.
    """
    # Classify context_type first — needed by MOOC-dropout disambiguation rule
    ctx_result = _classify_context_type(row)
    ctx_label = ctx_result["label"]

    outcome_scope_result = _classify_outcome_scope(row, ctx_label)
    target_construct_result = _classify_target_construct(row)
    prediction_timing_result = _classify_prediction_timing(row)
    cv_design_result = _classify_cv_design(row)
    supervised_ml_task_result = _classify_supervised_ml_task(row)
    risk_framing_result = _classify_risk_framing(row)
    actionability_result = _classify_actionability_status(row)
    evidence_quality_result = _classify_evidence_quality(row)

    # Unit of analysis inferred from outcome scope
    ev_combined = _text(
        _get_field(row, "raw_evidence"),
        _get_field(row, "raw_student_performance_definition", "Student Performance Definition"),
        _get_field(row, "raw_target", "Target"),
    )
    unit_result = _infer_unit_of_analysis(outcome_scope_result["label"], ev_combined)

    # --- Cross-dimension consistency guard (Change B, ho-018) ---
    # Rule: program-level target_construct + course-level outcome_scope = inconsistent.
    # Resolve by inspecting raw evidence:
    #   - Course-level pass/fail evidence → fix target_construct
    #   - Program-level GPA/degree evidence → fix outcome_scope
    #   - Unresolvable → conflict_flag + route to audit.
    _PROGRAM_LEVEL_TC = {
        "graduation_or_degree_completion",
        "retention_or_persistence",
        "time_to_completion",
    }
    tc_label = target_construct_result.get("label", "")
    os_label = outcome_scope_result.get("label", "")

    if tc_label in _PROGRAM_LEVEL_TC and os_label == "course_or_module":
        # Gather raw evidence for re-resolution
        _spd_guard = _get_field(row, "raw_student_performance_definition", "Student Performance Definition")
        _tgt_guard = _get_field(row, "raw_target", "Target")
        _ev_guard = _get_field(row, "raw_evidence")
        _moment_guard = _get_field(row, "raw_moment_of_prediction", "Moment of Prediction")
        _ctx_guard = _get_field(row, "raw_context", "Context")
        _guard_combined = _text(_spd_guard, _tgt_guard, _ev_guard, _moment_guard, _ctx_guard)

        # Signal set 1: evidence clearly course-level pass/fail or grade
        _course_pf_pats = [
            r"success\s*\(?\d?\)?\s*(vs|/|or)\s*failure",
            r"fail(ing|ed)?\s*\(?\d?\)?\s*(vs|/|or)\s*(pass|succeed)",
            r"pass\s*\(?\d?\)?\s*(vs|/|or)\s*fail",
            r"course\s*(pass|fail|grade|score|mark|complet)",
            r"final\s*(mark|grade|exam|score)",
            r"week\s*\d+\s*(of|out\s*of)\s*\d+",  # week N of M => course-level
        ]
        # Signal set 2: evidence genuinely program-level (overrides course label)
        _prog_override_pats = [
            r"gpa\s*(at|upon|after)\s*graduat",
            r"degree\s*complet",
            r"program\s*(persist|retent|complet|level|outcome)",
            r"first.?year\s*(retent|persist|surviv)",
        ]

        _course_pf_match = _any_match(_course_pf_pats, _guard_combined)
        _prog_override_match = _any_match(_prog_override_pats, _guard_combined)

        if _course_pf_match and not _prog_override_match:
            # Fix target_construct: course-level binary outcome → pass_fail_or_success_failure
            # (or grade_or_score if it's a continuous mark)
            _continuous_pats = [r"final\s*(mark|grade|score)\b(?!\s*(pass|fail))",
                                 r"grade\s*(0.?10|a-f|\d+)", r"continuous\s*value"]
            _new_tc = "grade_or_score" if _any_match(_continuous_pats, _guard_combined) else "pass_fail_or_success_failure"
            _old_tc = tc_label
            target_construct_result = _ok(
                _new_tc, "medium",
                f"consistency-guard (Change B): program-level TC '{_old_tc}' + "
                f"course-level outcome_scope; course-level pass/fail evidence "
                f"detected ({_spd_guard!r} | {_tgt_guard!r}) → fixed TC to '{_new_tc}'"
            )
        elif _prog_override_match and not _course_pf_match:
            # Fix outcome_scope to program_or_degree
            _old_os = os_label
            outcome_scope_result = _ok(
                "program_or_degree", "medium",
                f"consistency-guard (Change B): TC='{tc_label}' implies program-level; "
                f"program-level evidence detected → fixed outcome_scope "
                f"from '{_old_os}' to 'program_or_degree'"
            )
            # Recompute unit_of_analysis with corrected scope
            unit_result = _infer_unit_of_analysis("program_or_degree", ev_combined)
        else:
            # Unresolvable: flag conflict
            target_construct_result = _conflict(
                [tc_label, "pass_fail_or_success_failure"],
                f"consistency-guard: program-level TC '{tc_label}' conflicts with "
                f"course-level outcome_scope; insufficient evidence to resolve "
                f"({_spd_guard!r} | {_tgt_guard!r})"
            )

    # outcome_horizon + outcome_basis (d-043): computed from the FINAL
    # target_construct + outcome_scope labels (after the consistency guard above).
    # outcome_horizon is a deterministic coarsening of outcome_scope (counts column);
    # outcome_basis is an orthogonal detail annotation. Neither routes to audit, so
    # neither perturbs Table III count totals.
    outcome_horizon_result = _classify_outcome_horizon(outcome_scope_result.get("label", ""))
    outcome_basis_result = _classify_outcome_basis(
        row,
        target_construct_result.get("label", ""),
        outcome_scope_result.get("label", ""),
    )

    result: dict[str, Any] = {
        "supervised_ml_task": supervised_ml_task_result,
        "outcome_scope": outcome_scope_result,
        "unit_of_analysis": unit_result,
        "target_construct": target_construct_result,
        "outcome_horizon": outcome_horizon_result,
        "outcome_basis": outcome_basis_result,
        "prediction_timing": prediction_timing_result,
        "actionability_status": actionability_result,
        "risk_framing": risk_framing_result,
        "evidence_quality": evidence_quality_result,
        "cv_design": cv_design_result,
        "context_type": ctx_result,
    }

    # Determine route_to_audit: any dim with confidence="low" OR conflict_flag=True
    route = any(
        dim_res.get("confidence") == "low" or dim_res.get("conflict_flag") is True
        for dim_res in result.values()
        if isinstance(dim_res, dict)
    )
    result["route_to_audit"] = route
    result["manual_override_applied"] = False

    return result


# --- Pipeline runner: classify all rows and emit CSVs ---

def run_taxonomy_classification_pipeline(
    csv_path: str | Path | None = None,
    audit_path: str | Path | None = None,
    overrides_path: str | Path | None = None,
) -> None:
    """Classify all rows in pred_contribution_rows.csv and write back labels + audit CSV.

    This function is idempotent: re-running overwrites the classification columns with
    fresh labels. Audit rows are always re-generated from scratch.

    Parameters
    ----------
    csv_path:
        Path to pred_contribution_rows.csv (defaults to repo-relative path).
    audit_path:
        Path for taxonomy_audit.csv output (defaults to same directory as csv_path).
    overrides_path:
        Path to manual_overrides.yaml. If None, auto-detected from repo structure.
    """
    import datetime
    import json

    pd = _require_pandas()

    _repo_root = Path(__file__).resolve().parents[3]
    if csv_path is None:
        csv_path = _repo_root / "data" / "analysis_outputs" / "la_review" / "audits" / "pred_contribution_rows.csv"
    csv_path = Path(csv_path)
    if audit_path is None:
        audit_path = csv_path.parent / "taxonomy_audit.csv"
    audit_path = Path(audit_path)

    df = pd.read_csv(csv_path)

    # --- Load canonical Deployed/Deployable + Work Nature fields (Change A, ho-018) ---
    # These live in canonical JSON files (domain_properties) and are not yet columns
    # in pred_contribution_rows.csv.  We build a paper_id → (deployed, work_nature)
    # lookup so each row can see the canonical deployment classification.
    _canonical_deploy: dict[str, tuple[str, str]] = {}
    _canonical_dir = _repo_root / "data" / "pulled" / "notion" / "learning_analytics_review"
    if _canonical_dir.is_dir():
        for _jf in _canonical_dir.glob("*.canonical.json"):
            try:
                with open(_jf, encoding="utf-8") as _jfh:
                    _jdata = json.load(_jfh)
                for _ref in _jdata.get("references", []):
                    _pid = str(_ref.get("id", "")).strip()
                    if not _pid:
                        continue
                    _dp = (_ref.get("sync_metadata") or {}).get("domain_properties") or {}
                    _deployed = str(_dp.get("Deployed/ Deployable") or "").strip()
                    _wn = _dp.get("Work Nature") or []
                    if isinstance(_wn, list):
                        _wn = "; ".join(str(x) for x in _wn)
                    else:
                        _wn = str(_wn)
                    _lp = str(_dp.get("Learner Population") or "").strip()
                    if _deployed or _lp:
                        _canonical_deploy[_pid] = (_deployed, _wn, _lp)
            except Exception:
                pass  # Silently skip malformed JSON — do not crash the pipeline

    # Ensure classification columns are object dtype so we can write string labels
    _write_cols = [
        "supervised_ml_task", "outcome_scope", "unit_of_analysis",
        "target_construct", "outcome_horizon", "outcome_basis",
        "prediction_timing", "actionability_status",
        "risk_framing", "evidence_quality", "cv_design", "context_type",
        "classification_confidence", "classification_notes", "manual_override_applied",
    ]
    for col in _write_cols:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].astype(object)

    # Load manual overrides
    manual_overrides: list[dict[str, Any]] = []
    if overrides_path is None:
        candidate = _repo_root / "configs" / "reviews" / "la_student_success_review" / "manual_overrides.yaml"
        if candidate.exists():
            overrides_path = candidate
    if overrides_path and Path(overrides_path).exists():
        try:
            import yaml  # type: ignore[import]
            with open(overrides_path, encoding="utf-8") as fh:
                ov_data = yaml.safe_load(fh)
            manual_overrides = ov_data.get("overrides", []) or []
            # Filter out illustrative example entries
            manual_overrides = [
                o for o in manual_overrides
                if not str(o.get("contribution_id", "")).startswith("c-example")
            ]
        except Exception:
            pass  # YAML not available or malformed — proceed without overrides

    dims = [
        "supervised_ml_task", "outcome_scope", "unit_of_analysis",
        "target_construct", "outcome_horizon", "outcome_basis",
        "prediction_timing", "actionability_status",
        "risk_framing", "evidence_quality", "cv_design", "context_type",
    ]

    # Index overrides by contribution_id
    override_index: dict[str, list[dict[str, Any]]] = {}
    for ov in manual_overrides:
        cid = str(ov.get("contribution_id", ""))
        override_index.setdefault(cid, []).append(ov)

    audit_rows: list[dict[str, Any]] = []
    ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    for idx, raw_row in df.iterrows():
        row = dict(raw_row)
        # Inject canonical deployment metadata (Change A, ho-018) so
        # _classify_actionability_status can see it via _get_field().
        _pid_for_deploy = str(row.get("paper_id", "")).strip()
        if _pid_for_deploy in _canonical_deploy:
            _dep_val, _wn_val, _lp_val = _canonical_deploy[_pid_for_deploy]
            row.setdefault("raw_deployed_deployable", _dep_val)
            row.setdefault("raw_work_nature", _wn_val)
            if _lp_val:
                row.setdefault("raw_learner_population", _lp_val)
        classification = classify_contribution(row)

        # Apply manual overrides
        cid = str(row.get("contribution_id", ""))
        applied_override = False
        for ov in override_index.get(cid, []):
            field = ov.get("field", "")
            value = ov.get("value", "")
            rationale = ov.get("rationale", "")
            if field in dims and field in classification:
                vocab = _VOCAB.get(field, [])
                if vocab and value not in vocab:
                    # Override value not in vocab — escalate (log but don't crash)
                    pass
                else:
                    classification[field] = {
                        "label": value,
                        "confidence": "high",
                        "evidence": f"manual_override: {rationale}",
                    }
                    applied_override = True

        if applied_override:
            classification["manual_override_applied"] = True
            # Re-evaluate route_to_audit after overrides
            classification["route_to_audit"] = any(
                dim_res.get("confidence") == "low" or dim_res.get("conflict_flag") is True
                for dim_res in classification.values()
                if isinstance(dim_res, dict)
            )

        # Write labels back to DataFrame
        for dim in dims:
            dim_res = classification.get(dim, {})
            df.at[idx, dim] = dim_res.get("label", "unclear")

        df.at[idx, "classification_confidence"] = min(
            (classification.get(d, {}).get("confidence", "low") for d in dims),
            key=lambda c: {"high": 2, "medium": 1, "low": 0}.get(c, 0),
        )
        df.at[idx, "manual_override_applied"] = classification.get("manual_override_applied", False)

        # Build notes from any conflicts or low-confidence dims
        low_dims = [
            d for d in dims
            if classification.get(d, {}).get("confidence") == "low"
            or classification.get(d, {}).get("conflict_flag") is True
        ]
        df.at[idx, "classification_notes"] = (
            "low/conflict: " + ", ".join(low_dims) if low_dims else ""
        )

        # Route to audit if needed
        if classification.get("route_to_audit"):
            audit_rows.append({
                "contribution_id": row.get("contribution_id", ""),
                "paper_id": row.get("paper_id", ""),
                "paper_title": row.get("paper_title", ""),
                "audit_reason": "low_confidence/conflict: " + ", ".join(low_dims),
                "flagged_dimensions": json.dumps(low_dims),
                "dimension_results": json.dumps({
                    d: classification.get(d, {}) for d in dims
                }),
                "raw_evidence": row.get("raw_evidence", ""),
                "human_adjudication": "",
                "adjudication_status": "pending",
                "routed_at": ts,
            })

    # Write back enriched CSV
    df.to_csv(csv_path, index=False)

    # Write audit CSV
    if audit_rows:
        audit_df = pd.DataFrame(audit_rows)
    else:
        audit_df = pd.DataFrame(columns=[
            "contribution_id", "paper_id", "paper_title", "audit_reason",
            "flagged_dimensions", "dimension_results", "raw_evidence",
            "human_adjudication", "adjudication_status", "routed_at",
        ])

    # Sentinel validation entry: run the canonical conflict test case to confirm
    # audit routing is operational.  This entry is NEVER promoted to canonical
    # Table III — it is a system-test record (test-R-004-002 spec).
    sentinel_row: dict[str, Any] = {
        "raw_evidence": "Course Grade or Completion",
        "raw_student_performance_definition": "Course Grade or Completion",
        "raw_target": "Course Grade or Completion",
        "contribution_id": "_sentinel_conflict_test",
        "paper_id": "_sentinel",
        "paper_title": "[SYSTEM VALIDATION] Conflict test — Course Grade or Completion",
    }
    sentinel_cls = classify_contribution(sentinel_row)
    if sentinel_cls.get("route_to_audit"):
        low_dims_s = [
            d for d in dims
            if sentinel_cls.get(d, {}).get("confidence") == "low"
            or sentinel_cls.get(d, {}).get("conflict_flag") is True
        ]
        sentinel_audit_row = {
            "contribution_id": sentinel_row["contribution_id"],
            "paper_id": sentinel_row["paper_id"],
            "paper_title": sentinel_row["paper_title"],
            "audit_reason": "low_confidence/conflict: " + ", ".join(low_dims_s),
            "flagged_dimensions": json.dumps(low_dims_s),
            "dimension_results": json.dumps({d: sentinel_cls.get(d, {}) for d in dims}),
            "raw_evidence": sentinel_row["raw_evidence"],
            "human_adjudication": "",
            "adjudication_status": "pending",
            "routed_at": ts,
        }
        sentinel_df = pd.DataFrame([sentinel_audit_row])
        audit_df = pd.concat([audit_df, sentinel_df], ignore_index=True)

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_df.to_csv(audit_path, index=False)


__all__ = [
    "apply_overrides",
    "build_pred_horizon_task_detail",
    "build_pred_horizon_task_summary",
    "build_pred_horizon_task_summary_from_canonical",
    "classify_contribution",
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
    "run_taxonomy_classification_pipeline",
    "write_pred_horizon_task_summary_workbook",
]
