#!/usr/bin/env python3
"""Merge vote counts (output of scripts/fetch_votes.js) into catalog.json and rebuild the index.

Usage: python3 scripts/apply_votes.py votes.json
votes.json: {"<slug>": {"up": int, "reactions": int, "comments": int, "url": str|null}, ...}

Counts are additive-safe: a slug missing from votes.json keeps whatever it had (the discussion may just
have failed to load); a slug present is overwritten. Nothing else in the catalog is touched.
"""
import json, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.json"

def main(path):
    votes = json.loads(Path(path).read_text())
    cat = json.loads(CATALOG.read_text())
    today = date.today().isoformat()
    n = 0
    for slug, v in votes.items():
        if slug in cat["apps"]:
            cat["apps"][slug]["votes"] = {
                "up": int(v.get("up", 0)), "reactions": int(v.get("reactions", 0)),
                "comments": int(v.get("comments", 0)), "url": v.get("url"), "fetched": today,
            }
            n += 1
    cat["votes_fetched"] = today
    CATALOG.write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_index.py")], check=True)
    print(f"votes applied to {n} apps")

if __name__ == "__main__":
    main(sys.argv[1])
