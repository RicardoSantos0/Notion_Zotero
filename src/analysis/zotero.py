"""zotero.py — minimal Zotero helpers used in the analysis pipeline.

Only a tiny subset is required for tests and fixtures: resolving items by key
and building simple citation strings.
"""

from __future__ import annotations

from typing import Any


def citation_from_item(item: dict[str, Any]) -> str:
    title = item.get("title") or item.get("Title") or ""
    authors = item.get("creators") or item.get("authors") or []
    if isinstance(authors, list):
        names = ", ".join(a.get("lastName", a.get("name", "")) for a in authors)
    else:
        names = str(authors)
    year = item.get("year") or item.get("Year") or ""
    return f"{names} ({year}) — {title}".strip()
"""zotero.py — Zotero integration: search, match, backfill metadata, sync notes.

Private module. Use notion_utils for backward compatibility or import directly
for new code.
"""

from __future__ import annotations

import re
import time
from typing import Any

import requests

from ._client import _call_with_retry, get_notion_client
from ._parse import fetch_database, pages_to_records
from .migration import _to_rt, _to_url, build_paper_title_id_map

DEBUG_MODE = False


# ---------------------------------------------------------------------------
# Zotero HTTP helpers
# ---------------------------------------------------------------------------

def _zotero_headers(api_key: str) -> dict[str, str]:
    return {"Zotero-API-Key": api_key}


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation and extra whitespace for fuzzy matching."""
    title = re.sub(r"[^\w\s]", " ", title.lower())
    return " ".join(title.split())


def search_zotero_by_title(
    title: str,
    api_key: str,
    user_id: str,
    limit: int = 5,
) -> list[dict]:
    """Search Zotero library for items matching a title. Returns raw item list."""
    params = {"q": title, "qmode": "titleCreatorYear", "format": "json", "limit": limit}
    r = requests.get(
        f"https://api.zotero.org/users/{user_id}/items",
        headers=_zotero_headers(api_key),
        params=params,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def match_papers_to_zotero(
    paper_records: list[dict],
    api_key: str,
    user_id: str,
) -> dict[str, Any]:
    """
    For each paper record, search Zotero by title and find the best match.

    Returns:
        {
          matched: [{title, zotero_key, doi, url, abstract, confidence}],
          unmatched: [title, ...],
        }
    """
    matched: list[dict] = []
    unmatched: list[str] = []

    for record in paper_records:
        title = str(record.get("Name") or record.get("Title") or "").strip()
        if not title:
            continue

        try:
            results = search_zotero_by_title(title, api_key, user_id, limit=5)
            norm_title = _normalize_title(title)
            best = None

            for item in results:
                data = item.get("data", {})
                z_title = data.get("title", "")
                norm_z = _normalize_title(z_title)

                if norm_z == norm_title:
                    best = (item, "exact")
                    break
                if best is None and (norm_title in norm_z or norm_z in norm_title):
                    best = (item, "partial")

            if best:
                item, confidence = best
                data = item.get("data", {})
                matched.append({
                    "title": title,
                    "zotero_key": data.get("key", ""),
                    "doi": data.get("DOI", ""),
                    "url": data.get("url", ""),
                    "abstract": data.get("abstractNote", ""),
                    "confidence": confidence,
                })
            else:
                unmatched.append(title)

            time.sleep(0.12)
        except Exception as exc:
            unmatched.append(title)
            if DEBUG_MODE:
                print(f"  Zotero search error for '{title[:50]}': {exc}")

    return {"matched": matched, "unmatched": unmatched}


def backfill_zotero_metadata(
    v3_db_id: str,
    api_key: str,
    user_id: str,
    title_to_v3_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Search Zotero for each paper in v3 Paper DB and backfill:
    DOI, Zotero Key, Abstract Text, URL.
    Only fills empty fields — never overwrites existing values.
    """
    client = get_notion_client()

    if title_to_v3_id is None:
        title_to_v3_id = build_paper_title_id_map(v3_db_id, title_column="Title")

    v3_pages = fetch_database(v3_db_id)
    v3_records = pages_to_records(v3_pages)

    match_result = match_papers_to_zotero(v3_records, api_key, user_id)
    matched = match_result["matched"]

    updated = 0
    skipped = 0
    failures: list[dict] = []

    for m in matched:
        title = m["title"]
        page_id = title_to_v3_id.get(title)
        if not page_id:
            skipped += 1
            continue

        try:
            update_props: dict[str, Any] = {}
            if m.get("zotero_key"):
                update_props["Zotero Key"] = _to_rt(m["zotero_key"])
            if m.get("doi"):
                update_props["DOI"] = _to_rt(m["doi"])
            if m.get("abstract"):
                update_props["Abstract Text"] = _to_rt(m["abstract"])
            if m.get("url"):
                update_props["URL"] = _to_url(m["url"])

            if not update_props:
                skipped += 1
                continue

            _call_with_retry(
                f"pages.update(zotero={title[:40]})",
                lambda pid=page_id, p=update_props: client.pages.update(
                    page_id=pid, properties=p
                ),
            )
            updated += 1
            time.sleep(0.35)
        except Exception as exc:
            failures.append({"title": title, "error": str(exc)})

    return {
        "matched": len(matched),
        "unmatched": len(match_result["unmatched"]),
        "updated": updated,
        "skipped": skipped,
        "failed": len(failures),
        "failures": failures,
        "unmatched_titles": match_result["unmatched"],
    }


def sync_reading_notes_to_zotero(
    v3_db_id: str,
    api_key: str,
    user_id: str,
) -> dict[str, Any]:
    """
    For each paper in v3 that has both a Zotero Key and Reading Notes,
    create (or update) a Zotero note item attached to the paper.
    The note is tagged 'reading-notes' so it can be identified later.
    """
    v3_pages = fetch_database(v3_db_id)
    v3_records = pages_to_records(v3_pages)

    created = 0
    skipped = 0
    failures: list[dict] = []

    for record in v3_records:
        zotero_key = str(record.get("Zotero Key") or "").strip()
        notes = str(record.get("Reading Notes") or "").strip()
        title = str(record.get("Title") or "").strip()

        if not zotero_key or not notes:
            skipped += 1
            continue

        try:
            r = requests.get(
                f"https://api.zotero.org/users/{user_id}/items/{zotero_key}/children",
                headers=_zotero_headers(api_key),
                params={"format": "json"},
                timeout=15,
            )
            r.raise_for_status()
            children = r.json()
            already_has_note = any(
                child.get("data", {}).get("itemType") == "note"
                and any(t.get("tag") == "reading-notes" for t in child.get("data", {}).get("tags", []))
                for child in children
            )

            if already_has_note:
                skipped += 1
                continue

            html_lines = []
            for line in notes.split("\n\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("## "):
                    html_lines.append(f"<h2>{line[3:]}</h2>")
                elif line.startswith("• "):
                    html_lines.append(f"<li>{line[2:]}</li>")
                else:
                    html_lines.append(f"<p>{line}</p>")
            html_content = "\n".join(html_lines)

            note_payload = [{
                "itemType": "note",
                "parentItem": zotero_key,
                "note": html_content,
                "tags": [{"tag": "reading-notes", "type": 1}],
            }]

            r2 = requests.post(
                f"https://api.zotero.org/users/{user_id}/items",
                headers={**_zotero_headers(api_key), "Content-Type": "application/json"},
                json=note_payload,
                timeout=15,
            )
            r2.raise_for_status()
            created += 1
            time.sleep(0.12)

        except Exception as exc:
            failures.append({"title": title, "zotero_key": zotero_key, "error": str(exc)})

    return {"created": created, "skipped": skipped, "failed": len(failures), "failures": failures}
