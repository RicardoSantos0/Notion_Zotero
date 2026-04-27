"""Integration smoke for the reading list importer."""
from __future__ import annotations

from pathlib import Path
from notion_zotero.services.reading_list_importer import parse_fixture
import json
import pytest

pytestmark = pytest.mark.integration



def test_models_importable(tmp_path):
    # smoke test: create a simple canonical file and ensure it can be written
    sample = {
        "references": [{"id": "page_1", "title": "Sample"}],
        "tasks": [],
        "reference_tasks": [],
        "task_extractions": [],
        "annotations": [],
        "workflow_states": [],
    }
    p = tmp_path / "test_sample.canonical.json"
    p.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    assert p.exists()
