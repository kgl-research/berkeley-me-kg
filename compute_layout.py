#!/usr/bin/env python3
"""
UC Berkeley ME Department — Research Space 2D Layout
=====================================================
Computes BOTH UMAP and PCA projections from faculty embedding vectors
and stores both sets of coordinates in knowledge_graph.json.
The explorer can then switch between them.

Requires Python 3.11 + venv_umap:
    source venv_umap/bin/activate
    pip install umap-learn numpy

Usage:
    python3 compute_layout.py
    python3 compute_layout.py --n-neighbors 10   # tighter UMAP clusters
    python3 compute_layout.py --min-dist 0.2     # more spread
    python3 compute_layout.py --seed 99          # different random layout
"""

import json
import sys
import argparse
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("Missing numpy. Run: pip install numpy")
    sys.exit(1)


def run_umap(matrix, n_neighbors, min_dist, seed):
    try:
        import umap
    except ImportError:
        print("umap-learn not installed in this environment.")
        print("Activate venv_umap and run: pip install umap-learn")
        return None
    print(f"Running UMAP (n_neighbors={n_neighbors}, min_dist={min_dist}, metric=cosine)...")
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric='cosine',
        random_state=seed,
        verbose=False,
    )
    return reducer.fit_transform(matrix)


def run_pca(matrix):
    print("Running PCA projection to 2D...")
    mean = matrix.mean(axis=0)
    centered = matrix - mean
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx = np.argsort(eigenvalues)[::-1]
    top2 = eigenvectors[:, idx[:2]]
    return centered @ top2


def normalize_coords(coords, width=900, height=700, padding=80):
    coords = np.array(coords, dtype=np.float64)
    min_x, min_y = coords[:, 0].min(), coords[:, 1].min()
    max_x, max_y = coords[:, 0].max(), coords[:, 1].max()
    rx = max_x - min_x or 1
    ry = max_y - min_y or 1
    out = np.zeros_like(coords)
    out[:, 0] = ((coords[:, 0] - min_x) / rx) * (width  - 2*padding) + padding
    out[:, 1] = ((coords[:, 1] - min_y) / ry) * (height - 2*padding) + padding
    return out


def main():
    parser = argparse.ArgumentParser(description="Compute UMAP + PCA faculty layouts")
    parser.add_argument("--n-neighbors", type=int,   default=15)
    parser.add_argument("--min-dist",    type=float, default=0.1)
    parser.add_argument("--seed",        type=int,   default=42)
    args = parser.parse_args()

    embeddings_path = Path("output/faculty_embeddings.json")
    graph_path      = Path("output/knowledge_graph.json")

    if not embeddings_path.exists():
        print(f"Error: {embeddings_path} not found. Run compute_embeddings.py first.")
        sys.exit(1)
    if not graph_path.exists():
        print(f"Error: {graph_path} not found. Run scrape_faculty.py first.")
        sys.exit(1)

    with open(embeddings_path, encoding="utf-8") as f:
        cache = json.load(f)
    with open(graph_path, encoding="utf-8") as f:
        graph = json.load(f)

    print(f"Loaded {len(cache)} faculty embeddings")

    fac_ids = list(cache.keys())
    matrix  = np.array([cache[fid]["embedding"] for fid in fac_ids], dtype=np.float32)
    print(f"Embedding matrix: {matrix.shape}")
    print()

    # Run both projections
    pca_raw  = run_pca(matrix)
    pca_2d   = normalize_coords(pca_raw)
    print("PCA done.")
    print()

    umap_raw = run_umap(matrix, args.n_neighbors, args.min_dist, args.seed)
    if umap_raw is not None:
        umap_2d = normalize_coords(umap_raw)
        print("UMAP done.")
    else:
        umap_2d = None
        print("UMAP failed — only PCA coordinates will be stored.")
    print()

    # Build coordinate maps
    pca_map  = {fid: {"x": float(pca_2d[i, 0]),  "y": float(pca_2d[i, 1])}  for i, fid in enumerate(fac_ids)}
    umap_map = {fid: {"x": float(umap_2d[i, 0]), "y": float(umap_2d[i, 1])} for i, fid in enumerate(fac_ids)} if umap_2d is not None else {}

    # Write into faculty nodes
    updated = 0
    for fac in graph["nodes"]["faculty"]:
        fid = fac["id"]
        if fid in pca_map:
            fac["layout_x"]      = pca_map[fid]["x"]   # default layout (PCA)
            fac["layout_y"]      = pca_map[fid]["y"]
            fac["pca_x"]         = pca_map[fid]["x"]
            fac["pca_y"]         = pca_map[fid]["y"]
        if fid in umap_map:
            fac["umap_x"]        = umap_map[fid]["x"]
            fac["umap_y"]        = umap_map[fid]["y"]
        updated += 1

    graph["meta"]["has_layout"]    = True
    graph["meta"]["has_umap"]      = umap_2d is not None
    graph["meta"]["layout_method"] = "UMAP + PCA"
    graph["meta"]["umap_params"]   = {
        "n_neighbors": args.n_neighbors,
        "min_dist":    args.min_dist,
        "metric":      "cosine",
        "seed":        args.seed,
    }

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"Updated {updated} faculty nodes with layout coordinates")
    print(f"Stored: pca_x/pca_y" + (" + umap_x/umap_y" if umap_2d is not None else " only"))
    print()

    # Print positions for sanity check
    print(f"{'Name':<40} {'PCA_x':>7} {'PCA_y':>7}" + (f"  {'UMAP_x':>7} {'UMAP_y':>7}" if umap_2d is not None else ""))
    print("-" * (40 + 16 + (18 if umap_2d is not None else 0)))
    for fid in fac_ids:
        name = cache[fid]["name"]
        px, py = pca_map[fid]["x"], pca_map[fid]["y"]
        if umap_2d is not None:
            ux, uy = umap_map[fid]["x"], umap_map[fid]["y"]
            print(f"  {name:<40} {px:7.1f} {py:7.1f}  {ux:7.1f} {uy:7.1f}")
        else:
            print(f"  {name:<40} {px:7.1f} {py:7.1f}")

    print()
    print("Done. Reload the explorer to see updated layout.")
    print("The explorer will let you toggle between UMAP and PCA views.")


if __name__ == "__main__":
    main()
