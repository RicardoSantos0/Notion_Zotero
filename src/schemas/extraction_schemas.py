"""Canonical extraction schemas (Pydantic models).

These models capture the canonical shapes that the importer will produce. They
include provenance and helper constructors.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: str
    source_id: Optional[str] = None
    block_index: Optional[int] = None
    # Make extraction timestamp optional to allow deterministic canonical
    # outputs; set explicitly when desired.
    extraction_timestamp: Optional[datetime] = None
    tool_version: Optional[str] = None


class TaskExtraction(BaseModel):
    id: str
    reference_task_id: Optional[str]
    schema_name: str
    extracted: Any
    provenance: Provenance
    revision_status: Optional[str] = None


class Annotation(BaseModel):
    id: str
    reference_id: str
    text: str
    provenance: Provenance


class ReferenceTask(BaseModel):
    id: str
    reference_id: str
    task_id: str
    provenance: Provenance


def provenance_from_fixture(page_id: str, block_index: int | None = None) -> Provenance:
    # Keep provenance stable/deterministic by not including a generated
    # timestamp. Timestamp may be added during audit runs if needed.
    return Provenance(source="reading_list", source_id=page_id, block_index=block_index)


def build_extraction(id: str, reference_task_id: str | None, schema_name: str, extracted: Any, page_id: str, block_index: int | None) -> TaskExtraction:
    return TaskExtraction(
        id=id,
        reference_task_id=reference_task_id,
        schema_name=schema_name,
        extracted=extracted,
        provenance=provenance_from_fixture(page_id, block_index),
    )
