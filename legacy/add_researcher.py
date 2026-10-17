#!/usr/bin/env python3
"""
UC Berkeley ME Department — Add Researcher to Existing Map
===========================================================
Projects a new researcher into the existing UMAP space without
refitting — their position is computed relative to the learned
layout, so existing faculty don't move.

Usage:
    source venv_umap/bin/activate
    python3 add_researcher.py --openalex-id A1234567890
    python3 add_researcher.py --openalex-id A1234567890 --name "Jane Smith"
    python3 add_researcher.py --remove "Jane Smith"   # remove a previously added researcher
    python3 add_researcher.py --list                  # show all added researchers
"""

import json
import sys
import argparse
import math
import requests
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("Missing numpy. Run: pip install numpy")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Missing openai. Run: pip install openai")
    sys.exit(1)

import os

OPENALEX_BASE  = "https://api.openalex.org"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "UCBerkeleyMEKnowledgeGraph/1.0"})
MODEL_CHAR_LIMIT = 28000


# =============================================================================
# Helpers
# =============================================================================

def fetch_author(openalex_id):
    r = SESSION.get(f"{OPENALEX_BASE}/authors/{openalex_id}", timeout=20)
    if r.status_code != 200:
        print(f"Error fetching author {openalex_id}: HTTP {r.status_code}")
        return None
    return r.json()


def fetch_works(openalex_id):
    works, page, per_page = [], 1, 100
    while True:
        r = SESSION.get(f"{OPENALEX_BASE}/works", params={
            "filter": f"authorships.author.id:{openalex_id}",
            "per_page": per_page, "page": page,
            "select": "id,title,publication_year,primary_location,cited_by_count,abstract_inverted_index",
        }, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        batch = data.get("results", [])
        if not batch:
            break
        total = data.get("meta", {}).get("count", 0)
        for w in batch:
            abstract = reconstruct_abstract(w.get("abstract_inverted_index"))
            works.append({
                "title":          w.get("title","") or "",
                "abstract":       abstract,
                "citation_count": w.get("cited_by_count", 0),
                "year":           str(w.get("publication_year","") or ""),
            })
        if len(works) >= total:
            break
        page += 1
    return works


def reconstruct_abstract(inv):
    if not inv:
        return ""
    try:
        words = {}
        for word, positions in inv.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words[i] for i in sorted(words))
    except Exception:
        return ""


def citation_weight(citations, floor=0.1):
    return math.log1p(max(citations, 0)) + floor


def get_embedding(client, text, model="text-embedding-3-small"):
    text = text.replace("\n", " ").strip()[:MODEL_CHAR_LIMIT]
    if not text:
        return None
    try:
        response = client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding failed: {e}")
        return None


def weighted_average_embedding(client, works, model):
    pairs = []
    for w in works:
        text = w.get("abstract") or w.get("title") or ""
        if not text:
            continue
        emb = get_embedding(client, text, model)
        if emb:
            weight = citation_weight(w.get("citation_count") or 0)
            pairs.append((emb, weight))

    if not pairs:
        return None

    total_w = sum(w for _, w in pairs)
    dim = len(pairs[0][0])
    avg = [0.0] * dim
    for emb, w in pairs:
        nw = w / total_w
        for i in range(dim):
            avg[i] += emb[i] * nw
    return avg


def slugify(text):
    import re
    text = str(text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:100]


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Add a researcher to the ME knowledge graph map")
    parser.add_argument("--openalex-id", type=str, nargs="+", default=None,
                        help="One or more OpenAlex author IDs (e.g. A1234567890 A9876543210)")
    parser.add_argument("--name",        type=str, default=None,
                        help="Override display name (optional)")
    parser.add_argument("--remove",      type=str, default=None,
                        help="Remove an added researcher by name")
    parser.add_argument("--list",        action="store_true",
                        help="List all added researchers")
    parser.add_argument("--api-key",     type=str, default=None)
    parser.add_argument("--model",       type=str, default="text-embedding-3-small")
    args = parser.parse_args()

    graph_path      = Path("output/knowledge_graph.json")
    embeddings_path = Path("output/faculty_embeddings.json")
    umap_model_path = Path("output/umap_model.npy")  # saved UMAP transform data

    if not graph_path.exists():
        print("Error: output/knowledge_graph.json not found.")
        sys.exit(1)

    with open(graph_path, encoding="utf-8") as f:
        graph = json.load(f)

    # ── List ──────────────────────────────────────────────────────────────────
    if args.list:
        guests = [f for f in graph["nodes"]["faculty"] if f.get("is_guest")]
        if not guests:
            print("No added researchers.")
        else:
            print(f"{len(guests)} added researcher(s):")
            for g in guests:
                print(f"  {g['name']}  [{g.get('openalex_id','')}]")
        return

    # ── Remove ────────────────────────────────────────────────────────────────
    if args.remove:
        before = len(graph["nodes"]["faculty"])
        graph["nodes"]["faculty"] = [
            f for f in graph["nodes"]["faculty"]
            if not (f.get("is_guest") and f["name"].lower() == args.remove.lower())
        ]
        removed = before - len(graph["nodes"]["faculty"])
        if removed:
            fid = slugify(args.remove)
            graph["edges"]["faculty_authored"] = [
                e for e in graph["edges"]["faculty_authored"] if e["from"] != fid
            ]
            graph["edges"]["faculty_coauthored"] = [
                e for e in graph["edges"]["faculty_coauthored"]
                if e["from"] != fid and e["to"] != fid
            ]
            graph["edges"]["faculty_similar"] = [
                e for e in graph["edges"].get("faculty_similar", [])
                if e["from"] != fid and e["to"] != fid
            ]
            if embeddings_path.exists():
                with open(embeddings_path, encoding="utf-8") as f:
                    fac_cache = json.load(f)
                if fid in fac_cache:
                    del fac_cache[fid]
                    with open(embeddings_path, "w", encoding="utf-8") as f:
                        json.dump(fac_cache, f)
            with open(graph_path, "w", encoding="utf-8") as f:
                json.dump(graph, f, indent=2, ensure_ascii=False)
            print(f"Removed: {args.remove}")
        else:
            print(f"Not found: {args.remove}")
        return

    # ── Add ───────────────────────────────────────────────────────────────────
    if not args.openalex_id:
        parser.print_help()
        sys.exit(1)

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: No OpenAI API key. Set OPENAI_API_KEY or pass --api-key sk-...")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    for openalex_id in args.openalex_id:
        print(f"\n{'='*60}")
        print(f"Processing {openalex_id}...")

        # Reload graph and cache fresh each iteration so additions accumulate
        with open(graph_path, encoding="utf-8") as f:
            graph = json.load(f)
        if embeddings_path.exists():
            with open(embeddings_path, encoding="utf-8") as f:
                fac_cache = json.load(f)
        else:
            print(f"Error: {embeddings_path} not found. Run compute_embeddings.py first.")
            sys.exit(1)

        # Fetch author from OpenAlex
        print(f"Fetching author from OpenAlex...")
        author = fetch_author(openalex_id)
        if not author:
            print(f"Skipping {openalex_id} — could not fetch.")
            continue

        display_name = args.name or author.get("display_name", openalex_id)
        fid = slugify(display_name)
        print(f"Found: {display_name}")
        print(f"Citations: {author.get('cited_by_count',0):,}  |  Works: {author.get('works_count',0)}")

        # Check if already a core faculty member
        existing = next((f for f in graph["nodes"]["faculty"] if f["id"] == fid), None)
        if existing and not existing.get("is_guest"):
            print(f"Skipping — {display_name} is already a core faculty member.")
            continue

        # Fetch works and compute embedding
        print(f"Fetching publications...")
        works = fetch_works(openalex_id)
        print(f"Found {len(works)} works")

        sorted_recent = sorted(works, key=lambda w: w.get("year") or "0", reverse=True)
        all_titles    = " | ".join(w["title"] for w in sorted_recent if w.get("title"))

        print("Computing embedding...")
        guest_embedding = weighted_average_embedding(client, works, args.model)
        if not guest_embedding:
            print("No abstracts found, using titles only...")
            guest_embedding = get_embedding(client, all_titles, args.model)
        if not guest_embedding:
            print(f"Could not compute embedding for {display_name}, skipping.")
            continue

        # Compute similarity to all core (non-guest) faculty
        def cosine_sim(a, b):
            dot = sum(x*y for x,y in zip(a,b))
            na  = math.sqrt(sum(x*x for x in a))
            nb  = math.sqrt(sum(x*x for x in b))
            return dot/(na*nb) if na>0 and nb>0 else 0.0

        core_cache = {k: v for k, v in fac_cache.items() if not v.get("is_guest")}
        sim_edges = []
        for fid2, data in core_cache.items():
            sim = cosine_sim(guest_embedding, data["embedding"])
            sim_edges.append({"from": fid, "to": fid2, "similarity": round(sim, 4)})
        sim_edges.sort(key=lambda x: x["similarity"], reverse=True)

        fac_name = {f["id"]: f["name"] for f in graph["nodes"]["faculty"]}
        print(f"Top 5 most similar faculty:")
        for e in sim_edges[:5]:
            name = fac_name.get(e["to"], e["to"])
            print(f"  {name:<38} {e['similarity']:.3f}")

        # ── Nearest neighbor position interpolation ────────────────────────────
        # Place guest at weighted centroid of top-k most similar faculty positions
        # Weight = similarity score, so closer neighbors pull more
        K = 5
        top_k = sim_edges[:K]
        fac_by_id = {f["id"]: f for f in graph["nodes"]["faculty"] if not f.get("is_guest")}

        def interp_coords(top_k, x_field, y_field):
            weighted_x, weighted_y, total_w = 0.0, 0.0, 0.0
            for e in top_k:
                f = fac_by_id.get(e["to"])
                if f and f.get(x_field) is not None and f.get(y_field) is not None:
                    w = e["similarity"]
                    weighted_x += f[x_field] * w
                    weighted_y += f[y_field] * w
                    total_w    += w
            if total_w == 0:
                return None, None
            return weighted_x / total_w, weighted_y / total_w

        umap_x, umap_y = interp_coords(top_k, "umap_x", "umap_y")
        pca_x,  pca_y  = interp_coords(top_k, "pca_x",  "pca_y")

        if umap_x is None:
            print(f"Warning: could not compute position for {display_name} — no neighbor coordinates found.")
            continue

        print(f"UMAP position: ({umap_x:.1f}, {umap_y:.1f})  [interpolated from top {K} neighbors]")
        print(f"PCA position:  ({pca_x:.1f}, {pca_y:.1f})")

        # Build guest node with interpolated positions
        last_inst  = (author.get("last_known_institutions") or [{}])[0]
        guest_node = {
            "id":              fid,
            "name":            display_name,
            "category":        "guest",
            "is_guest":        True,
            "openalex_id":     openalex_id,
            "affiliation":     last_inst.get("display_name", ""),
            "interests":       [t.get("display_name","") for t in (author.get("topics") or [])[:8]],
            "h_index":         author.get("summary_stats", {}).get("h_index", 0),
            "i10_index":       author.get("summary_stats", {}).get("i10_index", 0),
            "total_citations": author.get("cited_by_count", 0),
            "works_count":     author.get("works_count", 0),
            "openalex_url":    author.get("id", ""),
            "profile_url":     "",
            "openalex_found":  True,
            "layout_x":        umap_x,
            "layout_y":        umap_y,
            "umap_x":          umap_x,
            "umap_y":          umap_y,
            "pca_x":           pca_x,
            "pca_y":           pca_y,
        }

        # Remove if re-adding, then append
        graph["nodes"]["faculty"] = [f for f in graph["nodes"]["faculty"] if f["id"] != fid]
        graph["nodes"]["faculty"].append(guest_node)

        # Update similarity edges
        existing_sim = [e for e in graph["edges"].get("faculty_similar", [])
                        if e["from"] != fid and e["to"] != fid]
        graph["edges"]["faculty_similar"] = existing_sim + sim_edges

        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)

        print(f"Added {display_name} to the graph.")

    print(f"\n{'='*60}")
    print(f"Done. Reload the explorer to see the new researcher(s).")
    print(f"No need to run compute_layout.py — positions are interpolated from existing faculty.")


if __name__ == "__main__":
    main()
