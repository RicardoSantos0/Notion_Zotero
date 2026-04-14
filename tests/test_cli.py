import json
from pathlib import Path

from src import cli


def test_merge_canonical_smoke(tmp_path):
    out = tmp_path / "merged.json"
    rc = cli.main(["merge-canonical", "--input", "fixtures/canonical", "--out", str(out)])
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) > 0


def test_dedupe_canonical_smoke(tmp_path):
    in_path = Path("fixtures/canonical_merged.json")
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
