"""Tests for CLI commands added in Phase 6-9: list-domain-packs, list-templates,
validate-fixtures, and --domain-pack flag on parse-fixtures."""
from __future__ import annotations

import json
from pathlib import Path

from notion_zotero import cli


def test_list_domain_packs_exits_zero(capsys):
    rc = cli.main(["list-domain-packs"])
    assert rc == 0


def test_list_domain_packs_output_contains_pack(capsys):
    cli.main(["list-domain-packs"])
    out = capsys.readouterr().out
    assert "education_learning_analytics" in out


def test_list_templates_exits_zero(capsys):
    rc = cli.main(["list-templates"])
    assert rc == 0


def test_list_templates_output_nonempty(capsys):
    cli.main(["list-templates"])
    out = capsys.readouterr().out
    assert len(out.strip()) > 0


def test_list_templates_contains_prediction(capsys):
    cli.main(["list-templates"])
    out = capsys.readouterr().out
    assert "prediction" in out.lower()


def test_validate_fixtures_exits_zero_on_valid_dir(tmp_path, capsys):
    bundle = {
        "provenance": {"domain_pack_id": "education_learning_analytics", "domain_pack_version": "1.0"},
        "references": [{"id": "p1", "title": "Test Paper"}],
        "tasks": [],
        "reference_tasks": [],
        "task_extractions": [],
        "annotations": [],
        "workflow_states": [],
    }
    (tmp_path / "p1.canonical.json").write_text(json.dumps(bundle), encoding="utf-8")
    rc = cli.main(["validate-fixtures", "--input", str(tmp_path)])
    assert rc == 0


def test_validate_fixtures_exits_one_on_malformed(tmp_path):
    import pytest
    (tmp_path / "bad.canonical.json").write_text("[1,2,3]", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        cli.main(["validate-fixtures", "--input", str(tmp_path)])
    assert exc.value.code == 1


def test_validate_fixtures_exits_one_on_missing_dir(tmp_path):
    import pytest
    with pytest.raises(SystemExit) as exc:
        cli.main(["validate-fixtures", "--input", str(tmp_path / "nonexistent")])
    assert exc.value.code == 1


def test_parse_fixtures_accepts_domain_pack_flag(tmp_path):
    fixture = {
        "page_id": "test-page-001",
        "title": "Test Paper",
        "properties": {
            "Status": {"type": "select", "select": {"name": "KT"}},
        },
        "tables": [],
        "blocks": [],
    }
    in_dir = tmp_path / "reading_list"
    in_dir.mkdir()
    (in_dir / "test-page-001.json").write_text(json.dumps(fixture), encoding="utf-8")
    out_dir = tmp_path / "canonical"
    rc = cli.main([
        "parse-fixtures",
        "--input", str(in_dir),
        "--out", str(out_dir),
        "--domain-pack", "education_learning_analytics",
    ])
    assert rc == 0
    assert out_dir.exists()


def test_parse_fixtures_domain_pack_stamps_provenance(tmp_path):
    fixture = {
        "page_id": "prov-test-001",
        "title": "Provenance Paper",
        "properties": {},
        "tables": [],
        "blocks": [],
    }
    in_dir = tmp_path / "reading_list"
    in_dir.mkdir()
    (in_dir / "prov-test-001.json").write_text(json.dumps(fixture), encoding="utf-8")
    out_dir = tmp_path / "canonical"
    cli.main([
        "parse-fixtures",
        "--input", str(in_dir),
        "--out", str(out_dir),
        "--domain-pack", "education_learning_analytics",
    ])
    canon = json.loads((out_dir / "prov-test-001.canonical.json").read_text(encoding="utf-8"))
    assert "provenance" in canon
    assert canon["provenance"]["domain_pack_id"] == "education_learning_analytics"
    assert canon["provenance"]["domain_pack_version"] == "1.0"
