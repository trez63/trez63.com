// Snapshot of like counts from Abacus (https://abacus.jasoncameron.dev), namespace "trez63.com", one counter per app slug.
// Run in any browser tab (the API allows CORS). Replace SLUGS with an array of at most 60 slugs per run:
// the service allows 30 requests per 10 seconds per visitor, so this paces itself at one request every 400ms.
// Returns a JSON string {slug: count}. A slug nobody has liked yet has no counter (404) and is reported as 0.
// A slug whose request failed is left out, so apply_likes.py keeps its previous number.
(async (slugs) => {
  const out = {};
  for (const slug of slugs) {
    try {
      const r = await fetch('https://abacus.jasoncameron.dev/get/trez63.com/' + slug);
      if (r.ok) out[slug] = +(await r.json()).value || 0;
      else if (r.status === 404) out[slug] = 0;
    } catch (e) { /* left out */ }
    await new Promise(r => setTimeout(r, 400));
  }
  return JSON.stringify(out);
})(SLUGS)
