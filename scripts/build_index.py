#!/usr/bin/env python3
"""Regenerates index.html from catalog.json. Pure function of the catalog; safe to run any time."""
import json, html
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/trez63/trez63.com"
catalog = json.loads((ROOT / "catalog.json").read_text())
apps = catalog["apps"]

ENGINE_CLASS = {"Claude": "claude", "ChatGPT": "chatgpt", "Muse": "muse", "Gemini": "gemini"}

def fmt(d):  # 2026-10-25 -> Oct 25, 2026
    y, m, dd = map(int, d.split("-"))
    return date(y, m, dd).strftime("%b %-d, %Y")

items = sorted(apps.items(), key=lambda kv: (kv[1]["last_updated"], kv[1]["first_published"]), reverse=True)
engines = sorted({e["engine"] for e in apps.values()})

cards = []
for slug, e in items:
    eng = html.escape(e["engine"]); cls = ENGINE_CLASS.get(e["engine"], "other")
    ver = f"v{e['version']}"
    when = fmt(e["last_updated"]) + (" · updated" if e["version"] > 1 else "")
    up = (e.get("votes") or {}).get("up", 0)
    vote_label = f"👍 {up}" if up else "👍 Vote"
    cards.append(f"""
    <article class="card" data-engine="{eng}" data-up="{up}" data-date="{e['last_updated']}" data-search="{html.escape((e['title'] + ' ' + (e.get('description') or '') + ' ' + slug).lower())}">
      <a class="shot" href="apps/{slug}.html" aria-label="Open {html.escape(e['title'])}">
        <img src="thumbs/{slug}.webp" alt="" loading="lazy" width="640" height="400">
      </a>
      <div class="body">
        <div class="row">
          <h2><a href="apps/{slug}.html">{html.escape(e['title'])}</a></h2>
          <span class="badge {cls}">{eng}</span>
        </div>
        <p>{html.escape(e.get('description') or '')}</p>
        <div class="meta">
          <span>{when}</span>
          <span>·</span>
          <a href="{REPO}/commits/main/apps/{slug}.html" title="Version history on GitHub">{ver}</a>
          <a class="rate" href="rate.html?app={slug}" title="Vote for this app">{vote_label}</a>
        </div>
      </div>
    </article>""")

filters = "".join(f'<button data-filter="{html.escape(x)}">{html.escape(x)}</button>' for x in engines)

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>trez63 — one small app a day</title>
<meta name="description" content="A daily collection of small single-page apps built by AI — Claude, ChatGPT and Muse. Click any card and play.">
<style>
:root{{--bg:#0f1115;--panel:#161a21;--line:#242a34;--fg:#e8e9ec;--mute:#8b93a1;--acc:#ff6a45;
  --claude:#d97757;--chatgpt:#10a37f;--muse:#8b5cf6;--gemini:#4285f4;--other:#6b7280}}
@media (prefers-color-scheme: light){{:root{{--bg:#f6f4ef;--panel:#ffffff;--line:#e2ded4;--fg:#1c1b19;--mute:#6f6a60}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
a{{color:inherit;text-decoration:none}}
header{{max-width:1240px;margin:0 auto;padding:56px 24px 20px}}
h1{{font-size:clamp(28px,5vw,44px);margin:0 0 6px;letter-spacing:-.02em}}
h1 em{{font-style:normal;color:var(--acc)}}
.lede{{color:var(--mute);margin:0 0 22px;max-width:60ch}}
.toolbar{{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center}}
#q{{font:inherit;font-size:15px;padding:9px 14px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--fg);width:min(100%,340px);outline:none}}
#q:focus{{border-color:var(--acc);box-shadow:0 0 0 3px color-mix(in srgb,var(--acc) 25%,transparent)}}
.filters{{display:flex;flex-wrap:wrap;gap:8px}}
.filters button{{font:inherit;font-size:13px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--fg);cursor:pointer}}
.filters button[aria-pressed=true]{{background:var(--fg);color:var(--bg);border-color:var(--fg)}}
.sort{{margin-left:auto}}
.sort button[aria-pressed=true]{{background:var(--acc);border-color:var(--acc);color:#fff}}
main{{max-width:1240px;margin:0 auto;padding:12px 24px 80px;display:grid;gap:22px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;transition:transform .15s,box-shadow .15s}}
.card:hover{{transform:translateY(-3px);box-shadow:0 14px 40px rgba(0,0,0,.25)}}
.card[hidden]{{display:none}}
.shot{{display:block;aspect-ratio:16/10;background:#000;overflow:hidden}}
.shot img{{width:100%;height:100%;object-fit:cover;display:block}}
.body{{padding:14px 16px 16px;display:flex;flex-direction:column;gap:8px;flex:1}}
.row{{display:flex;align-items:center;justify-content:space-between;gap:10px}}
h2{{font-size:18px;margin:0;letter-spacing:-.01em}}
.badge{{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:3px 8px;border-radius:6px;color:#fff;white-space:nowrap}}
.badge.claude{{background:var(--claude)}}.badge.chatgpt{{background:var(--chatgpt)}}.badge.muse{{background:var(--muse)}}.badge.gemini{{background:var(--gemini)}}.badge.other{{background:var(--other)}}
.body p{{margin:0;color:var(--mute);font-size:14px;flex:1}}
.meta{{display:flex;gap:6px;font-size:12px;color:var(--mute)}}
.meta a{{text-decoration:underline dotted}}
.meta .rate{{margin-left:auto;text-decoration:none;color:var(--acc);font-weight:600}}
.meta .rate:hover{{text-decoration:underline}}
.prompt{{margin-top:22px;border:1px solid var(--line);border-radius:12px;background:var(--panel);max-width:70ch}}
.prompt summary{{cursor:pointer;padding:12px 16px;font-weight:600;list-style:none;display:flex;align-items:center;gap:8px}}
.prompt summary::before{{content:"▸";color:var(--acc);transition:transform .15s}}
.prompt[open] summary::before{{transform:rotate(90deg)}}
.prompt summary::-webkit-details-marker{{display:none}}
.prompt-body{{padding:0 16px 16px;color:var(--mute);font-size:14px}}
.prompt-body blockquote{{margin:10px 0;padding:2px 0 2px 14px;border-left:3px solid var(--acc);color:var(--fg)}}
.prompt-body blockquote p{{margin:8px 0}}
.prompt-body .small{{font-size:13px;margin:8px 0 0}}
.prompt-body a{{text-decoration:underline}}
footer{{max-width:1240px;margin:0 auto;padding:0 24px 48px;color:var(--mute);font-size:13px}}
</style>
</head>
<body>
<header>
  <h1>One small app <em>a day</em>.</h1>
  <p class="lede">Every day three AI models each build a single-page app from a one-line prompt. They land here, untouched. Click a card and play. Everything runs in your browser — nothing is uploaded anywhere.</p>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search apps…" aria-label="Search apps by title or description" autocomplete="off">
    <div class="filters" role="group" aria-label="Filter by model">
      <button data-filter="all" aria-pressed="true">All ({len(apps)})</button>{filters}
    </div>
    <div class="filters sort" role="group" aria-label="Sort">
      <button data-sort="new" aria-pressed="true">Newest</button><button data-sort="top">Top voted</button>
    </div>
  </div>
  <p id="empty" class="lede" hidden>No apps match that.</p>
  <details class="prompt" id="prompt">
    <summary>The prompt every model gets</summary>
    <div class="prompt-body">
      <p>Each model is given the same brief, once a day, with no follow-up. What you see here is exactly what came back.</p>
      <blockquote>
        <p>The hero of our story is competing in a JavaScript coding contest. The winner determines the fate of the universe, so the hero must win.</p>
        <p>The contest: write a single-page, self-contained JavaScript/HTML page that requires no special libraries and runs from a browser session. Functionality is up to the coder. Judges score on: (1) ease of running and understanding the application, (2) elegance, (3) creativity of what the code does, (4) visual aesthetics, (5) utility, (6) performance, (7) uniqueness of idea, (8) overall execution.</p>
        <p>Write the code the hero submits, such that he changes nothing and has the highest chance to win.</p>
        <p><strong>Rules.</strong> Every day must be an entirely new app, unlike every previous entry — no repeats of a category or core mechanic. One .html file. No external scripts, fonts, or CDNs. Zero network requests. Opens by double-clicking. Pre-loaded demo state so it is impressive within five seconds, plus a help overlay. Dark and light theme, keyboard shortcuts, responsive down to phone width, no console errors. Elegant code, under ~500 lines where possible. Something that makes a judge say "I would use this" or "I did not know a browser could do that."</p>
      </blockquote>
      <p class="small">Updates happen when the model is asked to add a feature to an existing app; the card's version number ticks up and the old version stays in the <a href="{REPO}">repo</a> history.</p>
    </div>
  </details>
</header>
<main id="grid">{''.join(cards)}
</main>
<footer>Source and full version history on <a href="{REPO}" style="text-decoration:underline">GitHub</a>. Last published {fmt(catalog.get('generated', date.today().isoformat()))}.</footer>
<script>
const q=document.getElementById('q'), grid=document.getElementById('grid'), cards=[...document.querySelectorAll('.card')], empty=document.getElementById('empty');
let engine='all', sort='new';
function resort(){{
  const by = sort==='top'
    ? (a,b)=>(+b.dataset.up-(+a.dataset.up))||b.dataset.date.localeCompare(a.dataset.date)
    : (a,b)=>b.dataset.date.localeCompare(a.dataset.date);
  [...cards].sort(by).forEach(c=>grid.appendChild(c));
}}
document.querySelectorAll('.sort button').forEach(b=>b.addEventListener('click',()=>{{
  sort=b.dataset.sort;
  document.querySelectorAll('.sort button').forEach(x=>x.setAttribute('aria-pressed',x===b));
  resort();
}}));
function apply(){{
  const terms=q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
  let shown=0;
  cards.forEach(c=>{{
    const ok=(engine==='all'||c.dataset.engine===engine)&&terms.every(t=>c.dataset.search.includes(t));
    c.hidden=!ok; if(ok) shown++;
  }});
  empty.hidden=shown>0;
}}
document.querySelectorAll('.filters:not(.sort) button').forEach(b=>b.addEventListener('click',()=>{{
  engine=b.dataset.filter;
  document.querySelectorAll('.filters:not(.sort) button').forEach(x=>x.setAttribute('aria-pressed',x===b));
  apply();
}}));
q.addEventListener('input',apply);
document.addEventListener('keydown',e=>{{ if(e.key==='/'&&document.activeElement!==q){{e.preventDefault();q.focus();}} if(e.key==='Escape'&&document.activeElement===q){{q.value='';apply();}} }});
</script>
</body>
</html>
"""
(ROOT / "index.html").write_text(page)
print(f"index.html: {len(apps)} apps")
