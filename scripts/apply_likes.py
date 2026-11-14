#!/usr/bin/env python3
"""Merge like counts (output of scripts/fetch_likes.js) into catalog.json and rebuild the pages.

Usage: python3 scripts/apply_likes.py likes.json [more.json ...]
Each file: {"<slug>": <count>, ...}

The catalog copy is a backup of the counter service and the baseline the pages show before the live
count loads. Counters only ever go up, so a fetched number lower than the stored one is ignored: that
way a reset or outage at the service never erases what was recorded here.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.json"

def main(paths):
    cat = json.loads(CATALOG.read_text())
    changed = 0
    for path in paths:
        for slug, n in json.loads(Path(path).read_text()).items():
            e = cat["apps"].get(slug)
            if e is None: continue
            n = int(n)
            if n > int(e.get("likes") or 0):
                e["likes"] = n; changed += 1
    if changed:
        CATALOG.write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_index.py")], check=True)
    total = sum(int(e.get("likes") or 0) for e in cat["apps"].values())
    print(f"likes: {changed} apps changed, {total} likes recorded in total")

if __name__ == "__main__":
    main(sys.argv[1:])
