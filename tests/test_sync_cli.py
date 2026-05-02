"""Tests for the `sync` CLI subcommand (cmd_sync).

TP-019 compliance: cmd_sync calls load_dotenv() internally.  Every test that
exercises cmd_sync patches dotenv.load_dotenv so disk .env files cannot restore
env vars and cause silent live-network calls.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock


class TestSyncDryRun:
    def test_dry_run_default_output(self, tmp_path, capsys):
        """sync without --apply prints [DRY-RUN] and Sync complete."""
        from notion_zotero.cli import main

        notion_dir = tmp_path / "notion"
        zotero_dir = tmp_path / "zotero"
        baseline_dir = tmp_path / "baseline"
        notion_dir.mkdir()
        zotero_dir.mkdir()
        # baseline_dir intentionally absent — cmd_sync creates it

        with patch("dotenv.load_dotenv", return_value=None):
            main([
                "sync",
                "--notion-dir", str(notion_dir),
                "--zotero-dir", str(zotero_dir),
                "--baseline-dir", str(baseline_dir),
            ])

        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "Sync complete" in captured.out

    def test_dry_run_zero_transport_calls(self, tmp_path):
        """sync in dry-run mode must make zero HTTP calls at the transport layer."""
        from notion_zotero.cli import main

        notion_dir = tmp_path / "notion"
        zotero_dir = tmp_path / "zotero"
        baseline_dir = tmp_path / "baseline"
        notion_dir.mkdir()
        zotero_dir.mkdir()

        with patch("dotenv.load_dotenv", return_value=None), \
             patch("urllib.request.urlopen") as mock_urlopen, \
             patch("http.client.HTTPConnection.request") as mock_http, \
             patch("requests.Session.send") as mock_send:

            main([
                "sync",
                "--notion-dir", str(notion_dir),
                "--zotero-dir", str(zotero_dir),
                "--baseline-dir", str(baseline_dir),
            ])

        assert mock_urlopen.call_count == 0
        assert mock_http.call_count == 0
        assert mock_send.call_count == 0


class TestSyncApplyModeEnvVarValidation:
    def test_missing_env_vars_exits_with_code_1(self, tmp_path, monkeypatch):
        """--apply without env vars prints error to stderr and exits 1."""
        from notion_zotero.cli import main

        for var in ("NOTION_API_KEY", "ZOTERO_API_KEY", "ZOTERO_LIBRARY_ID"):
            monkeypatch.delenv(var, raising=False)

        notion_dir = tmp_path / "notion"
        zotero_dir = tmp_path / "zotero"
        baseline_dir = tmp_path / "baseline"
        notion_dir.mkdir()
        zotero_dir.mkdir()

        with patch("dotenv.load_dotenv", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                main([
                    "sync",
                    "--notion-dir", str(notion_dir),
                    "--zotero-dir", str(zotero_dir),
                    "--baseline-dir", str(baseline_dir),
                    "--apply",
                ])

        assert exc_info.value.code == 1


class TestSyncApplyModeWithEnvVars:
    def test_apply_mode_with_mocked_clients_succeeds(self, tmp_path, monkeypatch, capsys):
        """--apply with env vars and mocked writers completes without SystemExit."""
        from notion_zotero.cli import main

        monkeypatch.setenv("NOTION_API_KEY", "fake-notion-key")
        monkeypatch.setenv("ZOTERO_API_KEY", "fake-zotero-key")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "fake-lib-id")

        notion_dir = tmp_path / "notion"
        zotero_dir = tmp_path / "zotero"
        baseline_dir = tmp_path / "baseline"
        notion_dir.mkdir()
        zotero_dir.mkdir()

        mock_notion_adapter = MagicMock()
        mock_zotero_adapter = MagicMock()

        with patch("dotenv.load_dotenv", return_value=None), \
             patch("notion_zotero.connectors.notion.client.NotionClientAdapter",
                   return_value=mock_notion_adapter), \
             patch("notion_zotero.connectors.zotero.client.ZoteroClientAdapter",
                   return_value=mock_zotero_adapter), \
             patch("notion_zotero.writers.notion_writer.NotionWriter.write_reference",
                   return_value=[]), \
             patch("notion_zotero.writers.zotero_writer.ZoteroWriter.write_reference",
                   return_value=[]):

            main([
                "sync",
                "--notion-dir", str(notion_dir),
                "--zotero-dir", str(zotero_dir),
                "--baseline-dir", str(baseline_dir),
                "--apply",
            ])

        captured = capsys.readouterr()
        assert "Sync complete" in captured.out


class TestPlanSync:
    def test_plan_sync_writes_read_only_plan(self, tmp_path, capsys):
        from notion_zotero.cli import main

        notion_dir = tmp_path / "notion"
        zotero_dir = tmp_path / "zotero"
        out = tmp_path / "plans" / "sync_plan.json"
        notion_dir.mkdir()
        zotero_dir.mkdir()

        notion_bundle = {
            "bundle_id": "N1",
            "references": [
                {
                    "id": "N1",
                    "title": "Old title",
                    "authors": ["A. Researcher"],
                    "year": 2020,
                    "zotero_key": "Z1",
                }
            ],
        }
        zotero_bundle = {
            "bundle_id": "Z1",
            "references": [
                {
                    "id": "Z1",
                    "title": "New title",
                    "authors": ["A. Researcher"],
                    "year": 2020,
                    "zotero_key": "Z1",
                }
            ],
        }
        (notion_dir / "N1.canonical.json").write_text(json.dumps(notion_bundle), encoding="utf-8")
        (zotero_dir / "Z1.canonical.json").write_text(json.dumps(zotero_bundle), encoding="utf-8")

        main([
            "plan-sync",
            "--notion-dir",
            str(notion_dir),
            "--zotero-dir",
            str(zotero_dir),
            "--out",
            str(out),
        ])

        captured = capsys.readouterr()
        plan = json.loads(out.read_text(encoding="utf-8"))
        assert "Sync plan written" in captured.out
        assert "1 matched" in captured.out
        assert plan["summary"]["operations"] == 1
        assert plan["operations"][0]["operation"] == "update_notion_reference_field"

    def test_apply_plan_dry_run_prints_operations(self, tmp_path, capsys):
        from notion_zotero.cli import main

        plan = {
            "version": 1,
            "operations": [
                {
                    "operation": "update_notion_reference_field",
                    "target": "notion",
                    "source": "zotero",
                    "field": "title",
                    "old_value": "Old",
                    "new_value": "New",
                    "notion_reference_id": "page-1",
                    "reason": "zotero_owned_field",
                }
            ],
        }
        plan_path = tmp_path / "sync_plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        main(["apply-plan", "--plan", str(plan_path)])

        captured = capsys.readouterr()
        assert "[DRY-RUN] Planned 1 executable operation" in captured.out
        assert "notion.update [page-1] title" in captured.out
