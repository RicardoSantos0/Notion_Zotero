"""Integration smoke tests for CLI merge/dedupe/citation commands."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

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


def test_zotero_citation_print(capsys, tmp_path):
    # Build a minimal canonical fixture with complete provenance so the
    # TP-006 validator (source_id / domain_pack_id / domain_pack_version) passes.
    fixture = {
        "references": [
            {
                "id": "test-cite-001",
                "title": "Test Citation Paper",
                "authors": ["Author A"],
                "year": 2023,
                "journal": "Test Journal",
                "provenance": {
                    "source_id": "test-cite-001",
                    "domain_pack_id": "test-pack",
                    "domain_pack_version": "0.0.1",
                },
            }
        ]
    }
    p = tmp_path / "cite.canonical.json"
    p.write_text(json.dumps(fixture), encoding="utf-8")
    rc = cli.main(["zotero-citation", "--file", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() != ""
