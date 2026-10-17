#!/usr/bin/env python3
"""
Faculty vectors, validation, layouts, research-area clustering and explorer data.

Inputs : data/works.jsonl, data/faculty.json, data/paper_embeddings.npy, data/paper_index.json
Outputs: output/explorer_data.json   faculty-level data for the web explorer
         output/papers.json          compact per-paper records (coords, cluster, faculty)
         output/abstracts.json       id -> abstract (loaded on demand by the explorer)
         output/validation.json      all validation metrics
         data/faculty_vectors.npz    career / recent / era vectors

Method (see README "Methodology"):
  paper vectors   SPECTER2-proximity CLS embeddings, L2-normalised
  centering       all vectors are centred on the department-wide mean paper vector before any
                  similarity, PCA, UMAP or clustering (removes the common "scientific text" direction
                  that makes raw SPECTER cosines cluster around 0.8)
  career vector   weighted mean of a faculty member's paper vectors, w = log(2 + citations); renormalised
  recent vector   weighted mean with w = exp(-(REF_YEAR - year)/TAU) (TAU = 4 yr), no citation weight
  era vectors     unweighted means over 5-year windows (>= MIN_ERA_PAPERS papers)
  similarity      cosine between centred faculty vectors (also reported on raw vectors for comparison)
"""
import json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
import os
DATA, OUT = Path(os.environ.get("KG_DATA", ROOT / "data")), Path(os.environ.get("KG_OUT", ROOT / "output"))
OUT.mkdir(exist_ok=True)

REF_YEAR = 2026
TAU = 4.0
ERA_WINDOWS = [(1960, 1989), (1990, 1999), (2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2026)]
MIN_ERA_PAPERS = 5
MIN_RECENT = 8   # papers in the last 10 years required for a 'recent' vector / drift value
SEED = 42


def l2(x, axis=-1):
    n = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / np.clip(n, 1e-12, None)


def load():
    works = [json.loads(l) for l in open(DATA / "works.jsonl") if l.strip()]
    faculty = json.load(open(DATA / "faculty.json"))
    idx = json.load(open(DATA / "paper_index.json"))
    emb_path = DATA / "paper_embeddings.npy"
    if not emb_path.exists():
        emb_path = DATA / "paper_embeddings_f16.npy"   # float16 copy kept in git
    emb = np.load(emb_path).astype(np.float32)
    emb = l2(emb)
    row = {pid: i for i, pid in enumerate(idx["ids"])}
    works = [w for w in works if w["id"] in row]
    order = np.array([row[w["id"]] for w in works])
    emb = emb[order]
    kinds = [idx["text_kind"][row[w["id"]]] for w in works]
    assert np.allclose(np.linalg.norm(emb, axis=1), 1, atol=1e-3), "paper vectors must be unit length"
    return works, faculty, emb, kinds


def faculty_vectors(works, faculty, Pc):
    """Return career, recent, era vectors (centred, unit length) and per-faculty paper index lists."""
    wid = {w["id"]: i for i, w in enumerate(works)}
    F = len(faculty)
    career = np.zeros((F, Pc.shape[1]), np.float32)
    recent = np.zeros_like(career)
    eras = {}
    paper_rows = []
    weights_career, weights_recent = [], []
    for fi, f in enumerate(faculty):
        rows = np.array([wid[p] for p in f["works"] if p in wid], dtype=int)
        paper_rows.append(rows)
        if len(rows) == 0:
            weights_career.append(None); weights_recent.append(None)
            continue
        cites = np.array([works[r]["cited"] for r in rows], float)
        years = np.array([works[r]["year"] or 0 for r in rows], float)
        wc = np.log(2.0 + cites)
        wr = np.exp(-(REF_YEAR - years) / TAU) * (years > 0)
        weights_career.append(wc / wc.sum())
        weights_recent.append(wr / wr.sum() if wr.sum() > 0 else None)
        career[fi] = (Pc[rows] * (wc / wc.sum())[:, None]).sum(0)
        if wr.sum() > 0 and int((years >= REF_YEAR - 10).sum()) >= MIN_RECENT:
            recent[fi] = (Pc[rows] * (wr / wr.sum())[:, None]).sum(0)
        for (a, b) in ERA_WINDOWS:
            m = (years >= a) & (years <= b)
            if m.sum() >= MIN_ERA_PAPERS:
                eras[(fi, a, b)] = l2(Pc[rows[m]].mean(0))
    return l2(career), l2(recent), eras, paper_rows, weights_career, weights_recent


def validation(works, faculty, Pc, Praw, career_c, career_raw, paper_rows):
    """Quantitative checks that the embedding space behaves as a research-similarity space."""
    F = len(faculty)
    have = np.array([len(r) > 0 for r in paper_rows])
    out = {}
    S_c = career_c @ career_c.T
    S_r = career_raw @ career_raw.T
    out["self_similarity_max_abs_err"] = float(np.max(np.abs(np.diag(S_c)[have] - 1)))
    out["symmetry_max_abs_err"] = float(np.max(np.abs(S_c - S_c.T)))
    iu = np.triu_indices(F, 1)
    mask = have[iu[0]] & have[iu[1]]
    out["pairwise_cos_raw"] = {"mean": float(S_c[iu][mask].mean()), "std": float(S_c[iu][mask].std()), "min": float(S_c[iu][mask].min()), "max": float(S_c[iu][mask].max())}
    out["pairwise_cos_centred"] = {"mean": float(S_r[iu][mask].mean()), "std": float(S_r[iu][mask].std()), "min": float(S_r[iu][mask].min()), "max": float(S_r[iu][mask].max())}

    # 1) agreement with OpenAlex topic profiles (independent signal: OpenAlex topics are assigned by a
    #    separate classifier over title/abstract/venue/citations)
    topic_vecs = []
    allt = {}
    for rows in paper_rows:
        c = Counter()
        for r in rows:
            for t in works[r]["topics"][:1]:
                c[t[0]] += 1
                allt[t[0]] = t[1]
        topic_vecs.append(c)
    tids = sorted(allt)
    tpos = {t: i for i, t in enumerate(tids)}
    T = np.zeros((F, len(tids)))
    for fi, c in enumerate(topic_vecs):
        for t, n in c.items():
            T[fi, tpos[t]] = n
    T = l2(np.sqrt(T))  # Hellinger-style
    S_t = T @ T.T
    from scipy.stats import spearmanr
    st = S_t[iu][mask]
    out["spearman_vs_openalex_topics"] = {"raw": float(spearmanr(S_c[iu][mask], st).correlation), "centred": float(spearmanr(S_r[iu][mask], st).correlation)}

    # 2) co-authorship: pairs that co-publish should be more similar than pairs that do not (AUC)
    co = np.zeros((F, F))
    slug2i = {f["slug"]: i for i, f in enumerate(faculty)}
    for w in works:
        fs = [slug2i[s] for s in w["faculty"] if s in slug2i]
        for a in fs:
            for b in fs:
                if a != b:
                    co[a, b] += 1
    y = (co[iu][mask] > 0).astype(int)
    from sklearn.metrics import roc_auc_score
    if 0 < y.sum() < len(y):
        out["coauthor_auc"] = {"raw": float(roc_auc_score(y, S_c[iu][mask])), "centred": float(roc_auc_score(y, S_r[iu][mask]))}
        out["coauthor_pairs"] = int(y.sum())

    # 3) leave-one-out paper -> faculty assignment accuracy (does a paper land nearest its own author?)
    #    Only among faculty with >= 10 papers; multi-author-faculty papers count as correct if any author matches.
    elig = [fi for fi in range(F) if len(paper_rows[fi]) >= 10]
    C = np.zeros((len(elig), Pc.shape[1]), np.float32)
    sums = {fi: Pc[paper_rows[fi]].sum(0) for fi in elig}
    correct = total = 0
    per_fac = {}
    fac_of_paper = defaultdict(set)
    for j, fi in enumerate(elig):
        for r in paper_rows[fi]:
            fac_of_paper[r].add(fi)
    for j, fi in enumerate(elig):
        hits = 0
        for r in paper_rows[fi]:
            cents = np.stack([l2(sums[g] - (Pc[r] if r in set(paper_rows[g]) else 0)) for g in elig])
            sims = cents @ Pc[r]
            best = elig[int(np.argmax(sims))]
            ok = best in fac_of_paper[r]
            hits += ok
        per_fac[faculty[fi]["slug"]] = round(hits / len(paper_rows[fi]), 3)
        correct += hits; total += len(paper_rows[fi])
    out["loo_paper_to_faculty_accuracy"] = {"overall": round(correct / max(total, 1), 4), "n_faculty": len(elig), "chance": round(1 / len(elig), 4), "per_faculty": per_fac}
    return out, S_c, S_r, co, S_t


EXTRA_STOP = set("""sub sup mml jats math msub msup mrow mi mn mo xmlns abstract paper papers results result based using used use method methods approach approaches model models modeling modelling system systems study studies studied also however show shows shown present presented presents problem problems proposed propose new novel analysis analyses performance effect effects different various important significant provide provides provided obtained observed investigated investigate investigation experimental experiments experiment numerical theoretical theory compared comparison data case cases high low large small two three first second order time number work set given general simple non non-linear linear nonlinear well good better best developed develop development design designed process processes technique techniques application applications demonstrate demonstrated demonstrates potential properties property structure structures condition conditions parameters parameter value values function functions measurements measurement measured measure range rate rates type types term terms form forms field fields including included include control controller controllers dynamic dynamics equation equations solution solutions mechanical engineering research state states level levels total available content access el del los las una por con des und der die berkeley university california press copyright elsevier ieee asme wiley springer reserved rights""".split())
HTML_RE = re.compile(r"</?[a-zA-Z][^<>]{0,60}>")


def ctfidf_labels(works, labels, n_terms=8):
    """Class-based TF-IDF keyword labels per cluster (BERTopic-style)."""
    from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
    docs = defaultdict(list)
    for w, c in zip(works, labels):
        if c >= 0:
            docs[c].append(HTML_RE.sub(" ", (w["title"] or "") + ". " + (w["abstract"] or "")[:1500]))
    cl = sorted(docs)
    corpus = [" ".join(docs[c]) for c in cl]
    cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | EXTRA_STOP), ngram_range=(1, 2), min_df=2, max_df=0.9, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b")
    X = cv.fit_transform(corpus).astype(float)
    tf = X / X.sum(1)
    df = (X > 0).sum(0)
    A = X.sum() / len(cl)
    idf = np.log(1 + A / np.asarray(df).ravel())
    W = np.asarray(tf.multiply(idf).todense())
    vocab = np.array(cv.get_feature_names_out())
    out = {}
    for i, c in enumerate(cl):
        top = np.argsort(-W[i])[: n_terms * 3]
        terms, seen = [], set()
        for t in top:
            term = vocab[t]
            stem = term.split()[0][:5]
            if any(term in s or s in term for s in seen):
                continue
            seen.add(term); terms.append(term)
            if len(terms) >= n_terms:
                break
        out[int(c)] = terms
    return out


def main():
    works, faculty, Praw, kinds = load()
    N, D = Praw.shape
    print(f"{N} papers, {len(faculty)} faculty, dim {D}")
    mu = Praw.mean(0)
    # PRIMARY space = raw SPECTER2 vectors. Mean-centring was evaluated and rejected: it lowers
    # agreement with independent signals (Spearman vs OpenAlex topic profiles 0.71 -> 0.59,
    # co-authorship AUC 0.84 -> 0.83) because the shared component carries genuine field
    # information. Centred results are kept as a secondary matrix for comparison.
    Pc = Praw
    Pcen = l2(Praw - mu)

    career_c, recent_c, eras, paper_rows, wc, wr = faculty_vectors(works, faculty, Pc)
    career_cen, _, _, _, _, _ = faculty_vectors(works, faculty, Pcen)
    have = np.array([len(r) > 0 for r in paper_rows])
    print("validating ...")
    val, S_c, S_r, co, S_t = validation(works, faculty, Pc, Pcen, career_c, career_cen, paper_rows)
    val["n_papers"] = N
    val["n_title_only"] = int(sum(1 for k in kinds if k == "title"))
    print(json.dumps({k: v for k, v in val.items() if k != "loo_paper_to_faculty_accuracy"}, indent=1))
    print("LOO accuracy", val["loo_paper_to_faculty_accuracy"]["overall"], "chance", val["loo_paper_to_faculty_accuracy"]["chance"])
    F = len(faculty)
    hv_ = np.where(have)[0]
    pairs_sorted = np.sort(np.array([S_c[a, b] for ai, a in enumerate(hv_) for b in hv_[ai + 1:]]))
    sim_pct = [[(round(float(np.searchsorted(pairs_sorted, S_c[a, b]) / max(1, len(pairs_sorted))), 3) if (a != b and have[a] and have[b]) else None) for b in range(F)] for a in range(F)]

    # ---------- faculty layouts ----------
    from sklearn.decomposition import PCA
    import umap
    F = len(faculty)
    pca = PCA(n_components=10, random_state=SEED).fit(career_c[have])
    pc_career = pca.transform(career_c)
    pc_recent = pca.transform(recent_c)
    val["pca_explained_variance_ratio"] = [round(float(x), 4) for x in pca.explained_variance_ratio_]
    # Faculty layouts are fitted on the CAREER vectors ONLY. (Fitting jointly with recent and era
    # vectors was wrong: each person's own era vectors are their nearest neighbours, so the kNN graph
    # degenerates into one island per person.) Recent and era vectors are then placed out-of-sample.
    # Chosen on 5-/10-NN trust, global distance correlation and an isolation index (see README):
    #   t-SNE perplexity 10, PCA init:  trust5 0.68  trust10 0.68  rho 0.66  isolation 2.1  (default "map")
    #   UMAP nn=10 min_dist .5 PCA init: trust5 0.61  trust10 0.63  rho 0.64  isolation 1.9
    #   MDS on cosine distance:          trust5 0.42  trust10 0.55  rho 0.82  isolation 6.0
    from sklearn.manifold import TSNE, MDS
    from scipy.optimize import minimize
    era_keys = sorted(eras)
    hv = np.where(have)[0]
    nh = len(hv)
    Vh = career_c[hv]
    p2 = pca.transform(Vh)[:, :2]
    tsne = TSNE(n_components=2, perplexity=10, metric="cosine", init="pca", random_state=SEED)
    T = tsne.fit_transform(Vh)

    def tsne_affinities(v, perplexity=10.0):
        """Gaussian affinities p_j of an out-of-sample vector v to the career vectors, calibrated to the perplexity."""
        d = 1 - Vh @ v
        lo, hi = 1e-6, 1e6
        for _ in range(60):
            beta = np.sqrt(lo * hi)
            P = np.exp(-(d - d.min()) * beta); P /= P.sum()
            H = -(P[P > 0] * np.log(P[P > 0])).sum()
            if np.exp(H) > perplexity:
                lo = beta
            else:
                hi = beta
        return P

    def tsne_place(v, self_idx=None):
        """Out-of-sample t-SNE: position minimising KL(p || q) against the fitted map (q = Student-t kernel)."""
        P = tsne_affinities(v)
        def obj(x):
            q = 1.0 / (1.0 + ((T - x) ** 2).sum(1)); q /= q.sum()
            return (P * np.log((P + 1e-12) / (q + 1e-12))).sum()
        x0 = T[np.argmax(P)] if self_idx is None else T[self_idx]
        return minimize(obj, x0, method="L-BFGS-B").x

    um = umap.UMAP(n_neighbors=10, min_dist=0.5, metric="cosine", random_state=SEED, n_components=2, init=p2).fit(Vh)
    U = um.embedding_
    Dc = 1 - Vh @ Vh.T
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=SEED, normalized_stress="auto").fit(Dc)
    M = mds.embedding_
    def mds_place(v):
        dd = 1 - Vh @ v
        obj = lambda x: ((np.linalg.norm(M - x, axis=1) - dd) ** 2).sum()
        return minimize(obj, M[np.argmin(dd)], method="L-BFGS-B").x

    tsne_career = np.full((F, 2), np.nan); tsne_recent = np.full((F, 2), np.nan)
    umap_career = np.full((F, 2), np.nan); umap_recent = np.full((F, 2), np.nan)
    mds_career = np.full((F, 2), np.nan); mds_recent = np.full((F, 2), np.nan)
    tsne_career[hv] = T; umap_career[hv] = U; mds_career[hv] = M
    for k, fi in enumerate(hv):
        if np.linalg.norm(recent_c[fi]) > 0:
            tsne_recent[fi] = tsne_place(recent_c[fi], self_idx=k)
            umap_recent[fi] = um.transform(recent_c[fi][None])[0]
            mds_recent[fi] = mds_place(recent_c[fi])
        else:
            tsne_recent[fi] = T[k]; umap_recent[fi] = U[k]; mds_recent[fi] = M[k]
    row_of = {fi: k for k, fi in enumerate(hv)}
    tsne_era = {k: tsne_place(eras[k], self_idx=row_of.get(k[0])) for k in era_keys}
    umap_era = {k: um.transform(eras[k][None])[0] for k in era_keys}
    mds_era = {k: mds_place(eras[k]) for k in era_keys}
    # layout quality metrics (kNN trust against the cosine neighbourhoods, global distance correlation, isolation)
    from scipy.spatial.distance import cdist, pdist
    from scipy.stats import spearmanr as _sp
    Sh = Vh @ Vh.T
    def _trust(X, k):
        D2 = cdist(X, X); hits = 0
        for i in range(nh):
            hits += len(set(np.argsort(-Sh[i])[1:k + 1]) & set(np.argsort(D2[i])[1:k + 1]))
        return round(hits / (nh * k), 3)
    def _isol(X):
        D2 = cdist(X, X); np.fill_diagonal(D2, np.inf); nn_ = D2.min(1); return round(float(nn_.max() / np.median(nn_)), 2)
    val["layout_quality"] = {name: {"trust5": _trust(X, 5), "trust10": _trust(X, 10), "global_rho": round(float(_sp(pdist(X), pdist(Vh, "cosine")).correlation), 3), "isolation": _isol(X)} for name, X in [("tsne", T), ("umap", U), ("mds", M), ("pca", p2)]}
    pca_era = {k: pca.transform(eras[k][None])[0] for k in era_keys}

    # ---------- paper-level map + research areas ----------
    print("paper UMAP ...")
    pca50_model = PCA(n_components=50, random_state=SEED).fit(Pc)
    pca50 = pca50_model.transform(Pc)
    um_p = umap.UMAP(n_neighbors=15, min_dist=0.05, metric="cosine", random_state=SEED, n_components=2).fit(pca50)
    PXY = um_p.embedding_
    um5 = umap.UMAP(n_neighbors=15, min_dist=0.0, metric="cosine", random_state=SEED, n_components=5).fit_transform(pca50)
    import hdbscan
    MIN_CL = max(40, N // 250)
    cl = hdbscan.HDBSCAN(min_cluster_size=MIN_CL, min_samples=5, cluster_selection_method="eom").fit(um5)
    labels = cl.labels_.copy()
    print(f"HDBSCAN pass 1: {labels.max() + 1} clusters, {int((labels < 0).sum())} noise points")
    # recursively split oversized clusters (> MAX_FRAC of corpus): re-embed the subset with UMAP and re-cluster
    MAX_FRAC = 0.06
    for it in range(3):
        big = [c for c in range(labels.max() + 1) if (labels == c).sum() > MAX_FRAC * N]
        if not big:
            break
        for c in big:
            m = np.where(labels == c)[0]
            sub5 = umap.UMAP(n_neighbors=15, min_dist=0.0, metric="cosine", random_state=SEED, n_components=5).fit_transform(pca50[m])
            sub = hdbscan.HDBSCAN(min_cluster_size=max(40, len(m) // 25), min_samples=10, cluster_selection_method="eom").fit(sub5).labels_
            if sub.max() < 1:
                sub = hdbscan.HDBSCAN(min_cluster_size=max(40, len(m) // 25), min_samples=5, cluster_selection_method="leaf").fit(sub5).labels_
            if sub.max() < 1:
                print(f"  cluster {c} ({len(m)}) could not be split"); continue
            # noise inside the subset -> nearest sub-centroid
            sc = np.stack([sub5[sub == k].mean(0) for k in range(sub.max() + 1)])
            nz = sub < 0
            if nz.any():
                sub[nz] = ((sub5[nz][:, None, :] - sc[None]) ** 2).sum(-1).argmin(1)
            base = labels.max() + 1
            labels[m[sub > 0]] = base + sub[sub > 0] - 1
            print(f"  split cluster {c} ({len(m)} papers) into {sub.max() + 1}")
    # compact label ids
    uniq = sorted(set(labels[labels >= 0]))
    remap = {old: new for new, old in enumerate(uniq)}
    labels = np.array([remap[x] if x >= 0 else -1 for x in labels])
    n_cl = labels.max() + 1
    print(f"HDBSCAN final: {n_cl} clusters, {int((labels < 0).sum())} noise points")
    # assign noise to nearest cluster centroid (in 5-D UMAP space) for profiles, but remember it was noise
    cents5 = np.stack([um5[labels == c].mean(0) for c in range(n_cl)])
    noise = labels < 0
    if noise.any():
        d = ((um5[noise][:, None, :] - cents5[None]) ** 2).sum(-1)
        labels_filled = labels.copy(); labels_filled[noise] = d.argmin(1)
    else:
        labels_filled = labels
    terms = ctfidf_labels(works, labels_filled)
    areas = []
    slug2i = {f["slug"]: i for i, f in enumerate(faculty)}
    for c in range(n_cl):
        m = labels_filled == c
        topic_c = Counter(); sub_c = Counter(); fac_c = Counter(); yrs = Counter()
        for r in np.where(m)[0]:
            w = works[r]
            for t in w["topics"][:1]:
                topic_c[t[1]] += 1; sub_c[t[3]] += 1
            for s in w["faculty"]:
                fac_c[s] += 1
            if w["year"]:
                yrs[w["year"]] += 1
        cent = l2(Pc[m].mean(0))
        areas.append({
            "id": c, "size": int(m.sum()), "noise_fraction": round(float((labels[m] < 0).mean()), 3),
            "terms": terms.get(c, []),
            "top_topics": topic_c.most_common(5), "top_subfields": sub_c.most_common(3),
            "faculty": [[s, n] for s, n in fac_c.most_common()],
            "years": sorted(yrs.items()),
            "centroid_xy": [float(x) for x in PXY[m].mean(0)],
            "median_year": int(np.median([works[r]["year"] for r in np.where(m)[0] if works[r]["year"]])) if m.sum() else None,
            "mean_citations": round(float(np.mean([works[r]["cited"] for r in np.where(m)[0]])), 1),
            "faculty_sim": [float(x) for x in (career_c @ cent)],
        })
    # label: 3 c-TF-IDF terms
    for a in areas:
        a["label"] = " / ".join(a["terms"][:3])
    # coarse grouping of fine areas (average-linkage on centroids, cosine) -> ~N_COARSE groups
    from scipy.cluster.hierarchy import linkage as _lk, fcluster
    cents = np.stack([l2(Pc[labels_filled == a["id"]].mean(0)) for a in areas])
    N_COARSE = max(8, min(20, int(round(n_cl / 3))))
    if n_cl > N_COARSE:
        Zc = _lk(cents, method="average", metric="cosine")
        grp = fcluster(Zc, t=N_COARSE, criterion="maxclust") - 1
    else:
        grp = np.arange(n_cl)
    coarse_labels = grp[labels_filled]
    coarse_terms = ctfidf_labels(works, coarse_labels, n_terms=8)
    groups = []
    for gidx in range(grp.max() + 1):
        members = [a["id"] for a in areas if grp[a["id"]] == gidx]
        m = coarse_labels == gidx
        topic_c = Counter(); fac_c = Counter(); yrs = Counter()
        for r in np.where(m)[0]:
            w = works[r]
            for t in w["topics"][:1]:
                topic_c[t[1]] += 1
            for s_ in w["faculty"]:
                fac_c[s_] += 1
            if w["year"]:
                yrs[w["year"]] += 1
        groups.append({"id": int(gidx), "areas": members, "size": int(m.sum()), "terms": coarse_terms.get(gidx, []), "label": " / ".join(coarse_terms.get(gidx, [])[:3]),
                       "top_topics": topic_c.most_common(5), "faculty": [[s_, n] for s_, n in fac_c.most_common()], "years": sorted(yrs.items()),
                       "centroid_xy": [float(x) for x in PXY[m].mean(0)], "median_year": int(np.median([works[r]["year"] for r in np.where(m)[0] if works[r]["year"]])),
                       "mean_citations": round(float(np.mean([works[r]["cited"] for r in np.where(m)[0]])), 1)})
    for a in areas:
        a["group"] = int(grp[a["id"]])

    # per-faculty area profile, breadth, drift, centrality
    fac_out = []
    area_mat = np.zeros((F, n_cl))
    for fi, f in enumerate(faculty):
        rows = paper_rows[fi]
        for r in rows:
            area_mat[fi, labels_filled[r]] += 1
    for fi, f in enumerate(faculty):
        rows = paper_rows[fi]
        prof = area_mat[fi]
        p = prof / prof.sum() if prof.sum() else prof
        ent = float(-(p[p > 0] * np.log(p[p > 0])).sum()) if prof.sum() else None
        # breadth: mean pairwise cosine distance among own papers (subsample for big authors)
        if len(rows) >= 3:
            rr = rows if len(rows) <= 400 else np.random.RandomState(SEED).choice(rows, 400, replace=False)
            S = Pc[rr] @ Pc[rr].T
            iu = np.triu_indices(len(rr), 1)
            breadth = float(1 - S[iu].mean())
        else:
            breadth = None
        n_recent = int(sum(1 for r in rows if (works[r]["year"] or 0) >= REF_YEAR - 10))
        drift = float(1 - career_c[fi] @ recent_c[fi]) if have[fi] and np.linalg.norm(recent_c[fi]) > 0 and n_recent >= MIN_RECENT else None
        sims = S_c[fi].copy(); sims[fi] = np.nan
        sims[~have] = np.nan
        nn = np.argsort(-np.nan_to_num(sims, nan=-9))[:8]
        topics = Counter(); subfields = Counter(); venues = Counter(); yrs = Counter(); kw = Counter()
        for r in rows:
            w = works[r]
            for t in w["topics"][:1]:
                topics[t[1]] += 1; subfields[t[3]] += 1
            if w["venue"]:
                venues[w["venue"]] += 1
            if w["year"]:
                yrs[w["year"]] += 1
            for k in w["keywords"][:3]:
                kw[k] += 1
        cites = sorted([works[r]["cited"] for r in rows], reverse=True)
        h = sum(1 for i, c in enumerate(cites) if c >= i + 1)
        trajectory = []
        for (a, b) in ERA_WINDOWS:
            k = (fi, a, b)
            if k in eras:
                trajectory.append({"era": (f"≤{b}" if a <= 1960 else f"{a}-{b}"), "tsne": [float(x) for x in tsne_era[k]], "umap": [float(x) for x in umap_era[k]], "pca": [float(x) for x in pca_era[k][:2]], "mds": [float(x) for x in mds_era[k]], "n": int(((np.array([works[r]['year'] or 0 for r in rows]) >= a) & (np.array([works[r]['year'] or 0 for r in rows]) <= b)).sum())})
        fac_out.append({
            **{k: f[k] for k in ["slug", "name", "category", "title", "profile_url", "openalex_ids", "match_notes", "match_confidence", "research_description", "bio", "links", "n_works", "n_with_abstract", "total_citations", "first_year", "last_year"]},
            "h_index": h,
            "has_vector": bool(have[fi]),
            "tsne": [float(x) for x in tsne_career[fi]] if have[fi] else None,
            "tsne_recent": [float(x) for x in tsne_recent[fi]] if have[fi] else None,
            "umap": [float(x) for x in umap_career[fi]] if have[fi] else None,
            "umap_recent": [float(x) for x in umap_recent[fi]] if have[fi] else None,
            "pca": [float(x) for x in pc_career[fi][:2]] if have[fi] else None,
            "pca_recent": [float(x) for x in pc_recent[fi][:2]] if have[fi] else None,
            "mds": [float(x) for x in mds_career[fi]] if have[fi] else None,
            "mds_recent": [float(x) for x in mds_recent[fi]] if have[fi] else None,
            "paper_map_xy": [float(x) for x in np.median(PXY[rows], 0)] if len(rows) else None,
            "trajectory": trajectory,
            "area_profile": [[int(c), int(n)] for c, n in enumerate(prof) if n > 0],
            "group_profile": sorted(Counter(int(coarse_labels[r]) for r in rows).items()),
            "area_entropy": round(ent, 3) if ent is not None else None,
            "breadth": round(breadth, 4) if breadth is not None else None,
            "drift": round(drift, 4) if drift is not None else None,
            "n_recent": n_recent,
            "centrality": round(float(np.nanmean(sims)), 4) if have[fi] else None,
            "neighbors": [[int(j), round(float(S_c[fi, j]), 4), sim_pct[fi][j]] for j in nn if not np.isnan(sims[j])],
            "top_topics": topics.most_common(8), "top_subfields": subfields.most_common(4),
            "top_venues": venues.most_common(6), "top_keywords": kw.most_common(10),
            "years": sorted(yrs.items()),
            "coauthors": [[int(j), int(co[fi, j])] for j in np.argsort(-co[fi]) if co[fi, j] > 0],
            "vector": [round(float(x), 5) for x in career_c[fi]] if have[fi] else None,
            "vector_recent": [round(float(x), 5) for x in recent_c[fi]] if have[fi] and np.linalg.norm(recent_c[fi]) > 0 else None,
        })

    for key in ["breadth", "drift", "centrality"]:
        vals = sorted(f[key] for f in fac_out if f[key] is not None)
        for f in fac_out:
            f[key + "_pct"] = round(float(np.searchsorted(vals, f[key]) / max(1, len(vals) - 1)), 3) if f[key] is not None else None
    # similarity matrices (raw primary; centred for reference) + hierarchical ordering
    from scipy.cluster.hierarchy import linkage, leaves_list
    hv = np.where(have)[0]
    Z = linkage(career_c[hv], method="average", metric="cosine")
    order = [int(hv[i]) for i in leaves_list(Z)]

    explorer = {
        "meta": {
            "department": "Mechanical Engineering", "university": "UC Berkeley",
            "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "source": "OpenAlex (works, topics, citations) + me.berkeley.edu (roster, profiles)",
            "embedding_model": "allenai/specter2_base + specter2 proximity adapter (local CPU)",
            "embedding_dim": int(D), "n_papers": int(N), "n_faculty": F,
            "n_faculty_with_vectors": int(have.sum()),
            "weights": {"career": "log(2 + citations)", "recent": f"exp(-(REF_YEAR - year)/{TAU}), REF_YEAR={REF_YEAR}"},
            "similarity_space": "raw SPECTER2 cosine (primary); mean-centred cosine kept as similarity_centred for comparison",
            "tsne_faculty": {"perplexity": 10, "metric": "cosine", "init": "PCA", "seed": SEED, "fit_on": "career vectors only; recent and era vectors placed out-of-sample by minimising KL to the fitted map"},
            "umap_faculty": {"n_neighbors": 10, "min_dist": 0.5, "metric": "cosine", "init": "PCA", "seed": SEED, "fit_on": "career vectors only; recent/era via umap.transform"},
            "mds_faculty": "metric MDS on cosine distances between career vectors (recent/era points placed by out-of-sample projection: least-squares fit to distances)",
            "umap_papers": {"n_neighbors": 15, "min_dist": 0.05, "metric": "cosine", "pre_pca": 50, "seed": SEED},
            "clustering": {"method": "HDBSCAN on 5-D UMAP, oversized clusters (>6% of corpus) re-clustered recursively", "min_cluster_size": int(MIN_CL), "min_samples": 5, "n_areas": int(n_cl), "noise_points": int((labels < 0).sum())},
            "categories": sorted({f["category"] for f in faculty}),
        },
        "faculty": fac_out,
        "similarity": [[round(float(x), 4) for x in row] for row in S_c],
        "similarity_centred": [[round(float(x), 4) for x in row] for row in S_r],
        "similarity_percentile": sim_pct,
        "topic_similarity": [[round(float(x), 4) for x in row] for row in S_t],
        "coauthorship": [[int(x) for x in row] for row in co],
        "dendrogram_order": order,
        "areas": areas,
        "groups": groups,
        "validation": val,
    }
    def _nan2none(o):
        if isinstance(o, float):
            return None if (math.isnan(o) or math.isinf(o)) else o
        if isinstance(o, dict):
            return {k: _nan2none(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_nan2none(v) for v in o]
        return o
    explorer = _nan2none(explorer); val = _nan2none(val)
    json.dump(explorer, open(OUT / "explorer_data.json", "w"))
    papers = []
    for r, w in enumerate(works):
        papers.append({
            "id": w["id"], "t": w["title"], "y": w["year"], "c": w["cited"], "v": w["venue"], "d": w["doi"],
            "f": [slug2i[s] for s in w["faculty"] if s in slug2i],
            "x": round(float(PXY[r, 0]), 3), "yy": round(float(PXY[r, 1]), 3),
            "a": int(labels_filled[r]), "g": int(coarse_labels[r]), "noise": bool(labels[r] < 0), "k": kinds[r] == "title",
            "tp": w["topics"][0][1] if w["topics"] else None,
        })
    json.dump(papers, open(OUT / "papers.json", "w"))
    json.dump({w["id"]: w["abstract"] for w in works if w["abstract"]}, open(OUT / "abstracts.json", "w"))
    json.dump(val, open(OUT / "validation.json", "w"), indent=1)
    np.savez(DATA / "faculty_vectors.npz", career=career_c, recent=recent_c, mu=mu, have=have)
    import pickle
    (DATA / "models").mkdir(exist_ok=True)
    with open(DATA / "models" / "layouts.pkl", "wb") as fh:
        pickle.dump({"umap_faculty": um, "pca_faculty": pca, "mds_points": M, "tsne_points": T, "career_have": Vh, "umap_papers": um_p, "pca50_model": pca50_model}, fh)
    np.save(DATA / "paper_embeddings_f16.npy", Praw.astype(np.float16))
    print("wrote output/explorer_data.json, papers.json, abstracts.json, validation.json")
    for a in areas:
        print(f"area {a['id']:>2} n={a['size']:>5}  {a['label']}  | {a['top_topics'][0][0] if a['top_topics'] else ''}")


if __name__ == "__main__":
    main()
