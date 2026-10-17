// Browser-side OpenAlex works fetch. Runs on an api.openalex.org tab (same-origin fetch).
// __IDS__ is replaced with a JSON array of OpenAlex author IDs (A...).
// Results accumulate in window.__works (keyed by work id) and are downloaded as JSON chunks.
window.__IDS = __IDS__;
window.__wprog = {pages: 0, got: 0, err: [], finished: false, groups_done: 0};
window.__works = window.__works || {};
const wsleep = ms => new Promise(r => setTimeout(r, ms));
async function wget(url) {
  for (let t = 0; t < 4; t++) {
    try {
      const r = await fetch(url + (url.includes('?') ? '&' : '?') + 'mailto=kosa@berkeley.edu');
      if (r.status === 429) { window.__wprog.err.push('429'); window.__wprog.rate_limited = true; return null; }
      if (r.status >= 500) { await wsleep(2000 * (t + 1)); continue; }
      if (!r.ok) { window.__wprog.err.push(r.status + ' ' + url.slice(0, 100)); return null; }
      return await r.json();
    } catch (e) { await wsleep(1500 * (t + 1)); }
  }
  window.__wprog.err.push('fail ' + url.slice(0, 100));
  return null;
}
const WSEL = 'select=id,doi,title,publication_year,publication_date,type,cited_by_count,authorships,primary_location,topics,abstract_inverted_index,is_retracted,is_paratext,language,fwci,referenced_works_count,keywords';
function slimWork(w) {
  // keep only what the pipeline needs; abstract reconstructed later in python
  return {
    id: w.id.split('/').pop(), doi: w.doi, title: w.title, year: w.publication_year, date: w.publication_date,
    type: w.type, cited: w.cited_by_count, retracted: w.is_retracted, paratext: w.is_paratext, lang: w.language,
    fwci: w.fwci, nref: w.referenced_works_count,
    venue: w.primary_location && w.primary_location.source ? w.primary_location.source.display_name : null,
    venue_type: w.primary_location && w.primary_location.source ? w.primary_location.source.type : null,
    topics: (w.topics || []).slice(0, 3).map(t => [t.id.split('/').pop(), t.display_name, t.score, t.subfield && t.subfield.display_name, t.field && t.field.display_name]),
    keywords: (w.keywords || []).slice(0, 6).map(k => k.display_name),
    authors: (w.authorships || []).map(a => ({
      id: a.author && a.author.id ? a.author.id.split('/').pop() : null,
      name: a.author ? a.author.display_name : null,
      pos: a.author_position,
      inst: (a.institutions || []).map(i => i.id ? i.id.split('/').pop() : null).filter(Boolean),
      inst_names: (a.institutions || []).slice(0, 3).map(i => i.display_name),
    })),
    aii: w.abstract_inverted_index || null,
  };
}
(async () => {
  const ids = window.__IDS.slice();
  const groups = [];
  while (ids.length) groups.push(ids.splice(0, 40));
  for (const g of groups) {
    let cursor = '*';
    while (cursor) {
      if (window.__wprog.rate_limited) { window.__wprog.finished = 'rate_limited'; return; }
      const url = 'https://api.openalex.org/works?filter=authorships.author.id:' + g.join('|') + '&per_page=200&cursor=' + encodeURIComponent(cursor) + '&' + WSEL;
      const j = await wget(url);
      if (!j) { cursor = null; break; }
      for (const w of j.results) { window.__works[w.id] = slimWork(w); }
      window.__wprog.pages++; window.__wprog.got = Object.keys(window.__works).length;
      cursor = j.meta.next_cursor;
      if (j.results.length === 0) cursor = null;
    }
    window.__wprog.groups_done++;
  }
  window.__wprog.finished = true;
})();
'works job started';
