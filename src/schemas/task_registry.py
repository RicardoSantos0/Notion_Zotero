"""A simple, rule-driven task registry.

Tasks are registered with a predicate function that determines applicability to a
fixture item (a dict produced from the reading-list fixture). Parsers produce
extraction dicts or model instances.

This is intentionally small and testable.
"""
from __future__ import annotations

from typing import Callable, List, Any

TaskPredicate = Callable[[dict[str, Any]], bool]
TaskParser = Callable[[dict[str, Any]], dict[str, Any]]


class _Registry:
    def __init__(self) -> None:
        self._entries: List[tuple[str, TaskPredicate, TaskParser]] = []

    def register(self, name: str, predicate: TaskPredicate, parser: TaskParser) -> None:
        """Register a task parser under `name`.

        predicate(item) -> bool to indicate applicability.
        parser(item) -> extraction dict
        """
        self._entries.append((name, predicate, parser))

    def get_applicable(self, item: dict[str, Any]) -> List[tuple[str, TaskParser]]:
        out: List[tuple[str, TaskParser]] = []
        for name, pred, parser in self._entries:
            try:
                if pred(item):
                    out.append((name, parser))
            except Exception:
                # Guard: predicate errors mean not applicable
                continue
        return out


# module-level registry instance
registry = _Registry()


def register_task(name: str, predicate: TaskPredicate, parser: TaskParser) -> None:
    registry.register(name, predicate, parser)


def get_applicable_tasks(item: dict[str, Any]) -> List[tuple[str, TaskParser]]:
    return registry.get_applicable(item)


# -------------------------
# Default task predicates
# -------------------------


def _get_headers(item: dict[str, Any]) -> list[str]:
    rows = item.get("rows") or []
    if not rows:
        return []
    first = rows[0]
    if isinstance(first, dict):
        return list(first.keys())
    return []


def _heading_contains(item: dict[str, Any], token: str) -> bool:
    heading = (item.get("heading") or "")
    return token.lower() in heading.lower()


def _header_has(item: dict[str, Any], substr: str) -> bool:
    for h in _get_headers(item):
        if substr.lower() in str(h).lower():
            return True
    return False


def _pred_summary(item: dict[str, Any]) -> bool:
    if _heading_contains(item, "summary") or _heading_contains(item, "summary table"):
        return True
    # header contains comments/notes indicates a summary-like table
    if _header_has(item, "comment") or _header_has(item, "note"):
        return True
    return False


def _parser_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "summary_table", "extracted": item.get("rows", [])}


def _pred_methods(item: dict[str, Any]) -> bool:
    if _heading_contains(item, "method") or _heading_contains(item, "approach"):
        return True
    if _header_has(item, "method") or _header_has(item, "approach"):
        return True
    return False


def _parser_methods(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "methods_table", "extracted": item.get("rows", [])}


def _pred_dataset(item: dict[str, Any]) -> bool:
    if _heading_contains(item, "dataset") or _heading_contains(item, "data"):
        return True
    if _header_has(item, "dataset") or _header_has(item, "sample") or _header_has(item, "n"):
        return True
    return False


def _parser_dataset(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "dataset_table", "extracted": item.get("rows", [])}


# Register default lightweight parsers
register_task("Summary", _pred_summary, _parser_summary)
register_task("Methods", _pred_methods, _parser_methods)
register_task("Dataset", _pred_dataset, _parser_dataset)


# -------------------------
# Additional domain-aware predicates/parsers
# -------------------------


def _pred_findings(item: dict[str, Any]) -> bool:
    # Headings or headers mentioning results/findings/observations
    if _heading_contains(item, "result") or _heading_contains(item, "finding"):
        return True
    if _header_has(item, "result") or _header_has(item, "finding"):
        return True
    # Numeric columns often indicate measurement tables (means, p-values)
    for h in _get_headers(item):
        if any(tok in str(h).lower() for tok in ("p-value", "p value", "%", "mean", "median", "std", "sd", "f1", "accuracy", "auc")):
            return True
    return False


def _parser_findings(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "findings_table", "extracted": item.get("rows", [])}


def _pred_conclusions(item: dict[str, Any]) -> bool:
    if _heading_contains(item, "conclusion") or _heading_contains(item, "takeaway"):
        return True
    if _header_has(item, "implication") or _header_has(item, "interpretation"):
        return True
    return False


def _parser_conclusions(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "conclusions_table", "extracted": item.get("rows", [])}


def _pred_metrics(item: dict[str, Any]) -> bool:
    # Metrics tables often include named scores
    for h in _get_headers(item):
        if any(tok in str(h).lower() for tok in ("accuracy", "precision", "recall", "f1", "auc", "mse", "rmse", "mae")):
            return True
    # heading may mention metrics or evaluation
    if _heading_contains(item, "metric") or _heading_contains(item, "evaluation"):
        return True
    return False


def _parser_metrics(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "metrics_table", "extracted": item.get("rows", [])}


def _pred_population(item: dict[str, Any]) -> bool:
    # Participant/sample tables
    if _header_has(item, "participant") or _header_has(item, "participants") or _header_has(item, "sample"):
        return True
    if _header_has(item, "age") or _header_has(item, "gender") or _header_has(item, "sex"):
        return True
    return False


def _parser_population(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "population_table", "extracted": item.get("rows", [])}


def _pred_limitations(item: dict[str, Any]) -> bool:
    if _heading_contains(item, "limitation") or _heading_contains(item, "future work") or _heading_contains(item, "threat"):
        return True
    if _header_has(item, "limitation") or _header_has(item, "weakness"):
        return True
    return False


def _parser_limitations(item: dict[str, Any]) -> dict[str, Any]:
    return {"schema_name": "limitations_table", "extracted": item.get("rows", [])}


# Register additional domain-aware parsers
register_task("Findings", _pred_findings, _parser_findings)
register_task("Conclusions", _pred_conclusions, _parser_conclusions)
register_task("Metrics", _pred_metrics, _parser_metrics)
register_task("Population", _pred_population, _parser_population)
register_task("Limitations", _pred_limitations, _parser_limitations)

