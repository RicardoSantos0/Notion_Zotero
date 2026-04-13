import json
from pathlib import Path
import tempfile

from scripts.aggregate_canonical import aggregate_canonical


def make_canonical(page_id: str, title: str, doi: str = None, authors=None):
    return {
        "references": [
            {
                "id": page_id,
                "title": title,
                "doi": doi,
                "authors": authors or [],
            }
        ]
    }


def test_aggregate_dedup_by_doi(tmp_path: Path):
    d = tmp_path
    # two files with same DOI should dedupe into one
    a = make_canonical("p1", "Title A", doi="10.1000/xyz123", authors=["Alice"])
    b = make_canonical("p2", "Other Title", doi="10.1000/xyz123", authors=["Bob"])
    p1 = d / "p1.canonical.json"
    p2 = d / "p2.canonical.json"
    p1.write_text(json.dumps(a), encoding="utf-8")
    p2.write_text(json.dumps(b), encoding="utf-8")
    out = aggregate_canonical(d)
    assert len(out) == 1


def test_aggregate_fallback_title_authors(tmp_path: Path):
    d = tmp_path
    a = make_canonical("p1", "A Study on X", authors=["Alice Smith"])
    b = make_canonical("p2", "A study on x", authors=["Alice Smith"])
    p1 = d / "p1.canonical.json"
    p2 = d / "p2.canonical.json"
    p1.write_text(json.dumps(a), encoding="utf-8")
    p2.write_text(json.dumps(b), encoding="utf-8")
    out = aggregate_canonical(d)
    assert len(out) == 1
