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

    def test_apply_plan_invalid_plan_exits_cleanly(self, tmp_path, capsys):
        from notion_zotero.cli import main

        plan_path = tmp_path / "bad_sync_plan.json"
        plan_path.write_text(
            json.dumps({"version": 999, "operations": []}),
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc_info:
            main(["apply-plan", "--plan", str(plan_path)])

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "Error: invalid sync plan" in captured.err

    def test_apply_plan_apply_uses_live_notion_schema(self, tmp_path, monkeypatch, capsys):
        from notion_zotero.cli import main

        monkeypatch.setenv("NOTION_API_KEY", "fake-notion-key")
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

        plan = {
            "version": 1,
            "operations": [
                {
                    "operation": "update_notion_reference_field",
                    "operation_id": "op-1",
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
        log_dir = tmp_path / "write_logs"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        mock_reader = MagicMock()
        mock_reader.get_database_schema.return_value = {"Paper Title": "title"}
        mock_adapter = MagicMock()

        with patch("dotenv.load_dotenv", return_value=None), \
             patch("notion_zotero.connectors.notion.reader.NotionReader", return_value=mock_reader), \
             patch("notion_zotero.connectors.notion.client.NotionClientAdapter", return_value=mock_adapter):
            main([
                "apply-plan",
                "--plan",
                str(plan_path),
                "--apply",
                "--notion-database-id",
                "db-1",
                "--write-log-dir",
                str(log_dir),
            ])

        captured = capsys.readouterr()
        assert "[APPLY MODE] Applied 1 operation" in captured.out
        mock_reader.get_database_schema.assert_called_once_with("db-1")
        mock_adapter.pages.update.assert_called_once_with(
            "page-1",
            properties={"Paper Title": {"title": [{"text": {"content": "New"}}]}},
        )

    def test_apply_plan_apply_creates_approved_review_action(self, tmp_path, monkeypatch, capsys):
        from notion_zotero.cli import main

        monkeypatch.setenv("NOTION_API_KEY", "fake-notion-key")

        plan = {
            "version": 1,
            "operations": [],
            "review_actions": [
                {
                    "operation": "create_notion_page_from_zotero_record",
                    "operation_id": "create-Z1",
                    "target": "notion",
                    "source": "zotero",
                    "status": "approved",
                    "zotero_reference_id": "zotero-1",
                    "zotero_key": "Z1",
                    "title": "Brand New Paper",
                    "reference": {
                        "title": "Brand New Paper",
                        "year": 2026,
                        "zotero_key": "Z1",
                    },
                }
            ],
        }
        plan_path = tmp_path / "sync_plan.json"
        log_dir = tmp_path / "write_logs"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        mock_reader = MagicMock()
        mock_reader.get_database_schema.return_value = {
            "Paper Title": "title",
            "Publication Year": "number",
            "Zotero Key": "rich_text",
        }
        mock_reader.get_database_pages.return_value = []
        mock_adapter = MagicMock()
        mock_adapter.pages.create.return_value = {"id": "new-page-1"}

        with patch("dotenv.load_dotenv", return_value=None), \
             patch("notion_zotero.connectors.notion.reader.NotionReader", return_value=mock_reader), \
             patch("notion_zotero.connectors.notion.client.NotionClientAdapter", return_value=mock_adapter):
            main([
                "apply-plan",
                "--plan",
                str(plan_path),
                "--apply",
                "--include-reviewed-creates",
                "--notion-database-id",
                "db-1",
                "--write-log-dir",
                str(log_dir),
            ])

        captured = capsys.readouterr()
        assert "[APPLY MODE] Applied 1 operation" in captured.out
        mock_reader.get_database_pages.assert_called_once_with("db-1")
        mock_adapter.pages.create.assert_called_once()
        assert mock_adapter.pages.create.call_args.kwargs["parent"] == {"database_id": "db-1"}
        assert mock_adapter.pages.create.call_args.kwargs["properties"]["Paper Title"] == {
            "title": [{"text": {"content": "Brand New Paper"}}]
        }

    def test_review_plan_writes_markdown_report(self, tmp_path, capsys):
        from notion_zotero.cli import main

        plan = {
            "version": 1,
            "generated_at": "2026-06-02T00:00:00Z",
            "summary": {
                "notion_records": 1,
                "zotero_records": 1,
                "matched": 0,
                "operations": 0,
                "only_zotero": 1,
                "only_notion": 0,
                "ambiguous": 0,
                "review_actions": 1,
            },
            "review_actions": [
                {
                    "operation": "create_notion_page_from_zotero_record",
                    "status": "needs_review",
                    "zotero_key": "Z1",
                    "title": "Missing Notion Paper",
                    "reason": "zotero_record_missing_from_notion",
                }
            ],
        }
        plan_path = tmp_path / "sync_plan.json"
        report_path = tmp_path / "review.md"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        main(["review-plan", "--plan", str(plan_path), "--out", str(report_path)])

        captured = capsys.readouterr()
        assert "Sync plan review written" in captured.out
        assert "Missing Notion Paper" in report_path.read_text(encoding="utf-8")

    def test_rollback_plan_writes_json_from_write_logs(self, tmp_path, capsys):
        from notion_zotero.cli import main

        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        out = tmp_path / "plans" / "rollback_plan.json"
        entry = {
            "operation_id": "op-1",
            "session_id": "sess-1",
            "timestamp": "2026-06-02T12:00:00Z",
            "entity_type": "references",
            "entity_id": "notion-page-1",
            "field": "title",
            "old_value": "Old",
            "new_value": "New",
            "actor": "sync_plan_applier",
            "status": "applied",
            "error_message": None,
            "rollback_ref": None,
        }
        (log_dir / "write_log_20260602T120000Z_sess-1.ndjson").write_text(
            json.dumps(entry) + "\n",
            encoding="utf-8",
        )

        main([
            "rollback-plan",
            "--write-log-dir",
            str(log_dir),
            "--out",
            str(out),
        ])

        captured = capsys.readouterr()
        plan = json.loads(out.read_text(encoding="utf-8"))
        assert "Rollback plan written" in captured.out
        assert plan["summary"]["rollback_operations"] == 1
        assert plan["operations"][0]["new_value"] == "Old"

    def test_apply_rollback_plan_dry_run_prints_operations(self, tmp_path, capsys):
        from notion_zotero.cli import main

        plan = {
            "version": 1,
            "operations": [
                {
                    "operation": "rollback_notion_reference_field",
                    "operation_id": "rollback-op-1",
                    "rollback_ref": "op-1",
                    "target": "notion",
                    "source": "write_log",
                    "field": "title",
                    "old_value": "New",
                    "new_value": "Old",
                    "expected_current_value": "New",
                    "notion_reference_id": "page-1",
                }
            ],
        }
        plan_path = tmp_path / "rollback_plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        main(["apply-rollback-plan", "--plan", str(plan_path)])

        captured = capsys.readouterr()
        assert "[DRY-RUN] Planned 1 rollback operation" in captured.out
        assert "notion.rollback [page-1] title" in captured.out

    def test_apply_rollback_plan_apply_checks_current_values(self, tmp_path, monkeypatch, capsys):
        from notion_zotero.cli import main

        monkeypatch.setenv("NOTION_API_KEY", "fake-notion-key")
        plan = {
            "version": 1,
            "operations": [
                {
                    "operation": "rollback_notion_reference_field",
                    "operation_id": "rollback-op-1",
                    "rollback_ref": "op-1",
                    "target": "notion",
                    "source": "write_log",
                    "field": "title",
                    "old_value": "New",
                    "new_value": "Old",
                    "expected_current_value": "New",
                    "notion_reference_id": "page-1",
                }
            ],
        }
        plan_path = tmp_path / "rollback_plan.json"
        log_dir = tmp_path / "write_logs"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        mock_reader = MagicMock()
        mock_reader.get_database_schema.return_value = {"Paper Title": "title"}
        mock_reader.get_page.return_value = {"id": "page-1", "properties": {}}

        class Ref:
            title = "New"

        mock_reader.to_reference.return_value = Ref()
        mock_adapter = MagicMock()

        with patch("dotenv.load_dotenv", return_value=None), \
             patch("notion_zotero.connectors.notion.reader.NotionReader", return_value=mock_reader), \
             patch("notion_zotero.connectors.notion.client.NotionClientAdapter", return_value=mock_adapter):
            main([
                "apply-rollback-plan",
                "--plan",
                str(plan_path),
                "--apply",
                "--notion-database-id",
                "db-1",
                "--write-log-dir",
                str(log_dir),
            ])

        captured = capsys.readouterr()
        assert "[APPLY MODE] Applied 1 rollback operation" in captured.out
        mock_reader.get_page.assert_called_once_with("page-1")
        mock_adapter.pages.update.assert_called_once_with(
            "page-1",
            properties={"Paper Title": {"title": [{"text": {"content": "Old"}}]}},
        )


class TestStatus:
    def test_status_matches_by_title_when_notion_has_no_zotero_key(
        self,
        monkeypatch,
        capsys,
    ):
        from notion_zotero.cli import main

        class Ref:
            def __init__(self, **data):
                self.data = data

            def model_dump(self):
                return dict(self.data)

        mock_zotero = MagicMock()
        mock_zotero.get_items.return_value = [{"key": "Z1"}]
        mock_zotero.to_reference.return_value = Ref(
            id="Z1",
            title="Shared Paper",
            authors=["Full Author"],
            zotero_key="Z1",
        )
        mock_notion = MagicMock()
        mock_notion.get_database_pages.return_value = [{"id": "N1"}]
        mock_notion.to_reference.return_value = Ref(
            id="N1",
            title="Shared Paper",
            authors=["Author et al."],
            zotero_key=None,
        )
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-1")

        with patch("dotenv.load_dotenv", return_value=None), \
             patch("notion_zotero.connectors.zotero.reader.ZoteroReader", return_value=mock_zotero), \
             patch("notion_zotero.connectors.notion.reader.NotionReader", return_value=mock_notion):
            main(["status"])

        captured = capsys.readouterr()
        assert "Matched (in both): 1" in captured.out
        assert "Only in Zotero:    0" in captured.out
        assert "Only in Notion:    0" in captured.out
