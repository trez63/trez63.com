# trez63.com

One small single-page app a day, built by AI (Claude, ChatGPT, Muse). Served by GitHub Pages at https://trez63.com.

## Layout

| Path | What |
|---|---|
| `apps/<slug>.html` | The apps, one self-contained file each. Always the latest version; history is in git. |
| `thumbs/<slug>.webp` | 640×400 screenshot of each app, retaken whenever the app changes. |
| `catalog.json` | Source of truth for the index: title, engine, description, versions, dates, thumbnail recipe. |
| `index.html` | Generated. Do not edit by hand — run `scripts/build_index.py`. |
| `scripts/publish.py` | Daily publisher. Ingests a folder of HTML files, detects new/changed apps by hash, screenshots them, updates the catalog, rebuilds the index. |

## Daily flow

1. The AI engines drop their finished app into the connected source folder (filename convention: `<name>-<engine>.html`; a re-saved file with the same name is treated as a new version).
2. A scheduled Claude task stages that folder, runs `python3 scripts/publish.py --source <folder>`, writes a one-line description for anything new, and pushes to `main`.
3. GitHub Pages rebuilds within a minute.

Only `*.html` is ever published. Save files (`*.json`), shortcuts and anything else in the source folder are ignored.

## Votes

Voting is giscus on GitHub Discussions (category "App votes", one thread per app, term `app:<slug>`); a 👍 on the thread is a vote. The daily task pulls counts via `scripts/fetch_votes.js` (must run in a browser tab on the giscus.app origin — the API has no CORS), saves the JSON, and runs `scripts/apply_votes.py votes.json`, which writes `votes` into `catalog.json` and rebuilds the index (vote count on cards, "Top voted" sort).

## Privacy gate

`scripts/privacy_check.py` scans for emails, phone numbers, API keys/tokens, AWS account IDs, private IPs, home-directory paths, street addresses, SSN/card shapes, and (optionally, `--terms FILE`) a private word list kept outside the repo. `publish.py` runs it on every incoming file and refuses to copy anything with findings, then sweeps `apps/`, `catalog.json`, `index.html` and `README.md` before exiting. Run it by hand on anything else before committing: `python3 scripts/privacy_check.py --terms <file> <paths>`.
