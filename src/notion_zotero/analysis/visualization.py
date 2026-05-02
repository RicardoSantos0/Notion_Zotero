"""Domain-agnostic visualization helpers for analysis notebooks."""
from __future__ import annotations

import ast
import re
from typing import Any, Mapping, Sequence


STYLE_COLORS = {
    "background": "#F7F9FA",
    "panel": "#FFFFFF",
    "text": "#111827",
    "muted_text": "#5B6470",
    "grid": "#E6EBEF",
    "border": "#DDE3E8",
    "teal": "#0B8196",
    "orange": "#C96B00",
    "red": "#B91C1C",
    "green": "#16834A",
    "bluegray": "#60738A",
    "light_green": "#EAF7EF",
}

INFOGRAPHIC_PALETTE = [
    STYLE_COLORS["teal"],
    STYLE_COLORS["orange"],
    STYLE_COLORS["green"],
    STYLE_COLORS["red"],
    STYLE_COLORS["bluegray"],
    "#8A6F9E",
    "#4C9A7F",
]

DEFAULT_VALUE_PALETTE = {
    "value_1": STYLE_COLORS["teal"],
    "value_2": STYLE_COLORS["orange"],
    "value_3": STYLE_COLORS["green"],
    "value_4": STYLE_COLORS["red"],
    "value_5": STYLE_COLORS["bluegray"],
}


def set_infographic_seaborn_style(context: str = "talk") -> None:  # pragma: no cover
    """Apply the project infographic style to seaborn/matplotlib."""
    import seaborn as sns

    sns.set_theme(
        context=context,
        style="whitegrid",
        palette=INFOGRAPHIC_PALETTE,
        rc={
            "figure.facecolor": STYLE_COLORS["background"],
            "axes.facecolor": STYLE_COLORS["panel"],
            "savefig.facecolor": STYLE_COLORS["background"],
            "font.family": "sans-serif",
            "font.sans-serif": ["Inter", "Aptos", "Arial", "Helvetica", "DejaVu Sans"],
            "text.color": STYLE_COLORS["text"],
            "axes.labelcolor": STYLE_COLORS["muted_text"],
            "xtick.color": STYLE_COLORS["muted_text"],
            "ytick.color": STYLE_COLORS["muted_text"],
            "axes.titlesize": 18,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "grid.color": STYLE_COLORS["grid"],
            "grid.linewidth": 0.8,
            "axes.edgecolor": STYLE_COLORS["border"],
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "legend.frameon": False,
            "legend.fontsize": 11,
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        },
    )


def polish_infographic_axes(
    ax: Any,
    title: str | None = None,
    subtitle: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    show_y_grid: bool = True,
) -> Any:  # pragma: no cover
    """Apply final chart-level styling after creating a seaborn plot."""
    import seaborn as sns

    ax.set_axisbelow(True)
    if show_y_grid:
        ax.grid(axis="y", color=STYLE_COLORS["grid"], linewidth=0.8)
        ax.grid(axis="x", visible=False)
    else:
        ax.grid(False)

    sns.despine(ax=ax, left=True, bottom=False)

    if title:
        ax.set_title(
            title,
            loc="left",
            pad=22 if subtitle else 12,
            fontsize=18,
            fontweight="bold",
            color=STYLE_COLORS["text"],
        )
    if subtitle:
        ax.text(
            0,
            1.04,
            subtitle,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=11,
            fontstyle="italic",
            color=STYLE_COLORS["muted_text"],
        )
    if xlabel is not None:
        ax.set_xlabel(xlabel, labelpad=10)
    if ylabel is not None:
        ax.set_ylabel(ylabel, labelpad=10)

    ax.tick_params(axis="both", length=0)
    return ax


def add_bar_labels(ax: Any, fmt: str = "{:.0f}", padding: int = 3) -> Any:  # pragma: no cover
    """Add clean numeric labels above bars."""
    for container in ax.containers:
        ax.bar_label(
            container,
            fmt=fmt,
            padding=padding,
            fontsize=11,
            fontweight="bold",
            color=STYLE_COLORS["text"],
        )
    return ax


def parse_list_like_cell(value: Any) -> list[str]:
    """Parse list-like scalar cells into clean string values."""
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip().strip("'").strip('"') for item in value if str(item).strip()]
    if value is None:
        return []

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "n/a", "na", "not applicable"}:
        return []

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple, set)):
            return [
                str(item).strip().strip("'").strip('"')
                for item in parsed
                if str(item).strip()
            ]
    except Exception:
        pass

    text = text.strip("[]")
    return [
        item.strip().strip("'").strip('"')
        for item in re.split(r"\s*(?:,|;|\||\n)\s*", text)
        if item.strip()
    ]


def map_value_to_group(
    value: Any,
    group_patterns: Mapping[str, Sequence[str]],
    required_prefix: str | None = None,
) -> str | None:
    """Map a scalar/list-like value to the first group whose regex matches."""
    values = parse_list_like_cell(value)
    if not values and value is not None:
        values = [str(value).strip()]

    for item in values:
        text = str(item).strip()
        if required_prefix and not text.lower().startswith(required_prefix.lower()):
            continue
        for group, patterns in group_patterns.items():
            if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
                return group
    return None


def _resolve_entity_col(data: Any, entity_col: str | None) -> str:
    if entity_col:
        return entity_col
    if "page_id" in data.columns:
        return "page_id"
    if "id" in data.columns:
        return "id"
    raise ValueError("Provide entity_col when data has neither 'page_id' nor 'id'.")


def build_multivalue_trend(
    data: Any,
    value_col: str,
    selected_values: Sequence[str],
    year_col: str = "year",
    entity_col: str | None = None,
    group_source_cols: Sequence[str] | None = None,
    group_patterns: Mapping[str, Sequence[str]] | None = None,
    group_order: Sequence[str] | None = None,
    group_col: str = "group",
    value_output_col: str = "value",
    required_group_prefix: str | None = None,
) -> Any:  # pragma: no cover
    """Build yearly counts for any multi-value column, optionally grouped."""
    import pandas as pd

    entity_col = _resolve_entity_col(data, entity_col)
    group_source_cols = list(group_source_cols or [])
    group_order = list(group_order or [])

    base_cols = [entity_col, year_col, value_col]
    if group_source_cols:
        base_cols.extend(col for col in group_source_cols if col in data.columns)

    base = data[base_cols].copy().rename(columns={entity_col: "entity_key"})
    base[year_col] = pd.to_numeric(base[year_col], errors="coerce")
    base = base.dropna(subset=[year_col, value_col])
    base[year_col] = base[year_col].astype(int)
    base[value_output_col] = base[value_col].apply(parse_list_like_cell)
    base = base.explode(value_output_col)
    base[value_output_col] = base[value_output_col].astype(str).str.strip()
    base = base[base[value_output_col].isin(selected_values)].copy()

    if group_source_cols and group_patterns:
        base["_group_values"] = base.apply(
            lambda row: sum((parse_list_like_cell(row.get(col)) for col in group_source_cols), []),
            axis=1,
        )
        base = base.explode("_group_values")
        base[group_col] = base["_group_values"].apply(
            lambda item: map_value_to_group(
                item,
                group_patterns,
                required_prefix=required_group_prefix,
            )
        )
        valid_groups = group_order or list(group_patterns)
        base = base[base[group_col].isin(valid_groups)].copy()
        group_cols = [group_col, year_col, value_output_col]
        dedupe_cols = ["entity_key", group_col, year_col, value_output_col]
    else:
        group_cols = [year_col, value_output_col]
        dedupe_cols = ["entity_key", year_col, value_output_col]

    counts = (
        base.drop_duplicates(subset=dedupe_cols)
        .groupby(group_cols)
        .size()
        .reset_index(name="n")
    )

    if counts.empty:
        return counts

    years = range(counts[year_col].min(), counts[year_col].max() + 1)
    if group_source_cols and group_patterns:
        full_groups = group_order or list(group_patterns)
        full_index = pd.MultiIndex.from_product(
            [full_groups, years, selected_values],
            names=[group_col, year_col, value_output_col],
        )
    else:
        full_index = pd.MultiIndex.from_product(
            [years, selected_values],
            names=[year_col, value_output_col],
        )
    return counts.set_index(group_cols).reindex(full_index, fill_value=0).reset_index()


def plot_multivalue_trend(
    trend_df: Any,
    selected_values: Sequence[str],
    value_col: str = "value",
    year_col: str = "year",
    count_col: str = "n",
    palette: Mapping[str, str] | None = None,
    title: str = "Value Usage Over Time",
    legend_title: str = "Values",
) -> Any:  # pragma: no cover
    """Plot overall yearly trends for any multi-value column."""
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import seaborn as sns

    fig, ax = plt.subplots(figsize=(11, 5.8))
    sns.lineplot(
        data=trend_df,
        x=year_col,
        y=count_col,
        hue=value_col,
        hue_order=list(selected_values),
        palette=palette,
        marker="o",
        linewidth=2.8,
        markersize=7,
        ax=ax,
    )
    polish_infographic_axes(ax, title=title, xlabel="Publication year", ylabel="Number of records")
    ax.xaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))
    ax.legend(title=legend_title, loc="right", bbox_to_anchor=(1.02, 1), frameon=False)
    plt.tight_layout()
    return fig, ax


def plot_multivalue_facets(
    trend_df: Any,
    selected_values: Sequence[str],
    group_col: str = "group",
    group_order: Sequence[str] | None = None,
    group_title_map: Mapping[str, str] | None = None,
    value_col: str = "value",
    year_col: str = "year",
    count_col: str = "n",
    palette: Mapping[str, str] | None = None,
    legend_title: str = "Values",
) -> Any:  # pragma: no cover
    """Plot yearly multi-value trends faceted by any caller-provided group."""
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import seaborn as sns

    group_order = list(group_order or sorted(trend_df[group_col].dropna().unique()))
    group_title_map = dict(group_title_map or {})
    plot_df = trend_df.copy()
    plot_df[group_col] = plot_df[group_col].astype("category")
    plot_df[group_col] = plot_df[group_col].cat.set_categories(group_order, ordered=True)

    grid = sns.FacetGrid(
        data=plot_df,
        col=group_col,
        col_order=group_order,
        hue=value_col,
        hue_order=list(selected_values),
        palette=palette,
        col_wrap=2,
        height=3.8,
        aspect=1.45,
        sharex=True,
        sharey=True,
    )
    grid.map_dataframe(sns.lineplot, x=year_col, y=count_col, marker="o", linewidth=2.4, markersize=5.5)
    grid.figure.set_size_inches(13, 8.5)

    handles = []
    labels = []
    for ax in grid.axes.flat:
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            break

    for ax, group_code in zip(grid.axes.flat, group_order):
        polish_infographic_axes(
            ax,
            title=group_title_map.get(group_code, group_code),
            xlabel="Publication year",
            ylabel="Number of records",
        )
        ax.title.set_ha("center")
        ax.xaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))

    if handles:
        grid.figure.legend(
            handles,
            labels,
            title=legend_title,
            loc="lower center",
            ncol=len(selected_values),
            frameon=False,
            bbox_to_anchor=(0.5, -0.02),
        )
    grid.figure.tight_layout(rect=[0, 0.06, 1, 1])
    return grid


__all__ = [
    "STYLE_COLORS",
    "INFOGRAPHIC_PALETTE",
    "DEFAULT_VALUE_PALETTE",
    "set_infographic_seaborn_style",
    "polish_infographic_axes",
    "add_bar_labels",
    "parse_list_like_cell",
    "map_value_to_group",
    "build_multivalue_trend",
    "plot_multivalue_trend",
    "plot_multivalue_facets",
]
