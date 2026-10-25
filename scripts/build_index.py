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
SHARE_CSS = """
.share{position:relative}
.share>button{font:inherit;font-weight:700;font-size:12px;cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--fg);border-radius:7px;padding:9px 12px;white-space:nowrap}
.share>button:hover{background:#e2e6ee}
.share menu{position:absolute;right:0;top:calc(100% + 6px);z-index:20;margin:0;padding:6px;list-style:none;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 14px 40px rgba(23,33,45,.18);min-width:180px;display:none}
.share[open] menu{display:block}
.share menu a,.share menu button{display:block;width:100%;text-align:left;font:inherit;font-size:13px;background:none;border:0;color:var(--fg);padding:8px 10px;border-radius:7px;cursor:pointer;text-decoration:none}
.share menu a:hover,.share menu button:hover{background:#eef2ff}
"""
SHARE_JS = """
(function(){
  function wire(el){
    const url=el.dataset.url, title=el.dataset.title, text=el.dataset.text||title;
    const btn=el.querySelector('button.sb'), menu=el.querySelector('menu'), enc=encodeURIComponent;
    menu.innerHTML=`<li><button class="copy">Copy link</button></li>
      <li><a target="_blank" rel="noopener" href="https://x.com/intent/post?text=${enc(text)}&url=${enc(url)}">Post on X</a></li>
      <li><a target="_blank" rel="noopener" href="https://www.linkedin.com/sharing/share-offsite/?url=${enc(url)}">Share on LinkedIn</a></li>
      <li><a target="_blank" rel="noopener" href="https://www.reddit.com/submit?url=${enc(url)}&title=${enc(title)}">Post on Reddit</a></li>
      <li><a target="_blank" rel="noopener" href="https://bsky.app/intent/compose?text=${enc(text+' '+url)}">Post on Bluesky</a></li>
      <li><a href="mailto:?subject=${enc(title)}&body=${enc(text)}%0A${enc(url)}">Email</a></li>`;
    btn.addEventListener('click',async e=>{
      e.preventDefault(); e.stopPropagation();
      if(navigator.share){ try{ await navigator.share({title,text,url}); return; }catch(_){ if(_.name==='AbortError') return; } }
      document.querySelectorAll('.share[open]').forEach(o=>{ if(o!==el) o.removeAttribute('open'); });
      el.toggleAttribute('open');
    });
    menu.querySelector('.copy').addEventListener('click',async()=>{
      try{ await navigator.clipboard.writeText(url); btn.textContent='Copied ✓'; setTimeout(()=>btn.textContent='Share',1500); }catch(_){ prompt('Copy this link:',url); }
      el.removeAttribute('open');
    });
  }
  document.querySelectorAll('.share').forEach(wire);
  document.addEventListener('click',e=>{ if(!e.target.closest('.share')) document.querySelectorAll('.share[open]').forEach(o=>o.removeAttribute('open')); });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape') document.querySelectorAll('.share[open]').forEach(o=>o.removeAttribute('open')); });
})();
"""
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

def share_el(slug, e, cls="share"):
    url = f"{SITE}/p/{slug}.html"
    text = f"{e['title']} — a one-page app built by {e['engine']} from a single prompt. Play it, vote for it:"
    return (f'<span class="{cls}" data-url="{url}" data-title="{E(e["title"])} — trez63" data-text="{E(text)}">'
            f'<button class="sb" type="button" aria-haspopup="menu">Share</button><menu></menu></span>')

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
          <span class="acts"><a class="rate" href="rate.html?app={slug}" title="Vote for this app">👍 {u if u else 'Vote'}</a>{share_el(slug, e, "share mini")}</span>
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
<section class="board matchup" id="matchup" aria-label="Latest matchup">
  <div class="board-top">
    <h2 class="board-title"><span class="step-tag">01</span>Latest matchup <span class="board-note">{fmt(matchup_date)}</span></h2>
    <span class="board-note">{status}{' · ' + str(lead) + ' votes leads' if lead else ''}{'' if matchup_locked else '<span class="example-tag">VOTING OPEN</span>'}</span>
  </div>
  <div class="board-body"><div class="mgrid">{cols}</div></div>
</section>"""

rows = "".join(
    f'<tr><td><span class="badge {ENGINE_CLASS.get(en, "other")}">{E(en)}</span></td>'
    f'<td class="num">{wins[en]:g}</td><td class="num">{totals[en]}</td><td class="num">{counts[en]}</td></tr>'
    for en in board)
score_html = f"""
<section class="board score" aria-label="Scoreboard">
  <div class="board-top">
    <h2 class="board-title"><span class="step-tag">02</span>Scoreboard</h2>
    <span class="board-note">{rounds_locked} round{'s' if rounds_locked != 1 else ''} decided · a day's winner is the app with the most 👍 {WIN_AFTER_DAYS} days after it ships; ties split</span>
  </div>
  <table><thead><tr><th>Model</th><th class="num">Wins</th><th class="num">Total 👍</th><th class="num">Apps</th></tr></thead><tbody>{rows}</tbody></table>
</section>"""

CSS = """
:root{--bg:#eff1f5;--panel:#fff;--line:#dce1e9;--fg:#17212d;--mute:#677180;--acc:#244fe5;--acc-fg:#fff;--acc-soft:#eef2ff;--yellow:#e5ff80;--soft:#f6f8fb;--radius:16px;
  --claude:#c25a2c;--chatgpt:#2c816b;--muse:#6b4fe0;--gemini:#244fe5;--grok:#17212d;--llama:#0866ff;--mistral:#d9781a;--deepseek:#4d6bfe;--copilot:#6b4fe0;--other:#677180;color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 Arial,Helvetica,sans-serif;font-synthesis:none;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button{font:inherit}
.shell{max-width:1320px;margin:0 auto;padding:0 44px}
@media (max-width:720px){.shell{padding:0 18px}}
.topbar{height:88px;display:flex;align-items:center;justify-content:space-between;gap:15px;border-bottom:1px solid #d5dbe5}
.logo{display:flex;align-items:center;gap:10px;font-size:25px;font-weight:800;letter-spacing:-1.1px}
.logo i{width:27px;height:27px;border-radius:7px;background:var(--acc);display:inline-block;position:relative}
.logo i::after{content:"";position:absolute;inset:8px;border-radius:3px;background:var(--yellow)}
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
.mgrid{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.card{background:var(--soft);border:1px solid var(--line);border-radius:12px;overflow:visible;display:flex;flex-direction:column;position:relative}
.card[hidden]{display:none}
.card:has(.share[open]){z-index:30}
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
.meta .acts{margin-left:auto;display:flex;gap:6px;align-items:center}
.meta .rate{text-decoration:none;background:var(--fg);color:#fff;font:700 11px Arial,Helvetica,sans-serif;padding:6px 10px;border-radius:6px}
.meta .rate:hover{filter:brightness(1.15)}
.card .share menu{top:auto;bottom:calc(100% + 6px)}
.share.mini>button{font-size:11px;font-weight:700;padding:5px 10px;border-radius:6px;border:1px solid var(--line);background:#fff}
.score table{border-collapse:separate;border-spacing:0;width:100%;max-width:560px}
.score th,.score td{padding:11px 23px;text-align:left;border-top:1px solid var(--line);font-size:14px}
.score th{font:11px "Courier New",monospace;letter-spacing:1px;text-transform:uppercase;color:var(--mute);border-top:0;padding-top:0}
.score .num{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
.toolbar{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;padding:0 23px 14px}
#q{font:inherit;font-size:14px;padding:10px 13px;border-radius:7px;border:1px solid var(--line);background:#fff;color:var(--fg);width:min(100%,320px);outline:none}
#q:focus-visible{outline:3px solid var(--acc);outline-offset:3px}
.filters{display:flex;flex-wrap:wrap;gap:7px}
.filters button{padding:9px 12px;border-radius:6px;border:1px solid var(--line);background:#fff;color:var(--fg);cursor:pointer;font-size:11px;font-weight:700}
.filters button:hover{background:#e2e6ee}
.filters button[aria-pressed=true]{background:var(--fg);color:#fff;border-color:var(--fg)}
.sort{margin-left:auto}
.sort button[aria-pressed=true]{background:var(--acc);border-color:var(--acc);color:#fff}
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
SITE_DESC = f"Every day {eng_list} each build a single-page app from the same one-line prompt. Play them, vote for the winner."
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
<style>{CSS}{SHARE_CSS}</style>
</head>
<body>
<div class="shell">
<div class="topbar">
  <a class="logo" href="./"><i></i>trez63</a>
  <nav class="nav">
    <span class="privacy">RUNS IN YOUR BROWSER · NOTHING UPLOADED</span>
    <a href="#prompt">The prompt</a>
    <a href="feed.xml">RSS</a>
    <a class="new" href="#matchup">Play today's {n_word}</a>
  </nav>
</div>
<header class="hero">
  <div>
    <div class="eyebrow">{n_word} models · one prompt · every day</div>
    <h1>One small app <em>a day.</em></h1>
  </div>
  <p class="hero-copy"><strong>{eng_list}</strong> each build a single-page app from the same one-line brief. They land here untouched. Play them, then vote for the one that should win.</p>
</header>
{PROMPT}
{matchup_html}
{score_html}
<section class="board all">
  <div class="board-top">
    <h2 class="board-title"><span class="step-tag">03</span>All apps <span class="board-note">{len(apps)}</span></h2>
  </div>
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
  <p id="empty" hidden>No apps match that.</p>
  <main id="grid">{cards}
  </main>
</section>
<footer>SOURCE AND FULL VERSION HISTORY ON <a href="{REPO}">GITHUB</a> · <a href="feed.xml">RSS</a> · LAST PUBLISHED {fmt(catalog.get('generated', TODAY.isoformat())).upper()}</footer>
</div>
<script>{JS}{SHARE_JS}</script>
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
.vote{{background:var(--fg);color:#fff!important;font-weight:700;font-size:12px;padding:9px 13px;border-radius:7px;white-space:nowrap}}
.vote:hover{{filter:brightness(1.15)}}
.raw{{color:var(--mute);white-space:nowrap;font:11px "Courier New",monospace;letter-spacing:.5px}} .raw:hover{{color:var(--fg)}}
.back{{font-weight:800;font-size:15px;letter-spacing:-.6px;color:var(--fg)!important}}
iframe{{flex:1;border:0;width:100%;background:#fff}}
@media (max-width:640px){{.desc,.raw{{display:none}}}}
{SHARE_CSS}
</style>
</head>
<body>
<div class="bar">
  <a class="back" href="../">← trez63</a>
  <span class="title">{E(e['title'])}</span>
  <span class="badge {cls}">{eng}</span>
  <span class="desc">{E(desc)}</span>
  <a class="raw" href="../apps/{slug}.html" title="Open the app on its own, full window">open raw ↗</a>
  {share_el(slug, e)}
  <a class="vote" href="../rate.html?app={slug}">👍 {('Vote · ' + str(u)) if u else 'Vote'}</a>
</div>
<iframe src="../apps/{slug}.html" title="{E(e['title'])}" allow="clipboard-write; fullscreen; autoplay" allowfullscreen></iframe>
<script>{SHARE_JS}</script>
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
