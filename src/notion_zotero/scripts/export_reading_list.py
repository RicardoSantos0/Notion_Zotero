#!/usr/bin/env python3
import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv


def plain_text(rich):
    if not rich:
        return ""
    parts = []
    for r in rich:
        if isinstance(r, dict):
            if "plain_text" in r:
                parts.append(r["plain_text"])
            elif "text" in r and isinstance(r["text"], dict):
                parts.append(r["text"].get("content", ""))
        elif isinstance(r, str):
            parts.append(r)
    return "".join(parts)


def get_title(page):
    props = page.get("properties", {})
    for _, p in props.items():
        if p.get("type") == "title":
            return plain_text(p.get("title", []))
    return page.get("id")


def fetch_blocks(notion, block_id):
    out = []
    start = None
    while True:
        resp = notion.blocks.children.list(block_id=block_id, start_cursor=start, page_size=100)
        out.extend(resp.get("results", []))
        if resp.get("has_more"):
            start = resp.get("next_cursor")
        else:
            break
    return out


def serialize_block(b):
    t = b.get("type")
    text = ""
    if t in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do"):
        text = plain_text(b.get(t, {}).get("rich_text", []))
    return {"id": b.get("id"), "type": t, "text": text, "raw": b}


def extract_tables(blocks, notion):
    tables = []
    for idx, b in enumerate(blocks):
        if b.get("type") == "table":
            rows = fetch_blocks(notion, b["id"])
            parsed = []
            for r in rows:
                if r.get("type") == "table_row":
                    cells = r.get("table_row", {}).get("cells", [])
                    parsed.append([plain_text(c) for c in cells])
            heading = None
            for j in range(max(0, idx - 5), idx):
                bt = blocks[j]
                if bt.get("type", "").startswith("heading"):
                    heading = plain_text(bt.get(bt["type"], {}).get("rich_text", []))
                    break
            tables.append({"block_id": b["id"], "heading": heading, "rows": parsed, "index": idx})
    return tables


def export_page(notion, page_id, out_dir):
    page = notion.pages.retrieve(page_id=page_id)
    blocks = fetch_blocks(notion, page_id)
    fixture = {
        "page_id": page_id,
        "title": get_title(page),
        "properties": page.get("properties", {}),
        "tables": extract_tables(blocks, notion),
        "blocks": [serialize_block(b) for b in blocks],
    }
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / f"{page_id}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(fixture, fh, ensure_ascii=False, indent=2)
    print("WROTE:", path)


def export_database(notion, database_id, out_dir):
    def _query_db(notion_client, db_id, start_cursor=None, page_size=100):
        # Prefer the high-level SDK method if available
        if hasattr(notion_client, "databases") and hasattr(notion_client.databases, "query"):
            if start_cursor:
                return notion_client.databases.query(database_id=db_id, start_cursor=start_cursor, page_size=page_size)
            return notion_client.databases.query(database_id=db_id, page_size=page_size)

        # If the SDK exposes data_sources, prefer querying the active
        # platform data source (some Notion setups use data_sources).
        try:
            if hasattr(notion_client, "data_sources") and hasattr(notion_client.data_sources, "query"):
                try:
                    db_obj = notion_client.databases.retrieve(database_id=db_id)
                except Exception:
                    db_obj = None
                if db_obj:
                    for ds in db_obj.get("data_sources") or []:
                        ds_id = ds.get("id")
                        if not ds_id:
                            continue
                        try:
                            ds_meta = notion_client.data_sources.retrieve(data_source_id=ds_id)
                        except Exception:
                            ds_meta = None
                        if ds_meta and not ds_meta.get("in_trash") and not ds_meta.get("archived"):
                            try:
                                return notion_client.data_sources.query(data_source_id=ds_id, start_cursor=start_cursor, page_size=page_size)
                            except Exception:
                                # try next fallback if this fails
                                pass
        except Exception:
            # Non-fatal; continue to other fallbacks
            pass

        payload = {"page_size": page_size}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        try:
            # Use named-arg signature for compatibility with notion-client v3
            return notion_client.request(path=f"databases/{db_id}/query", method="POST", body=payload)
        except TypeError:
            if hasattr(notion_client, "_client") and hasattr(notion_client._client, "post"):
                try:
                    return notion_client._client.post(f"databases/{db_id}/query", json=payload)
                except TypeError:
                    return notion_client._client.post(f"databases/{db_id}/query", data=payload)
            raise RuntimeError("Unable to query database via notion client fallback")

    start = None
    while True:
        resp = _query_db(notion, database_id, start, page_size=100)
        for r in resp.get("results", []):
            export_page(notion, r.get("id"), out_dir)
        if resp.get("has_more"):
            start = resp.get("next_cursor")
        else:
            break


def main():
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--database-id")
    p.add_argument("--page-id")
    p.add_argument("--out", default="data/raw/notion")
    args = p.parse_args()
    token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_INTEGRATION_TOKEN")
    if not token:
        p.error("Set NOTION_TOKEN in environment (do not commit secrets).")
    from notion_client import Client
    notion = Client(auth=token)
    if args.database_id:
        export_database(notion, args.database_id, args.out)
    elif args.page_id:
        export_page(notion, args.page_id, args.out)
    else:
        p.error("Provide --database-id or --page-id")


if __name__ == '__main__':
    main()
