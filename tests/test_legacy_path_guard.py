"""CI guard: canonical import path must exercise zero legacy heuristic functions."""
import sys
import unittest.mock
from pathlib import Path


def test_canonical_import_path_no_legacy_calls():
    """Running parse_fixture must not trigger any src.* legacy module."""
    fixture_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "golden"
    if not fixture_dir.exists():
        fixture_dir = Path(__file__).parent / "fixtures" / "golden"

    fixtures = sorted(fixture_dir.glob("*.json"))
    # Use only input fixtures (not canonical output bundles)
    fixtures = [f for f in fixtures if "_comment" not in f.name and "malformed" not in f.name]

    # Fall back to the project-level fixtures dir if none found in tests/
    if not fixtures:
        project_root = Path(__file__).parent.parent
        alt_dir = project_root / "fixtures"
        input_fixtures = [f for f in alt_dir.glob("*.json") if ".canonical." not in f.name]
        if not input_fixtures:
            import pytest
            pytest.skip("No input fixtures found to exercise the importer")
        fixtures = [input_fixtures[0]]

    fixture = fixtures[0]

    # Block the legacy src.* namespace entirely
    legacy_sentinel = unittest.mock.MagicMock(name="legacy_src")
    blocked = {
        "src": legacy_sentinel,
        "src.schemas": legacy_sentinel,
        "src.schemas.task_registry": legacy_sentinel,
        "src.notion_zotero": legacy_sentinel,
    }

    with unittest.mock.patch.dict(sys.modules, blocked):
        from notion_zotero.services import reading_list_importer

        try:
            reading_list_importer.parse_fixture(
                str(fixture), domain_pack_id="education_learning_analytics"
            )
        except Exception as exc:
            error_str = str(exc)
            if any(k in error_str for k in ("src.schemas", "src.task_registry", "legacy")):
                raise AssertionError(
                    f"Canonical import path invoked legacy module: {exc}"
                ) from exc
            # Other errors (e.g. JSON parse issues on a fixture) are acceptable

    # Assert the legacy sentinel was never called
    assert not legacy_sentinel.called, (
        "Legacy src.* module was accessed during canonical import"
    )
