from pathlib import Path


def _fixtures_dir() -> Path:
    # Locate the repository root relative to this test file
    here = Path(__file__).resolve()
    repo = here.parent
    project = repo.parent
    fixtures = project / "fixtures" / "reading_list"
    return fixtures


def test_parse_fixture_is_deterministic_and_has_provenance():
    # Ensure the Notion_Zotero project root is on sys.path before importing
    import sys
    fixtures = _fixtures_dir()
    project_root = fixtures.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    import importlib
    import types
    importlib.invalidate_caches()
    # Make a package placeholder for `src` pointing at the local src/ dir so
    # relative imports inside the module resolve correctly and do not collide
    # with other workspace packages named `src`.
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(project_root / "src")]
    import sys
    # Force-local `src` package override for the duration of this test run.
    sys.modules["src"] = src_pkg
    rli = importlib.import_module("src.services.reading_list_importer")
    files = sorted(fixtures.glob("*.json"))
    assert files, "No reading_list fixtures found for test"

    first = files[0]
    page_id1, canon1 = rli.parse_fixture(first)
    page_id2, canon2 = rli.parse_fixture(first)
    assert page_id1 == page_id2
    # canonical outputs must be stable across runs
    assert canon1 == canon2

    # Every extraction must include provenance information
    for e in canon1.get("task_extractions", []):
        prov = e.get("provenance")
        assert prov is not None
        assert prov.get("source") == "reading_list" or prov.get("page_id") is not None

    # IDs should use deterministic prefixes
    for ex in canon1.get("task_extractions", []):
        assert ex.get("id", "").startswith("ex_")
    for an in canon1.get("annotations", []):
        assert an.get("id", "").startswith("an_")
