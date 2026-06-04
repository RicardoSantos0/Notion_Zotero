from __future__ import annotations

import json

import pytest


def test_load_project_config_reads_json(tmp_path):
    from notion_zotero.core.config import config_get, load_project_config

    config_path = tmp_path / "notion_zotero.config.json"
    config_path.write_text(
        json.dumps({"paths": {"sync_plan": "custom/sync_plan.json"}}),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config_get(config, "paths.sync_plan") == "custom/sync_plan.json"
    assert config_get(config, "missing.value", "fallback") == "fallback"


def test_load_project_config_rejects_missing_explicit_file(tmp_path):
    from notion_zotero.core.config import ConfigError, load_project_config

    with pytest.raises(ConfigError, match="Config file not found"):
        load_project_config(tmp_path / "missing.json")


def test_cli_config_supplies_plan_sync_defaults(tmp_path, capsys):
    from notion_zotero.cli import main

    notion_dir = tmp_path / "notion"
    zotero_dir = tmp_path / "zotero"
    out = tmp_path / "plans" / "sync_plan.json"
    notion_dir.mkdir()
    zotero_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "paths": {
                    "notion_review_dir": str(notion_dir),
                    "zotero_dir": str(zotero_dir),
                    "sync_plan": str(out),
                }
            }
        ),
        encoding="utf-8",
    )

    rc = main(["--config", str(config_path), "plan-sync"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Sync plan written" in captured.out
    assert out.exists()


def test_cli_config_error_returns_one(tmp_path, capsys):
    from notion_zotero.cli import main

    rc = main(["--config", str(tmp_path / "missing.json"), "plan-sync"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Config file not found" in captured.err
