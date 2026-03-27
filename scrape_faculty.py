#!/usr/bin/env python3
"""
UC Berkeley ME Department — Faculty Publication Knowledge Graph Builder
=======================================================================
Uses the FREE OpenAlex API — no rate limiting, no CAPTCHAs, no Scholar blocks.
Only requires the `requests` library (usually already installed).

Installation:
    pip install requests tqdm

Usage:
    python3 scrape_faculty.py                          # all faculty, all pubs
    python3 scrape_faculty.py --categories core joint  # subset
    python3 scrape_faculty.py --faculty "Kosa Goucher-Lambert"  # single person
    python3 scrape_faculty.py --resume                 # continue after interruption

Outputs written to ./output/:
    knowledge_graph.json
    csv/  (6 CSV files)
    neo4j/import.cypher
    checkpoint.json
    scrape.log
"""

import json
import csv
import time
import logging
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from urllib.parse import quote

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("Missing dependencies. Run:  pip install requests tqdm")
    sys.exit(1)

# OpenAlex polite pool — just add your email and you get higher rate limits
# https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
OPENALEX_EMAIL = "your@email.com"   # <-- optionally replace with your email
OPENALEX_BASE  = "https://api.openalex.org"
UC_BERKELEY_ID = "I40120149"        # OpenAlex institution ID for UC Berkeley

# =============================================================================
# FACULTY ROSTER
# openalex_id: the author's OpenAlex ID (format: A123456789)
# If blank, we search by name + UC Berkeley affiliation.
# =============================================================================

FACULTY = {

    "core": [
        {"name": "M. Reza Alam",            "openalex_id": "A5033988175", "url": "https://me.berkeley.edu/people/m-reza-alam/"},
        {"name": "Francesco Borrelli",       "openalex_id": "", "url": "https://me.berkeley.edu/people/francesco-borrelli/"},
        {"name": "Van P. Carey",             "openalex_id": "", "url": "https://me.berkeley.edu/people/van-p-carey/"},
        {"name": "Chris Dames",              "openalex_id": "", "url": "https://me.berkeley.edu/people/chris-dames/"},
        {"name": "Michael Frenklach",        "openalex_id": "", "url": "https://me.berkeley.edu/people/michael-frenklach/"},
        {"name": "Michael Gollner",          "openalex_id": "", "url": "https://me.berkeley.edu/people/michael-gollner/"},
        {"name": "Kosa Goucher-Lambert",     "openalex_id": "", "url": "https://me.berkeley.edu/people/kosa-goucher-lambert/"},
        {"name": "Costas Grigoropoulos",     "openalex_id": "", "url": "https://me.berkeley.edu/people/costas-grigoropoulos/"},
        {"name": "Grace X. Gu",              "openalex_id": "", "url": "https://me.berkeley.edu/people/grace-x-gu/"},
        {"name": "Claudio Hail",             "openalex_id": "", "url": "https://me.berkeley.edu/people/claudio-hail/"},
        {"name": "Roberto Horowitz",         "openalex_id": "", "url": "https://me.berkeley.edu/people/roberto-horowitz/"},
        {"name": "Alexis Kaminski",          "openalex_id": "", "url": "https://me.berkeley.edu/people/alexis-kaminski/"},
        {"name": "Ken Kamrin",               "openalex_id": "", "url": "https://me.berkeley.edu/people/ken-kamrin/"},
        {"name": "Homayoon Kazerooni",       "openalex_id": "A5077696000", "url": "https://me.berkeley.edu/people/homayoon-kazerooni/"},
        {"name": "Kyriakos Komvopoulos",     "openalex_id": "A5085102760", "url": "https://me.berkeley.edu/people/kyriakos-komvopoulos/"},
        {"name": "Liwei Lin",                "openalex_id": "", "url": "https://me.berkeley.edu/people/liwei-lin/"},
        {"name": "Fai Ma",                   "openalex_id": "", "url": "https://me.berkeley.edu/people/fai-ma/"},
        {"name": "Simo Makiharju",           "openalex_id": "", "url": "https://me.berkeley.edu/people/simo-makiharju/"},
        {"name": "Sara McMains",             "openalex_id": "", "url": "https://me.berkeley.edu/people/sara-mcmains/"},
        {"name": "Negar Mehr",               "openalex_id": "A5062267932", "url": "https://me.berkeley.edu/people/negar-mehr/"},
        {"name": "Mohammad R. K. Mofrad",    "openalex_id": "", "url": "https://me.berkeley.edu/people/mohammad-r-k-mofrad/"},
        {"name": "Mark W. Mueller",          "openalex_id": "", "url": "https://me.berkeley.edu/people/mark-w-mueller/"},
        {"name": "Grace D. O'Connell",       "openalex_id": "", "url": "https://me.berkeley.edu/people/grace-d-oconnell/"},
        {"name": "Oliver M. O'Reilly",       "openalex_id": "", "url": "https://me.berkeley.edu/people/oliver-m-oreilly/"},
        {"name": "Panayiotis Papadopoulos",  "openalex_id": "", "url": "https://me.berkeley.edu/people/panayiotis-papadopoulos/"},
        {"name": "Kameshwar Poolla",         "openalex_id": "", "url": "https://me.berkeley.edu/people/kameshwar-poolla/"},
        {"name": "Lisa Pruitt",              "openalex_id": "", "url": "https://me.berkeley.edu/people/lisa-pruitt/"},
        {"name": "Omer Savas",               "openalex_id": "", "url": "https://me.berkeley.edu/people/omer-savas/"},
        {"name": "Thomas Schutzius",         "openalex_id": "", "url": "https://me.berkeley.edu/people/thomas-schutzius/"},
        {"name": "Shawn Shadden",            "openalex_id": "", "url": "https://me.berkeley.edu/people/shawn-shadden/"},
        {"name": "Lydia Sohn",               "openalex_id": "", "url": "https://me.berkeley.edu/people/lydia-sohn/"},
        {"name": "Koushil Sreenath",         "openalex_id": "", "url": "https://me.berkeley.edu/people/koushil-sreenath/"},
        {"name": "David Steigmann",          "openalex_id": "", "url": "https://me.berkeley.edu/people/david-steigmann/"},
        {"name": "Hannah Stuart",            "openalex_id": "", "url": "https://me.berkeley.edu/people/hannah-stuart/"},
        {"name": "Hayden Taylor",            "openalex_id": "", "url": "https://me.berkeley.edu/people/hayden-taylor/"},
        {"name": "Masayoshi Tomizuka",       "openalex_id": "", "url": "https://me.berkeley.edu/people/masayoshi-tomizuka/"},
        {"name": "Lining Yao",               "openalex_id": "", "url": "https://me.berkeley.edu/people/lining-yao/"},
        {"name": "Tarek I. Zohdi",           "openalex_id": "", "url": "https://me.berkeley.edu/people/tarek-i-zohdi/"},
    ],

    "joint": [
        {"name": "Murat Arcak",              "openalex_id": "", "url": "https://me.berkeley.edu/people/murat-arcak/"},
        {"name": "Saikat Chaudhuri",         "openalex_id": "", "url": "https://me.berkeley.edu/people/saikat-chaudhuri/"},
        {"name": "Peter Hosemann",           "openalex_id": "", "url": "https://me.berkeley.edu/people/peter-hosemann/"},
        {"name": "Dorian Liepmann",          "openalex_id": "", "url": "https://me.berkeley.edu/people/dorian-liepmann/"},
        {"name": "Robert O. Ritchie",        "openalex_id": "", "url": "https://me.berkeley.edu/people/robert-o-ritchie/"},
        {"name": "S. Shankar Sastry",        "openalex_id": "", "url": "https://me.berkeley.edu/people/s-shankar-sastry/"},
        {"name": "Somayeh Sojoudi",          "openalex_id": "", "url": "https://me.berkeley.edu/people/somayeh-sojoudi/"},
    ],

    "grad_school": [
        {"name": "Alice M. Agogino",         "openalex_id": "", "url": "https://me.berkeley.edu/people/alice-m-agogino/"},
        {"name": "David B. Bogy",            "openalex_id": "", "url": "https://me.berkeley.edu/people/david-b-bogy/"},
        {"name": "Carlos Fernandez-Pello",   "openalex_id": "", "url": "https://me.berkeley.edu/people/carlos-fernandez-pello/"},
        {"name": "Boris Rubinsky",           "openalex_id": "", "url": "https://me.berkeley.edu/people/boris-rubinsky/"},
    ],

    "emeritus": [
        {"name": "David M. Auslander",       "openalex_id": "", "url": "https://me.berkeley.edu/people/david-m-auslander/"},
        {"name": "James Casey",              "openalex_id": "A5080775953", "url": "https://me.berkeley.edu/people/james-casey/"},
        {"name": "Jyh-Yuan Chen",            "openalex_id": "A5041673125", "url": "https://me.berkeley.edu/people/jyh-yuan-chen/"},
        {"name": "Robert Dibble",            "openalex_id": "", "url": "https://me.berkeley.edu/people/robert-dibble/"},
        {"name": "Ralph Greif",              "openalex_id": "A5072930401", "url": "https://me.berkeley.edu/people/ralph-greif/"},
        # George Johnson — correct OpenAlex ID not found, excluded from graph
        {"name": "Tony M. Keaveny",          "openalex_id": "", "url": "https://me.berkeley.edu/people/tony-m-keaveny/"},
        {"name": "Dennis K. Lieu",           "openalex_id": "A5109856231", "url": "https://me.berkeley.edu/people/dennis-k-lieu/"},
        {"name": "Philip S. Marcus",         "openalex_id": "A5067592185", "url": "https://me.berkeley.edu/people/philip-s-marcus/"},
        {"name": "Stephen Morris",           "openalex_id": "", "url": "https://me.berkeley.edu/people/stephen-morris/"},
        {"name": "Patrick J. Pagni",         "openalex_id": "", "url": "https://me.berkeley.edu/people/patrick-j-pagni/"},
        {"name": "Benson H. Tongue",         "openalex_id": "", "url": "https://me.berkeley.edu/people/benson-h-tongue/"},
        {"name": "Paul K. Wright",           "openalex_id": "A5102817905", "url": "https://me.berkeley.edu/people/paul-k-wright/"},
        {"name": "Kazuo Yamazaki",           "openalex_id": "", "url": "https://me.berkeley.edu/people/kazuo-yamazaki/"},
        {"name": "Ronald W. Yeung",          "openalex_id": "", "url": "https://me.berkeley.edu/people/ronald-w-yeung/"},
        {"name": "Xiang Zhang",              "openalex_id": "", "url": "https://me.berkeley.edu/people/xiang-zhang/"},
    ],

    "adjunct": [
        {"name": "David Horsley",            "openalex_id": "", "url": "https://me.berkeley.edu/people/david-horsley/"},
        {"name": "Samuel Mao",               "openalex_id": "", "url": "https://me.berkeley.edu/people/samuel-mao/"},
        {"name": "Ravi Prasher",             "openalex_id": "", "url": "https://me.berkeley.edu/people/ravi-prasher/"},
        {"name": "Vassilia Zorba",           "openalex_id": "", "url": "https://me.berkeley.edu/people/vassilia-zorba/"},
    ],
}

ALL_CATEGORIES = list(FACULTY.keys())


# =============================================================================
# Utilities
# =============================================================================

def slugify(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:100]

def make_pub_id(title, year):
    return slugify(str(title))[:72] + f"_{year}"

def setup_logging(log_file):
    log = logging.getLogger("kg_builder")
    log.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
    fh.setFormatter(fmt); ch.setFormatter(fmt)
    log.addHandler(fh); log.addHandler(ch)
    return log


# =============================================================================
# OpenAlex API helpers
# =============================================================================

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"UCBerkeleyMEKnowledgeGraph/1.0 (mailto:{OPENALEX_EMAIL})"})

def oa_get(url, params=None, log=None, retries=5):
    """GET from OpenAlex with retry on failure."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = 10 * (attempt + 1)
                if log: log.warning(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                if log: log.warning(f"  HTTP {r.status_code} for {url}")
                time.sleep(2 ** attempt)
        except Exception as e:
            wait = 2 ** attempt
            if log: log.warning(f"  Request failed (attempt {attempt+1}): {e} | waiting {wait}s")
            time.sleep(wait)
    return None


def find_author_by_id(openalex_id, log):
    """Fetch author directly by OpenAlex ID."""
    url = f"{OPENALEX_BASE}/authors/{openalex_id}"
    return oa_get(url, log=log)


def find_author_by_name(name, log):
    """
    Search for an author by name, filtering to UC Berkeley.
    Returns the best match or None.
    """
    # First try: name search filtered to UC Berkeley
    data = oa_get(
        f"{OPENALEX_BASE}/authors",
        params={
            "filter": f"display_name.search:{name},last_known_institutions.id:{UC_BERKELEY_ID}",
            "per_page": 5,
        },
        log=log,
    )
    if data and data.get("results"):
        return data["results"][0]

    # Second try: name search without institution filter
    data = oa_get(
        f"{OPENALEX_BASE}/authors",
        params={
            "filter": f"display_name.search:{name}",
            "per_page": 5,
        },
        log=log,
    )
    if data and data.get("results"):
        # Pick the one with highest citation count as best guess
        results = sorted(data["results"], key=lambda x: x.get("cited_by_count", 0), reverse=True)
        return results[0]

    return None


def fetch_all_works(author_id, log):
    """
    Fetch ALL works for an author using OpenAlex pagination.
    Returns a list of work dicts with title, abstract, authors, journal, year, citations.
    """
    works = []
    page = 1
    per_page = 100  # max allowed by OpenAlex
    total = None

    while True:
        data = oa_get(
            f"{OPENALEX_BASE}/works",
            params={
                "filter": f"authorships.author.id:{author_id}",
                "per_page": per_page,
                "page": page,
                "select": "id,title,publication_year,primary_location,authorships,cited_by_count,abstract_inverted_index,doi",
            },
            log=log,
        )
        if not data:
            break

        if total is None:
            total = data.get("meta", {}).get("count", 0)
            log.info(f"  Total works in OpenAlex: {total}")

        batch = data.get("results", [])
        if not batch:
            break

        for work in batch:
            # Reconstruct abstract from inverted index
            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))

            # Get venue name
            primary = work.get("primary_location") or {}
            source = primary.get("source") or {}
            journal = source.get("display_name", "")

            # Get authors
            authorships = work.get("authorships", [])
            authors_raw = ", ".join(
                a.get("author", {}).get("display_name", "")
                for a in authorships[:20]  # cap at 20 to keep manageable
            )

            works.append({
                "title":          work.get("title", "") or "",
                "year":           str(work.get("publication_year", "") or ""),
                "journal":        journal,
                "abstract":       abstract,
                "citation_count": work.get("cited_by_count", 0),
                "authors_raw":    authors_raw,
                "doi":            work.get("doi", "") or "",
                "openalex_id":    work.get("id", "") or "",
            })

        if len(works) >= total:
            break
        page += 1
        time.sleep(0.1)  # be polite — tiny delay between pages

    return works


def reconstruct_abstract(inverted_index):
    """
    OpenAlex stores abstracts as inverted indexes {word: [positions]}.
    This reconstructs the original text.
    """
    if not inverted_index:
        return ""
    try:
        words = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words[i] for i in sorted(words.keys()))
    except Exception:
        return ""


# =============================================================================
# Checkpoint system
# =============================================================================

def load_checkpoint(path):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        print(f"Resuming: {len(data['completed'])} faculty already done.")
        return data
    return {
        "completed": [], "faculty_nodes": {}, "pub_nodes": {},
        "journal_nodes": {}, "authored_edges": [], "pub_journal_edges": [], "errors": [],
    }

def save_checkpoint(state, path):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    tmp.replace(path)


# =============================================================================
# Main scraper
# =============================================================================

def build_graph(categories, pub_limit, single_faculty, resume, output_dir, log):
    checkpoint_path = output_dir / "checkpoint.json"
    state = load_checkpoint(checkpoint_path) if resume else {
        "completed": [], "faculty_nodes": {}, "pub_nodes": {},
        "journal_nodes": {}, "authored_edges": [], "pub_journal_edges": [], "errors": [],
    }

    # Build roster
    if single_faculty:
        roster_entry = None
        for cat, members in FACULTY.items():
            for m in members:
                if m["name"].lower() == single_faculty.lower():
                    roster_entry = {**m, "category": cat}
                    break
        if not roster_entry:
            roster_entry = {"name": single_faculty, "openalex_id": "", "category": "custom", "url": ""}
        roster = [roster_entry]
    else:
        roster = []
        for cat in categories:
            for f in FACULTY.get(cat, []):
                roster.append({**f, "category": cat})

    done_set = set(state["completed"])
    remaining = [f for f in roster if f["name"] not in done_set]
    log.info(f"Roster: {len(roster)} | Done: {len(done_set)} | Remaining: {len(remaining)}")

    for faculty_info in tqdm(remaining, desc="Faculty", unit="person"):
        name       = faculty_info["name"]
        cat        = faculty_info.get("category", "unknown")
        oa_id      = faculty_info.get("openalex_id", "")
        fid        = slugify(name)

        log.info(f"-- {name}  [{cat}]")

        # Find author on OpenAlex
        if oa_id:
            log.info(f"  Looking up by OpenAlex ID: {oa_id}")
            author = find_author_by_id(oa_id, log)
        else:
            log.info(f"  Searching by name...")
            author = find_author_by_name(name, log)

        if not author:
            log.warning(f"  Not found on OpenAlex: {name}")
            state["errors"].append({"faculty": name, "error": "not found on OpenAlex"})
            state["faculty_nodes"][fid] = {
                "id": fid, "name": name, "category": cat,
                "profile_url": faculty_info.get("url", ""),
                "openalex_found": False, "openalex_id": "",
                "affiliation": "", "interests": [],
                "h_index": 0, "total_citations": 0, "works_count": 0,
                "openalex_url": "",
            }
            state["completed"].append(name)
            save_checkpoint(state, checkpoint_path)
            continue

        resolved_id = author.get("id", "").split("/")[-1]  # e.g. A123456789

        # Build faculty node
        last_inst = (author.get("last_known_institutions") or [{}])[0]
        topics = [t.get("display_name", "") for t in (author.get("topics") or [])[:8]]

        fnode = {
            "id":              fid,
            "name":            name,
            "category":        cat,
            "profile_url":     faculty_info.get("url", ""),
            "openalex_found":  True,
            "openalex_id":     resolved_id,
            "affiliation":     last_inst.get("display_name", ""),
            "interests":       topics,
            "h_index":         author.get("summary_stats", {}).get("h_index", 0),
            "i10_index":       author.get("summary_stats", {}).get("i10_index", 0),
            "total_citations": author.get("cited_by_count", 0),
            "works_count":     author.get("works_count", 0),
            "openalex_url":    author.get("id", ""),
            "orcid":           author.get("orcid", "") or "",
        }
        state["faculty_nodes"][fid] = fnode
        log.info(f"  Found: h={fnode['h_index']}, citations={fnode['total_citations']:,}, works={fnode['works_count']}")

        # Fetch all works
        works = fetch_all_works(resolved_id, log)
        if pub_limit:
            works = works[:pub_limit]

        log.info(f"  Processing {len(works)} works...")

        for work in tqdm(works, desc=f"  {name.split()[-1]}", leave=False, unit="pub"):
            if not work["title"]:
                continue

            pid = make_pub_id(work["title"], work["year"])

            if pid not in state["pub_nodes"]:
                state["pub_nodes"][pid] = {
                    "id":             pid,
                    "title":          work["title"],
                    "year":           work["year"],
                    "journal":        work["journal"],
                    "abstract":       work["abstract"],
                    "citation_count": work["citation_count"],
                    "authors_raw":    work["authors_raw"],
                    "doi":            work["doi"],
                    "openalex_url":   work["openalex_id"],
                }
                jname = work["journal"]
                if jname:
                    jid = slugify(jname)
                    if jid not in state["journal_nodes"]:
                        state["journal_nodes"][jid] = {"id": jid, "name": jname}
                    state["pub_journal_edges"].append({"from": pid, "to": jid})

            state["authored_edges"].append({"from": fid, "to": pid, "year": work["year"]})

        state["completed"].append(name)
        save_checkpoint(state, checkpoint_path)
        log.info(f"  Done. Checkpoint saved.")
        time.sleep(0.5)  # tiny pause between faculty — not really needed but polite

    # Build co-authorship edges
    log.info("Building co-authorship edges...")
    pub_to_faculty = defaultdict(list)
    for edge in state["authored_edges"]:
        pub_to_faculty[edge["to"]].append(edge["from"])

    coauthored = []
    for pid, fids in pub_to_faculty.items():
        unique = list(dict.fromkeys(fids))
        if len(unique) < 2:
            continue
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                coauthored.append({"from": unique[i], "to": unique[j], "via_publication": pid})

    graph = {
        "meta": {
            "generated_at":   datetime.utcnow().isoformat() + "Z",
            "department":     "Mechanical Engineering",
            "university":     "UC Berkeley",
            "source":         "OpenAlex",
            "categories":     categories if not single_faculty else ["custom"],
            "pub_limit":      pub_limit,
            "total_faculty":  len(state["faculty_nodes"]),
            "total_pubs":     len(state["pub_nodes"]),
            "total_journals": len(state["journal_nodes"]),
        },
        "nodes": {
            "faculty":      list(state["faculty_nodes"].values()),
            "publications": list(state["pub_nodes"].values()),
            "journals":     list(state["journal_nodes"].values()),
        },
        "edges": {
            "faculty_authored":   state["authored_edges"],
            "pub_in_journal":     state["pub_journal_edges"],
            "faculty_coauthored": coauthored,
        },
        "errors": state["errors"],
    }
    return graph


# =============================================================================
# Output writers
# =============================================================================

def write_json(graph, out_dir, log):
    path = out_dir / "knowledge_graph.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    log.info(f"JSON  -> {path}  ({path.stat().st_size // 1024} KB)")

def write_csv(graph, out_dir, log):
    csv_dir = out_dir / "csv"; csv_dir.mkdir(exist_ok=True)

    fac_fields = ["id","name","category","openalex_found","openalex_id","h_index","i10_index",
                  "total_citations","works_count","interests","affiliation","openalex_url","orcid","profile_url"]
    with open(csv_dir / "faculty.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fac_fields, extrasaction="ignore")
        w.writeheader()
        for row in graph["nodes"]["faculty"]:
            r = dict(row); r["interests"] = " | ".join(r.get("interests") or [])
            w.writerow(r)

    pub_fields = ["id","title","year","journal","citation_count","abstract","authors_raw","doi","openalex_url"]
    with open(csv_dir / "publications.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pub_fields, extrasaction="ignore")
        w.writeheader(); w.writerows(graph["nodes"]["publications"])

    with open(csv_dir / "journals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","name"])
        w.writeheader(); w.writerows(graph["nodes"]["journals"])

    with open(csv_dir / "faculty_authored.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["from","to","year"])
        w.writeheader(); w.writerows(graph["edges"]["faculty_authored"])

    with open(csv_dir / "pub_in_journal.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["from","to"])
        w.writeheader(); w.writerows(graph["edges"]["pub_in_journal"])

    with open(csv_dir / "faculty_coauthored.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["from","to","via_publication"])
        w.writeheader(); w.writerows(graph["edges"]["faculty_coauthored"])

    log.info(f"CSVs  -> {csv_dir}/")

def esc(s):
    if s is None: return "null"
    return "'" + str(s).replace("\\","\\\\").replace("'","\\'").replace("\n"," ").replace("\r","") + "'"

def write_cypher(graph, out_dir, log):
    neo_dir = out_dir / "neo4j"; neo_dir.mkdir(exist_ok=True)
    lines = [
        f"// UC Berkeley ME Knowledge Graph — OpenAlex — {graph['meta']['generated_at']}",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Faculty) REQUIRE f.id IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Publication) REQUIRE p.id IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Journal) REQUIRE j.id IS UNIQUE;",
        "",
    ]
    for f in graph["nodes"]["faculty"]:
        interests = "[" + ",".join(esc(i) for i in (f.get("interests") or [])) + "]"
        lines.append(f"MERGE (f:Faculty {{id:{esc(f['id'])}}}) SET f.name={esc(f['name'])},f.category={esc(f.get('category',''))},f.h_index={f.get('h_index') or 0},f.total_citations={f.get('total_citations') or 0},f.interests={interests},f.openalex_url={esc(f.get('openalex_url',''))},f.profile_url={esc(f.get('profile_url',''))};")
    for j in graph["nodes"]["journals"]:
        lines.append(f"MERGE (j:Journal {{id:{esc(j['id'])}}}) SET j.name={esc(j['name'])};")
    for p in graph["nodes"]["publications"]:
        lines.append(f"MERGE (p:Publication {{id:{esc(p['id'])}}}) SET p.title={esc(p['title'])},p.year={esc(p.get('year',''))},p.citation_count={p.get('citation_count') or 0},p.abstract={esc((p.get('abstract') or '')[:2000])},p.journal={esc(p.get('journal',''))},p.doi={esc(p.get('doi',''))};")
    for e in graph["edges"]["faculty_authored"]:
        lines.append(f"MATCH (f:Faculty {{id:{esc(e['from'])}}}),(p:Publication {{id:{esc(e['to'])}}}) MERGE (f)-[:AUTHORED {{year:{esc(e.get('year',''))}}}]->(p);")
    for e in graph["edges"]["pub_in_journal"]:
        lines.append(f"MATCH (p:Publication {{id:{esc(e['from'])}}}),(j:Journal {{id:{esc(e['to'])}}}) MERGE (p)-[:PUBLISHED_IN]->(j);")
    for e in graph["edges"]["faculty_coauthored"]:
        lines.append(f"MATCH (a:Faculty {{id:{esc(e['from'])}}}),(b:Faculty {{id:{esc(e['to'])}}}) MERGE (a)-[:CO_AUTHORED {{via:{esc(e['via_publication'])}}}]->(b);")
    path = neo_dir / "import.cypher"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log.info(f"Neo4j -> {path}")

def print_summary(graph, log):
    n, e = graph["nodes"], graph["edges"]
    log.info("="*50)
    log.info(f"  Faculty:       {len(n['faculty']):>6}")
    log.info(f"  Publications:  {len(n['publications']):>6,}")
    log.info(f"  Journals:      {len(n['journals']):>6,}")
    log.info(f"  Authored:      {len(e['faculty_authored']):>6,}")
    log.info(f"  Co-authored:   {len(e['faculty_coauthored']):>6,}")
    log.info(f"  Errors:        {len(graph['errors']):>6}")
    log.info("="*50)
    top = sorted(n["faculty"], key=lambda x: x.get("total_citations") or 0, reverse=True)[:10]
    log.info("  Top 10 by citations:")
    for f in top:
        log.info(f"    {f['name']:<38} {f.get('total_citations',0):>8,}")
    if graph["errors"]:
        log.info("  Not found:")
        for err in graph["errors"]:
            log.info(f"    {err['faculty']}")


# =============================================================================
# Entry point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="UC Berkeley ME Faculty Knowledge Graph Builder (OpenAlex)")
    parser.add_argument("--categories", nargs="+", choices=ALL_CATEGORIES, default=ALL_CATEGORIES)
    parser.add_argument("--limit", type=int, default=None, help="Max publications per faculty")
    parser.add_argument("--faculty", type=str, default=None, help="Single faculty member by name")
    parser.add_argument("--output", type=str, default="output")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    log = setup_logging(output_dir / "scrape.log")
    log.info(f"Source: OpenAlex API (no rate limiting)")
    log.info(f"Categories: {args.categories} | Limit: {args.limit or 'all'}")

    graph = build_graph(args.categories, args.limit, args.faculty, args.resume, output_dir, log)

    write_json(graph, output_dir, log)
    write_csv(graph, output_dir, log)
    write_cypher(graph, output_dir, log)
    print_summary(graph, log)
    log.info(f"Done. Files in: {output_dir.resolve()}/")


if __name__ == "__main__":
    main()
