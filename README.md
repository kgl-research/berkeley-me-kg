# Berkeley ME Research Map

An interactive map of the research landscape of the UC Berkeley Department of Mechanical Engineering, built from OpenAlex publication data and locally computed SPECTER2 embeddings.

**[→ Open the map](https://kgl-research.github.io/berkeley-me-kg)**

73 faculty (core, joint, graduate-school, emeritus, lecturers, adjunct) · 18,008 publications · 69 automatically discovered research areas in 20 groups · built 2026-10-17.

## What you can explore

| View | What it shows |
|---|---|
| **Map** | Faculty positioned by research similarity. Layouts: UMAP (local structure), MDS (global distances), PCA, or each person's centroid in the paper cloud. Toggle *career* vs *recent* vectors, or draw career→recent drift arrows. Colour by category, dominant research area, drift or breadth; overlay co-authorship or nearest-neighbour links. |
| **Paper cloud** | All 18k papers as points (UMAP of paper embeddings), coloured by research area, year or citations, with faculty centroids and area labels. A year slider / play button animates how the department's output grew; click a faculty centroid to light up their papers. |
| **Research areas** | The discovered areas (coarse: 20 groups · fine: 69 clusters) with c-TF-IDF labels, the matching OpenAlex topics, papers-per-year sparklines and the faculty who publish in them, plus a faculty × area heatmap. |
| **Similarity** | Faculty × faculty matrix: cosine, percentile rank, mean-centred cosine (for comparison), OpenAlex topic-profile similarity, co-authored papers, or "similar but never co-authored". Ordered by hierarchical clustering, category or name. |
| **Collaboration** | Intra-department co-authorship network (optionally with semantic neighbour links), and a ranked table of pairs with high similarity but no joint papers — potential collaborations. |
| **Trajectories** | Each faculty member's research centroid per 5-year era drawn as a path, and a ranking by research drift. |
| **Faculty / Compare / Publications** | Sortable metrics table; side-by-side comparison of up to four people; searchable publication database (titles, and abstracts once loaded) filterable by faculty, area and year. |
| **Methods** | Full methodology and the validation numbers for this build. |

Every profile panel shows the OpenAlex identity used, a confidence label and the notes behind it.

## Data sources

* **Roster, titles, research descriptions**: [me.berkeley.edu/faculty](https://me.berkeley.edu/faculty/), scraped per profile page.
* **Publications, citations, topics, affiliations**: [OpenAlex](https://openalex.org) works and author records (fetched 2026-10-17).
* **Embeddings**: [`allenai/specter2_base`](https://huggingface.co/allenai/specter2_base) with the [`allenai/specter2`](https://huggingface.co/allenai/specter2) proximity adapter, run locally on CPU. No external embedding API.

## Methodology (short version — the Methods tab has the long one)

1. **Identity.** Every faculty member is resolved to one or more OpenAlex author IDs by searching name variants and checking affiliations, topic profiles and sample papers against their department profile (`data/raw/author_map.json`, with notes and a confidence label per person). Split profiles are merged. Profiles that OpenAlex has merged with namesakes (e.g. James Casey + a historian of Spain) are cleaned with per-paper affiliation, topic and field filters.
2. **Corpus.** Paratext, retractions, errata, editorials, letters, machine translations and non-English records are dropped; duplicates merged by DOI; abstracts stripped of markup and boilerplate. A three-signal audit (`pipeline/audit_attribution.py`: implausible year, field mismatch without a plausible affiliation, and low leave-one-out similarity to the person's own papers) removed 58 further mis-attributed papers — all listed in `data/audit_attribution.json`.
3. **Embeddings.** `title [SEP] abstract` → SPECTER2 proximity CLS vector (768-d, unit length). Papers without an abstract in OpenAlex (6,150) are embedded from the title and flagged.
4. **Faculty vectors.** *Career* = weighted mean of paper vectors with weight `log(2 + citations)`; *recent* = weighted mean with `exp(-(2026 − year)/4)` (needs ≥ 8 papers in the last 10 years); *era* vectors = unweighted means over 5-year windows with ≥ 5 papers.
5. **Similarity space.** Raw cosine — deliberately. Mean-centring the vectors (the usual fix for the ≈0.9 baseline cosine of SPECTER embeddings) was evaluated against two independent signals and rejected: Spearman correlation with OpenAlex topic-profile similarity drops from 0.71 to 0.59 and co-authorship AUC from 0.84 to 0.83, and removing more principal directions makes it worse. Because raw cosines are compressed, the interface reports every pair's percentile rank among all faculty pairs next to the cosine.
6. **Layouts.** PCA; UMAP (cosine, n_neighbors 12, min_dist 0.5, initialised from PCA — chosen on 5-NN trust and global-distance correlation) fitted jointly on career, recent and era vectors; metric MDS on cosine distances. Paper cloud: PCA-50 → UMAP.
7. **Research areas.** HDBSCAN on a 5-D UMAP of the papers, with oversized clusters re-clustered recursively; outliers attached to the nearest area and flagged. Labels from class-based TF-IDF; fine areas grouped into coarse groups by average-linkage clustering of their centroids.
8. **Validation (this build).** Self-similarity/symmetry errors < 1e-6 · Spearman vs OpenAlex topics 0.71 · co-authorship AUC 0.84 (128 co-author pairs) · leave-one-out paper→own-faculty nearest-centroid accuracy 53.4 % over 70 faculty (chance 1.4 %).

## Repository layout

```
index.html                 the explorer (single file, D3 vendored in lib/)
output/explorer_data.json  faculty records, similarity matrices, areas, layouts, validation
output/papers.json         compact per-paper records (coordinates, area, faculty, citations)
output/abstracts.json      id → abstract (loaded on demand)
pipeline/fetch_openalex.py roster scrape · author candidate search · works + author download
pipeline/build_corpus.py   cleaning, deduplication, identity filters → data/works.jsonl, data/faculty.json
pipeline/embed_papers.py   SPECTER2 embeddings (CPU, resumable, text-hash cache)
pipeline/audit_attribution.py  three-signal mis-attribution audit (--apply to remove)
pipeline/analyze.py        faculty vectors, validation, layouts, clustering → output/
pipeline/add_researcher.py project an outside researcher into the map
data/raw/author_map.json   the identity decisions (ids, filters, confidence, notes)
data/raw/roster.json, me_faculty_profiles.json, authors.json   scraped inputs
data/audit_*.json          what was dropped and why
data/paper_embeddings_f16.npy  the 18k paper embeddings (float16 copy; float32 is regenerated)
legacy/                    the 2026-03 pipeline (OpenAI embeddings) kept for reference
```

## Rebuilding

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt            # torch (CPU), transformers, adapters, umap-learn, hdbscan, scikit-learn …

# model weights (~440 MB) — once
python3 -c "from huggingface_hub import snapshot_download as s; s('allenai/specter2_base', local_dir='models/specter2_base'); s('allenai/specter2', local_dir='models/specter2_adapter')"

export OPENALEX_API_KEY=...                # free key from your OpenAlex account (10,000 credits/day)
export OPENALEX_MAILTO=you@berkeley.edu

python3 pipeline/fetch_openalex.py roster          # me.berkeley.edu → data/raw/roster.json, profiles
python3 pipeline/fetch_openalex.py candidates      # OpenAlex author candidates → review, edit data/raw/author_map.json
python3 pipeline/fetch_openalex.py works authors   # ~200 credits for the whole department
python3 pipeline/build_corpus.py
python3 pipeline/embed_papers.py                   # ~1 h on 2 CPU cores for 18k papers; cached by text hash
python3 pipeline/audit_attribution.py --apply      # review the printed table first if you like
python3 pipeline/embed_papers.py                   # no-op unless texts changed
python3 pipeline/analyze.py                        # ~5 min
python3 -m http.server                             # open http://localhost:8000
```

Notes on OpenAlex credits (changed in 2025): anonymous access is 1,000 credits/day; an API key raises it to 10,000. Paged `/works` requests cost 1 credit per request (200 records), but an author *search* costs 1 credit per returned record — so use `search` sparingly and never paginate searches.

### Adding an outside researcher

```bash
python3 pipeline/add_researcher.py A5012345678     # OpenAlex author id
```
Fetches their works, embeds them with the same model and weighting, and writes `output/external.json`; the Map view draws them as dashed green nodes with their nearest faculty.

## Changes from the March 2026 version

* **Institution filter bug fixed.** The old scripts filtered OpenAlex authors by institution `I40120149` — that is the University of Oxford; UC Berkeley is `I95457486`. This was the main reason so many faculty needed manual fixing.
* **Identity corrections.** Shankar Sastry was mapped to a 5-paper stub instead of his real profile (1,271 works); Fernandez-Pello, Tomizuka, Sreenath, Açıkmeşe, Zohdi, Mehr and Alam had split profiles that are now merged; Casey, Chen, Wright, Lin, Taylor and Zhang have namesake contamination removed (hundreds of papers, including a historian's and several physicians').
* **Roster refreshed**: Açıkmeşe, Sangid, Rey Gomez, Miller, George Johnson and the lecturers added; Frenklach and Savaş moved to emeritus; Chaudhuri, Morris, Pagni and Prasher dropped (no longer listed).
* **Local embeddings** (SPECTER2, trained on scientific citation structure) replace OpenAI `text-embedding-3-small`; nothing leaves the machine.
* **Measured, not assumed.** Centring vs raw cosine, UMAP initialisation and the clustering granularity were chosen by validation against OpenAlex topics and co-authorship rather than by default.
* **New views**: paper cloud with time animation, discovered research areas at two granularities, MDS layout, drift arrows and era trajectories, collaboration network with "potential collaborators", similarity percentiles, per-profile identity notes.

## Limitations

* OpenAlex disambiguation remains imperfect; profiles marked *medium* confidence carry filters and may still contain or miss a few papers.
* About a third of records have no abstract in OpenAlex (many IEEE/ASME conference papers); those are embedded from the title alone.
* 2-D layouts distort distances — use the Similarity view and neighbour lists for pairwise questions.
* Citation-weighted career vectors emphasise older, well-cited work; the *recent* toggle shows current activity.
* Google Scholar would give better coverage for some people but has no usable API; OpenAlex works, DOIs and topics are the ground truth here.

## License

MIT (see `LICENSE`). D3 (`lib/d3.v7.min.js`) is ISC-licensed; OpenAlex data is CC0.
