#!/usr/bin/env python3
"""
Project an external researcher into the department map.

Fetches their works from OpenAlex, embeds them locally with the same SPECTER2 model, builds a
career vector with the same weighting, and reports nearest faculty, best-matching research
areas and a position in the UMAP / PCA faculty layouts. Added researchers are written to
output/external.json, which the explorer draws as dashed nodes.

Usage
  export OPENALEX_API_KEY=... OPENALEX_MAILTO=you@berkeley.edu
  python3 pipeline/add_researcher.py A5012345678 [A5... ...]
  python3 pipeline/add_researcher.py --remove A5012345678
  python3 pipeline/add_researcher.py --list
"""
import json, os, pickle, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
DATA, OUT = ROOT / "data", ROOT / "output"
EXT = OUT / "external.json"


def main():
    args = sys.argv[1:]
    ext = json.load(open(EXT)) if EXT.exists() else []
    if not args or args[0] == "--list":
        for e in ext:
            print(e["id"], e["name"], e["n_works"], "nearest:", ", ".join(n[0] for n in e["neighbors"][:3]))
        return
    if args[0] == "--remove":
        ext = [e for e in ext if e["id"] not in args[1:]]
        json.dump(ext, open(EXT, "w"), indent=1); return

    from fetch_openalex import get, slim_work, ASEL, WSEL
    from embed_papers import load_model, embed_batch, paper_text
    from build_corpus import reconstruct_abstract, clean_abstract, DROP_TYPES
    tok, model = load_model(ROOT.parent / "models" if (ROOT.parent / "models").exists() else ROOT / "models")
    D = json.load(open(OUT / "explorer_data.json"))
    fv = np.load(DATA / "faculty_vectors.npz")
    career, have = fv["career"], fv["have"]
    lay = pickle.load(open(DATA / "models" / "layouts.pkl", "rb"))
    F = D["faculty"]
    for aid in args:
        a = get(f"/authors/{aid}", select=ASEL)
        works, cursor = [], "*"
        while cursor:
            j = get("/works", filter=f"authorships.author.id:{aid}", per_page=200, cursor=cursor, select=WSEL)
            works += [slim_work(w) for w in j["results"]]
            cursor = j["meta"].get("next_cursor") if j["results"] else None
        recs = []
        for w in works:
            if w.get("paratext") or w.get("retracted") or (w.get("type") in DROP_TYPES):
                continue
            abstract = clean_abstract(w.get("abstract_text") or "")
            if not (w.get("title") or abstract):
                continue
            recs.append({"id": w["id"], "title": w.get("title") or "", "abstract": abstract, "cited": w.get("cited") or 0, "year": w.get("year")})
        texts = [paper_text(r, tok.sep_token)[0] for r in recs]
        E = np.vstack([embed_batch(tok, model, texts[i:i + 16], 512) for i in range(0, len(texts), 16)]) if texts else np.zeros((0, 768))
        wts = np.log(2.0 + np.array([r["cited"] for r in recs], float)); v = (E * (wts / wts.sum())[:, None]).sum(0); v /= np.linalg.norm(v)
        sims = career @ v; sims[~have] = -9
        order = np.argsort(-sims)[:8]
        pairs = np.sort(np.array(D["similarity"])[np.triu_indices(len(F), 1)])
        nb = [[F[j]["name"], round(float(sims[j]), 4), round(float(np.searchsorted(pairs, sims[j]) / len(pairs)), 3)] for j in order]
        umap_xy = lay["umap_faculty"].transform(v[None])[0].tolist()
        pca_xy = lay["pca_faculty"].transform(v[None])[0][:2].tolist()
        entry = {"id": aid, "name": a["display_name"], "n_works": len(recs), "cited": a.get("cited_by_count"), "h_index": (a.get("summary_stats") or {}).get("h_index"),
                 "institutions": [i["display_name"] for i in a.get("last_known_institutions") or []], "topics": [t["display_name"] for t in (a.get("topics") or [])[:6]],
                 "umap": umap_xy, "pca": pca_xy, "neighbors": nb, "vector": [round(float(x), 5) for x in v]}
        ext = [e for e in ext if e["id"] != aid] + [entry]
        print(f"{a['display_name']}: {len(recs)} works; nearest faculty: " + ", ".join(f"{n[0]} ({n[2]*100:.0f}th pct)" for n in nb[:5]))
    json.dump(ext, open(EXT, "w"), indent=1)
    print(f"wrote {EXT}")


if __name__ == "__main__":
    main()
