#!/usr/bin/env python3
"""
Attribution audit: find papers that probably do not belong to the faculty member they are
assigned to (OpenAlex disambiguation errors), using three independent signals.

  1. Timeline: papers published long before the person's career start
     (career start = first year with >=3 papers in a 3-year window; flag if year < start - 5).
  2. Embedding outliers (informational): 2-means split of the person's papers in centred SPECTER2 space;
     a minority sub-cluster whose centroid is far from the majority centroid (cosine < 0.15)
     and whose papers rarely carry a plausible affiliation is flagged.
  3. Field mismatch: OpenAlex top-level field of the paper's primary topic is far from the
     person's dominant fields (e.g. 'Medicine' for a mechanician) AND the person's authorship
     has no Berkeley/LBL affiliation on that paper AND the paper is among the 5% least similar
     to the person's own centroid (leave-one-out, centred SPECTER2 space). Requiring all three
     keeps genuine interdisciplinary work (bone fracture, biological control, kidney stones).

Writes data/audit_attribution.json and prints a summary. With --apply, removes papers that
fail rule 1 (year < start - 8) or rule 3 (field mismatch with no plausible affiliation) from
data/works.jsonl / faculty.json and records the drops in the audit file.
"""
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ENG_FIELDS = {"Engineering", "Physics and Astronomy", "Materials Science", "Computer Science", "Mathematics", "Chemical Engineering", "Energy", "Chemistry", "Earth and Planetary Sciences", "Environmental Science", "Decision Sciences", "Multidisciplinary"}
PLAUSIBLE = ["berkeley", "university of california system", "lawrence berkeley", "lawrence livermore", "sandia"]


def l2(x):
    return x / np.clip(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12, None)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); args = ap.parse_args()
    works = [json.loads(l) for l in open(DATA / "works.jsonl") if l.strip()]
    faculty = json.load(open(DATA / "faculty.json"))
    amap = json.load(open(DATA / "raw" / "author_map.json"))
    idx = json.load(open(DATA / "paper_index.json"))
    emb_path = DATA / "paper_embeddings.npy"
    if not emb_path.exists():
        emb_path = DATA / "paper_embeddings_f16.npy"
    emb = np.load(emb_path).astype(np.float32)
    row = {pid: i for i, pid in enumerate(idx["ids"])}
    mu = emb.mean(0); Pc = l2(emb - mu)
    wid = {w["id"]: w for w in works}
    report = {}; drops = defaultdict(set)
    for f in faculty:
        ids = set(amap.get(f["slug"], {}).get("ids", []))
        ws = [wid[p] for p in f["works"] if p in wid]
        if len(ws) < 5:
            continue
        years = sorted(w["year"] for w in ws if w["year"])
        yc = Counter(years)
        start = None
        for y in range(min(years), max(years) + 1):
            if sum(yc.get(y + k, 0) for k in range(3)) >= 3:
                start = y; break
        early = [w for w in ws if w["year"] and start and w["year"] < start - 5]
        # field profile
        fields = Counter(t[4] for w in ws for t in w["topics"][:1] if t[4])
        dom_fields = {k for k, _ in fields.most_common(3)}
        def plausible(w):
            for a in w["authors"]:
                if a["id"] in ids:
                    names = " ".join(a.get("inst_names", []) if "inst_names" in a else []).lower()
                    return any(p in names for p in PLAUSIBLE) if names else None
            return None
        # embedding evidence: leave-one-out similarity of each paper to the person's own centroid
        rows_all = np.array([row[w["id"]] for w in ws if w["id"] in row])
        S = Pc[rows_all].sum(0)
        loo = {}
        for w in ws:
            if w["id"] in row:
                v = Pc[row[w["id"]]]
                c = S - v
                loo[w["id"]] = float(v @ c / (np.linalg.norm(c) + 1e-9))
        thr = float(np.percentile(list(loo.values()), 5)) if loo else -1
        mismatch = []
        for w in ws:
            t = w["topics"][0] if w["topics"] else None
            if t and t[4] and t[4] not in ENG_FIELDS and t[4] not in dom_fields:
                if plausible(w) is not True and loo.get(w["id"], 1) <= thr:
                    mismatch.append(w)
        # embedding bimodality
        rows = np.array([row[w["id"]] for w in ws if w["id"] in row])
        X = Pc[rows]
        flag_cluster = None
        if len(rows) >= 20:
            from sklearn.cluster import KMeans
            km = KMeans(n_clusters=2, n_init=5, random_state=0).fit(X)
            lab = km.labels_; c0, c1 = l2(X[lab == 0].mean(0)), l2(X[lab == 1].mean(0))
            sep = float(c0 @ c1); minor = 0 if (lab == 0).sum() < (lab == 1).sum() else 1
            frac = float((lab == minor).mean())
            minor_ws = [ws[i] for i in np.where(lab == minor)[0]]
            pl = [plausible(w) for w in minor_ws]
            pl_rate = sum(1 for p in pl if p) / max(1, sum(1 for p in pl if p is not None))
            topics_minor = Counter(t[1] for w in minor_ws for t in w["topics"][:1]).most_common(3)
            flag_cluster = {"separation_cos": round(sep, 3), "minor_fraction": round(frac, 3), "minor_n": int((lab == minor).sum()), "minor_plausible_aff_rate": round(pl_rate, 2), "minor_topics": topics_minor, "flag": bool(sep < 0.15 and frac >= 0.08 and pl_rate < 0.5)}
        report[f["slug"]] = {"name": f["name"], "n": len(ws), "career_start": start, "early_papers": [[w["year"], w["title"][:70]] for w in sorted(early, key=lambda w: w["year"])[:8]], "n_early": len(early),
                             "n_field_mismatch": len(mismatch), "loo_p5": round(thr, 3), "field_mismatch_examples": [[w["year"], (w["topics"][0][4] if w["topics"] else ""), w["title"][:60]] for w in mismatch[:6]], "dominant_fields": fields.most_common(4), "cluster": flag_cluster}
        if args.apply:
            for w in ws:
                if w["year"] and start and w["year"] < start - 8:
                    drops[f["slug"]].add(w["id"])
            for w in mismatch:
                drops[f["slug"]].add(w["id"])
    # print summary
    for s, r in sorted(report.items(), key=lambda kv: -(kv[1]["n_early"] + kv[1]["n_field_mismatch"])):
        c = r["cluster"] or {}
        if r["n_early"] or r["n_field_mismatch"] or c.get("flag"):
            print(f"{r['name']:<26} n={r['n']:>4} start={r['career_start']} early={r['n_early']:>3} field_mismatch={r['n_field_mismatch']:>3} cluster_flag={c.get('flag')} sep={c.get('separation_cos')} minor={c.get('minor_n')} pl={c.get('minor_plausible_aff_rate')} {c.get('minor_topics', [])[:2]}")
            for e in r["early_papers"][:3]:
                print(f"     early: {e}")
            for e in r["field_mismatch_examples"][:3]:
                print(f"     field: {e}")
    if args.apply:
        total = 0
        for f in faculty:
            d = drops.get(f["slug"], set())
            if d:
                f["works"] = [p for p in f["works"] if p not in d]; total += len(d)
        # remove faculty assignment; drop work entirely if no faculty left
        kept = []
        for w in works:
            w["faculty"] = [s for s in w["faculty"] if w["id"] not in drops.get(s, set())]
            if w["faculty"]:
                kept.append(w)
        for f in faculty:
            ws = [wid[p] for p in f["works"]]
            f["n_works"] = len(ws); f["n_with_abstract"] = sum(1 for w in ws if w["abstract"]); f["total_citations"] = sum(w["cited"] for w in ws)
            yrs = [w["year"] for w in ws if w["year"]]; f["first_year"] = min(yrs) if yrs else None; f["last_year"] = max(yrs) if yrs else None
        with open(DATA / "works.jsonl", "w") as fh:
            for w in kept:
                fh.write(json.dumps(w, ensure_ascii=False) + "\n")
        json.dump(faculty, open(DATA / "faculty.json", "w"), indent=1, ensure_ascii=False)
        report["_applied_drops"] = {s: sorted(d) for s, d in drops.items()}
        print(f"\napplied: removed {total} faculty-paper assignments; {len(works) - len(kept)} works dropped entirely")
    json.dump(report, open(DATA / "audit_attribution.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
