from pathlib import Path
import pytest

pytestmark = pytest.mark.integration

from notion_zotero.services.reading_list_importer import parse_fixture


def test_importer_produces_deterministic_ids_and_task_mapping():
    path = Path(__file__).parent.parent / "fixtures" / "sample_page.json"
    pid1, out1 = parse_fixture(path)
    pid2, out2 = parse_fixture(path)

    assert pid1 == pid2 == "page-001"

    # deterministic ids: extraction ids should match across runs
    ex1 = {e["id"] for e in out1["task_extractions"]}
    ex2 = {e["id"] for e in out2["task_extractions"]}
    assert ex1 == ex2

    # annotations created for paragraphs
    assert len(out1.get("annotations", [])) >= 1

    # status mapping should produce canonical token for 'Read' -> 'done'
    states = [w.get("state") for w in out1.get("workflow_states", [])]
    assert "done" in states

    # Domain-pack mapping: heading containing 'prediction' should map to a prediction template
    templates = [e.get("template_id") or e.get("schema_name") for e in out1.get("task_extractions", [])]
    assert any(t == "prediction_modeling" for t in templates)
