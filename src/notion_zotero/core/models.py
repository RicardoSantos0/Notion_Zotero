"""Canonical core models for `notion_zotero`.

Implemented as Pydantic v2 BaseModels.

Design decisions:
- Per-model ConfigDict: Task and WorkflowState use strict=True because they
  have no Any-typed or heterogeneous fields. All other models use strict=False
  because they carry fields such as `extracted: Any`, `provenance: dict`, or
  `created_from_source: Optional[dict]` that hold heterogeneous values.
  arbitrary_types_allowed=True is retained where strict=False is used.
- Provenance completeness (TP-006): Reference and TaskExtraction carry a
  @model_validator(mode='after') that raises ValueError when the provenance
  dict is non-empty but missing any of the three required keys: source_id,
  domain_pack_id, domain_pack_version. An empty dict is also rejected — callers
  must supply all three keys or omit the field only in tests via a fixture.
- model_dump() is provided natively by Pydantic v2.
- ValidationStatus defaults to UNKNOWN so every object is auditable.
- sync_metadata defaults to {} as a reserved connector dict.
"""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from notion_zotero.core.enums import ValidationStatus

_PROVENANCE_REQUIRED_KEYS = {"source_id", "domain_pack_id", "domain_pack_version"}


def _check_provenance(provenance: dict) -> dict:
    """Raise ValueError when provenance is missing required keys."""
    missing = _PROVENANCE_REQUIRED_KEYS - provenance.keys()
    if missing:
        raise ValueError(
            f"provenance must contain keys: source_id, domain_pack_id, "
            f"domain_pack_version — missing: {sorted(missing)}"
        )
    return provenance


class Reference(BaseModel):
    model_config = ConfigDict(strict=False, arbitrary_types_allowed=True)

    id: str
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    zotero_key: Optional[str] = None
    abstract: Optional[str] = None
    item_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    sync_metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_provenance_keys(self) -> "Reference":
        _check_provenance(self.provenance)
        return self


class Task(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    template_id: Optional[str] = None
    family: Optional[str] = None
    domain_pack: Optional[str] = None
    provenance: dict = Field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    sync_metadata: dict = Field(default_factory=dict)


class ReferenceTask(BaseModel):
    model_config = ConfigDict(strict=False, arbitrary_types_allowed=True)

    id: str
    reference_id: str
    task_id: str
    assignment_source: Optional[str] = None
    inclusion_decision_for_task: Optional[str] = None
    relevance_notes: Optional[str] = None
    created_from_source: Optional[dict] = None
    template_id: Optional[str] = None
    provenance: dict = Field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    sync_metadata: dict = Field(default_factory=dict)


class TaskExtraction(BaseModel):
    model_config = ConfigDict(strict=False, arbitrary_types_allowed=True)

    id: str
    reference_task_id: Optional[str]
    template_id: Optional[str]
    schema_name: Optional[str]
    raw_headers: Optional[List[str]] = None
    extracted: Any = None
    validation: Optional[dict] = None
    provenance: dict = Field(default_factory=dict)
    revision_status: Optional[str] = None
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    sync_metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_provenance_keys(self) -> "TaskExtraction":
        _check_provenance(self.provenance)
        return self


class WorkflowState(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    reference_id: str
    state: str
    source_field: Optional[str] = None
    provenance: dict = Field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    sync_metadata: dict = Field(default_factory=dict)


class Annotation(BaseModel):
    model_config = ConfigDict(strict=False, arbitrary_types_allowed=True)

    id: str
    reference_id: str
    kind: Optional[str]
    text: str
    provenance: dict = Field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    sync_metadata: dict = Field(default_factory=dict)


__all__ = [
    "Reference",
    "Task",
    "ReferenceTask",
    "TaskExtraction",
    "WorkflowState",
    "Annotation",
]
