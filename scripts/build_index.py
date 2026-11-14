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

ENGINE_CLASS = {"Claude": "claude", "ChatGPT": "chatgpt", "Muse": "muse", "Gemini": "gemini", "Grok": "grok",
                "Llama": "llama", "Mistral": "mistral", "DeepSeek": "deepseek", "Copilot": "copilot"}
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
CAT_LABEL = {"tool": "Tools", "art": "Generative art", "game": "Games", "audio": "Audio", "sim": "Simulations",
             "image": "Image", "finance": "Finance", "dev": "Dev tools", "focus": "Focus", "text": "Text", "edu": "Explainers"}
LIKE_CSS = """
button.like{font:700 11px Arial,Helvetica,sans-serif;display:inline-flex;align-items:center;gap:5px;cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--fg);border-radius:6px;padding:5px 9px;white-space:nowrap;line-height:1}
button.like i{font-style:normal;font-size:13px;line-height:1;color:var(--mute)}
button.like b{font-variant-numeric:tabular-nums;min-width:1ch;text-align:right}
button.like:hover{border-color:var(--acc)}
button.like:hover i{color:var(--acc)}
button.like:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
button.like.on{background:var(--acc-soft,#eef2ff);border-color:var(--acc);color:var(--acc);cursor:default}
button.like.on i{color:var(--acc)}
"""
LIKE_JS = """
(function(){
  // Likes are counted by Abacus (abacus.jasoncameron.dev), one counter per app. No account, no cookies;
  // this browser remembers what it liked in localStorage. Counts baked into the page are the last snapshot.
  const API='https://abacus.jasoncameron.dev', NS='trez63.com';
  const store=(s)=>({get(k){try{return s.getItem(k)}catch(e){return null}},set(k,v){try{s.setItem(k,v)}catch(e){}}});
  const ls=store(window.localStorage), ss=store(window.sessionStorage);
  const btns=[...document.querySelectorAll('button.like')];
  const put=(b,n)=>{ b.dataset.n=n; b.querySelector('b').textContent=n; const c=b.closest('.card'); if(c) c.dataset.likes=n; };
  const raise=(b,n)=>{ if(n>(+b.dataset.n||0)) put(b,n); };
  const mark=(b,on)=>{ b.classList.toggle('on',on); b.setAttribute('aria-pressed',on); b.title=on?'You liked this':'Like this app'; };
  btns.forEach(b=>{
    const slug=b.dataset.slug;
    if(ls.get('liked:'+slug)) mark(b,true);
    b.addEventListener('click',async ev=>{
      ev.preventDefault(); ev.stopPropagation();
      if(b.classList.contains('on')||b.dataset.busy) return;
      const before=+b.dataset.n||0; b.dataset.busy=1; mark(b,true); put(b,before+1);
      try{
        const r=await fetch(API+'/hit/'+NS+'/'+slug); if(!r.ok) throw 0;
        const j=await r.json(); ls.set('liked:'+slug,'1'); raise(b,+j.value||0); ss.set('likes:'+slug,b.dataset.n+'|'+Date.now());
      }catch(e){ mark(b,false); put(b,before); }
      delete b.dataset.busy;
    });
  });
  // Refresh counts for what is on screen, one request every 400ms (the service allows 30 per 10s per visitor).
  const queue=[], seen=new Set();
  const want=b=>{ const slug=b.dataset.slug; if(seen.has(slug)) return; seen.add(slug);
    const c=(ss.get('likes:'+slug)||'').split('|'); if(c[1] && Date.now()-c[1]<600000){ raise(b,+c[0]||0); return; }
    queue.push(b); };
  setInterval(async()=>{ const b=queue.shift(); if(!b) return;
    try{ const r=await fetch(API+'/get/'+NS+'/'+b.dataset.slug); const n=r.ok?(+(await r.json()).value||0):0;
      if(r.ok||r.status===404){ raise(b,n); ss.set('likes:'+b.dataset.slug,b.dataset.n+'|'+Date.now()); } }catch(e){}
  },400);
  if('IntersectionObserver' in window){
    const io=new IntersectionObserver(es=>es.forEach(e=>{ if(e.isIntersecting){ want(e.target); io.unobserve(e.target); } }),{rootMargin:'200px'});
    btns.forEach(b=>io.observe(b));
  } else btns.slice(0,12).forEach(want);
})();
"""
E = html.escape

def fmt(d):
    y, m, dd = map(int, d.split("-")); return date(y, m, dd).strftime("%b %-d, %Y")
def pub(e): return e["first_published"]
def has_preview(slug): return (ROOT / "previews" / f"{slug}.webm").exists()

# ------------------------------------------------------------------ cards
all_engines = sorted({e["engine"] for e in apps.values()})
def shot(slug, e, lazy=True):
    v = f'<video src="previews/{slug}.webm" muted loop playsinline preload="none" poster="thumbs/{slug}.webp"></video>' if has_preview(slug) else ""
    return (f'<a class="shot" href="p/{slug}.html" aria-label="Open {E(e["title"])}">'
            f'<img src="thumbs/{slug}.webp" alt="" {"loading=lazy" if lazy else ""} width="640" height="400">{v}</a>')

def likes(e): return int(e.get("likes") or 0)
def like_btn(slug, e):
    return (f'<button class="like" type="button" data-slug="{slug}" data-n="{likes(e)}" aria-pressed="false" '
            f'title="Like this app" aria-label="Like {E(e["title"])}"><i aria-hidden="true">♥</i><b>{likes(e)}</b></button>')

def card(slug, e, big=False):
    eng = E(e["engine"]); cls = ENGINE_CLASS.get(e["engine"], "other")
    cat = e.get("category", "")
    search = E((e["title"] + " " + (e.get("description") or "") + " " + slug + " " + cat + " " + e["engine"]).lower())
    return f"""
    <article class="card{' big' if big else ''}" data-engine="{eng}" data-cat="{E(cat)}" data-date="{e['last_updated']}" data-likes="{likes(e)}" data-search="{search}">
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
          <span class="acts">{like_btn(slug, e)}</span>
        </div>
      </div>
    </article>"""

items = sorted(apps.items(), key=lambda kv: (kv[1]["last_updated"], pub(kv[1])), reverse=True)
cards = "".join(card(s, e) for s, e in items)
engine_filters = "".join(f'<button data-filter="{E(x)}">{E(x)}</button>' for x in all_engines)
cats_present = sorted({e.get("category") for e in apps.values() if e.get("category")}, key=lambda c: CAT_LABEL.get(c, c))
cat_filters = "".join(f'<button data-cat="{E(c)}">{E(CAT_LABEL.get(c, c))}</button>' for c in cats_present)



CSS = """
:root{--bg:#eff1f5;--panel:#fff;--line:#dce1e9;--fg:#17212d;--mute:#677180;--acc:#244fe5;--acc-fg:#fff;--acc-soft:#eef2ff;--yellow:#e5ff80;--soft:#f6f8fb;--radius:16px;
  --claude:#c25a2c;--chatgpt:#2c816b;--muse:#6b4fe0;--gemini:#244fe5;--grok:#17212d;--llama:#0866ff;--mistral:#d9781a;--deepseek:#4d6bfe;--copilot:#6b4fe0;--other:#677180;color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 Arial,Helvetica,sans-serif;font-synthesis:none;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button{font:inherit}
.shell{max-width:1320px;margin:0 auto;padding:0 44px}
@media (max-width:720px){.shell{padding:0 18px}}
.topbar{height:104px;display:flex;align-items:center;justify-content:space-between;gap:15px;border-bottom:1px solid #d5dbe5}
@media (max-width:720px){.topbar{height:76px}.nav a:not(.new){display:none}.nav a.new{white-space:nowrap}}
.logo{display:flex;align-items:center}
.logo img{height:86px;width:auto;display:block;margin-left:-6px}
@media (max-width:720px){.logo img{height:56px;margin-left:-4px}}
.nav{display:flex;align-items:center;gap:8px}
.nav a{padding:10px 13px;border-radius:7px;font-size:12px;font-weight:700}
.nav a:hover{background:#e2e6ee}
.nav a.new{background:var(--fg);color:#fff}
.privacy{font:10px/1.3 "Courier New",monospace;letter-spacing:.7px;color:var(--mute);display:flex;gap:6px;align-items:center;margin-right:8px}
.privacy::before{content:"";width:6px;height:6px;background:#2c816b;border-radius:50%;flex:none}
@media (max-width:720px){.privacy{display:none}}
.hero{display:flex;align-items:flex-end;justify-content:space-between;gap:25px;padding:36px 0 30px;flex-wrap:wrap}
.eyebrow{font:11px/1.4 "Courier New",monospace;letter-spacing:1.1px;color:var(--acc);text-transform:uppercase;margin-bottom:12px}
h1{font-size:clamp(40px,5.2vw,65px);line-height:.99;letter-spacing:-3.2px;font-weight:800;margin:0;max-width:11ch}
h1 em{font-style:normal;color:var(--acc)}
@media (max-width:720px){h1{letter-spacing:-2px}}
.hero-copy{max-width:300px;font-size:14px;color:var(--mute);line-height:1.65;padding-bottom:2px}
.hero-copy strong{color:var(--fg)}
.cta{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.cta a{padding:10px 13px;border-radius:7px;font-size:12px;font-weight:700;border:1px solid var(--line);background:#fff}
.cta a.p{background:var(--fg);color:#fff;border-color:var(--fg)}
.cta a:hover{filter:brightness(.97)}
.lede{display:none}
.decision{display:flex;align-items:center;gap:20px;padding:18px 23px;background:var(--fg);color:#fff;border-radius:12px;margin-bottom:17px;flex-wrap:wrap}
.decision label{font:10px/1.5 "Courier New",monospace;letter-spacing:1.1px;flex:none;color:#c0c9d7}
.decision .q{flex:1;min-width:200px;font-size:19px;font-weight:600;letter-spacing:-.4px;line-height:1.3}
.decision .example-tag{font-size:10px;background:var(--yellow);color:var(--fg);padding:7px 10px;border-radius:5px;white-space:nowrap;font-weight:700}
.prompt{border:0;background:none;max-width:none;margin:0 0 17px}
.prompt summary{cursor:pointer;list-style:none;display:block}
.prompt summary::-webkit-details-marker{display:none}
.prompt summary .decision{margin:0}
.prompt[open] summary .decision{border-radius:12px 12px 0 0}
.prompt-body{background:#fff;border:1px solid var(--line);border-top:0;border-radius:0 0 12px 12px;padding:18px 23px 20px;color:var(--mute);font-size:14px;line-height:1.65}
.prompt-body blockquote{margin:10px 0;padding:2px 0 2px 14px;border-left:3px solid var(--acc);color:var(--fg)}
.prompt-body blockquote p{margin:8px 0}
.prompt-body .small{font-size:12px;margin:8px 0 0}
.prompt-body a{text-decoration:underline}
.board{background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;margin-bottom:17px}
.board-top{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:20px 23px 17px;flex-wrap:wrap}
.board-title{font-size:14px;font-weight:700;display:flex;gap:11px;align-items:center;margin:0}
.step-tag{font:11px "Courier New",monospace;color:var(--acc);background:var(--acc-soft);border-radius:4px;padding:5px 7px;letter-spacing:.5px}
.board-note{font-size:12px;color:var(--mute)}
.board-note .example-tag{font-size:10px;background:var(--yellow);color:var(--fg);padding:5px 8px;border-radius:5px;font-weight:700;margin-left:8px}
.board-body{padding:0 23px 23px}
.mgrid,main{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(290px,1fr))}
.mgrid{grid-template-columns:repeat(auto-fit,minmax(215px,1fr))}
.card{background:var(--soft);border:1px solid var(--line);border-radius:12px;overflow:visible;display:flex;flex-direction:column;position:relative}
.card[hidden]{display:none}
.shot{display:block;aspect-ratio:16/10;background:#000;overflow:hidden;position:relative;border-radius:12px 12px 0 0;border-bottom:1px solid var(--line)}
.shot img,.shot video{width:100%;height:100%;object-fit:cover;display:block}
.shot video{position:absolute;inset:0;opacity:0;transition:opacity .25s}
.card:hover .shot video.ready{opacity:1}
.body{padding:13px 15px 15px;display:flex;flex-direction:column;gap:6px;flex:1}
.row{display:flex;align-items:center;justify-content:space-between;gap:10px}
h2{margin:0}
.card h2{font-size:16px;letter-spacing:-.3px;font-weight:700}
.badge{font:10px "Courier New",monospace;letter-spacing:.8px;text-transform:uppercase;padding:4px 7px;border-radius:4px;color:#fff;white-space:nowrap}
.badge.claude{background:var(--claude)}.badge.chatgpt{background:var(--chatgpt)}.badge.muse{background:var(--muse)}.badge.gemini{background:var(--gemini)}.badge.grok{background:var(--grok)}.badge.llama{background:var(--llama)}.badge.mistral{background:var(--mistral)}.badge.deepseek{background:var(--deepseek)}.badge.copilot{background:var(--copilot)}.badge.other{background:var(--other)}
.body p{margin:0;color:var(--mute);font-size:13px;flex:1;line-height:1.55}
.meta{display:flex;flex-wrap:wrap;gap:6px;font:11px "Courier New",monospace;color:var(--mute);align-items:center;letter-spacing:.3px}
.meta a{text-decoration:underline dotted}
.meta .acts{margin-left:auto}
.sort{margin-left:auto}
.toolbar{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;padding:0 23px 14px}
#q{font:inherit;font-size:14px;padding:10px 13px;border-radius:7px;border:1px solid var(--line);background:#fff;color:var(--fg);width:min(100%,320px);outline:none}
#q:focus-visible{outline:3px solid var(--acc);outline-offset:3px}
.filters{display:flex;flex-wrap:wrap;gap:7px}
.filters button{padding:9px 12px;border-radius:6px;border:1px solid var(--line);background:#fff;color:var(--fg);cursor:pointer;font-size:11px;font-weight:700}
.filters button:hover{background:#e2e6ee}
.filters button[aria-pressed=true]{background:var(--fg);color:#fff;border-color:var(--fg)}
.cats{padding:0 23px 20px}
.cats button{font:11px "Courier New",monospace;letter-spacing:.5px;background:var(--soft)}
.cats button[aria-pressed=true]{background:var(--acc-soft);color:var(--acc);border-color:var(--acc)}
#empty{padding:0 23px 20px;color:var(--mute);font-size:13px;margin:0}
main{padding:0 23px 23px}
footer{padding:10px 0 48px;color:var(--mute);font:11px "Courier New",monospace;letter-spacing:.5px}
footer a{text-decoration:underline}
"""

JS = """
const q=document.getElementById('q'), grid=document.getElementById('grid'), cards=[...grid.querySelectorAll('.card')], empty=document.getElementById('empty');
let engine='all', cat='all';
function apply(){
  const terms=q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
  let shown=0;
  cards.forEach(c=>{
    const ok=(engine==='all'||c.dataset.engine===engine)&&(cat==='all'||c.dataset.cat===cat)&&terms.every(t=>c.dataset.search.includes(t));
    c.hidden=!ok; if(ok) shown++;
  });
  empty.hidden=shown>0;
}
function press(group,b){ group.forEach(x=>x.setAttribute('aria-pressed',x===b)); }
const eng=[...document.querySelectorAll('.engines button')], cts=[...document.querySelectorAll('.cats button')];
eng.forEach(b=>b.addEventListener('click',()=>{engine=b.dataset.filter;press(eng,b);apply();}));
cts.forEach(b=>b.addEventListener('click',()=>{cat=(cat===b.dataset.cat?'all':b.dataset.cat);press(cts,cat==='all'?null:b);apply();}));
const srt=[...document.querySelectorAll('.sort button')];
srt.forEach(b=>b.addEventListener('click',()=>{
  press(srt,b);
  const byDate=(a,c)=>c.dataset.date.localeCompare(a.dataset.date);
  const by=b.dataset.sort==='top' ? (a,c)=>(+c.dataset.likes-(+a.dataset.likes))||byDate(a,c) : byDate;
  [...cards].sort(by).forEach(c=>grid.appendChild(c));
}));
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
    <summary><div class="decision"><label>THE PROMPT</label><span class="q">Every model gets the same brief. Click to read it.</span><span class="example-tag">SAME FOR ALL</span></div></summary>
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
n_eng = len(all_engines)
eng_list = (", ".join(all_engines[:-1]) + " and " + all_engines[-1]) if n_eng > 1 else (all_engines[0] if all_engines else "AI models")
n_word = WORDS.get(n_eng, str(n_eng))
SITE_DESC = f"Every day {eng_list} each build a single-page app from the same one-line prompt. Play them all."
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>trez63 — one small app a day</title>
<meta name="description" content="{SITE_DESC}">
<link rel="canonical" href="{SITE}/">
<link rel="alternate" type="application/rss+xml" title="trez63 — new apps" href="{SITE}/feed.xml">
<link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="64x64" href="assets/favicon-64.png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
{og("trez63 — one small app a day", SITE_DESC, f"{SITE}/assets/og.png", SITE + "/")}
<style>{CSS}{LIKE_CSS}</style>
</head>
<body>
<div class="shell">
<div class="topbar">
  <a class="logo" href="./"><img src="assets/logo.png" alt="trez63.com" width="{int(400*1175/783)}" height="400"></a>
  <nav class="nav">
    <span class="privacy">RUNS IN YOUR BROWSER · NOTHING UPLOADED</span>
    <a href="#prompt">The prompt</a>
    <a href="feed.xml">RSS</a>
    <a class="new" href="#all">Browse apps</a>
  </nav>
</div>
<header class="hero">
  <div>
    <div class="eyebrow">{n_word} models · one prompt · every day</div>
    <h1>One small app <em>a day.</em></h1>
  </div>
  <p class="hero-copy"><strong>{eng_list}</strong> each build a single-page app from the same one-line brief. They land here untouched. Click any card and play.</p>
</header>
{PROMPT}
<section class="board all" id="all">
  <div class="board-top">
    <h2 class="board-title">All apps <span class="board-note">{len(apps)}</span></h2>
  </div>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search apps…" aria-label="Search apps by title or description" autocomplete="off">
    <div class="filters engines" role="group" aria-label="Filter by model">
      <button data-filter="all" aria-pressed="true">All</button>{engine_filters}
    </div>
    <div class="filters sort" role="group" aria-label="Sort">
      <button data-sort="new" aria-pressed="true">Newest</button><button data-sort="top">Most liked</button>
    </div>
  </div>
  <div class="filters cats" role="group" aria-label="Filter by category">{cat_filters}</div>
  <p id="empty" hidden>No apps match that.</p>
  <main id="grid">{cards}
  </main>
</section>
<footer>SOURCE AND FULL VERSION HISTORY ON <a href="{REPO}">GITHUB</a> · <a href="feed.xml">RSS</a> · LAST PUBLISHED {fmt(catalog.get('generated', TODAY.isoformat())).upper()}</footer>
</div>
<script>{JS}{LIKE_JS}</script>
</body>
</html>
"""
(ROOT / "index.html").write_text(page)

# ------------------------------------------------------------------ play pages: p/<slug>.html
PDIR = ROOT / "p"; PDIR.mkdir(exist_ok=True)
for old in PDIR.glob("*.html"):
    if old.stem not in apps: old.unlink()
for slug, e in apps.items():
    eng = E(e["engine"]); cls = ENGINE_CLASS.get(e["engine"], "other")
    desc = e.get("description") or ""
    (PDIR / f"{slug}.html").write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(e['title'])} — trez63</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{SITE}/p/{slug}.html">
<link rel="icon" type="image/png" sizes="32x32" href="../assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="64x64" href="../assets/favicon-64.png">
<link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
{og(e['title'] + ' — built by ' + e['engine'], desc, f"{SITE}/thumbs/{slug}.webp", f"{SITE}/p/{slug}.html")}
<style>
:root{{--bg:#eff1f5;--panel:#fff;--line:#dce1e9;--fg:#17212d;--mute:#677180;--acc:#244fe5;--acc-fg:#fff;--yellow:#e5ff80;--claude:#c25a2c;--chatgpt:#2c816b;--muse:#6b4fe0;--gemini:#244fe5;--grok:#17212d;--llama:#0866ff;--mistral:#d9781a;--deepseek:#4d6bfe;--copilot:#6b4fe0;--other:#677180;color-scheme:light}}
*{{box-sizing:border-box}}html,body{{height:100%;margin:0}}
body{{display:flex;flex-direction:column;background:var(--bg);color:var(--fg);font:13px Arial,Helvetica,sans-serif}}
.bar{{display:flex;align-items:center;gap:12px;padding:0 16px;height:52px;background:var(--panel);border-bottom:1px solid #d5dbe5;flex:none}}
.bar a{{color:inherit;text-decoration:none}}
.back{{color:var(--mute)}} .back:hover{{color:var(--fg)}}
.title{{font-weight:800;font-size:16px;letter-spacing:-.4px}}
.badge{{font:10px "Courier New",monospace;letter-spacing:.8px;text-transform:uppercase;padding:4px 7px;border-radius:4px;color:#fff}}
.badge.claude{{background:var(--claude)}}.badge.chatgpt{{background:var(--chatgpt)}}.badge.muse{{background:var(--muse)}}.badge.gemini{{background:var(--gemini)}}.badge.grok{{background:var(--grok)}}.badge.llama{{background:var(--llama)}}.badge.mistral{{background:var(--mistral)}}.badge.deepseek{{background:var(--deepseek)}}.badge.copilot{{background:var(--copilot)}}.badge.other{{background:var(--other)}}
.desc{{color:var(--mute);overflow:hidden;white-space:nowrap;text-overflow:ellipsis;flex:1;min-width:0}}
.raw{{color:var(--mute);white-space:nowrap;font:11px "Courier New",monospace;letter-spacing:.5px}} .raw:hover{{color:var(--fg)}}
.back img{{height:36px;width:auto;display:block}}
iframe{{flex:1;border:0;width:100%;background:#fff}}
@media (max-width:640px){{.desc,.raw{{display:none}}}}
{LIKE_CSS}
</style>
</head>
<body>
<div class="bar">
  <a class="back" href="../" title="All apps"><img src="../assets/mark-192.png" alt="trez63" width="192" height="192"></a>
  <span class="title">{E(e['title'])}</span>
  <span class="badge {cls}">{eng}</span>
  <span class="desc">{E(desc)}</span>
  <a class="raw" href="../apps/{slug}.html" title="Open the app on its own, full window">open raw ↗</a>
  {like_btn(slug, e)}
</div>
<iframe src="../apps/{slug}.html" title="{E(e['title'])}" allow="clipboard-write; fullscreen; autoplay" allowfullscreen></iframe>
<script>{LIKE_JS}</script>
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
print(f"index.html: {len(apps)} apps · {len(list(PDIR.glob('*.html')))} play pages · feed.xml")
