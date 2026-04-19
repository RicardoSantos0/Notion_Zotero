"""Canonical core models for `notion_zotero`.

Implemented as lightweight dataclasses to avoid introducing runtime
dependencies during the refactor. Each model exposes `model_dump()` to be
compatible with code that later expects a pydantic-like interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class Reference:
    id: str
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    zotero_key: Optional[str] = None
    abstract: Optional[str] = None
    item_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Task:
    id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    template_id: Optional[str] = None
    family: Optional[str] = None
    domain_pack: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReferenceTask:
    id: str
    reference_id: str
    task_id: str
    assignment_source: Optional[str] = None
    inclusion_decision_for_task: Optional[str] = None
    relevance_notes: Optional[str] = None
    created_from_source: Optional[Dict[str, Any]] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskExtraction:
    id: str
    reference_task_id: Optional[str]
    template_id: Optional[str]
    schema_name: Optional[str]
    raw_headers: Optional[List[str]] = None
    extracted: Any = None
    validation: Optional[Dict[str, Any]] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    revision_status: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowState:
    id: str
    reference_id: str
    state: str
    source_field: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Annotation:
    id: str
    reference_id: str
    kind: Optional[str]
    text: str
    provenance: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = [
    "Reference",
    "Task",
    "ReferenceTask",
    "TaskExtraction",
    "WorkflowState",
    "Annotation",
]
