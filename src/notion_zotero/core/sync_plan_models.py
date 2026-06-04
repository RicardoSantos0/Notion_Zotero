"""Typed models for review-first sync plans."""
from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from notion_zotero.core.field_ownership import ZOTERO_OWNED

SYNC_PLAN_VERSION = 1


class SyncPlanValidationError(ValueError):
    """Raised when a sync plan is malformed or uses an unsupported version."""


class SyncPlanSummary(BaseModel):
    model_config = ConfigDict(extra="allow", strict=False)

    notion_records: int = 0
    zotero_records: int = 0
    matched: int = 0
    operations: int = 0
    only_zotero: int = 0
    only_notion: int = 0
    ambiguous: int = 0
    review_actions: int = 0


class MatchKey(BaseModel):
    model_config = ConfigDict(extra="allow", strict=False)

    type: str
    value: Any


class SyncPlanOperation(BaseModel):
    model_config = ConfigDict(extra="allow", strict=False)

    operation: Literal["update_notion_reference_field"]
    operation_id: str | None = None
    target: Literal["notion"]
    source: Literal["zotero"]
    field: str
    old_value: Any = None
    new_value: Any = None
    notion_reference_id: str
    reason: str | None = None

    @field_validator("field", "notion_reference_id")
    @classmethod
    def _non_empty_string(cls, value: str) -> str:
        if not str(value or "").strip():
            raise ValueError("must be a non-empty string")
        return str(value)

    @field_validator("operation_id")
    @classmethod
    def _operation_id_non_empty_when_present(cls, value: str | None) -> str | None:
        if value is not None and not str(value).strip():
            raise ValueError("must be a non-empty string when provided")
        return str(value) if value is not None else None

    @field_validator("field")
    @classmethod
    def _field_is_zotero_owned(cls, value: str) -> str:
        if value not in ZOTERO_OWNED:
            raise ValueError(f"field must be Zotero-owned: {value}")
        return value


class SyncPlanMatch(BaseModel):
    model_config = ConfigDict(extra="allow", strict=False)

    match_id: str
    match_key: MatchKey
    match_confidence: Literal["strong", "weak"] | None = None
    notion: dict[str, Any] = Field(default_factory=dict)
    zotero: dict[str, Any] = Field(default_factory=dict)
    bibliographic_diffs: list[dict[str, Any]] = Field(default_factory=list)


class SyncPlan(BaseModel):
    model_config = ConfigDict(extra="allow", strict=False)

    version: int
    generated_at: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    summary: SyncPlanSummary = Field(default_factory=SyncPlanSummary)
    matches: list[SyncPlanMatch] = Field(default_factory=list)
    operations: list[SyncPlanOperation] = Field(default_factory=list)
    only_zotero: list[dict[str, Any]] = Field(default_factory=list)
    only_notion: list[dict[str, Any]] = Field(default_factory=list)
    ambiguous: list[dict[str, Any]] = Field(default_factory=list)
    review_actions: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def _supported_version(cls, value: int) -> int:
        if value != SYNC_PLAN_VERSION:
            raise ValueError(f"unsupported sync plan version: {value}")
        return value

    @model_validator(mode="after")
    def _summary_matches_operations(self) -> "SyncPlan":
        if self.summary.operations and self.summary.operations != len(self.operations):
            raise ValueError(
                "summary.operations does not match the number of executable operations"
            )
        return self


def validate_sync_plan(plan: Mapping[str, Any]) -> SyncPlan:
    """Validate *plan* and return a typed SyncPlan model.

    Raises SyncPlanValidationError with a compact Pydantic error summary when
    the plan is malformed.
    """
    try:
        return SyncPlan.model_validate(plan)
    except ValidationError as exc:
        raise SyncPlanValidationError(str(exc)) from exc


def dump_sync_plan(plan: SyncPlan | Mapping[str, Any]) -> dict[str, Any]:
    """Return a plain dict for a typed or already-dict sync plan."""
    if isinstance(plan, SyncPlan):
        return plan.model_dump(mode="json")
    return dict(plan)


__all__ = [
    "SYNC_PLAN_VERSION",
    "SyncPlan",
    "SyncPlanOperation",
    "SyncPlanSummary",
    "SyncPlanValidationError",
    "dump_sync_plan",
    "validate_sync_plan",
]
