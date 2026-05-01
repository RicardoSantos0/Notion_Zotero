"""Tests for the `diff` CLI subcommand (cmd_diff / diff_dirs)."""
from __future__ import annotations

import json
import pytest


_SAMPLE_BUNDLE = {
    "bundle_id": "test-bundle",
    "references": [{"id": "ref-1", "title": "A paper"}],
    "tasks": [],
    "reference_tasks": [],
    "task_extractions": [],
    "workflow_states": [],
    "annotations": [],
}


def _write_bundle(directory, filename, bundle):
    path = directory / filename
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


class TestDiffCLINormalOperation:
    def test_normal_diff_output_contains_bundles_compared(self, tmp_path, capsys):
        """diff with one matching file prints summary and total line."""
        from notion_zotero.cli import main

        base_dir = tmp_path / "base"
        upd_dir = tmp_path / "upd"
        base_dir.mkdir()
        upd_dir.mkdir()

        _write_bundle(base_dir, "test-bundle.canonical.json", _SAMPLE_BUNDLE)
        _write_bundle(upd_dir, "test-bundle.canonical.json", _SAMPLE_BUNDLE)

        main(["diff", "--baseline", str(base_dir), "--updated", str(upd_dir)])

        captured = capsys.readouterr()
        assert "bundle(s) compared" in captured.out

    def test_empty_dirs_print_zero_bundles(self, tmp_path, capsys):
        """diff on two empty directories prints Total: 0."""
        from notion_zotero.cli import main

        base_dir = tmp_path / "base"
        upd_dir = tmp_path / "upd"
        base_dir.mkdir()
        upd_dir.mkdir()

        main(["diff", "--baseline", str(base_dir), "--updated", str(upd_dir)])

        captured = capsys.readouterr()
        assert "Total: 0 bundle(s) compared." in captured.out

    def test_diff_with_changes_shows_diffs_in_summary(self, tmp_path, capsys):
        """When baseline and updated differ, summary mentions the change count."""
        from notion_zotero.cli import main

        base_dir = tmp_path / "base"
        upd_dir = tmp_path / "upd"
        base_dir.mkdir()
        upd_dir.mkdir()

        mutated = dict(_SAMPLE_BUNDLE)
        mutated["references"] = [{"id": "ref-1", "title": "Changed title"}]

        _write_bundle(base_dir, "test-bundle.canonical.json", _SAMPLE_BUNDLE)
        _write_bundle(upd_dir, "test-bundle.canonical.json", mutated)

        main(["diff", "--baseline", str(base_dir), "--updated", str(upd_dir)])

        captured = capsys.readouterr()
        # Summary line should mention diffs, not "No differences"
        assert "diff(s)" in captured.out or "changed" in captured.out


class TestDiffCLIArgumentErrors:
    def test_missing_baseline_arg_exits(self):
        """--baseline is required; omitting it causes SystemExit."""
        from notion_zotero.cli import main

        with pytest.raises(SystemExit):
            main(["diff", "--updated", "/some/path"])

    def test_missing_updated_arg_exits(self):
        """--updated is required; omitting it causes SystemExit."""
        from notion_zotero.cli import main

        with pytest.raises(SystemExit):
            main(["diff", "--baseline", "/some/path"])
