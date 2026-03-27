# Department Research Knowledge Graph

An interactive map of a university department's research landscape, built from faculty publication data using semantic embeddings and dimensionality reduction.

**[→ View the UC Berkeley ME Department Map](https://kgl-research.github.io/berkeley-me-kg)**

---

## What it shows

The map positions faculty by research similarity — faculty whose publication abstracts are semantically similar appear close together. Four views are available:

- **Research Space** — scatter plot of faculty positioned by UMAP/PCA projection of publication embeddings. Toggle between UMAP (better local clusters) and PCA (better global structure). Node size reflects fused impact score (h-index + citations + publication count).
- **Faculty Table** — sortable by any metric, filterable by category and keyword.
- **Publications** — searchable database of all publications. Filter by faculty, year, or keyword across titles and abstracts.
- **Compare** — select up to 4 faculty to view side by side.

---

## Build your own map

### Requirements

- Python 3.11 (for UMAP) — install via [pyenv](https://github.com/pyenv/pyenv)
- Python 3.x for everything else
- An [OpenAI API key](https://platform.openai.com/api-keys) (embeddings cost ~$0.05–0.50 for a department)
- An [OpenAlex](https://openalex.org) account (free, no key needed)

### Setup

```bash
git clone https://github.com/kgl-research/berkeley-me-kg
cd berkeley-me-kg

# Main environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# UMAP environment (requires Python 3.11)
brew install pyenv
pyenv install 3.11
pyenv local 3.11
python3 -m venv venv_umap
source venv_umap/bin/activate
pip install -r requirements_umap.txt

export OPENAI_API_KEY="sk-..."
```

### 1. Edit the faculty roster

Open `scrape_faculty.py` and replace the `FACULTY` dictionary with your department's faculty. Each entry needs a name and faculty page URL:

```python
FACULTY = {
    "core": [
        {"name": "Jane Smith", "openalex_id": "", "url": "https://dept.edu/people/jane-smith/"},
        ...
    ],
    "emeritus": [...],
}
```

Set `OPENALEX_EMAIL` to your email for higher OpenAlex rate limits.

### 2. Run the pipeline

```bash
# Activate main environment
source venv/bin/activate

# Step 1: Scrape faculty publications from OpenAlex (~10–20 min)
python3 scrape_faculty.py

# Step 2: Fix any incorrect OpenAlex matches (interactive)
python3 fix_faculty.py

# Step 3: Compute embeddings (~$0.05–0.50, ~5–15 min)
python3 compute_embeddings.py

# Step 4: Compute 2D layout (switch to UMAP environment)
deactivate
source venv_umap/bin/activate
python3 compute_layout.py
```

Output is written to `output/knowledge_graph.json`.

### 3. View the map

Open `knowledge_graph_explorer.html` in a browser and load `output/knowledge_graph.json` via the file picker.

---

## Fixing incorrect faculty matches

OpenAlex sometimes matches the wrong person, especially for faculty with common names. Run `fix_faculty.py` to interactively correct matches — it shows sample publications for each candidate so you can confirm the right person.

For faculty you've already found the correct OpenAlex ID for, add it directly to the `TO_FIX` list in `fix_faculty.py`:

```python
TO_FIX = [
    ("Faculty Name", "Search Name", "A1234567890"),  # known ID — auto-confirmed
    ("Another Name", "Search Name", None),            # unknown — will prompt
]
```

Find the correct OpenAlex ID by searching at [openalex.org](https://openalex.org) and copying the author ID from the URL.

---

## Adding external researchers

To project a researcher from outside your department into the map:

```bash
source venv_umap/bin/activate

# Add one or more researchers by OpenAlex ID
python3 add_researcher.py --openalex-id A1234567890
python3 add_researcher.py --openalex-id A1234567890 A9876543210 A5555555555

# List added researchers
python3 add_researcher.py --list

# Remove an added researcher
python3 add_researcher.py --remove "Researcher Name"
```

Added researchers appear as dashed green circles in the map, positioned by nearest-neighbor interpolation from their most similar existing faculty. The existing map doesn't change.

---

## Publishing to GitHub Pages

1. Create a GitHub repository
2. Copy `index.html` and `output/knowledge_graph.json` into the repo root
3. Go to **Settings → Pages → Source: Deploy from branch → main → / (root)**
4. Your map will be live at `https://yourusername.github.io/repo-name`

`index.html` automatically fetches `knowledge_graph.json` on load — no file picker needed.

---

## Methodology

**Data source:** [OpenAlex](https://openalex.org) — open, free scholarly data with no rate limits for polite use.

**Embeddings:** Each publication abstract is embedded independently using OpenAI `text-embedding-3-small`. Each faculty member's embedding is a citation-weighted average of their publication embeddings, where the weight for each paper is `log(1 + citations) + 0.1`. Log scaling prevents a single highly-cited paper from dominating the representation.

**Layout:** Two projections are computed and stored:
- **UMAP** (default) — better local structure, clusters semantically similar faculty together
- **PCA** — better global structure, more interpretable axes

**Similarity:** Cosine similarity between faculty embedding vectors, computed in the full 1,536-dimensional space. The percentages shown in the detail panel are more reliable than the 2D map positions for pairwise comparison.

**Limitations:**
- OpenAlex abstract coverage varies — some faculty have few or no abstracts available
- Faculty with common names may be incorrectly matched in OpenAlex (use `fix_faculty.py`)
- Cosine similarity captures vocabulary overlap, not disciplinary context — faculty using similar technical terms may appear similar even if their research goals differ
- PCA and UMAP both lose information in the projection to 2D

---

## Built with

- [OpenAlex](https://openalex.org) — open scholarly metadata
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings) — semantic text embeddings
- [UMAP](https://umap-learn.readthedocs.io) — dimensionality reduction
- [D3.js](https://d3js.org) — interactive visualization
