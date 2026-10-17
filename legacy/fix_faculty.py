#!/usr/bin/env python3
"""
Fix mismatched faculty OpenAlex IDs.
Looks up each problematic faculty member, shows candidates, and lets you
confirm the right one. Then re-fetches their publications.

Usage:
    python3 fix_faculty.py
"""

import json
import requests
import sys
from pathlib import Path

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "UCBerkeleyMEKnowledgeGraph/1.0 (mailto:kosa@berkeley.edu)"})

OPENALEX_BASE  = "https://api.openalex.org"
UC_BERKELEY_ID = "I40120149"

# Faculty to fix: (name_in_graph, search_name, known_openalex_id or None)
TO_FIX = [
    ("M. Reza Alam",          "M. Reza Alam",           "A5033988175"),
    ("Homayoon Kazerooni",    "Homayoon Kazerooni",     "A5077696000"),
    ("Philip S. Marcus",      "Philip S. Marcus",        "A5067592185"),
    ("Paul K. Wright",        "Paul K. Wright",          "A5102817905"),
    ("James Casey",           "James Casey",             "A5080775953"),
    ("Kyriakos Komvopoulos",  "Kyriakos Komvopoulos",   "A5085102760"),
    ("Jyh-Yuan Chen",         "Jyh-Yuan Chen",           "A5041673125"),
    ("Dennis K. Lieu",        "Dennis Lieu",             "A5109856231"),
    ("Ralph Greif",           "Ralph Greif",             "A5072930401"),
    ("Negar Mehr",            "Negar Mehr",              "A5062267932"),
]


def search_author(name, with_berkeley=True):
    """Try multiple name variations to find the right author."""
    # Build a list of name variants to try
    parts = name.split()
    variants = [
        name,
        parts[-1],                                    # last name only
        parts[0][0] + " " + parts[-1],               # first initial + last
        " ".join(parts[1:]) if len(parts) > 1 else name,  # drop first name
    ]
    for variant in variants:
        params = {"per_page": 5}
        if with_berkeley:
            params["filter"] = f"display_name.search:{variant},last_known_institutions.id:{UC_BERKELEY_ID}"
        else:
            params["filter"] = f"display_name.search:{variant}"
        try:
            r = SESSION.get(f"{OPENALEX_BASE}/authors", params=params, timeout=20)
            results = r.json().get("results", []) if r.status_code == 200 else []
            if results:
                return results
        except Exception:
            pass
    return []


def fetch_works(openalex_id):
    """Fetch all works for an author from OpenAlex."""
    works = []
    page, per_page = 1, 100
    while True:
        r = SESSION.get(f"{OPENALEX_BASE}/works", params={
            "filter": f"authorships.author.id:{openalex_id}",
            "per_page": per_page, "page": page,
            "select": "id,title,publication_year,primary_location,authorships,cited_by_count,abstract_inverted_index,doi",
        }, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        batch = data.get("results", [])
        if not batch:
            break
        total = data.get("meta", {}).get("count", 0)
        for work in batch:
            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
            source = (work.get("primary_location") or {}).get("source") or {}
            authorships = work.get("authorships", [])
            authors_raw = ", ".join(a.get("author",{}).get("display_name","") for a in authorships[:20])
            works.append({
                "title":          work.get("title","") or "",
                "year":           str(work.get("publication_year","") or ""),
                "journal":        source.get("display_name",""),
                "abstract":       abstract,
                "citation_count": work.get("cited_by_count",0),
                "authors_raw":    authors_raw,
                "doi":            work.get("doi","") or "",
                "openalex_url":   work.get("id","") or "",
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


def slugify(text):
    import re
    text = str(text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:100]


def make_pub_id(title, year):
    return slugify(str(title))[:72] + f"_{year}"


def main():
    graph_path = Path("output/knowledge_graph.json")
    if not graph_path.exists():
        print("Error: output/knowledge_graph.json not found")
        sys.exit(1)

    with open(graph_path, encoding="utf-8") as f:
        graph = json.load(f)

    fac_by_name = {f["name"]: f for f in graph["nodes"]["faculty"]}
    pub_nodes   = {p["id"]: p for p in graph["nodes"]["publications"]}
    journal_nodes = {j["id"]: j for j in graph["nodes"]["journals"]}
    authored_edges = graph["edges"]["faculty_authored"]
    pub_journal_edges = graph["edges"]["pub_in_journal"]

    confirmed = {}  # name -> openalex author object

    for display_name, search_name, known_id in TO_FIX:
        fac = fac_by_name.get(display_name)
        if not fac:
            print(f"\nSkipping {display_name} — not found in graph")
            continue

        print(f"\n{'='*60}")
        print(f"Faculty:  {display_name}")
        print(f"Current OpenAlex ID:  {fac.get('openalex_id','none')}")
        print(f"Current citations:    {fac.get('total_citations',0):,}")

        # If we already know the correct ID, fetch directly — no search needed
        if known_id:
            print(f"  Using known ID: {known_id}")
            r = SESSION.get(f"{OPENALEX_BASE}/authors/{known_id}", timeout=20)
            if r.status_code == 200:
                author = r.json()
                confirmed[display_name] = author
                print(f"  ✓ Auto-confirmed: {author.get('display_name','')} ({known_id})")
                print(f"    Citations: {author.get('cited_by_count',0):,}  |  Works: {author.get('works_count',0)}")
            else:
                print(f"  Failed to fetch ID {known_id}, falling back to search...")
                known_id = None

        if not known_id:
            candidates = search_author(search_name, with_berkeley=True)
            if not candidates:
                print("  No Berkeley results — trying broader search...")
                candidates = search_author(search_name, with_berkeley=False)

            if not candidates:
                print("  No candidates found. Skipping.")
                continue

            print(f"\n  Candidates:")
            for i, c in enumerate(candidates):
                inst = (c.get("last_known_institutions") or [{}])[0].get("display_name","unknown")
                oa_id = c["id"].split("/")[-1]
                print(f"\n  [{i}] {c['display_name']}")
                print(f"       ID: {oa_id}  |  Citations: {c.get('cited_by_count',0):,}  |  Works: {c.get('works_count',0)}")
                print(f"       Institution: {inst}")
                try:
                    r = SESSION.get(f"{OPENALEX_BASE}/works", params={
                        "filter": f"authorships.author.id:{oa_id}",
                        "per_page": 3, "page": 1,
                        "sort": "cited_by_count:desc",
                        "select": "title,publication_year,cited_by_count,primary_location",
                    }, timeout=15)
                    if r.status_code == 200:
                        samples = r.json().get("results", [])
                        if samples:
                            print(f"       Top publications:")
                            for s in samples:
                                venue = ((s.get("primary_location") or {}).get("source") or {}).get("display_name","")
                                cites = s.get("cited_by_count", 0)
                                year  = s.get("publication_year", "")
                                title = (s.get("title") or "")[:70]
                                print(f"         • {title}")
                                print(f"           {venue} {year} · {cites:,} citations")
                except Exception:
                    pass

            choice = input(f"\n  Select [0-{len(candidates)-1}] or 's' to skip: ").strip()
            if choice.lower() == 's' or not choice:
                print("  Skipped.")
                continue

            try:
                selected = candidates[int(choice)]
                confirmed[display_name] = selected
                print(f"  ✓ Confirmed: {selected['display_name']} ({selected['id'].split('/')[-1]})")
            except (ValueError, IndexError):
                print("  Invalid input, skipped.")

    if not confirmed:
        print("\nNo changes made.")
        return

    # For each confirmed faculty: update metadata + re-fetch publications
    print(f"\n{'='*60}")
    print(f"Updating {len(confirmed)} faculty members...")

    for display_name, author in confirmed.items():
        fac = fac_by_name[display_name]
        fid = fac["id"]
        new_id = author["id"].split("/")[-1]

        # Update faculty node
        fac.update({
            "openalex_id":     new_id,
            "openalex_url":    author["id"],
            "openalex_found":  True,
            "total_citations": author.get("cited_by_count", 0),
            "works_count":     author.get("works_count", 0),
            "h_index":         author.get("summary_stats", {}).get("h_index", 0),
            "i10_index":       author.get("summary_stats", {}).get("i10_index", 0),
            "affiliation":     (author.get("last_known_institutions") or [{}])[0].get("display_name",""),
            "interests":       [t.get("display_name","") for t in (author.get("topics") or [])[:8]],
        })

        # Remove old authored edges for this faculty
        authored_edges[:] = [e for e in authored_edges if e["from"] != fid]

        # Fetch publications
        print(f"\n  Fetching publications for {display_name} ({new_id})...")
        works = fetch_works(new_id)
        print(f"  Found {len(works)} works")

        for work in works:
            if not work["title"]:
                continue
            pid = make_pub_id(work["title"], work["year"])

            if pid not in pub_nodes:
                pub_nodes[pid] = {
                    "id":             pid,
                    "title":          work["title"],
                    "year":           work["year"],
                    "journal":        work["journal"],
                    "abstract":       work["abstract"],
                    "citation_count": work["citation_count"],
                    "authors_raw":    work["authors_raw"],
                    "doi":            work["doi"],
                    "openalex_url":   work["openalex_url"],
                }
                jname = work["journal"]
                if jname:
                    jid = slugify(jname)
                    if jid not in journal_nodes:
                        journal_nodes[jid] = {"id": jid, "name": jname}
                        pub_journal_edges.append({"from": pid, "to": jid})

            authored_edges.append({"from": fid, "to": pid, "year": work["year"]})

        print(f"  Done: {len(works)} publications added")

    # Rebuild graph
    graph["nodes"]["faculty"]      = list(fac_by_name.values())
    graph["nodes"]["publications"] = list(pub_nodes.values())
    graph["nodes"]["journals"]     = list(journal_nodes.values())
    graph["edges"]["faculty_authored"]  = authored_edges
    graph["edges"]["pub_in_journal"]    = pub_journal_edges

    # Rebuild co-authorship edges
    from collections import defaultdict
    pub_to_fac = defaultdict(list)
    for e in authored_edges:
        pub_to_fac[e["to"]].append(e["from"])
    coauthored = []
    for pid, fids in pub_to_fac.items():
        unique = list(dict.fromkeys(fids))
        if len(unique) < 2:
            continue
        for i in range(len(unique)):
            for j in range(i+1, len(unique)):
                coauthored.append({"from": unique[i], "to": unique[j], "via_publication": pid})
    graph["edges"]["faculty_coauthored"] = coauthored

    # Update meta
    graph["meta"]["total_faculty"]  = len(graph["nodes"]["faculty"])
    graph["meta"]["total_pubs"]     = len(graph["nodes"]["publications"])
    graph["meta"]["total_journals"] = len(graph["nodes"]["journals"])

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved updated graph to {graph_path}")
    print(f"  Publications: {len(graph['nodes']['publications']):,}")
    print(f"  Authored edges: {len(authored_edges):,}")
    print("\nDon't forget to re-run:")
    print("  python3 compute_embeddings.py  (to update similarity scores)")
    print("  python3 compute_layout.py      (to update 2D positions)")


if __name__ == "__main__":
    main()
