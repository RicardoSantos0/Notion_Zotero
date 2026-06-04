"""Markdown review reports for sync plans."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from notion_zotero.core.sync_plan_models import dump_sync_plan, validate_sync_plan


def _display(value: Any, max_chars: int = 120) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        text = "; ".join(_display(item, max_chars=max_chars) for item in value if item is not None)
    else:
        text = str(value)
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    text = text.replace("|", "\\|")
    if len(text) > max_chars:
        return text[: max_chars - 3].rstrip() + "..."
    return text


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["_None._"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_display(cell) for cell in row) + " |")
    return lines


def _summary_rows(summary: Mapping[str, Any]) -> list[list[Any]]:
    keys = (
        "notion_records",
        "zotero_records",
        "matched",
        "operations",
        "only_zotero",
        "only_notion",
        "ambiguous",
        "review_actions",
    )
    return [[key.replace("_", " "), summary.get(key, 0)] for key in keys]


def render_sync_plan_markdown(plan: Mapping[str, Any], max_rows: int = 25) -> str:
    """Render a sync plan as a human-reviewable Markdown report."""
    summary = plan.get("summary") or {}
    inputs = plan.get("inputs") or {}
    lines: list[str] = [
        "# Sync Plan Review",
        "",
        f"- Plan version: {_display(plan.get('version'))}",
        f"- Generated at: {_display(plan.get('generated_at'))}",
        f"- Notion input: {_display(inputs.get('notion_dir'), max_chars=180)}",
        f"- Zotero input: {_display(inputs.get('zotero_dir'), max_chars=180)}",
        "",
        "## Summary",
        "",
        *_markdown_table(["Metric", "Count"], _summary_rows(summary)),
        "",
        "## Executable Operations",
        "",
    ]

    operations = list(plan.get("operations") or [])
    operation_rows = [
        [
            op.get("operation_id"),
            op.get("field"),
            op.get("notion_reference_id"),
            op.get("old_value"),
            op.get("new_value"),
        ]
        for op in operations[:max_rows]
    ]
    lines.extend(_markdown_table(["Operation ID", "Field", "Notion page", "Old", "New"], operation_rows))
    if len(operations) > max_rows:
        lines.append(f"_Showing {max_rows} of {len(operations)} operations._")

    lines.extend(["", "## Matches", ""])
    matches = list(plan.get("matches") or [])
    match_rows = [
        [
            match.get("match_id"),
            (match.get("match_key") or {}).get("type"),
            match.get("match_confidence", ""),
            (match.get("notion") or {}).get("title"),
            (match.get("zotero") or {}).get("title"),
            len(match.get("bibliographic_diffs") or []),
        ]
        for match in matches[:max_rows]
    ]
    lines.extend(_markdown_table(["Match ID", "Key", "Confidence", "Notion title", "Zotero title", "Diffs"], match_rows))
    if len(matches) > max_rows:
        lines.append(f"_Showing {max_rows} of {len(matches)} matches._")

    lines.extend(["", "## Ambiguous Matches", ""])
    ambiguous = list(plan.get("ambiguous") or [])
    ambiguous_rows = []
    for item in ambiguous[:max_rows]:
        candidates = item.get("candidates") or []
        ambiguous_rows.append(
            [
                item.get("reason"),
                (item.get("zotero") or {}).get("title"),
                len(candidates),
                "; ".join(
                    _display((candidate.get("notion") or {}).get("title"), max_chars=60)
                    for candidate in candidates[:3]
                ),
            ]
        )
    lines.extend(_markdown_table(["Reason", "Zotero title", "Candidates", "Candidate titles"], ambiguous_rows))
    if len(ambiguous) > max_rows:
        lines.append(f"_Showing {max_rows} of {len(ambiguous)} ambiguous entries._")

    lines.extend(["", "## Zotero-Only Review Actions", ""])
    review_actions = list(plan.get("review_actions") or [])
    review_rows = [
        [
            action.get("operation"),
            action.get("status"),
            action.get("zotero_key"),
            action.get("title"),
            action.get("reason"),
        ]
        for action in review_actions[:max_rows]
    ]
    lines.extend(_markdown_table(["Operation", "Status", "Zotero key", "Title", "Reason"], review_rows))
    if len(review_actions) > max_rows:
        lines.append(f"_Showing {max_rows} of {len(review_actions)} review actions._")

    lines.extend(["", "## Only In Notion", ""])
    only_notion = list(plan.get("only_notion") or [])
    only_notion_rows = [
        [record.get("reference_id"), record.get("title"), record.get("year"), record.get("doi")]
        for record in only_notion[:max_rows]
    ]
    lines.extend(_markdown_table(["Reference ID", "Title", "Year", "DOI"], only_notion_rows))
    if len(only_notion) > max_rows:
        lines.append(f"_Showing {max_rows} of {len(only_notion)} Notion-only records._")

    return "\n".join(lines).rstrip() + "\n"


def write_sync_plan_report(
    plan: Mapping[str, Any],
    output_path: str | Path,
    max_rows: int = 25,
) -> Path:
    """Write a Markdown review report for *plan* and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_sync_plan_markdown(plan, max_rows=max_rows), encoding="utf-8")
    return path


def write_sync_plan_report_from_file(
    plan_path: str | Path,
    output_path: str | Path,
    max_rows: int = 25,
) -> Path:
    plan = validate_sync_plan(json.loads(Path(plan_path).read_text(encoding="utf-8")))
    return write_sync_plan_report(dump_sync_plan(plan), output_path, max_rows=max_rows)


__all__ = [
    "render_sync_plan_markdown",
    "write_sync_plan_report",
    "write_sync_plan_report_from_file",
]
