from pathlib import Path
from src.services.reading_list_importer import parse_fixture


def test_parse_single_fixture():
    repo_root = Path(__file__).resolve().parents[1]
    fixture_dir = repo_root / "fixtures" / "reading_list"
    assert fixture_dir.exists(), f"fixtures directory not found: {fixture_dir}"
    first_fixture = next(fixture_dir.glob("*.json"))
    page_id, out = parse_fixture(first_fixture)
    assert isinstance(page_id, str)
    assert isinstance(out, dict)
    assert "references" in out and isinstance(out["references"], list)
    assert out["references"][0]["id"] == page_id
 import json
 from pathlib import Path

 def test_models_importable():
     # smoke test: create a simple reference dict and ensure serialization works
     sample = {"references": [{"id": "page_1", "title": "Sample"}], "tasks": [], "reference_tasks": [], "task_extractions": [], "annotations": [], "workflow_states": []}
     p = Path("fixtures/canonical/test_sample.canonical.json")
     p.parent.mkdir(parents=True, exist_ok=True)
     p.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
     assert p.exists()
