#!/usr/bin/env python3
"""Regenerates index.html, p/<slug>.html (play pages with social meta) and feed.xml from catalog.json.
Pure function of the catalog; safe to run any time."""
import json, html
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://trez63.com"
REPO = "https://github.com/trez63/trez63.com"
catalog = json.loads((ROOT / "catalog.json").read_text())
apps = catalog["apps"]
TODAY = date.today()

ENGINE_CLASS = {"Claude": "claude", "ChatGPT": "chatgpt", "Muse": "muse", "Gemini": "gemini"}
CAT_LABEL = {"tool": "Tools", "art": "Generative art", "game": "Games", "audio": "Audio", "sim": "Simulations",
             "image": "Image", "finance": "Finance", "dev": "Dev tools", "focus": "Focus", "text": "Text", "edu": "Explainers"}
WIN_AFTER_DAYS = 7           # a day's winner is locked this many days after publish
E = html.escape

def fmt(d):
    y, m, dd = map(int, d.split("-")); return date(y, m, dd).strftime("%b %-d, %Y")
def up(e): return int((e.get("votes") or {}).get("up", 0))
def pub(e): return e["first_published"]
def has_preview(slug): return (ROOT / "previews" / f"{slug}.webm").exists()

# ------------------------------------------------------------------ scoreboard
by_day = defaultdict(list)
for slug, e in apps.items(): by_day[pub(e)].append((slug, e))
wins = defaultdict(float); rounds_locked = 0
for d, entries in by_day.items():
    if len({e["engine"] for _, e in entries}) < 2: continue            # a round needs 2+ engines
    if date.fromisoformat(d) + timedelta(days=WIN_AFTER_DAYS) > TODAY: continue
    best = max(up(e) for _, e in entries)
    if best == 0: continue
    winners = {e["engine"] for _, e in entries if up(e) == best}
    for w in winners: wins[w] += 1 / len(winners)
    rounds_locked += 1
all_engines = sorted({e["engine"] for e in apps.values()})
totals = {en: sum(up(e) for e in apps.values() if e["engine"] == en) for en in all_engines}
counts = {en: sum(1 for e in apps.values() if e["engine"] == en) for en in all_engines}
board = sorted(all_engines, key=lambda en: (-wins[en], -totals[en], en))

# ------------------------------------------------------------------ matchup: newest app per engine
newest = {}
for slug, e in sorted(apps.items(), key=lambda kv: (pub(kv[1]), kv[1]["last_updated"]), reverse=True):
    newest.setdefault(e["engine"], (slug, e))
matchup = [newest[en] for en in all_engines if en in newest]
matchup_date = max(pub(e) for _, e in matchup) if matchup else None
matchup_locked = bool(matchup_date) and date.fromisoformat(matchup_date) + timedelta(days=WIN_AFTER_DAYS) <= TODAY

# ------------------------------------------------------------------ cards
def shot(slug, e, lazy=True):
    v = f'<video src="previews/{slug}.webm" muted loop playsinline preload="none" poster="thumbs/{slug}.webp"></video>' if has_preview(slug) else ""
    return (f'<a class="shot" href="p/{slug}.html" aria-label="Open {E(e["title"])}">'
            f'<img src="thumbs/{slug}.webp" alt="" {"loading=lazy" if lazy else ""} width="640" height="400">{v}</a>')

def card(slug, e, big=False):
    eng = E(e["engine"]); cls = ENGINE_CLASS.get(e["engine"], "other"); u = up(e)
    cat = e.get("category", "")
    search = E((e["title"] + " " + (e.get("description") or "") + " " + slug + " " + cat + " " + e["engine"]).lower())
    return f"""
    <article class="card{' big' if big else ''}" data-engine="{eng}" data-cat="{E(cat)}" data-up="{u}" data-date="{e['last_updated']}" data-search="{search}">
      {shot(slug, e, lazy=not big)}
      <div class="body">
        <div class="row">
          <h2><a href="p/{slug}.html">{E(e['title'])}</a></h2>
          <span class="badge {cls}">{eng}</span>
        </div>
        <p>{E(e.get('description') or '')}</p>
        <div class="meta">
          <span>{fmt(e['last_updated'])}{' · updated' if e['version'] > 1 else ''}</span>
          <span>·</span>
          <a href="{REPO}/commits/main/apps/{slug}.html" title="Version history on GitHub">v{e['version']}</a>
          {f'<span>· {E(CAT_LABEL.get(cat, cat))}</span>' if cat else ''}
          <a class="rate" href="rate.html?app={slug}" title="Vote for this app">👍 {u if u else 'Vote'}</a>
        </div>
      </div>
    </article>"""

items = sorted(apps.items(), key=lambda kv: (kv[1]["last_updated"], pub(kv[1])), reverse=True)
cards = "".join(card(s, e) for s, e in items)
engine_filters = "".join(f'<button data-filter="{E(x)}">{E(x)}</button>' for x in all_engines)
cats_present = sorted({e.get("category") for e in apps.values() if e.get("category")}, key=lambda c: CAT_LABEL.get(c, c))
cat_filters = "".join(f'<button data-cat="{E(c)}">{E(CAT_LABEL.get(c, c))}</button>' for c in cats_present)

matchup_html = ""
if len(matchup) >= 2:
    lead = max(up(e) for _, e in matchup)
    cols = "".join(card(s, e, big=True) for s, e in matchup)
    status = ("Winner locked" if matchup_locked else
              f"Voting open — winner locks {fmt((date.fromisoformat(matchup_date) + timedelta(days=WIN_AFTER_DAYS)).isoformat())}")
    matchup_html = f"""
<section class="matchup" aria-label="Latest matchup">
  <div class="mh">
    <h2>Latest matchup <span class="dim">· {fmt(matchup_date)}</span></h2>
    <span class="dim">{status}{' · ' + str(lead) + ' votes leads' if lead else ''}</span>
  </div>
  <div class="mgrid">{cols}</div>
</section>"""

rows = "".join(
    f'<tr><td><span class="badge {ENGINE_CLASS.get(en, "other")}">{E(en)}</span></td>'
    f'<td class="num">{wins[en]:g}</td><td class="num">{totals[en]}</td><td class="num">{counts[en]}</td></tr>'
    for en in board)
score_html = f"""
<section class="score" aria-label="Scoreboard">
  <div class="mh"><h2>Scoreboard</h2><span class="dim">{rounds_locked} round{'s' if rounds_locked != 1 else ''} decided · a day's winner is the app with the most 👍 {WIN_AFTER_DAYS} days after it ships; ties split</span></div>
  <table><thead><tr><th>Model</th><th class="num">Wins</th><th class="num">Total 👍</th><th class="num">Apps</th></tr></thead><tbody>{rows}</tbody></table>
</section>"""

CSS = """
:root{--bg:#0f1115;--panel:#161a21;--line:#242a34;--fg:#e8e9ec;--mute:#8b93a1;--acc:#ff6a45;
  --claude:#d97757;--chatgpt:#10a37f;--muse:#8b5cf6;--gemini:#4285f4;--other:#6b7280}
@media (prefers-color-scheme: light){:root{--bg:#f6f4ef;--panel:#ffffff;--line:#e2ded4;--fg:#1c1b19;--mute:#6f6a60}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:inherit;text-decoration:none}
header,main,section,footer{max-width:1240px;margin:0 auto;padding-left:24px;padding-right:24px}
header{padding-top:56px;padding-bottom:8px}
h1{font-size:clamp(28px,5vw,44px);margin:0 0 6px;letter-spacing:-.02em}
h1 em{font-style:normal;color:var(--acc)}
.lede{color:var(--mute);margin:0 0 22px;max-width:60ch}
.toolbar{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center}
#q{font:inherit;font-size:15px;padding:9px 14px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--fg);width:min(100%,340px);outline:none}
#q:focus{border-color:var(--acc);box-shadow:0 0 0 3px color-mix(in srgb,var(--acc) 25%,transparent)}
.filters{display:flex;flex-wrap:wrap;gap:8px}
.filters button{font:inherit;font-size:13px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--fg);cursor:pointer}
.filters button[aria-pressed=true]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.sort{margin-left:auto}
.sort button[aria-pressed=true]{background:var(--acc);border-color:var(--acc);color:#fff}
.cats{margin-top:10px}
.cats button[aria-pressed=true]{background:var(--mute);border-color:var(--mute);color:var(--bg)}
.prompt{margin-top:22px;border:1px solid var(--line);border-radius:12px;background:var(--panel);max-width:70ch}
.prompt summary{cursor:pointer;padding:12px 16px;font-weight:600;list-style:none;display:flex;align-items:center;gap:8px}
.prompt summary::before{content:"▸";color:var(--acc);transition:transform .15s}
.prompt[open] summary::before{transform:rotate(90deg)}
.prompt summary::-webkit-details-marker{display:none}
.prompt-body{padding:0 16px 16px;color:var(--mute);font-size:14px}
.prompt-body blockquote{margin:10px 0;padding:2px 0 2px 14px;border-left:3px solid var(--acc);color:var(--fg)}
.prompt-body blockquote p{margin:8px 0}
.prompt-body .small{font-size:13px;margin:8px 0 0}
.prompt-body a{text-decoration:underline}
.mh{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:6px 16px;margin:0 0 12px}
.mh h2{font-size:22px;margin:0;letter-spacing:-.01em}
.dim{color:var(--mute);font-size:13px;font-weight:400}
.matchup{padding-top:36px}
.mgrid{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.score{padding-top:36px}
.score table{border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;min-width:min(100%,460px)}
.score th,.score td{padding:10px 16px;text-align:left;border-top:1px solid var(--line)}
.score th{font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.05em;border-top:0}
.score .num{text-align:right;font-variant-numeric:tabular-nums}
.all{padding-top:36px}
main{padding-top:12px;padding-bottom:80px;display:grid;gap:22px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-3px);box-shadow:0 14px 40px rgba(0,0,0,.25)}
.card[hidden]{display:none}
.card.big .body p{font-size:15px}
.shot{display:block;aspect-ratio:16/10;background:#000;overflow:hidden;position:relative}
.shot img,.shot video{width:100%;height:100%;object-fit:cover;display:block}
.shot video{position:absolute;inset:0;opacity:0;transition:opacity .25s}
.card:hover .shot video.ready{opacity:1}
.body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:8px;flex:1}
.row{display:flex;align-items:center;justify-content:space-between;gap:10px}
h2{font-size:18px;margin:0;letter-spacing:-.01em}
.badge{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:3px 8px;border-radius:6px;color:#fff;white-space:nowrap}
.badge.claude{background:var(--claude)}.badge.chatgpt{background:var(--chatgpt)}.badge.muse{background:var(--muse)}.badge.gemini{background:var(--gemini)}.badge.other{background:var(--other)}
.body p{margin:0;color:var(--mute);font-size:14px;flex:1}
.meta{display:flex;flex-wrap:wrap;gap:6px;font-size:12px;color:var(--mute);align-items:center}
.meta a{text-decoration:underline dotted}
.meta .rate{margin-left:auto;text-decoration:none;color:var(--acc);font-weight:600}
.meta .rate:hover{text-decoration:underline}
footer{padding-bottom:48px;color:var(--mute);font-size:13px}
footer a{text-decoration:underline}
"""

JS = """
const q=document.getElementById('q'), grid=document.getElementById('grid'), cards=[...grid.querySelectorAll('.card')], empty=document.getElementById('empty');
let engine='all', cat='all', sort='new';
function apply(){
  const terms=q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
  let shown=0;
  cards.forEach(c=>{
    const ok=(engine==='all'||c.dataset.engine===engine)&&(cat==='all'||c.dataset.cat===cat)&&terms.every(t=>c.dataset.search.includes(t));
    c.hidden=!ok; if(ok) shown++;
  });
  empty.hidden=shown>0;
}
function resort(){
  const by = sort==='top'
    ? (a,b)=>(+b.dataset.up-(+a.dataset.up))||b.dataset.date.localeCompare(a.dataset.date)
    : (a,b)=>b.dataset.date.localeCompare(a.dataset.date);
  [...cards].sort(by).forEach(c=>grid.appendChild(c));
}
function press(group,b){ group.forEach(x=>x.setAttribute('aria-pressed',x===b)); }
const eng=[...document.querySelectorAll('.engines button')], cts=[...document.querySelectorAll('.cats button')], srt=[...document.querySelectorAll('.sort button')];
eng.forEach(b=>b.addEventListener('click',()=>{engine=b.dataset.filter;press(eng,b);apply();}));
cts.forEach(b=>b.addEventListener('click',()=>{cat=(cat===b.dataset.cat?'all':b.dataset.cat);press(cts,cat==='all'?null:b);apply();}));
srt.forEach(b=>b.addEventListener('click',()=>{sort=b.dataset.sort;press(srt,b);resort();}));
q.addEventListener('input',apply);
document.addEventListener('keydown',e=>{ if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus();} if(e.key==='Escape'&&document.activeElement===q){q.value='';apply();} });
document.querySelectorAll('.card').forEach(c=>{
  const v=c.querySelector('video'); if(!v) return;
  c.addEventListener('mouseenter',()=>{ if(v.preload==='none'){v.preload='auto';v.load();} v.play().then(()=>v.classList.add('ready')).catch(()=>{}); });
  c.addEventListener('mouseleave',()=>{ v.pause(); v.classList.remove('ready'); });
});
"""

PROMPT = f"""
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
  </details>"""

def og(title, desc, img, url):
    return f"""<meta property="og:type" content="website">
<meta property="og:site_name" content="trez63">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{img}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{img}">"""

newest_slug = items[0][0] if items else ""
SITE_DESC = "Every day Claude, ChatGPT and Muse each build a single-page app from the same one-line prompt. Play them, vote for the winner."
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>trez63 — one small app a day</title>
<meta name="description" content="{SITE_DESC}">
<link rel="canonical" href="{SITE}/">
<link rel="alternate" type="application/rss+xml" title="trez63 — new apps" href="{SITE}/feed.xml">
{og("trez63 — one small app a day", SITE_DESC, f"{SITE}/thumbs/{newest_slug}.webp", SITE + "/")}
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>One small app <em>a day</em>.</h1>
  <p class="lede">Every day three AI models each build a single-page app from the same one-line prompt. They land here, untouched. Play them, then vote for the one that should win. Everything runs in your browser — nothing is uploaded anywhere.</p>
  {PROMPT}
</header>
{matchup_html}
{score_html}
<section class="all">
  <div class="mh"><h2>All apps <span class="dim">· {len(apps)}</span></h2></div>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search apps…" aria-label="Search apps by title or description" autocomplete="off">
    <div class="filters engines" role="group" aria-label="Filter by model">
      <button data-filter="all" aria-pressed="true">All</button>{engine_filters}
    </div>
    <div class="filters sort" role="group" aria-label="Sort">
      <button data-sort="new" aria-pressed="true">Newest</button><button data-sort="top">Top voted</button>
    </div>
  </div>
  <div class="filters cats" role="group" aria-label="Filter by category">{cat_filters}</div>
  <p id="empty" class="lede" hidden>No apps match that.</p>
</section>
<main id="grid">{cards}
</main>
<footer>Source and full version history on <a href="{REPO}">GitHub</a> · <a href="feed.xml">RSS</a> · Last published {fmt(catalog.get('generated', TODAY.isoformat()))}.</footer>
<script>{JS}</script>
</body>
</html>
"""
(ROOT / "index.html").write_text(page)

# ------------------------------------------------------------------ play pages: p/<slug>.html
PDIR = ROOT / "p"; PDIR.mkdir(exist_ok=True)
for old in PDIR.glob("*.html"):
    if old.stem not in apps: old.unlink()
for slug, e in apps.items():
    eng = E(e["engine"]); cls = ENGINE_CLASS.get(e["engine"], "other"); u = up(e)
    desc = e.get("description") or ""
    (PDIR / f"{slug}.html").write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(e['title'])} — trez63</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{SITE}/p/{slug}.html">
{og(e['title'] + ' — built by ' + e['engine'], desc, f"{SITE}/thumbs/{slug}.webp", f"{SITE}/p/{slug}.html")}
<style>
:root{{--bg:#0f1115;--panel:#161a21;--line:#242a34;--fg:#e8e9ec;--mute:#8b93a1;--acc:#ff6a45;--claude:#d97757;--chatgpt:#10a37f;--muse:#8b5cf6;--gemini:#4285f4;--other:#6b7280}}
@media (prefers-color-scheme: light){{:root{{--bg:#f6f4ef;--panel:#ffffff;--line:#e2ded4;--fg:#1c1b19;--mute:#6f6a60}}}}
*{{box-sizing:border-box}}html,body{{height:100%;margin:0}}
body{{display:flex;flex-direction:column;background:var(--bg);color:var(--fg);font:14px system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.bar{{display:flex;align-items:center;gap:12px;padding:8px 14px;background:var(--panel);border-bottom:1px solid var(--line);flex:none}}
.bar a{{color:inherit;text-decoration:none}}
.back{{color:var(--mute)}} .back:hover{{color:var(--fg)}}
.title{{font-weight:600}}
.badge{{font-size:10px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;border-radius:5px;color:#fff}}
.badge.claude{{background:var(--claude)}}.badge.chatgpt{{background:var(--chatgpt)}}.badge.muse{{background:var(--muse)}}.badge.gemini{{background:var(--gemini)}}.badge.other{{background:var(--other)}}
.desc{{color:var(--mute);overflow:hidden;white-space:nowrap;text-overflow:ellipsis;flex:1;min-width:0}}
.vote{{background:var(--acc);color:#fff!important;font-weight:600;padding:6px 12px;border-radius:999px;white-space:nowrap}}
.raw{{color:var(--mute);white-space:nowrap}} .raw:hover{{color:var(--fg)}}
iframe{{flex:1;border:0;width:100%;background:#fff}}
@media (max-width:640px){{.desc,.raw{{display:none}}}}
</style>
</head>
<body>
<div class="bar">
  <a class="back" href="../">← trez63</a>
  <span class="title">{E(e['title'])}</span>
  <span class="badge {cls}">{eng}</span>
  <span class="desc">{E(desc)}</span>
  <a class="raw" href="../apps/{slug}.html" title="Open the app on its own, full window">open raw ↗</a>
  <a class="vote" href="../rate.html?app={slug}">👍 {('Vote · ' + str(u)) if u else 'Vote'}</a>
</div>
<iframe src="../apps/{slug}.html" title="{E(e['title'])}" allow="clipboard-write; fullscreen; autoplay" allowfullscreen></iframe>
</body>
</html>
""")

# ------------------------------------------------------------------ feed.xml
def rfc822(d):
    y, m, dd = map(int, d.split("-")); return date(y, m, dd).strftime("%a, %d %b %Y 12:00:00 +0000")
feed_items = "".join(f"""
  <item>
    <title>{E(e['title'])} ({E(e['engine'])})</title>
    <link>{SITE}/p/{slug}.html</link>
    <guid isPermaLink="true">{SITE}/p/{slug}.html</guid>
    <pubDate>{rfc822(e['last_updated'])}</pubDate>
    <description>{E(e.get('description') or '')}</description>
  </item>""" for slug, e in items[:50])
(ROOT / "feed.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>trez63 — one small app a day</title>
  <link>{SITE}/</link>
  <description>{SITE_DESC}</description>
  <lastBuildDate>{rfc822(TODAY.isoformat())}</lastBuildDate>{feed_items}
</channel></rss>
""")
print(f"index.html: {len(apps)} apps · {len(list(PDIR.glob('*.html')))} play pages · feed.xml · wins {dict(wins)}")
