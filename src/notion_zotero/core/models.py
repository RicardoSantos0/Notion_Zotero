"""Canonical core models for `notion_zotero`.

Implemented as Pydantic v2 BaseModels with strict validation.

Design decisions:
- ConfigDict(strict=False, arbitrary_types_allowed=True): strict=True was
  relaxed because `extracted` holds Any-typed data (list[dict], None, etc.)
  and `provenance` is an open dict that receives heterogeneous values from
  callers. Pydantic strict mode rejects e.g. passing `None` where `Optional`
  is expected at coercion boundaries that exist in the existing test suite.
  arbitrary_types_allowed=True is required to allow dict[str,Any] fields with
  complex nested values.
- model_dump() is provided natively by Pydantic v2 and is therefore no longer
  hand-rolled on each class.
- ValidationStatus defaults to UNKNOWN so every object is auditable.
- sync_metadata defaults to {} as a reserved connector dict.
- provenance must include source_id, domain_pack_id, domain_pack_version at
  runtime (enforced by importer, not at Pydantic field level, because callers
  supply partial provenance dicts during construction).
"""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from notion_zotero.core.enums import ValidationStatus

_cfg = ConfigDict(strict=False, arbitrary_types_allowed=True)


class Reference(BaseModel):
    model_config = _cfg

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


class Task(BaseModel):
    model_config = _cfg

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
    model_config = _cfg

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
    model_config = _cfg

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


class WorkflowState(BaseModel):
    model_config = _cfg

    id: str
    reference_id: str
    state: str
    source_field: Optional[str] = None
    provenance: dict = Field(default_factory=dict)
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    sync_metadata: dict = Field(default_factory=dict)


class Annotation(BaseModel):
    model_config = _cfg

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
