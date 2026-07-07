"""Predictive contribution-row builder (WP2, T3.2).

Converts accepted PRED canonical bundles into contribution-level rows:
one row per *distinct* predictive contribution extracted from a paper.
A paper reporting multiple targets or experiments yields multiple rows.

Stable ``contribution_id``
--------------------------
A deterministic SHA-256 hash of the tuple:

    (paper_id, raw_task, raw_target, raw_moment_of_prediction,
     raw_models_signature)

where ``raw_models_signature`` is the first 80 characters of the
``Models`` field (trimmed, lower-cased).  The hash is reproducible
across Python versions and operating systems because it operates on
UTF-8-encoded strings, not Python hash().

Output columns
--------------
Identity / provenance
    contribution_id  paper_id  paper_title  year

Raw evidence (preserve verbatim from canonical)
    raw_task  raw_student_performance_definition  raw_target
    raw_moment_of_prediction  raw_context  raw_sample_setting
    raw_models  raw_assessment_strategy

Synthesised raw-evidence summary (for test-R-003-001)
    raw_evidence

Taxonomy placeholders (filled by T3.3 classifier)
    supervised_ml_task  outcome_scope  unit_of_analysis
    target_construct  prediction_timing  actionability_status
    risk_framing  evidence_quality  cv_design  context_type

Classifier metadata placeholders
    classification_confidence  classification_notes
    manual_override_applied
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Canonical field constants
# ---------------------------------------------------------------------------

#: schema_name value for PRED extractions
PRED_SCHEMA_NAME = "prediction_modeling"

#: Workflow-state substrings that mark an accepted PRED paper
_PRED_ACCEPTED_STATES = (
    "performance prediction",
    "prediction task",
)

# Taxonomy dimension placeholders (T3.3 fills these)
_TAXONOMY_PLACEHOLDER_COLS: list[str] = [
    "supervised_ml_task",
    "outcome_scope",
    "unit_of_analysis",
    "target_construct",
    "prediction_timing",
    "actionability_status",
    "risk_framing",
    "evidence_quality",
    "cv_design",
    "context_type",
]

_CLASSIFIER_META_COLS: list[str] = [
    "classification_confidence",
    "classification_notes",
    "manual_override_applied",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str(value: Any) -> str:
    """Coerce a canonical field value to a clean string."""
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if v is not None)
    return str(value).strip()


def _is_pred_accepted(bundle: dict) -> bool:
    """Return True when the bundle is accepted for the performance-prediction task."""
    for ws in bundle.get("workflow_states", []):
        state = (ws.get("state") or "").lower()
        if any(s in state for s in _PRED_ACCEPTED_STATES):
            return True
    return False


#: Keywords marking a paper that uses an LLM as a primary method (T6.5 overlay).
_LLM_KEYWORDS: tuple[str, ...] = (
    "llm", "large language model", "gpt", "chatgpt", "bert", "roberta",
    "deberta", "distilbert", "electra", "llama", "t5", "xlnet", "bard",
    "gemini", "language model", "prompt-based", "generative pre", "transformer-based language",
)


def _detect_llm_primary(raw_models: str, raw_task: str, raw_evidence: str) -> bool:
    """Heuristic: True when an LLM appears as a primary method for the contribution."""
    text = " ".join([raw_models, raw_task, raw_evidence]).lower()
    return any(kw in text for kw in _LLM_KEYWORDS)


def _contribution_id(
    paper_id: str,
    raw_task: str,
    raw_target: str,
    raw_moment: str,
    raw_models: str,
) -> str:
    """Return a stable 16-hex-char contribution ID (first 16 chars of SHA-256).

    The digest is computed over the concatenated UTF-8 representation of the
    five discriminating fields separated by the unit-separator character
    (U+001F) to avoid accidental collisions between adjacent field values.
    """
    sep = "\x1f"  # ASCII unit separator
    models_sig = raw_models[:80].lower().strip()
    payload = sep.join(
        [
            paper_id.strip(),
            raw_task.lower().strip(),
            raw_target.lower().strip(),
            raw_moment.lower().strip(),
            models_sig,
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:16]


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------


def build_contribution_rows(
    canonical_dir: str | Path,
) -> list[dict[str, Any]]:
    """Return a list of contribution-row dicts for all accepted PRED papers.

    Args:
        canonical_dir:
            Directory containing ``*.canonical.json`` bundle files.

    Returns:
        List of dicts, one per distinct predictive contribution row.
        Each dict contains all columns defined in the module docstring.
    """
    canonical_dir = Path(canonical_dir)

    # Load and index the Reading List for title/year lookups
    rl_by_id: dict[str, dict[str, Any]] = {}
    for path in sorted(canonical_dir.glob("*.canonical.json")):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        refs = bundle.get("references") or []
        for ref in refs:
            rid = ref.get("id") or ""
            if rid:
                rl_by_id[rid] = ref

    rows: list[dict[str, Any]] = []

    for path in sorted(canonical_dir.glob("*.canonical.json")):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not _is_pred_accepted(bundle):
            continue

        refs = bundle.get("references") or []
        ref = refs[0] if refs else {}
        paper_id = _str(ref.get("id") or bundle.get("provenance", {}).get("source_id", ""))
        if not paper_id:
            continue

        # Resolve title and year from RL first, then from inline ref
        rl_ref = rl_by_id.get(paper_id, ref)
        paper_title = _str(rl_ref.get("title") or ref.get("title", ""))
        year_raw = rl_ref.get("year") or ref.get("year")
        year = int(year_raw) if year_raw is not None else None

        # Extract paper-level domain properties for the actionability classifier.
        # sync_metadata.domain_properties holds "Deployed/ Deployable" and
        # "Work Nature" which are paper-level (not per-extraction-row) fields.
        sm = ref.get("sync_metadata") or {}
        if isinstance(sm, str):
            # Legacy: sync_metadata was sometimes serialised as a string
            try:
                import ast as _ast
                sm = _ast.literal_eval(sm)
            except Exception:
                sm = {}
        dp = sm.get("domain_properties", {}) if isinstance(sm, dict) else {}
        raw_deployed_deployable = _str(dp.get("Deployed/ Deployable", ""))
        raw_work_nature = _str(dp.get("Work Nature", ""))
        # Paper-level "Learner Population" description (exported from Notion) —
        # high-signal for HEI/program-vs-course scope disambiguation (d-043 review).
        raw_learner_population = _str(dp.get("Learner Population", ""))

        # Find prediction_modeling extraction blocks
        for te in bundle.get("task_extractions", []):
            if te.get("schema_name") != PRED_SCHEMA_NAME:
                continue
            for extracted_row in te.get("extracted") or []:
                raw_task = _str(extracted_row.get("Task"))
                raw_spd = _str(extracted_row.get("Student Performance Definition"))
                raw_target = _str(extracted_row.get("Target"))
                raw_moment = _str(extracted_row.get("Moment of Prediction"))
                raw_context = _str(extracted_row.get("Context"))
                raw_sample = _str(
                    extracted_row.get("Students", "")
                    or extracted_row.get("Courses", "")
                )
                raw_models = _str(extracted_row.get("Models"))
                raw_assessment = _str(extracted_row.get("Assessment Strategy"))

                # Synthesised raw_evidence for T3.3 classifier convenience.
                # If ALL primary evidence fields are empty this is a blank
                # extraction row — skip it (do not emit a contribution row
                # with no evidence).
                evidence_parts = [
                    p for p in [raw_spd, raw_target, raw_moment, raw_context]
                    if p
                ]
                if raw_task:
                    raw_evidence = " | ".join(evidence_parts) if evidence_parts else raw_task
                elif evidence_parts:
                    raw_evidence = " | ".join(evidence_parts)
                else:
                    # Nothing useful in this extracted row — skip it
                    continue

                cid = _contribution_id(
                    paper_id,
                    raw_task,
                    raw_target,
                    raw_moment,
                    raw_models,
                )

                row: dict[str, Any] = {
                    # Identity
                    "contribution_id": cid,
                    "paper_id": paper_id,
                    "paper_title": paper_title,
                    "year": year,
                    # Raw evidence columns
                    "raw_task": raw_task,
                    "raw_student_performance_definition": raw_spd,
                    "raw_target": raw_target,
                    "raw_moment_of_prediction": raw_moment,
                    "raw_context": raw_context,
                    "raw_sample_setting": raw_sample,
                    "raw_models": raw_models,
                    "raw_assessment_strategy": raw_assessment,
                    # Paper-level domain properties (actionability classifier)
                    "raw_deployed_deployable": raw_deployed_deployable,
                    "raw_work_nature": raw_work_nature,
                    # Paper-level learner population (scope disambiguation)
                    "raw_learner_population": raw_learner_population,
                    # Synthesised for test-R-003-001
                    "raw_evidence": raw_evidence,
                    # T6.5 LLM overlay: primary-method LLM tag
                    "llm_primary": _detect_llm_primary(raw_models, raw_task, raw_evidence),
                }

                # Taxonomy placeholders
                for col in _TAXONOMY_PLACEHOLDER_COLS:
                    row[col] = ""

                # Classifier metadata placeholders
                row["classification_confidence"] = ""
                row["classification_notes"] = ""
                row["manual_override_applied"] = ""

                rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def deduplicate_contribution_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove exact duplicate contribution_ids, keeping first occurrence.

    Two extraction rows from the same paper with identical discriminating
    fields (same task, target, moment, models signature) collapse to one.
    """
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        cid = row["contribution_id"]
        if cid not in seen:
            seen.add(cid)
            deduped.append(row)
    return deduped


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

#: Ordered column list for the CSV
CONTRIBUTION_ROW_COLUMNS: list[str] = [
    "contribution_id",
    "paper_id",
    "paper_title",
    "year",
    "raw_task",
    "raw_student_performance_definition",
    "raw_target",
    "raw_moment_of_prediction",
    "raw_context",
    "raw_sample_setting",
    "raw_models",
    "raw_assessment_strategy",
    "raw_learner_population",
    "raw_evidence",
    "llm_primary",
    *_TAXONOMY_PLACEHOLDER_COLS,
    *_CLASSIFIER_META_COLS,
]


def write_contribution_rows_csv(
    rows: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """Write contribution rows to a CSV file.

    Args:
        rows:        List of contribution-row dicts (from
                     :func:`build_contribution_rows`).
        output_path: Destination CSV path.  Parent directories are
                     created automatically.

    Returns:
        The resolved absolute path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=CONTRIBUTION_ROW_COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    return output_path.resolve()


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


def build_and_write_contribution_rows(
    canonical_dir: str | Path,
    output_path: str | Path,
    *,
    deduplicate: bool = True,
) -> tuple[Path, int, int]:
    """Build contribution rows and write them to CSV.

    Args:
        canonical_dir:  Directory of ``*.canonical.json`` bundle files.
        output_path:    Destination CSV path.
        deduplicate:    When True (default) collapse identical contributions.

    Returns:
        Tuple of (csv_path, contribution_row_count, unique_paper_count).
    """
    rows = build_contribution_rows(canonical_dir)
    if deduplicate:
        rows = deduplicate_contribution_rows(rows)

    unique_papers = len({r["paper_id"] for r in rows})
    csv_path = write_contribution_rows_csv(rows, output_path)
    return csv_path, len(rows), unique_papers


__all__ = [
    "CONTRIBUTION_ROW_COLUMNS",
    "PRED_SCHEMA_NAME",
    "build_and_write_contribution_rows",
    "build_contribution_rows",
    "deduplicate_contribution_rows",
    "write_contribution_rows_csv",
]
