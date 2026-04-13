#!/usr/bin/env python3
import json
import argparse
from pathlib import Path
import re
from typing import Dict, Any, List


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def authors_key(authors: List[str]) -> str:
    if not authors:
        return ""
    return "|".join(normalize_text(a) for a in authors)


def record_key(rec: Dict[str, Any]):
    # rec is the canonical dict with a `references` list
    refs = rec.get("references") or []
    if not refs:
        return ("none", "")
    r = refs[0]
    doi = (r.get("doi") or "").strip().lower()
    if doi:
        return ("doi", doi)
    title = normalize_text(r.get("title") or "")
    auth = authors_key(r.get("authors") or [])
    return ("tt", f"{title}|{auth}")


def merge_records(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    # Merge two canonical records preferring non-empty fields from b
    out = dict(a)
    # shallow merge for top-level keys
    for k, v in b.items():
        if not out.get(k) and v:
            out[k] = v
        elif isinstance(out.get(k), list) and isinstance(v, list):
            # merge lists deduplicating by JSON
            seen = {json.dumps(x, sort_keys=True) for x in out[k]}
            for item in v:
                js = json.dumps(item, sort_keys=True)
                if js not in seen:
                    out[k].append(item)
                    seen.add(js)
    return out


def aggregate_canonical(input_dir: Path) -> List[Dict[str, Any]]:
    files = sorted(input_dir.glob("*.canonical.json"))
    by_key = {}
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        key = record_key(data)
        if key in by_key:
            by_key[key] = merge_records(by_key[key], data)
        else:
            by_key[key] = data
    return list(by_key.values())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="fixtures/canonical")
    p.add_argument("--out", default="fixtures/canonical_merged.json")
    args = p.parse_args()
    input_dir = Path(args.input)
    merged = aggregate_canonical(input_dir)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out_path} ({len(merged)} records)")


if __name__ == '__main__':
    main()
