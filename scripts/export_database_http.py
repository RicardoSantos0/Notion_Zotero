#!/usr/bin/env python3
import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
import httpx


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


def fetch_blocks_http(token: str, block_id: str):
    out = []
    start = None
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
    client = httpx.Client(headers=headers, timeout=30.0)
    try:
        while True:
            params = {"page_size": 100}
            if start:
                params["start_cursor"] = start
            resp = client.get(f"https://api.notion.com/v1/blocks/{block_id}/children", params=params)
            resp.raise_for_status()
            body = resp.json()
            out.extend(body.get("results", []))
            if body.get("has_more"):
                start = body.get("next_cursor")
            else:
                break
    finally:
        client.close()
    return out


def serialize_block(b):
    t = b.get("type")
    text = ""
    if t in (
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
    ):
        text = plain_text(b.get(t, {}).get("rich_text", []))
    return {"id": b.get("id"), "type": t, "text": text, "raw": b}


def extract_tables(blocks, token: str):
    tables = []
    for idx, b in enumerate(blocks):
        if b.get("type") == "table":
            rows = fetch_blocks_http(token, b["id"])
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


def export_page_http(token: str, page_id: str, out_dir: str):
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
    client = httpx.Client(headers=headers, timeout=30.0)
    try:
        rpage = client.get(f"https://api.notion.com/v1/pages/{page_id}")
        rpage.raise_for_status()
        page = rpage.json()
        blocks = fetch_blocks_http(token, page_id)
        fixture = {
            "page_id": page_id,
            "title": get_title(page),
            "properties": page.get("properties", {}),
            "tables": extract_tables(blocks, token),
            "blocks": [serialize_block(b) for b in blocks],
        }
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        path = Path(out_dir) / f"{page_id}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(fixture, fh, ensure_ascii=False, indent=2)
        print("WROTE:", path)
    finally:
        client.close()


def export_database_http(token: str, database_id: str, out_dir: str):
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
    client = httpx.Client(headers=headers, timeout=30.0)
    try:
        start = None
        while True:
            payload = {"page_size": 100}
            if start:
                payload["start_cursor"] = start
            resp = client.post(f"https://api.notion.com/v1/databases/{database_id}/query", json=payload)
            resp.raise_for_status()
            body = resp.json()
            for r in body.get("results", []):
                pid = r.get("id")
                export_page_http(token, pid, out_dir)
            if body.get("has_more"):
                start = body.get("next_cursor")
            else:
                break
    finally:
        client.close()


def main():
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--database-id")
    p.add_argument("--out", default="fixtures/reading_list")
    args = p.parse_args()
    token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_INTEGRATION_TOKEN")
    if not token:
        p.error("Set NOTION_TOKEN in environment (do not commit secrets).")
    if not args.database_id:
        p.error("Provide --database-id")
    export_database_http(token, args.database_id, args.out)


if __name__ == '__main__':
    main()
