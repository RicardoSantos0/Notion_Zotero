"""Round-trip serialisation tests for canonical core models."""
from __future__ import annotations

import json
from pathlib import Path

from notion_zotero.core.models import (
    Reference,
    Task,
    ReferenceTask,
    TaskExtraction,
    WorkflowState,
    Annotation,
)

GOLDEN = Path(__file__).parent / "fixtures" / "golden"


def test_reference_roundtrip():
    ref = Reference(id="ref-001", title="Test Title", authors=["Author A"], year=2022)
    data = ref.model_dump()
    restored = Reference(**data)
    assert restored == ref


def test_reference_with_provenance_roundtrip():
    ref = Reference(
        id="ref-002",
        title="Paper",
        provenance={"source_page_id": "p-001", "source_property": "Title"},
    )
    data = ref.model_dump()
    restored = Reference(**data)
    assert restored.provenance["source_page_id"] == "p-001"


def test_task_roundtrip():
    task = Task(id="t-001", name="Knowledge Tracing", template_id="sequence_tracing")
    data = task.model_dump()
    assert Task(**data) == task


def test_reference_task_roundtrip():
    rt = ReferenceTask(
        id="rt-001",
        reference_id="ref-001",
        task_id="t-001",
        assignment_source="status_field",
    )
    assert ReferenceTask(**rt.model_dump()) == rt


def test_task_extraction_roundtrip():
    te = TaskExtraction(
        id="te-001",
        reference_task_id="rt-001",
        template_id="prediction_modeling",
        schema_name="prediction_modeling",
        extracted=[{"Metric": "AUC", "Value": "0.86"}],
    )
    assert TaskExtraction(**te.model_dump()) == te


def test_workflow_state_roundtrip():
    ws = WorkflowState(id="ws-001", reference_id="ref-001", state="included")
    assert WorkflowState(**ws.model_dump()) == ws


def test_annotation_roundtrip():
    ann = Annotation(id="a-001", reference_id="ref-001", kind="note", text="See figure 3.")
    assert Annotation(**ann.model_dump()) == ann


def test_golden_ela_fixture_is_valid_json():
    p = GOLDEN / "education_learning_analytics_page.json"
    assert p.exists(), f"Golden fixture not found: {p}"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["object"] == "page"
    assert "properties" in data


def test_golden_generic_fixture_is_valid_json():
    p = GOLDEN / "generic_template_page.json"
    assert p.exists(), f"Golden fixture not found: {p}"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["object"] == "page"
    assert "children" in data
