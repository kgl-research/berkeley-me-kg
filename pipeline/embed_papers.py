#!/usr/bin/env python3
"""
Embed publications locally with SPECTER2 (allenai/specter2_base + proximity adapter).

Input : data/works.jsonl         (one OpenAlex work per line; see fetch step)
Output: data/paper_embeddings.npy (float32, N x 768, L2-normalised rows)
        data/paper_index.json     (row -> work id, plus 'text_kind': 'title+abstract' | 'title')

Runs on CPU. Batches are length-sorted to minimise padding. Resumable: rows already
present in the .npy are skipped on re-run.

Usage:
    python3 pipeline/embed_papers.py [--model-dir models] [--batch 16] [--max-len 512]
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent


def load_model(model_dir):
    from transformers import AutoTokenizer
    from adapters import AutoAdapterModel
    tok = AutoTokenizer.from_pretrained(model_dir / "specter2_base")
    model = AutoAdapterModel.from_pretrained(model_dir / "specter2_base")
    model.load_adapter(str(model_dir / "specter2_adapter"), load_as="proximity", set_active=True)
    model.eval()
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    return tok, model


def paper_text(w, sep):
    title = (w.get("title") or "").strip()
    abstract = (w.get("abstract") or "").strip()
    if abstract:
        return title + sep + abstract, "title+abstract"
    return title, "title"


@torch.no_grad()
def embed_batch(tok, model, texts, max_len):
    inp = tok(texts, padding=True, truncation=True, max_length=max_len, return_tensors="pt")
    out = model(**inp)
    cls = out.last_hidden_state[:, 0, :]
    return torch.nn.functional.normalize(cls, dim=1).cpu().numpy().astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default=str(ROOT.parent / "models"))
    ap.add_argument("--works", default=str(ROOT / "data" / "works.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "paper_embeddings.npy"))
    ap.add_argument("--index", default=str(ROOT / "data" / "paper_index.json"))
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cache-from", nargs="*", default=[], help="extra (npy,index.json) pairs as npy:index to reuse embeddings from")
    args = ap.parse_args()

    works = []
    with open(args.works) as f:
        for line in f:
            if line.strip():
                works.append(json.loads(line))
    if args.limit:
        works = works[: args.limit]
    print(f"{len(works)} works")

    tok, model = load_model(Path(args.model_dir))
    sep = tok.sep_token

    texts, kinds, ids, hashes = [], [], [], []
    for w in works:
        t, k = paper_text(w, sep)
        texts.append(t); kinds.append(k); ids.append(w["id"]); hashes.append(hashlib.md5(t.encode()).hexdigest()[:12])

    # resume support
    done = {}
    for pair in args.cache_from:
        npy, idxf = pair.split(":")
        if os.path.exists(npy) and os.path.exists(idxf):
            cidx = json.load(open(idxf)); cemb = np.load(npy)
            hs = cidx.get("hash") or [None] * len(cidx["ids"])
            for row, pid in enumerate(cidx["ids"]):
                if np.any(cemb[row]):
                    done[(pid, hs[row])] = cemb[row]
            print(f"cache {npy}: {len(done)} usable")
    if os.path.exists(args.out) and os.path.exists(args.index):
        prev = json.load(open(args.index))
        prev_emb = np.load(args.out)
        hs = prev.get("hash") or [None] * len(prev["ids"])
        for row, pid in enumerate(prev["ids"]):
            if np.any(prev_emb[row]):
                done[(pid, hs[row])] = prev_emb[row]
        print(f"resuming: {len(done)} already embedded")

    emb = np.zeros((len(works), 768), dtype=np.float32)
    todo = [i for i, pid in enumerate(ids) if (pid, hashes[i]) not in done]
    for i, pid in enumerate(ids):
        if (pid, hashes[i]) in done:
            emb[i] = done[(pid, hashes[i])]

    # length-sorted batching
    todo.sort(key=lambda i: len(texts[i]))
    t0 = time.time(); n = 0
    for b in range(0, len(todo), args.batch):
        idx = todo[b : b + args.batch]
        emb[idx] = embed_batch(tok, model, [texts[i] for i in idx], args.max_len)
        n += len(idx)
        if (b // args.batch) % 25 == 0:
            rate = n / max(1e-6, time.time() - t0)
            eta = (len(todo) - n) / max(rate, 1e-6)
            print(f"  {n}/{len(todo)}  {rate:.1f} papers/s  eta {eta/60:.1f} min", flush=True)
            if (b // args.batch) % 200 == 0 and n > 0:
                np.save(args.out, emb)
                json.dump({"ids": ids, "text_kind": kinds, "hash": hashes}, open(args.index, "w"))
    np.save(args.out, emb)
    json.dump({"ids": ids, "text_kind": kinds, "hash": hashes}, open(args.index, "w"))
    print(f"done {n} new embeddings in {(time.time()-t0)/60:.1f} min -> {args.out}")


if __name__ == "__main__":
    main()
