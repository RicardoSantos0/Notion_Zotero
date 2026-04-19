import json
from pathlib import Path

from notion_zotero import cli


def test_merge_canonical_smoke(tmp_path):
    out = tmp_path / "merged.json"
    rc = cli.main(["merge-canonical", "--input", "fixtures/canonical", "--out", str(out)])
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) > 0


def test_dedupe_canonical_smoke(tmp_path):
    # Create a minimal canonical merged JSON at runtime so the test is self-contained
    sample = [
        {
            "references": [{"id": "page_1", "title": "Sample A", "doi": "10.1000/1", "authors": ["Alice"]}],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [],
            "annotations": [],
            "workflow_states": [],
        },
        {
            "references": [{"id": "page_2", "title": "Sample B", "authors": ["Bob"]}],
            "tasks": [],
            "reference_tasks": [],
            "task_extractions": [],
            "annotations": [],
            "workflow_states": [],
        },
    ]
    in_path = tmp_path / "canonical_merged.json"
    in_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    out = tmp_path / "dedup.json"
    rc = cli.main(["dedupe-canonical", "--input", str(in_path), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    orig = json.loads(in_path.read_text(encoding="utf-8"))
    assert len(data) <= len(orig)


def test_zotero_citation_print(capsys):
    path = "fixtures/canonical/003e69cb-f908-470d-bab2-c26eed3c63d3.canonical.json"
    rc = cli.main(["zotero-citation", "--file", path])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() != ""
