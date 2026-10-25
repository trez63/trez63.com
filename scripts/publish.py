#!/usr/bin/env python3
"""
trez63.com publisher.

Usage:
  python3 scripts/publish.py --source <dir-with-html-files> [--no-thumbs] [--force-thumbs slug,slug]

What it does, per *.html in --source:
  1. Derives a slug + engine from the filename  (carve-claude.html -> slug "carve", engine "Claude")
  2. Hashes the file. New slug -> added as v1. Changed hash -> copied over apps/<slug>.html, version bumped.
     Unchanged -> skipped.
  3. Screenshots new/changed apps with headless Chromium into thumbs/<slug>.webp
     (per-app interaction recipe lives in catalog.json under "thumb"; a generic poke is the default).
  4. Updates catalog.json (title, description, engine, versions, dates).
  5. Regenerates index.html from catalog.json via scripts/build_index.py.

Anything that is not *.html (save-game .json files, .lnk shortcuts) is ignored on purpose.
Descriptions: the catalog's "description" is authoritative once set; the script only seeds it
from <meta description> / a tagline / <title> when the entry is new, so a human (or Claude)
can write a better one afterwards and it will stick.
"""
import argparse, hashlib, json, re, shutil, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPS, THUMBS = ROOT / "apps", ROOT / "thumbs"
CATALOG = ROOT / "catalog.json"

ENGINE_SUFFIX = {
    "claude": "Claude",
    "codex": "ChatGPT", "chatgpt": "ChatGPT", "gpt": "ChatGPT", "openai": "ChatGPT",
    "muse": "Muse",
    "gemini": "Gemini",
}

def slug_and_engine(filename: str):
    stem = Path(filename).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    m = re.match(r"^(.*?)-(" + "|".join(ENGINE_SUFFIX) + r")$", stem)
    if m:
        return m.group(1), ENGINE_SUFFIX[m.group(2)]
    return stem, None

def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]

def strip_markup(html: str):
    html = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", html)

def seed_meta(html: str):
    """Best-effort title + description from the file itself."""
    title = re.search(r"<title>([^<]*)</title>", html, re.I)
    title = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
    desc = ""
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html, re.I)
    if m:
        desc = m.group(1)
    else:
        m = re.search(r'<p[^>]*class="[^"]*(?:tag|lede|intro|sub)[^"]*"[^>]*>(.*?)</p>', html, re.S | re.I)
        if m:
            desc = re.sub(r"<[^>]+>", "", m.group(1))
    # "NAME — subtitle" titles: split
    name, sub = title, ""
    for sep in (" — ", " – ", " - ", ": "):
        if sep in title:
            name, sub = title.split(sep, 1)
            break
    if not desc:
        desc = sub
    desc = re.sub(r"\s+", " ", desc).replace("&mdash;", "—").replace("&nbsp;", " ").strip()
    return name.strip().title() if name.isupper() else name.strip(), desc

# ---------------------------------------------------------------- thumbnails
GENERIC_ACTIONS = [
    {"wait": 1200},
    {"key": "Escape"},
    {"click": [0.5, 0.55]},
    {"type": "trez63"},
    {"drag": [[0.3, 0.45], [0.7, 0.6]]},
    {"drag": [[0.6, 0.35], [0.4, 0.7]]},
    {"click": [0.35, 0.65]},
    {"wait": 1500},
]

def screenshot(app_path: Path, out: Path, actions):
    from playwright.sync_api import sync_playwright
    W, H = 1280, 800
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto(app_path.resolve().as_uri())
        for a in actions:
            try:
                if "wait" in a:   pg.wait_for_timeout(a["wait"])
                elif "key" in a:  pg.keyboard.press(a["key"])
                elif "type" in a: pg.keyboard.type(a["type"], delay=40)
                elif "click" in a:
                    x, y = a["click"]; pg.mouse.click(x * W, y * H)
                elif "drag" in a:
                    (x1, y1), (x2, y2) = a["drag"]
                    pg.mouse.move(x1 * W, y1 * H); pg.mouse.down()
                    for i in range(1, 21):
                        pg.mouse.move((x1 + (x2 - x1) * i / 20) * W, (y1 + (y2 - y1) * i / 20) * H)
                    pg.mouse.up()
                elif "selector_click" in a:
                    pg.click(a["selector_click"], timeout=2000)
                elif "eval" in a:
                    pg.evaluate(a["eval"])
            except Exception as e:  # a failed step never kills the capture
                print(f"   (thumb step {a} skipped: {type(e).__name__})")
        pg.screenshot(path=str(out.with_suffix(".png")))
        b.close()
    # downscale to 640x400 webp
    from PIL import Image
    im = Image.open(out.with_suffix(".png")).convert("RGB").resize((640, 400), Image.LANCZOS)
    im.save(out, "WEBP", quality=82)
    out.with_suffix(".png").unlink(missing_ok=True)

def fallback_card(slug, title, engine, out: Path):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (640, 400), "#15181d"); d = ImageDraw.Draw(im)
    d.text((40, 160), title, fill="#e9e7e1"); d.text((40, 200), engine or "", fill="#8f8c86")
    im.save(out, "WEBP", quality=82)

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--no-thumbs", action="store_true")
    ap.add_argument("--force-thumbs", default="", help="comma list of slugs to re-screenshot")
    ap.add_argument("--terms", default="", help="private-terms file for scripts/privacy_check.py (kept outside the repo)")
    args = ap.parse_args()
    src = Path(args.source)
    today = date.today().isoformat()
    force = set(filter(None, args.force_thumbs.split(",")))

    catalog = json.loads(CATALOG.read_text()) if CATALOG.exists() else {"apps": {}}
    apps = catalog["apps"]
    APPS.mkdir(exist_ok=True); THUMBS.mkdir(exist_ok=True)

    changed, blocked = [], []
    for f in sorted(src.glob("*.html")):
        slug, engine = slug_and_engine(f.name)
        h = sha(f)
        entry = apps.get(slug)
        if entry and entry.get("sha") == h:
            print(f"= {slug}: unchanged")
            continue
        # PRIVACY GATE: a file with findings is never copied into the public repo.
        chk = subprocess.run([sys.executable, str(ROOT / "scripts" / "privacy_check.py")]
                             + (["--terms", args.terms] if args.terms else []) + [str(f)],
                             capture_output=True, text=True)
        if chk.returncode != 0:
            print(f"✗ {slug}: BLOCKED by privacy check\n" + "\n".join("    " + l for l in chk.stdout.splitlines()[:8]))
            blocked.append(slug)
            continue
        html = f.read_text(encoding="utf-8", errors="ignore")
        title, desc = seed_meta(html)
        shutil.copy2(f, APPS / f"{slug}.html")
        if entry is None:
            apps[slug] = entry = {
                "title": title or slug, "engine": engine or "Unknown", "description": desc,
                "source_file": f.name, "first_published": today, "last_updated": today,
                "version": 1, "sha": h, "versions": [{"v": 1, "date": today, "sha": h}],
            }
            print(f"+ {slug}: new  [{entry['engine']}]  {entry['title']}")
        else:
            entry["version"] += 1
            entry["last_updated"] = today
            entry["sha"] = h
            entry["source_file"] = f.name
            if engine and entry.get("engine") in (None, "Unknown"): entry["engine"] = engine
            if title: entry["title"] = title
            entry["versions"].append({"v": entry["version"], "date": today, "sha": h})
            print(f"^ {slug}: updated -> v{entry['version']}")
        changed.append(slug)

    if not args.no_thumbs:
        for slug in sorted(set(changed) | force):
            e = apps[slug]; out = THUMBS / f"{slug}.webp"
            try:
                screenshot(APPS / f"{slug}.html", out, e.get("thumb", {}).get("actions", GENERIC_ACTIONS))
                print(f"  📷 {slug}")
            except Exception as ex:
                print(f"  ⚠ {slug}: screenshot failed ({ex}); fallback card")
                fallback_card(slug, e["title"], e["engine"], out)

    catalog["generated"] = today
    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_index.py")], check=True)
    print(f"\n{len(changed)} new/updated: {', '.join(changed) or '-'}")
    if blocked:
        print(f"BLOCKED (not published): {', '.join(blocked)}")
    # final sweep of everything that is about to be committed
    final = subprocess.run([sys.executable, str(ROOT / "scripts" / "privacy_check.py")]
                           + (["--terms", args.terms] if args.terms else [])
                           + [str(ROOT / "apps"), str(CATALOG), str(ROOT / "index.html"), str(ROOT / "README.md")],
                           capture_output=True, text=True)
    print(final.stdout.strip().splitlines()[-1])
    if final.returncode != 0:
        print(final.stdout); sys.exit(2)

if __name__ == "__main__":
    main()
