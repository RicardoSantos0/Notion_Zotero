"""Enumerations used by the canonical core models."""
from __future__ import annotations

from enum import Enum


class WorkflowStateEnum(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class AnnotationKind(str, Enum):
    NOTE = "note"
    HIGHLIGHT = "highlight"
    COMMENT = "comment"


class AssignmentDecision(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"


class ValidationStatus(str, Enum):
    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"


__all__ = ["WorkflowStateEnum", "AnnotationKind", "AssignmentDecision", "ValidationStatus"]
