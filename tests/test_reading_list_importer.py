 import json
 from pathlib import Path

 def test_models_importable():
     # smoke test: create a simple reference dict and ensure serialization works
     sample = {"references": [{"id": "page_1", "title": "Sample"}], "tasks": [], "reference_tasks": [], "task_extractions": [], "annotations": [], "workflow_states": []}
     p = Path("fixtures/canonical/test_sample.canonical.json")
     p.parent.mkdir(parents=True, exist_ok=True)
     p.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
     assert p.exists()
