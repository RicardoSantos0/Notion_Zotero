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

REVIEWED_HORIZON_TITLE_PATTERNS: dict[str, list[str]] = {
    "Long-term": [
        r"multi-model heterogeneous ensemble",
        r"improved multi-view hypergraph",
        r"high-stakes examinations",
        r"early segmentation of students according to their academic performance",
        r"university student retention",
        r"university student dropout.*preference",
        r"mooc learner behavior prediction",
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

PRED_TARGET_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Dropout / retention": [
        r"dropout",
        r"drop out",
        r"drop-out",
        r"withdraw",
        r"retention",
        r"persist",
    ],
    "Pass/fail": [
        r"pass\s*(\(\d\))?\s*(vs|/|or)\s*fail",
        r"fail\s*(\(\d\))?\s*(vs|/|or)\s*pass",
        r"\bpass\b.*\bfail\b",
        r"\bfail\b.*\bpass\b",
    ],
    "Grade / score / performance": [
        r"grade",
        r"mark",
        r"score",
        r"exam",
        r"gpa",
        r"performance",
        r"achievement",
    ],
    "At-risk status": [
        r"at.?risk",
        r"risk of fail",
        r"risk of dropping",
    ],
    "Certification / completion": [
        r"certificat",
        r"completion",
        r"complete",
    ],
    "Assessment / assignment outcome": [
        r"assessment",
        r"assignment",
        r"quiz",
        r"submission",
        r"summative",
        r"formative",
    ],
    "Next interaction / question outcome": [
        r"next.*interaction",
        r"quality of next interaction",
        r"next.*question",
        r"question.*correct",
        r"correctness",
    ],
}


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
    targets: list[str] = []
    for target, patterns in PRED_TARGET_ALIAS_PATTERNS.items():
        if _has_any(text, patterns):
            targets.append(target)
    if "Dropout / retention" in targets:
        targets = [target for target in targets if target != "Certification / completion"]
    return targets or ["Other / ambiguous"]


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
        text, [r"week", r"early", r"during", r"every", r"half"]
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
                "Early/actionable prediction",
                "Implemented intervention or deployment",
            ]
        )
    return pd.DataFrame(output_rows).drop_duplicates()


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
    "has_implemented_intervention_or_deployment",
    "is_early_actionable_prediction",
    "raw_target_evidence",
    "write_pred_horizon_task_summary_workbook",
]
