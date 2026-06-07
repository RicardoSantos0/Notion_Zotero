"""LA-review figure-data builders and Figure 1-6 renderers (T5.1 / T5.2).

Reconstructs the figure data for the learning-analytics review from the
canonical bundles (the original Figure 2-3 plotting code was lost) and renders
Figures 1-6 as PNG + Markdown caption.

Data builders (write to ``data/analysis_outputs/la_review/figure_data/``)
------------------------------------------------------------------------
build_prisma_flow                     -> prisma_flow.csv                  (Fig 1)
build_representation_usage_over_time  -> representation_usage_over_time.csv (Fig 2, wide)
build_representation_by_task_over_time-> representation_by_task_over_time.csv (Fig 3, long)
build_data_source_task_heatmap        -> data_source_task_heatmap.csv     (Fig 4)
build_actionability_funnel            -> actionability_funnel.csv         (Fig 6)
build_all_figure_data                 -> all of the above

Renderers (write to ``data/analysis_outputs/la_review/figures/``)
-----------------------------------------------------------------
render_all_figures -> figure_{1..6}.png + figure_{1..6}_caption.md
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from notion_zotero.analysis.paper_tables import (
    _TABLE2_TASK_ORDER,
    _bundle_extracted_rows,
    _bundle_paper_id,
    _bundle_task_label,
    _collect_models,
    _collect_representations,
    _load_canonical_bundles,
    _pred_paper_maturity,
    generate_table2,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LA_REVIEW_ROOT = _REPO_ROOT / "data" / "analysis_outputs" / "la_review"

#: Learner-representation categories shown in Figures 2-3 (most recurring).
_REPRESENTATION_CATEGORIES: list[str] = [
    "Prior academic performance",
    "LMS activity",
    "Demographics",
    "Assessment interactions",
    "Course / content metadata",
    "Temporal / sequential behavior",
    "Forum / social interaction",
]

#: Ordered PRISMA stages (identification -> inclusion).
_PRISMA_STAGE_ORDER: list[str] = [
    "Records identified",
    "Excluded at title screening",
    "Excluded after abstract",
    "Excluded after full-text",
    "Studies included",
]


def _figure_data_dir(out_dir: "str | Path | None") -> Path:
    return Path(out_dir) if out_dir else _LA_REVIEW_ROOT / "figure_data"


def _figures_dir(out_dir: "str | Path | None") -> Path:
    return Path(out_dir) if out_dir else _LA_REVIEW_ROOT / "figures"


def _paper_year(bundle: dict) -> "int | None":
    for ref in bundle.get("references") or []:
        raw = ref.get("year")
        if raw:
            try:
                return int(str(raw)[:4])
            except (TypeError, ValueError):
                continue
    return None


def _prisma_stage(bundle: dict) -> str:
    """Classify a paper into a PRISMA stage from its workflow-state log."""
    states = [str(w.get("state", "")).lower() for w in bundle.get("workflow_states") or []]
    if any(s.startswith("accepted for") for s in states):
        return "included"
    if any("rejected after full" in s for s in states):
        return "excluded_fulltext"
    if any("rejected after abstract" in s for s in states):
        return "excluded_abstract"
    if any(("rejected before reading" in s) or s.startswith("rejected for") for s in states):
        return "excluded_screening"
    return "other"


# ---------------------------------------------------------------------------
# Figure 1 — PRISMA flow
# ---------------------------------------------------------------------------


def build_prisma_flow(
    canonical_dir: "str | Path", out_dir: "str | Path | None" = None
) -> "Any":
    """Build the PRISMA selection funnel from per-paper workflow states."""
    import pandas as pd

    bundles = _load_canonical_bundles(Path(canonical_dir))
    stages = [_prisma_stage(b) for b in bundles]
    identified = len(bundles)
    rows = [
        {"Stage": "Records identified", "Count": identified},
        {"Stage": "Excluded at title screening", "Count": stages.count("excluded_screening")},
        {"Stage": "Excluded after abstract", "Count": stages.count("excluded_abstract")},
        {"Stage": "Excluded after full-text", "Count": stages.count("excluded_fulltext")},
        {"Stage": "Studies included", "Count": stages.count("included")},
    ]
    df = pd.DataFrame(rows, columns=["Stage", "Count"])
    _write_csv(df, out_dir, "prisma_flow.csv")
    return df


# ---------------------------------------------------------------------------
# Figure 2 — representation usage over time (wide)
# Figure 3 — representation by task over time (long)
# ---------------------------------------------------------------------------


def _representation_records(bundles: list[dict]) -> list[tuple[int, str, str, str]]:
    """Yield ``(year, task, paper_id, representation_category)`` records."""
    records: list[tuple[int, str, str, str]] = []
    for bundle in bundles:
        year = _paper_year(bundle)
        if year is None:
            continue
        task = _bundle_task_label(bundle) or "PRED"
        paper_id = _bundle_paper_id(bundle)
        if not paper_id:
            continue
        rows = _bundle_extracted_rows(bundle)
        for category in set(_collect_representations(rows, task)):
            if category in _REPRESENTATION_CATEGORIES:
                records.append((year, task, paper_id, category))
    return records


def build_representation_usage_over_time(
    canonical_dir: "str | Path", out_dir: "str | Path | None" = None
) -> "Any":
    """Wide year x representation-category unique-paper counts (Figure 2)."""
    import pandas as pd

    bundles = _load_canonical_bundles(Path(canonical_dir))
    records = _representation_records(bundles)
    if not records:
        df = pd.DataFrame(columns=["year", *_REPRESENTATION_CATEGORIES])
        _write_csv(df, out_dir, "representation_usage_over_time.csv")
        return df

    long_df = pd.DataFrame(records, columns=["year", "task", "paper_id", "representation"])
    counts = (
        long_df.drop_duplicates(["year", "representation", "paper_id"])
        .groupby(["year", "representation"])
        .size()
        .reset_index(name="n")
    )
    wide = (
        counts.pivot(index="year", columns="representation", values="n")
        .reindex(columns=_REPRESENTATION_CATEGORIES)
        .fillna(0)
        .astype(int)
        .reset_index()
        .sort_values("year")
    )
    wide.columns.name = None
    _write_csv(wide, out_dir, "representation_usage_over_time.csv")
    return wide


def build_representation_by_task_over_time(
    canonical_dir: "str | Path", out_dir: "str | Path | None" = None
) -> "Any":
    """Long year x task x representation unique-paper counts (Figure 3)."""
    import pandas as pd

    bundles = _load_canonical_bundles(Path(canonical_dir))
    records = _representation_records(bundles)
    if not records:
        df = pd.DataFrame(columns=["year", "task", "representation", "n_papers"])
        _write_csv(df, out_dir, "representation_by_task_over_time.csv")
        return df

    long_df = pd.DataFrame(records, columns=["year", "task", "paper_id", "representation"])
    counts = (
        long_df.drop_duplicates(["year", "task", "representation", "paper_id"])
        .groupby(["year", "task", "representation"])
        .size()
        .reset_index(name="n_papers")
        .sort_values(["year", "task", "representation"])
    )
    _write_csv(counts, out_dir, "representation_by_task_over_time.csv")
    return counts


# ---------------------------------------------------------------------------
# Figure 4 — data-source x task heatmap
# ---------------------------------------------------------------------------


def build_data_source_task_heatmap(
    canonical_dir: "str | Path", out_dir: "str | Path | None" = None
) -> "Any":
    """Data-source x task unique-paper matrix (Figure 4), reusing Table 2."""
    df = generate_table2(canonical_dir)
    matrix = df.drop(columns=[c for c in ("Total",) if c in df.columns])
    _write_csv(matrix, out_dir, "data_source_task_heatmap.csv")
    return matrix


# ---------------------------------------------------------------------------
# Figure 6 — actionability / deployment funnel (PRED)
# ---------------------------------------------------------------------------


def build_actionability_funnel(
    canonical_dir: "str | Path", out_dir: "str | Path | None" = None
) -> "Any":
    """PRED deployment funnel: classified -> backtested+ -> deployed+ -> intervention."""
    import pandas as pd

    maturity = _pred_paper_maturity(Path(canonical_dir))
    total = len(maturity)
    deployed = sum(
        1
        for m in maturity.values()
        if m in ("deployed", "deployed with intervention evaluation")
    )
    intervention = sum(
        1 for m in maturity.values() if m == "deployed with intervention evaluation"
    )
    rows = [
        {"Stage": "PRED papers classified", "Count": total},
        {"Stage": "Evaluated (backtested or better)", "Count": total},
        {"Stage": "Deployed or deployable", "Count": deployed},
        {"Stage": "Deployed with intervention evaluation", "Count": intervention},
    ]
    df = pd.DataFrame(rows, columns=["Stage", "Count"])
    _write_csv(df, out_dir, "actionability_funnel.csv")
    return df


# ---------------------------------------------------------------------------
# Figure 7 — model family by task and year (data-contingent: GO, Models 93%)
# ---------------------------------------------------------------------------

#: Ordered (family, keyword) rules — first match wins (specific before generic).
_MODEL_FAMILY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Neural / deep", ("dkt", "dkvmn", "sakt", "akt", "saint", "neural", "mlp",
                        "perceptron", "cnn", "convolut", "rnn", "lstm", "gru",
                        "transformer", "deep", "bert", "gpt", "attention", "autoencoder")),
    ("Tree ensemble", ("random forest", "gradient boost", "xgboost", "lightgbm",
                        "catboost", "adaboost", "decision tree", "extra tree",
                        "bagging", "boost")),
    ("Probabilistic / Bayesian", ("bkt", "bayes", "markov", "hmm",
                                   "expectation", "gaussian", "latent", "probabilistic")),
    ("SVM / kernel", ("support vector", "svm", "kernel")),
    ("Recommender", ("collaborative filtering", "content-based", "hybrid recommendation",
                     "knowledge-based recommendation", "matrix factorization")),
    ("Clustering", ("k-means", "kmeans", "hierarchical clustering", "dbscan", "cluster")),
    ("Instance-based", ("k-nearest", "knn", "nearest neighbor")),
    ("Linear", ("logistic", "linear regression", "lasso", "ridge", "elastic",
                "linear model", "regression")),
]


def _model_family(model_label: str) -> str:
    text = model_label.lower()
    for family, keywords in _MODEL_FAMILY_RULES:
        if any(kw in text for kw in keywords):
            return family
    return "Other"


def build_model_family_by_task_year(
    canonical_dir: "str | Path", out_dir: "str | Path | None" = None
) -> "Any":
    """Distinct-paper counts per (year, task, model_family) — Figure 7 (R-010)."""
    import pandas as pd

    bundles = _load_canonical_bundles(Path(canonical_dir))
    paper_sets: dict[tuple[int, str, str], set[str]] = {}
    for bundle in bundles:
        year = _paper_year(bundle)
        task = _bundle_task_label(bundle)
        paper_id = _bundle_paper_id(bundle)
        if year is None or task is None or not paper_id:
            continue
        rows = _bundle_extracted_rows(bundle)
        families = {_model_family(m) for m in _collect_models(rows, task)}
        for family in families:
            paper_sets.setdefault((year, task, family), set()).add(paper_id)

    records = [
        {"year": y, "task": t, "model_family": f, "paper_count": len(papers)}
        for (y, t, f), papers in paper_sets.items()
    ]
    df = pd.DataFrame(
        sorted(records, key=lambda r: (r["year"], r["task"], r["model_family"]))
        or [],
        columns=["year", "task", "model_family", "paper_count"],
    )
    _write_csv(df, out_dir, "model_family_by_task_year.csv")
    return df


# ---------------------------------------------------------------------------
# Figure 8 — ambiguity audit dashboard (developer tool, stretch)
# ---------------------------------------------------------------------------


def _unmatched_data_source_count(canonical_dir: Path) -> int:
    """Distinct unmatched data-source tokens across the corpus."""
    from notion_zotero.analysis.table_normalization import extract_canonical_terms
    from notion_zotero.schemas.domain_packs import education_learning_analytics as ela

    bundles = _load_canonical_bundles(canonical_dir)
    unmatched: set[str] = set()
    for bundle in bundles:
        for row in _bundle_extracted_rows(bundle):
            raw = row.get("Data sources")
            if raw is None:
                continue
            for term in extract_canonical_terms(
                raw,
                alias_patterns=ela.DATA_SOURCE_ALIAS_PATTERNS,
                keep_unmatched=True,
                missing_values=ela.DATA_SOURCE_MISSING_VALUES,
            ):
                if not term["matched"]:
                    unmatched.add(str(term["raw_token"]).strip().lower())
    return len(unmatched)


def compute_audit_metrics(canonical_dir: "str | Path") -> dict[str, int]:
    """Return the three Figure-8 audit metrics as non-negative ints (R-011)."""
    from notion_zotero.analysis.contribution_rows import (
        build_contribution_rows,
        deduplicate_contribution_rows,
    )
    from notion_zotero.analysis.predictive_problem_table import (
        _classify_rows,
        _load_manual_overrides,
    )

    canonical_dir = Path(canonical_dir)
    classified = _classify_rows(
        deduplicate_contribution_rows(build_contribution_rows(canonical_dir))
    )
    low_conf = sum(
        1 for r in classified if r.get("classification_confidence") == "low"
    )
    return {
        "unmatched_terms_count": int(_unmatched_data_source_count(canonical_dir)),
        "low_confidence_rows_count": int(low_conf),
        "override_count": int(len(_load_manual_overrides())),
    }


def build_audit_dashboard(
    canonical_dir: "str | Path", figures_dir: "str | Path | None" = None
) -> dict[str, int]:
    """Render Figure 8 audit dashboard PNG + companion metadata JSON (R-011)."""
    import json

    metrics = compute_audit_metrics(canonical_dir)
    fig_dir = _figures_dir(figures_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)

    plt, fig, ax = _new_axes((9, 5.5))
    labels = ["Unmatched\nterms", "Low-confidence\nrows", "Manual\noverrides"]
    values = [
        metrics["unmatched_terms_count"],
        metrics["low_confidence_rows_count"],
        metrics["override_count"],
    ]
    ax.bar(labels, values, color=["#C44E52", "#DD8452", "#8172B3"])
    for x, v in enumerate(values):
        ax.text(x, v, str(v), ha="center", va="bottom")
    ax.set_ylabel("Count")
    ax.set_title("Figure 8 — Taxonomy ambiguity audit dashboard (developer tool)")
    fig.tight_layout()
    fig.savefig(fig_dir / "figure_8_audit_dashboard.png", dpi=150)
    plt.close(fig)

    (fig_dir / "figure_8_metadata.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    return metrics


def build_all_figure_data(
    canonical_dir: "str | Path", out_dir: "str | Path | None" = None
) -> "dict[str, Any]":
    """Build and write all figure-data CSVs; return them keyed by filename stem."""
    return {
        "prisma_flow": build_prisma_flow(canonical_dir, out_dir),
        "representation_usage_over_time": build_representation_usage_over_time(canonical_dir, out_dir),
        "representation_by_task_over_time": build_representation_by_task_over_time(canonical_dir, out_dir),
        "data_source_task_heatmap": build_data_source_task_heatmap(canonical_dir, out_dir),
        "actionability_funnel": build_actionability_funnel(canonical_dir, out_dir),
        "model_family_by_task_year": build_model_family_by_task_year(canonical_dir, out_dir),
    }


def _write_csv(df: "Any", out_dir: "str | Path | None", name: str) -> Path:
    directory = _figure_data_dir(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    df.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Figure rendering (matplotlib, headless)
# ---------------------------------------------------------------------------


def _new_axes(figsize: tuple[float, float] = (10.0, 6.0)):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt, *plt.subplots(figsize=figsize)


def _save(plt, fig, figures_dir: Path, num: int, caption: str) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(figures_dir / f"figure_{num}.png", dpi=150)
    plt.close(fig)
    (figures_dir / f"figure_{num}_caption.md").write_text(caption, encoding="utf-8")


def render_all_figures(
    figure_data_dir: "str | Path | None" = None,
    figures_dir: "str | Path | None" = None,
) -> list[Path]:
    """Render Figures 1-6 (PNG + caption) from the figure-data CSVs."""
    import pandas as pd

    data_dir = _figure_data_dir(figure_data_dir)
    fig_dir = _figures_dir(figures_dir)

    # Figure 1 — PRISMA funnel
    prisma = pd.read_csv(data_dir / "prisma_flow.csv")
    plt, fig, ax = _new_axes((9, 6))
    ax.barh(prisma["Stage"][::-1], prisma["Count"][::-1], color="#4C72B0")
    for y, v in enumerate(prisma["Count"][::-1]):
        ax.text(v, y, f" {v}", va="center")
    ax.set_xlabel("Papers")
    ax.set_title("Figure 1 — PRISMA study-selection flow")
    _save(
        plt, fig, fig_dir, 1,
        "**Figure 1.** PRISMA flow of study identification, screening, and inclusion "
        "for the learning-analytics review, derived from the screening workflow log.\n",
    )

    # Figure 2 — representation usage over time
    rep = pd.read_csv(data_dir / "representation_usage_over_time.csv")
    plt, fig, ax = _new_axes((11, 6))
    for col in [c for c in rep.columns if c != "year"]:
        ax.plot(rep["year"], rep[col], marker="o", label=col)
    ax.set_xlabel("Year")
    ax.set_ylabel("Papers")
    ax.set_title("Figure 2 — Learner-representation usage over time")
    ax.legend(fontsize=8, ncol=2)
    _save(
        plt, fig, fig_dir, 2,
        "**Figure 2.** Number of papers using each learner-representation category by "
        "publication year.\n",
    )

    # Figure 3 — representation by task over time (faceted totals per task)
    rbt = pd.read_csv(data_dir / "representation_by_task_over_time.csv")
    plt, fig, ax = _new_axes((11, 6))
    for task in _TABLE2_TASK_ORDER:
        sub = rbt[rbt["task"] == task].groupby("year")["n_papers"].sum()
        if not sub.empty:
            ax.plot(sub.index, sub.values, marker="o", label=task)
    ax.set_xlabel("Year")
    ax.set_ylabel("Representation mentions")
    ax.set_title("Figure 3 — Representation richness by task over time")
    ax.legend()
    _save(
        plt, fig, fig_dir, 3,
        "**Figure 3.** Total learner-representation category mentions per analytical "
        "task by year.\n",
    )

    # Figure 4 — data-source x task heatmap
    heat = pd.read_csv(data_dir / "data_source_task_heatmap.csv")
    tasks = [c for c in heat.columns if c != "Data source"]
    plt, fig, ax = _new_axes((9, 8))
    matrix = heat[tasks].to_numpy()
    im = ax.imshow(matrix, aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(tasks)), tasks)
    ax.set_yticks(range(len(heat)), heat["Data source"], fontsize=7)
    fig.colorbar(im, ax=ax, label="Papers")
    ax.set_title("Figure 4 — Data sources by task")
    _save(
        plt, fig, fig_dir, 4,
        "**Figure 4.** Heatmap of distinct papers using each data source, by "
        "analytical task.\n",
    )

    # Figure 5 — conceptual framework (static diagram)
    plt, fig, ax = _new_axes((11, 4))
    stages = ["Data\nsources", "Learner\nrepresentation", "Model /\nML task",
              "Prediction /\noutput", "Actionability /\nintervention"]
    for i, label in enumerate(stages):
        ax.add_patch(plt.Rectangle((i * 2.1, 0), 1.8, 1.4, fc="#DCE6F1", ec="#4C72B0"))
        ax.text(i * 2.1 + 0.9, 0.7, label, ha="center", va="center", fontsize=9)
        if i < len(stages) - 1:
            ax.annotate("", xy=(i * 2.1 + 2.1, 0.7), xytext=(i * 2.1 + 1.8, 0.7),
                        arrowprops=dict(arrowstyle="->", color="#4C72B0"))
    ax.set_xlim(-0.2, len(stages) * 2.1)
    ax.set_ylim(-0.3, 1.7)
    ax.axis("off")
    ax.set_title("Figure 5 — Conceptual framework of the learning-analytics pipeline")
    _save(
        plt, fig, fig_dir, 5,
        "**Figure 5.** Conceptual framework linking data sources, learner "
        "representations, models, predictions, and actionable interventions.\n",
    )

    # Figure 6 — actionability funnel
    funnel = pd.read_csv(data_dir / "actionability_funnel.csv")
    plt, fig, ax = _new_axes((9, 6))
    ax.barh(funnel["Stage"][::-1], funnel["Count"][::-1], color="#55A868")
    for y, v in enumerate(funnel["Count"][::-1]):
        ax.text(v, y, f" {v}", va="center")
    ax.set_xlabel("Papers")
    ax.set_title("Figure 6 — Actionability / deployment funnel (PRED)")
    _save(
        plt, fig, fig_dir, 6,
        "**Figure 6.** Deployment funnel for predictive-modelling papers: from "
        "classified studies to deployed systems with evaluated interventions.\n",
    )

    # Figure 7 — model family by task (stacked bars, aggregated over years)
    mfam = pd.read_csv(data_dir / "model_family_by_task_year.csv")
    plt, fig, ax = _new_axes((10, 6))
    if not mfam.empty:
        pivot = (
            mfam.groupby(["task", "model_family"])["paper_count"].sum().unstack(fill_value=0)
            .reindex(_TABLE2_TASK_ORDER)
        )
        bottom = [0.0] * len(pivot)
        for family in pivot.columns:
            ax.bar(pivot.index, pivot[family], bottom=bottom, label=family)
            bottom = [b + v for b, v in zip(bottom, pivot[family])]
        ax.legend(fontsize=8, ncol=2)
    ax.set_ylabel("Paper-model mentions")
    ax.set_title("Figure 7 — Model family by task")
    fig.tight_layout()
    fig.savefig(fig_dir / "figure_7_model_family.png", dpi=150)
    plt.close(fig)
    (fig_dir / "figure_7_caption.md").write_text(
        "**Figure 7.** Distribution of model families across analytical tasks "
        "(model_family coverage 93% of PRED papers).\n",
        encoding="utf-8",
    )

    return sorted(fig_dir.glob("figure_*.png"))


__all__ = [
    "build_prisma_flow",
    "build_representation_usage_over_time",
    "build_representation_by_task_over_time",
    "build_data_source_task_heatmap",
    "build_actionability_funnel",
    "build_model_family_by_task_year",
    "compute_audit_metrics",
    "build_audit_dashboard",
    "build_all_figure_data",
    "render_all_figures",
]
