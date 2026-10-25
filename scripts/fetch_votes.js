// Run this in a browser tab whose origin is https://giscus.app (any page there, e.g. the API URL itself),
// so the fetches are same-origin and not blocked by CORS. It returns a JSON string:
//   {"<slug>": {"up": 3, "reactions": 5, "comments": 1, "url": "https://github.com/..."}, ...}
// Slugs with no discussion yet (nobody has voted) are omitted.
// Usage from the daily task: paste the slug list in, run via the browser javascript tool, save the result,
// then:  python3 scripts/apply_votes.py votes.json
(async (slugs) => {
  const out = {};
  for (const slug of slugs) {
    const u = `https://giscus.app/api/discussions?repo=trez63%2Ftrez63.com&term=${encodeURIComponent('app:' + slug)}&category=App%20votes&strict=1&first=1`;
    try {
      const r = await fetch(u);
      if (!r.ok) continue;                       // 404 = no discussion yet
      const j = await r.json();
      const d = j.discussion || j;
      const rx = d.reactions || {};
      out[slug] = {
        up: (rx.THUMBS_UP && rx.THUMBS_UP.count) || 0,
        reactions: d.reactionCount || 0,
        comments: d.totalCommentCount || 0,
        url: d.url || null,
      };
    } catch (e) { /* skip */ }
    await new Promise(r => setTimeout(r, 150));  // be polite
  }
  return JSON.stringify(out);
})(SLUGS)
