from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class Reference(BaseModel):
    id: str
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    zotero_key: Optional[str] = None
    abstract: Optional[str] = None
    item_type: Optional[str] = None
    tags: List[str] = []


class Task(BaseModel):
    id: str
    name: str
    aliases: List[str] = []


class ReferenceTask(BaseModel):
    id: str
    reference_id: str
    task_id: str
    inclusion_decision_for_task: Optional[str] = None
    relevance_notes: Optional[str] = None
    created_from_source: Optional[Dict] = None
    provenance: Optional[Dict] = None


class TaskExtraction(BaseModel):
    id: str
    reference_task_id: Optional[str]
    schema_name: Optional[str]
    extracted: Any
    provenance: Optional[Dict] = None
    revision_status: Optional[str] = None


class WorkflowState(BaseModel):
    id: str
    reference_id: str
    state: str


class Annotation(BaseModel):
    id: str
    reference_id: str
    text: str
    provenance: Optional[Dict] = None
