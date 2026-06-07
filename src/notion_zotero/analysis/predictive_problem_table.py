"""Table III generator and ``pred-problem-table`` CLI (T3.4).

Produces the redesigned Table III counts (predictive problem taxonomy) from
canonical PRED bundle files, without hardcoding any numbers.

Public API
----------
generate_table3(canonical_dir) -> pandas.DataFrame
    Compose build_contribution_rows -> classify_contribution per row ->
    aggregate into Table III counts (R-005 schema).

main(argv=None)
    Argparse CLI entry point.  Writes three artefacts to ``--output-dir``:
      * table_3_counts.xlsx   (5 sheets)
      * table_3_detail.csv    (per-contribution classified rows)
      * table_3_preview.md    (Markdown render of counts table)

Output sheet manifest
---------------------
  table_3_counts      aggregated counts table (R-005: one row per
                      outcome_scope x supervised_ml_task x target_construct)
  table_3_detail      classified contribution rows (one row per contribution)
  taxonomy_audit      low-confidence / conflict rows flagged by classifier
  manual_overrides    overrides applied (from manual_overrides.yaml)
  term_dictionary     controlled vocabulary from learning_analytics_taxonomy.yaml

R-005 table_3_counts columns
-----------------------------
  outcome_scope               disambiguated taxonomy label (no Horizon column)
  supervised_ml_task          taxonomy label
  target_construct            disambiguated taxonomy label
  unique_papers               count of distinct paper_id in combination
  contribution_rows           count of contribution rows in combination
  early_actionable_papers     papers with early/actionable prediction timing
  deployed_intervention_papers papers with deployed/intervention actionability
  Notes                       free-text; flags audit-routed combinations
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Pandas guard
# ---------------------------------------------------------------------------


def _require_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for generate_table3. "
            "Install the analysis extras: pip install -e .[analysis]"
        ) from exc
    return pd


# ---------------------------------------------------------------------------
# Helpers – loading overrides and taxonomy vocab
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[4]  # …/Notion_Zotero


def _load_manual_overrides(overrides_path: Path | None = None) -> list[dict[str, Any]]:
    """Load manual_overrides.yaml entries (filter illustrative examples)."""
    if overrides_path is None:
        overrides_path = (
            _REPO_ROOT
            / "configs"
            / "reviews"
            / "la_student_success_review"
            / "manual_overrides.yaml"
        )
    if not Path(overrides_path).exists():
        return []
    try:
        import yaml  # type: ignore[import]

        with open(overrides_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        entries = data.get("overrides", []) or []
        return [
            e
            for e in entries
            if not str(e.get("contribution_id", "")).startswith("c-example")
        ]
    except Exception:
        return []


def _load_term_dictionary() -> list[dict[str, str]]:
    """Load the taxonomy controlled vocabulary from learning_analytics_taxonomy.yaml."""
    taxonomy_path = (
        _REPO_ROOT
        / "src"
        / "notion_zotero"
        / "schemas"
        / "domain_packs"
        / "learning_analytics_taxonomy.yaml"
    )
    rows: list[dict[str, str]] = []
    if not taxonomy_path.exists():
        return rows
    try:
        import yaml  # type: ignore[import]

        with open(taxonomy_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        dimensions = data.get("dimensions", {}) or {}
        for dim_name, dim_data in dimensions.items():
            if not isinstance(dim_data, dict):
                continue
            vocab = dim_data.get("vocabulary", []) or []
            definition = dim_data.get("definition", "") or ""
            notes = dim_data.get("notes", "") or ""
            for term in vocab:
                rows.append(
                    {
                        "dimension": dim_name,
                        "term": str(term),
                        "definition": str(definition).strip(),
                        "notes": str(notes).strip(),
                    }
                )
    except Exception:
        pass
    return rows


# ---------------------------------------------------------------------------
# Core classify-and-collect pipeline
# ---------------------------------------------------------------------------

_TAXONOMY_DIMS = [
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


def _classify_rows(contribution_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run classify_contribution() on each row and flatten labels into the dict."""
    from notion_zotero.analysis.pred_horizon_summary import classify_contribution

    classified: list[dict[str, Any]] = []
    for row in contribution_rows:
        result = classify_contribution(row)
        enriched = dict(row)
        for dim in _TAXONOMY_DIMS:
            dim_result = result.get(dim, {})
            if isinstance(dim_result, dict):
                enriched[dim] = dim_result.get("label", "unclear")
                enriched[f"{dim}_confidence"] = dim_result.get("confidence", "low")
                enriched[f"{dim}_evidence"] = dim_result.get("evidence", "")
            else:
                enriched[dim] = str(dim_result)
                enriched[f"{dim}_confidence"] = "low"
                enriched[f"{dim}_evidence"] = ""

        # Derive classification_confidence = minimum confidence across all dims
        confidences = [
            enriched.get(f"{dim}_confidence", "low") for dim in _TAXONOMY_DIMS
        ]
        _weight = {"high": 2, "medium": 1, "low": 0}
        min_conf = min(confidences, key=lambda c: _weight.get(c, 0))
        enriched["classification_confidence"] = min_conf

        # route_to_audit flag
        enriched["route_to_audit"] = bool(result.get("route_to_audit", False))
        enriched["manual_override_applied"] = bool(
            result.get("manual_override_applied", False)
        )
        classified.append(enriched)
    return classified


# ---------------------------------------------------------------------------
# Table III aggregation (R-005)
# ---------------------------------------------------------------------------

# Canonical sort order for outcome_scope labels (coarse-to-fine temporal order)
_OUTCOME_SCOPE_ORDER: list[str] = [
    "interaction_or_item",
    "assessment",
    "course_or_module",
    "term_or_semester",
    "program_or_degree",
    "institution_or_system",
    "mixed_or_multiple",
    "unclear",
]

# Canonical sort order for supervised_ml_task labels
_ML_TASK_ORDER: list[str] = [
    "classification",
    "regression",
    "survival",
    "sequence_forecast",
    "ranking",
    "other",
    "unclear",
]

# ---------------------------------------------------------------------------
# Change 1: TARGET_GROUP_MAP — fine-grained target_construct → 6 display groups
# ---------------------------------------------------------------------------

TARGET_GROUP_MAP: dict[str, str] = {
    "grade_or_score": "grade_or_score",
    "pass_fail_or_success_failure": "pass_fail_or_at_risk",
    "at_risk_or_performance_tier": "pass_fail_or_at_risk",
    "dropout_or_withdrawal": "dropout_or_retention",
    "retention_or_persistence": "dropout_or_retention",
    "completion_or_certification": "completion_or_graduation",
    "graduation_or_degree_completion": "completion_or_graduation",
    "time_to_completion": "completion_or_graduation",
    "gpa_or_cumulative_performance": "gpa_or_cumulative",
    "submission_timing_or_delay": "other",
    "next_interaction_correctness": "other",
    "learning_gain_or_skill_mastery": "other",
    "enrolment_or_course_selection": "other",
    "unclear": "other",
    "other_or_unclear": "other",
}


def _is_early_actionable(row: dict[str, Any]) -> bool:
    """Heuristic: prediction timing is early enough to allow intervention."""
    timing = str(row.get("prediction_timing", "unclear"))
    early_timings = {
        "before_course_or_at_course_enrolment",
        "early_course",
        "mid_course",
        "before_program_or_at_admission",
        "program_milestone",
        "continuous_or_repeated",
    }
    return timing in early_timings


def _is_implemented(row: dict[str, Any]) -> bool:
    """True when actionability_status indicates real deployment or intervention."""
    status = str(row.get("actionability_status", "unclear"))
    return status in (
        "deployed_or_deployable",
        "deployed_with_intervention_evaluation",
    )


def aggregate_table3(classified_rows: list[dict[str, Any]]) -> "Any":
    """Aggregate classified contribution rows into Table III counts DataFrame.

    Implements R-005: one row per (outcome_scope, supervised_ml_task,
    target_group) — where target_group is the 6-group display label derived
    via TARGET_GROUP_MAP from the fine-grained target_construct.

    Columns:
      outcome_scope | supervised_ml_task | target_construct |
      unique_papers | contribution_rows |
      early_actionable_papers | deployed_intervention_papers | Notes

    Note: the column is named ``target_construct`` in output for R-005
    compatibility, but its values are the 6 display groups.

    Conflict-flagged rows (route_to_audit=True) carry their classifier-assigned
    taxonomy labels and are noted in the Notes column.  They are never silently
    merged.

    Rows are sorted by descending unique_papers (most prevalent first);
    ties broken by target_group overall frequency then outcome_scope.
    """
    pd = _require_pandas()

    # Accumulate per-bucket paper sets, contribution counts, and audit flags
    # key = (outcome_scope, supervised_ml_task, target_group)
    paper_sets: dict[tuple[str, str, str], set[str]] = {}
    early_sets: dict[tuple[str, str, str], set[str]] = {}
    deployed_sets: dict[tuple[str, str, str], set[str]] = {}
    contrib_counts: dict[tuple[str, str, str], int] = {}
    audit_counts: dict[tuple[str, str, str], int] = {}

    for row in classified_rows:
        outcome_scope = str(row.get("outcome_scope") or "unclear")
        supervised_ml_task = str(row.get("supervised_ml_task") or "other")
        fine_target = str(row.get("target_construct") or "other_or_unclear")
        # Map fine label → 6-group display label; unknown fine labels fall to "other"
        target_group = TARGET_GROUP_MAP.get(fine_target, "other")
        key = (outcome_scope, supervised_ml_task, target_group)

        paper_id = str(row.get("paper_id", ""))

        if key not in paper_sets:
            paper_sets[key] = set()
            early_sets[key] = set()
            deployed_sets[key] = set()
            contrib_counts[key] = 0
            audit_counts[key] = 0

        contrib_counts[key] += 1
        if row.get("route_to_audit"):
            audit_counts[key] += 1

        if paper_id:
            paper_sets[key].add(paper_id)
            if _is_early_actionable(row):
                early_sets[key].add(paper_id)
            # Change 3: wire deployed_intervention_papers — _is_implemented
            # checks actionability_status ∈ {deployed_or_deployable,
            # deployed_with_intervention_evaluation}
            if _is_implemented(row):
                deployed_sets[key].add(paper_id)

    if not paper_sets:
        return pd.DataFrame(
            columns=[
                "outcome_scope",
                "supervised_ml_task",
                "target_construct",
                "unique_papers",
                "contribution_rows",
                "early_actionable_papers",
                "deployed_intervention_papers",
                "Notes",
            ]
        )

    # Change 2: sort by descending unique_papers; ties broken by target_group
    # overall frequency (across all outcome_scope × ml_task combos), then
    # outcome_scope canonical order.
    #
    # Compute target_group overall paper counts for tie-breaking.
    tg_total: dict[str, int] = {}
    for k, pset in paper_sets.items():
        tg = k[2]
        tg_total[tg] = tg_total.get(tg, 0) + len(pset)

    def _sort_key(k: tuple[str, str, str]) -> tuple[int, int, int]:
        n_papers = len(paper_sets[k])
        tg_freq = tg_total.get(k[2], 0)
        os_idx = (
            _OUTCOME_SCOPE_ORDER.index(k[0]) if k[0] in _OUTCOME_SCOPE_ORDER else 99
        )
        # Negative for descending; outcome_scope ascending for stable ordering
        return (-n_papers, -tg_freq, os_idx)

    sorted_keys = sorted(paper_sets.keys(), key=_sort_key)

    output_rows: list[dict[str, Any]] = []
    for key in sorted_keys:
        outcome_scope, supervised_ml_task, target_group = key
        n_audit = audit_counts[key]
        notes = (
            f"{n_audit} row(s) routed to taxonomy_audit"
            if n_audit > 0
            else ""
        )
        output_rows.append(
            {
                "outcome_scope": outcome_scope,
                "supervised_ml_task": supervised_ml_task,
                # R-005 column is named target_construct; value is the display group
                "target_construct": target_group,
                "unique_papers": len(paper_sets[key]),
                "contribution_rows": contrib_counts[key],
                "early_actionable_papers": len(early_sets[key]),
                "deployed_intervention_papers": len(deployed_sets[key]),
                "Notes": notes,
            }
        )

    return pd.DataFrame(output_rows)


# ---------------------------------------------------------------------------
# generate_table3 — public entry point
# ---------------------------------------------------------------------------


def generate_table3(canonical_dir: str | Path) -> "Any":
    """Compose build_contribution_rows -> classify -> aggregate into Table III.

    Implements the R-005 contract: the returned DataFrame is keyed by
    (outcome_scope, supervised_ml_task, target_construct) — the disambiguated
    taxonomy labels assigned by the classifier.  There is no ``Horizon`` column.

    Args:
        canonical_dir:
            Directory containing ``*.canonical.json`` canonical bundle files.

    Returns:
        pandas.DataFrame with columns (R-005):
          outcome_scope | supervised_ml_task | target_construct |
          unique_papers | contribution_rows |
          early_actionable_papers | deployed_intervention_papers | Notes
    """
    from notion_zotero.analysis.contribution_rows import (
        build_contribution_rows,
        deduplicate_contribution_rows,
    )

    canonical_dir = Path(canonical_dir)
    rows = build_contribution_rows(canonical_dir)
    rows = deduplicate_contribution_rows(rows)
    classified = _classify_rows(rows)
    return aggregate_table3(classified)


# ---------------------------------------------------------------------------
# Taxonomy audit extraction
# ---------------------------------------------------------------------------


def _build_taxonomy_audit(classified_rows: list[dict[str, Any]]) -> "Any":
    """Return a DataFrame of rows flagged for audit (low-confidence or conflict)."""
    pd = _require_pandas()

    audit_rows = [r for r in classified_rows if r.get("route_to_audit")]
    if not audit_rows:
        cols = [
            "contribution_id",
            "paper_id",
            "paper_title",
            "route_to_audit",
            "classification_confidence",
            "classification_notes",
            "raw_evidence",
        ] + _TAXONOMY_DIMS
        return pd.DataFrame(columns=cols)

    records: list[dict[str, Any]] = []
    for row in audit_rows:
        rec: dict[str, Any] = {
            "contribution_id": row.get("contribution_id", ""),
            "paper_id": row.get("paper_id", ""),
            "paper_title": row.get("paper_title", ""),
            "route_to_audit": row.get("route_to_audit", False),
            "classification_confidence": row.get("classification_confidence", "low"),
            "classification_notes": row.get("classification_notes", ""),
            "raw_evidence": row.get("raw_evidence", ""),
        }
        for dim in _TAXONOMY_DIMS:
            rec[dim] = row.get(dim, "unclear")
        records.append(rec)

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Markdown preview renderer
# ---------------------------------------------------------------------------


def _render_markdown(counts_df: "Any") -> str:
    """Render the Table III counts DataFrame as a Markdown table (R-005 schema)."""
    lines: list[str] = [
        "# Table III — Predictive Modelling Problem Taxonomy (R-005)",
        "",
        "Decomposition of predictive modelling contributions by disambiguated",
        "outcome scope, supervised ML task, and target construct.",
        "Columns: outcome_scope | supervised_ml_task | target_construct |",
        "unique_papers | contribution_rows | early_actionable_papers |",
        "deployed_intervention_papers | Notes",
        "",
        "> Note: `unique_papers` counts distinct paper IDs per combination;",
        "> `contribution_rows` counts individual extracted contribution rows",
        "> (a paper with multiple targets yields multiple rows).",
        "",
    ]
    if counts_df.empty:
        lines.append("*(No data — canonical_dir returned zero accepted PRED bundles.)*")
        return "\n".join(lines)

    cols = list(counts_df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines.append(header)
    lines.append(sep)

    for _, row in counts_df.iterrows():
        cells = [str(row[c]) for c in cols]
        lines.append("| " + " | ".join(cells) + " |")

    total_papers = counts_df["unique_papers"].sum() if "unique_papers" in counts_df.columns else "?"
    total_contribs = counts_df["contribution_rows"].sum() if "contribution_rows" in counts_df.columns else "?"
    lines.append("")
    lines.append(
        f"*{len(counts_df)} taxonomy combinations. "
        f"Total unique_papers (sum, may double-count multi-contribution papers): {total_papers}. "
        f"Total contribution_rows: {total_contribs}. "
        "See table_3_detail.csv for per-contribution rows.*"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5-sheet workbook writer
# ---------------------------------------------------------------------------


def _write_workbook(
    output_path: Path,
    counts_df: "Any",
    detail_df: "Any",
    audit_df: "Any",
    overrides_rows: list[dict[str, Any]],
    term_dict_rows: list[dict[str, str]],
) -> None:
    """Write the 5-sheet workbook to output_path."""
    pd = _require_pandas()

    overrides_df = pd.DataFrame(overrides_rows) if overrides_rows else pd.DataFrame(
        columns=["contribution_id", "paper_id", "field", "value", "rationale",
                 "reviewer", "date", "supersedes"]
    )
    term_dict_df = pd.DataFrame(term_dict_rows) if term_dict_rows else pd.DataFrame(
        columns=["dimension", "term", "definition", "notes"]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            counts_df.to_excel(writer, sheet_name="table_3_counts", index=False)
            detail_df.to_excel(writer, sheet_name="table_3_detail", index=False)
            audit_df.to_excel(writer, sheet_name="taxonomy_audit", index=False)
            overrides_df.to_excel(writer, sheet_name="manual_overrides", index=False)
            term_dict_df.to_excel(writer, sheet_name="term_dictionary", index=False)
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required to write Excel workbooks. "
            "Install with: pip install openpyxl"
        ) from exc


# ---------------------------------------------------------------------------
# detail_df builder — flat columns, one row per classified contribution
# ---------------------------------------------------------------------------


def _build_detail_df(classified_rows: list[dict[str, Any]]) -> "Any":
    """Return a DataFrame with one row per classified contribution.

    Columns include all raw evidence fields, all 10 taxonomy dimensions
    (assigned by classify_contribution), and classifier metadata.
    No derived Horizon / display-label columns — the taxonomy labels
    (outcome_scope, supervised_ml_task, target_construct) are the
    canonical values and do not need re-mapping.
    """
    pd = _require_pandas()
    if not classified_rows:
        return pd.DataFrame()

    keep_cols = [
        "contribution_id",
        "paper_id",
        "paper_title",
        "year",
        "raw_task",
        "raw_target",
        "raw_student_performance_definition",
        "raw_moment_of_prediction",
        "raw_context",
        "raw_evidence",
        "raw_models",
        "raw_assessment_strategy",
        "classification_confidence",
        "route_to_audit",
        "manual_override_applied",
    ] + _TAXONOMY_DIMS

    records: list[dict[str, Any]] = []
    for row in classified_rows:
        rec: dict[str, Any] = {}
        for col in keep_cols:
            rec[col] = row.get(col, "")
        records.append(rec)

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# main — argparse CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Argparse CLI entry point for ``pred-problem-table``.

    Usage::

        pred-problem-table \\
            --canonical-dir data/pulled/notion/learning_analytics_review \\
            --output-dir    data/analysis_outputs/la_review/tables

    Writes three artefacts to ``--output-dir``:
      * ``table_3_counts.xlsx``   — 5-sheet workbook
      * ``table_3_detail.csv``    — per-contribution classified rows
      * ``table_3_preview.md``    — Markdown render of the counts table
    """
    parser = argparse.ArgumentParser(
        prog="pred-problem-table",
        description=(
            "Generate Table III (predictive problem taxonomy) from canonical bundles. "
            "Writes table_3_counts.xlsx, table_3_detail.csv, and table_3_preview.md."
        ),
    )
    parser.add_argument(
        "--canonical-dir",
        required=True,
        help="Directory containing *.canonical.json bundle files.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/analysis_outputs/la_review/tables",
        help="Output directory for generated artefacts (default: data/analysis_outputs/la_review/tables).",
    )
    parser.add_argument(
        "--overrides-path",
        default=None,
        help="Path to manual_overrides.yaml (auto-detected if not supplied).",
    )
    args = parser.parse_args(argv)

    canonical_dir = Path(args.canonical_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Load and classify ---
    from notion_zotero.analysis.contribution_rows import (
        build_contribution_rows,
        deduplicate_contribution_rows,
    )

    print(f"Loading canonical bundles from: {canonical_dir}", file=sys.stderr)
    rows = build_contribution_rows(canonical_dir)
    rows = deduplicate_contribution_rows(rows)
    print(f"  Found {len(rows)} deduplicated contribution rows.", file=sys.stderr)

    classified = _classify_rows(rows)
    print(f"  Classified {len(classified)} rows.", file=sys.stderr)

    # --- Build outputs ---
    counts_df = aggregate_table3(classified)
    detail_df = _build_detail_df(classified)
    audit_df = _build_taxonomy_audit(classified)

    overrides_path = (
        Path(args.overrides_path) if args.overrides_path else None
    )
    overrides_rows = _load_manual_overrides(overrides_path)
    term_dict_rows = _load_term_dictionary()

    # --- Write artefacts ---
    xlsx_path = output_dir / "table_3_counts.xlsx"
    csv_path = output_dir / "table_3_detail.csv"
    md_path = output_dir / "table_3_preview.md"

    _write_workbook(
        xlsx_path, counts_df, detail_df, audit_df, overrides_rows, term_dict_rows
    )
    print(f"  Wrote workbook: {xlsx_path}", file=sys.stderr)

    detail_df.to_csv(csv_path, index=False)
    print(f"  Wrote detail CSV: {csv_path}", file=sys.stderr)

    md_text = _render_markdown(counts_df)
    md_path.write_text(md_text, encoding="utf-8")
    print(f"  Wrote Markdown preview: {md_path}", file=sys.stderr)

    # Print summary to stdout
    print("\n=== Table III Summary ===")
    if not counts_df.empty:
        print(counts_df.to_string(index=False))
    else:
        print("(No accepted PRED contributions found in canonical bundles.)")

    n_audit = len(audit_df)
    n_overrides = len(overrides_rows)
    print(f"\nContributions classified: {len(classified)}")
    print(f"Rows routed to taxonomy audit: {n_audit}")
    print(f"Manual overrides in config: {n_overrides}")


# ---------------------------------------------------------------------------
# Audit gate (T7.1) — pre-export validation
# ---------------------------------------------------------------------------

_TAXONOMY_YAML = (
    Path(__file__).resolve().parents[1]
    / "schemas" / "domain_packs" / "learning_analytics_taxonomy.yaml"
)
_AUDIT_REQUIRED_FIELDS = ("contribution_id", "raw_evidence")
_AUDIT_ALLOWED_SENTINELS = {"", "unclear", "nan", "none"}


class AuditGateError(Exception):
    """Raised by :func:`run_audit_gate` when pre-export checks fail."""


def _load_taxonomy_vocab() -> dict[str, set[str]]:
    """Load ``{dimension: {valid terms}}`` from the taxonomy YAML."""
    try:
        import yaml  # type: ignore[import]

        data = yaml.safe_load(_TAXONOMY_YAML.read_text(encoding="utf-8"))
    except Exception:
        return {}
    vocab: dict[str, set[str]] = {}
    for dim, dim_data in (data.get("dimensions") or {}).items():
        if isinstance(dim_data, dict):
            vocab[dim] = {str(t) for t in (dim_data.get("vocabulary") or [])}
    return vocab


def run_audit_gate(df: "Any", report_path: "str | Path | None" = None) -> None:
    """Pre-export audit gate (R-017).

    Validates each taxonomy-dimension column against the controlled vocabulary
    and checks that required fields are populated.  On any violation it writes
    ``audit_gate_report.md`` (when *report_path* is given) and raises
    :class:`AuditGateError`.  Returns ``None`` on clean data.
    """
    vocab = _load_taxonomy_vocab()
    columns = list(getattr(df, "columns", []))
    violations: list[str] = []

    for dim, valid in vocab.items():
        if dim not in columns:
            continue
        for idx, value in df[dim].items():
            term = str(value).strip()
            if term.lower() in _AUDIT_ALLOWED_SENTINELS:
                continue
            if term not in valid:
                violations.append(
                    f"row {idx}: column '{dim}' has unmatched term '{term}'"
                )

    for field in _AUDIT_REQUIRED_FIELDS:
        if field not in columns:
            continue
        for idx, value in df[field].items():
            cell = str(value).strip()
            if not cell or cell.lower() == "nan":
                violations.append(f"row {idx}: required field '{field}' is empty")

    if violations:
        if report_path is not None:
            report_path = Path(report_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                "# Audit Gate Report — EXPORT BLOCKED",
                "",
                f"**{len(violations)} violation(s) found.** Resolve all before export.",
                "",
                *[f"- {v}" for v in violations],
            ]
            report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        raise AuditGateError(
            f"Audit gate failed with {len(violations)} violation(s); "
            "see audit_gate_report.md"
        )
    return None


__all__ = [
    "generate_table3",
    "aggregate_table3",
    "main",
    "TARGET_GROUP_MAP",
    "AuditGateError",
    "run_audit_gate",
]
