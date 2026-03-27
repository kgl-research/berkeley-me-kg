#!/usr/bin/env python3
"""
UC Berkeley ME Department — Faculty Research Similarity via Embeddings
=======================================================================
Embeds each publication abstract independently, then computes a
citation-weighted average embedding per faculty member.

Weighting scheme:
  - Each paper gets weight = log(1 + citations) / sum(log(1 + citations))
  - Log scaling prevents a single blockbuster paper from dominating
  - Papers with 0 citations get a small floor weight so they still contribute
  - Papers without abstracts contribute their title only

Installation:
    pip install openai tqdm

Usage:
    export OPENAI_API_KEY="sk-..."
    python3 compute_embeddings.py

    python3 compute_embeddings.py --api-key sk-...
    python3 compute_embeddings.py --no-weight    # equal weighting instead

Output:
    Adds "faculty_similar" edges to knowledge_graph.json
    Writes output/pub_embeddings.json   (per-publication cache)
    Writes output/faculty_embeddings.json (per-faculty weighted average)
"""

import json
import argparse
import os
import sys
import math
from pathlib import Path

try:
    from openai import OpenAI
    from tqdm import tqdm
except ImportError:
    print("Missing dependencies. Run:  pip install openai tqdm")
    sys.exit(1)


# =============================================================================
# Helpers
# =============================================================================

def cosine_similarity(a, b):
    dot  = sum(x * y for x, y in zip(a, b))
    na   = math.sqrt(sum(x * x for x in a))
    nb   = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


def get_embedding(client, text, model):
    """Embed a single text string. Returns vector or None on failure."""
    text = text.replace("\n", " ").strip()
    if not text:
        return None
    # Truncate to model limit (~28k chars to stay safely under 8192 tokens)
    text = text[:28000]
    try:
        response = client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        tqdm.write(f"    Embedding failed: {e}")
        return None


def weighted_average(embeddings_and_weights):
    """
    Compute a weighted average of embedding vectors.
    Input: list of (embedding_vector, weight) tuples
    Returns: averaged vector (normalized weights sum to 1)
    """
    if not embeddings_and_weights:
        return None

    total_weight = sum(w for _, w in embeddings_and_weights)
    if total_weight == 0:
        # Fall back to equal weighting
        total_weight = len(embeddings_and_weights)
        embeddings_and_weights = [(e, 1.0) for e, _ in embeddings_and_weights]

    dim = len(embeddings_and_weights[0][0])
    avg = [0.0] * dim
    for emb, w in embeddings_and_weights:
        norm_w = w / total_weight
        for i in range(dim):
            avg[i] += emb[i] * norm_w
    return avg


def citation_weight(citations, floor=0.1):
    """
    Log-scaled citation weight with a floor so zero-citation papers still count.
    floor=0.1 means a paper with 0 citations gets 10% of the weight
    that a paper with 1 citation would get.
    """
    return math.log1p(max(citations, 0)) + floor


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Per-abstract citation-weighted faculty embeddings")
    parser.add_argument("--input",     type=str,   default="output/knowledge_graph.json")
    parser.add_argument("--api-key",   type=str,   default=None)
    parser.add_argument("--model",     type=str,   default="text-embedding-3-small")
    parser.add_argument("--no-weight", action="store_true",
                        help="Use equal weighting instead of citation weighting")
    parser.add_argument("--threshold", type=float, default=0.0,
                        help="Min cosine similarity to store as edge (default: 0 = store all)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: No OpenAI API key. Set OPENAI_API_KEY or pass --api-key sk-...")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Load graph
    graph_path = Path(args.input)
    if not graph_path.exists():
        print(f"Error: {graph_path} not found. Run scrape_faculty.py first.")
        sys.exit(1)

    print(f"Loading {graph_path}...")
    with open(graph_path, encoding="utf-8") as f:
        graph = json.load(f)

    faculty_list   = graph["nodes"]["faculty"]
    publications   = {p["id"]: p for p in graph["nodes"]["publications"]}
    authored_edges = graph["edges"]["faculty_authored"]

    print(f"Faculty: {len(faculty_list)}")
    print(f"Publications: {len(publications)}")

    # Build per-faculty pub list
    fac_pubs = {}
    for edge in authored_edges:
        fid, pid = edge["from"], edge["to"]
        if pid in publications:
            fac_pubs.setdefault(fid, []).append(publications[pid])

    # ==========================================================================
    # Step 1: Embed publications (cached per-pub)
    # ==========================================================================
    pub_cache_path = Path("output/pub_embeddings.json")
    pub_cache = {}
    if pub_cache_path.exists():
        with open(pub_cache_path, encoding="utf-8") as f:
            pub_cache = json.load(f)
        print(f"Loaded pub cache: {len(pub_cache)} publications already embedded")

    # Determine which publications need embedding
    # Only embed pubs that belong to at least one faculty we'll process
    active_fac = [f for f in faculty_list if f.get("openalex_found", True)]
    needed_pub_ids = set()
    for fac in active_fac:
        for pub in fac_pubs.get(fac["id"], []):
            needed_pub_ids.add(pub["id"])

    to_embed_pubs = [publications[pid] for pid in needed_pub_ids if pid not in pub_cache]

    if to_embed_pubs:
        # Estimate cost
        total_chars = sum(
            len(p.get("abstract") or p.get("title") or "")
            for p in to_embed_pubs
        )
        est_tokens = total_chars / 4
        est_cost   = est_tokens / 1_000_000 * 0.02
        print(f"\nEmbedding {len(to_embed_pubs):,} publications...")
        print(f"Model: {args.model}")
        print(f"Estimated tokens: ~{est_tokens:,.0f}")
        print(f"Estimated cost:   ~${est_cost:.4f}")
        print(f"Weighting: {'equal' if args.no_weight else 'citation-weighted (log scale)'}\n")

        for pub in tqdm(to_embed_pubs, unit="pub"):
            # Use abstract if available, fall back to title
            text = pub.get("abstract") or pub.get("title") or ""
            if not text:
                continue
            emb = get_embedding(client, text, model=args.model)
            if emb:
                pub_cache[pub["id"]] = emb

        # Save pub cache
        with open(pub_cache_path, "w", encoding="utf-8") as f:
            json.dump(pub_cache, f)
        print(f"\nPub embeddings saved to {pub_cache_path}")
    else:
        print("All required publications already cached.")

    # ==========================================================================
    # Step 2: Compute per-faculty weighted average embeddings
    # ==========================================================================
    print("\nComputing faculty embeddings (citation-weighted averages)...")
    fac_cache_path = Path("output/faculty_embeddings.json")
    fac_cache = {}

    stats = {"embedded": 0, "skipped": 0, "avg_pubs_used": []}

    for fac in tqdm(active_fac, unit="faculty"):
        fid  = fac["id"]
        pubs = fac_pubs.get(fid, [])

        pairs = []  # (embedding, weight)
        for pub in pubs:
            emb = pub_cache.get(pub["id"])
            if emb is None:
                continue
            if args.no_weight:
                w = 1.0
            else:
                w = citation_weight(pub.get("citation_count") or 0)
            pairs.append((emb, w))

        if not pairs:
            tqdm.write(f"  Skipping {fac['name']} — no embedded publications")
            stats["skipped"] += 1
            continue

        avg_emb = weighted_average(pairs)
        if avg_emb:
            fac_cache[fid] = {
                "name":       fac["name"],
                "embedding":  avg_emb,
                "pubs_used":  len(pairs),
                "total_pubs": len(pubs),
                "weighted":   not args.no_weight,
            }
            stats["embedded"] += 1
            stats["avg_pubs_used"].append(len(pairs))

    with open(fac_cache_path, "w", encoding="utf-8") as f:
        json.dump(fac_cache, f)

    avg_pubs = sum(stats["avg_pubs_used"]) / max(len(stats["avg_pubs_used"]), 1)
    print(f"Faculty embedded: {stats['embedded']}  |  Skipped: {stats['skipped']}")
    print(f"Avg publications used per faculty: {avg_pubs:.1f}")
    print(f"Faculty embeddings saved to {fac_cache_path}")

    # ==========================================================================
    # Step 3: Pairwise cosine similarity
    # ==========================================================================
    print(f"\nComputing pairwise similarities...")
    fac_ids = list(fac_cache.keys())
    similar_edges = []

    for i in range(len(fac_ids)):
        for j in range(i + 1, len(fac_ids)):
            sim = cosine_similarity(fac_cache[fac_ids[i]]["embedding"],
                                    fac_cache[fac_ids[j]]["embedding"])
            if sim >= args.threshold:
                similar_edges.append({
                    "from":       fac_ids[i],
                    "to":         fac_ids[j],
                    "similarity": round(sim, 4),
                })

    print(f"Stored {len(similar_edges)} similarity pairs")

    # Show top 15 most similar
    top = sorted(similar_edges, key=lambda x: x["similarity"], reverse=True)[:15]
    fac_name = {f["id"]: f["name"] for f in faculty_list}
    print("\nTop 15 most similar faculty pairs:")
    for e in top:
        a = fac_name.get(e["from"], e["from"])
        b = fac_name.get(e["to"],   e["to"])
        print(f"  {a:<38} <-> {b:<38} {e['similarity']:.3f}")

    # ==========================================================================
    # Step 4: Write back to graph
    # ==========================================================================
    graph["edges"]["faculty_similar"] = similar_edges
    graph["meta"]["embedding_model"]          = args.model
    graph["meta"]["embedding_method"]         = "per-abstract citation-weighted average"
    graph["meta"]["embedding_weighted"]       = not args.no_weight
    graph["meta"]["similarity_threshold"]     = args.threshold
    graph["meta"]["embeddings_computed_at"]   = \
        __import__("datetime").datetime.utcnow().isoformat() + "Z"

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Similarity edges written to {graph_path}")
    print("Next: python3 compute_layout.py")


if __name__ == "__main__":
    main()
