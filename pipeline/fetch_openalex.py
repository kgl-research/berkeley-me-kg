#!/usr/bin/env python3
"""
Fetch everything the pipeline needs from OpenAlex.

Steps
  roster      scrape the department faculty listing + profile pages (me.berkeley.edu)
  candidates  search OpenAlex author candidates for every roster entry (for manual review)
  works       download all works for the confirmed author ids in data/raw/author_map.json
  authors     download the author records (summary stats) for the confirmed ids

Usage
  export OPENALEX_API_KEY=...        # free key from your OpenAlex account; 10k credits/day
  export OPENALEX_MAILTO=you@berkeley.edu
  python3 pipeline/fetch_openalex.py roster
  python3 pipeline/fetch_openalex.py candidates      # then edit data/raw/author_map.json
  python3 pipeline/fetch_openalex.py works authors

Credits: a paged /works or /authors/{id} request costs 1 credit regardless of page size (we use
200 per page), an author *search* costs 1 credit per returned record. The whole department is
~120 credits for works + 84 for author records; the candidate search is ~10 per query.
"""
import json, os, re, sys, time, unicodedata
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
API = "https://api.openalex.org"
KEY = os.environ.get("OPENALEX_API_KEY", "")
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
UCB, LBL = "I95457486", "I148283060"   # UC Berkeley, Lawrence Berkeley National Laboratory (NOT I40120149 = Oxford)
S = requests.Session()
S.headers["User-Agent"] = f"berkeley-me-kg/2.0 (mailto:{MAILTO})"


def get(path, **params):
    if KEY:
        params["api_key"] = KEY
    if MAILTO:
        params["mailto"] = MAILTO
    for attempt in range(5):
        r = S.get(API + path, params=params, timeout=60)
        if r.status_code == 429:
            wait = int(r.headers.get("retry-after", "5"))
            print(f"  rate limited ({r.headers.get('x-ratelimit-remaining')} credits left); sleeping {min(wait, 120)}s", file=sys.stderr)
            time.sleep(min(wait, 120)); continue
        if r.status_code >= 500:
            time.sleep(2 * (attempt + 1)); continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("OpenAlex request failed: " + path)


ASEL = "id,display_name,display_name_alternatives,orcid,works_count,cited_by_count,summary_stats,affiliations,last_known_institutions,topics,counts_by_year"
WSEL = "id,doi,title,publication_year,publication_date,type,cited_by_count,authorships,primary_location,topics,abstract_inverted_index,is_retracted,is_paratext,language,fwci,referenced_works_count,keywords"


def aii_text(aii):
    if not aii:
        return ""
    pos = sorted((i, w) for w, idxs in aii.items() for i in idxs)
    return re.sub(r"\s+", " ", " ".join(w for _, w in pos)).strip()


def slim_work(w):
    src = (w.get("primary_location") or {}).get("source") or {}
    return {
        "id": w["id"].split("/")[-1], "doi": w.get("doi"), "title": w.get("title"), "year": w.get("publication_year"), "date": w.get("publication_date"),
        "type": w.get("type"), "cited": w.get("cited_by_count"), "retracted": w.get("is_retracted"), "paratext": w.get("is_paratext"), "lang": w.get("language"),
        "fwci": w.get("fwci"), "nref": w.get("referenced_works_count"), "venue": src.get("display_name"), "venue_type": src.get("type"),
        "topics": [[t["id"].split("/")[-1], t["display_name"], t.get("score"), (t.get("subfield") or {}).get("display_name"), (t.get("field") or {}).get("display_name")] for t in (w.get("topics") or [])[:3]],
        "keywords": [k["display_name"] for k in (w.get("keywords") or [])[:6]],
        "authors": [{"id": (a.get("author") or {}).get("id", "").split("/")[-1] or None, "name": (a.get("author") or {}).get("display_name"), "pos": a.get("author_position"),
                     "inst": [i["id"].split("/")[-1] for i in a.get("institutions") or [] if i.get("id")], "inst_names": [i.get("display_name") for i in (a.get("institutions") or [])[:3]]} for a in w.get("authorships") or []],
        "abstract_text": aii_text(w.get("abstract_inverted_index")),
    }


def step_roster():
    from bs4 import BeautifulSoup
    html = S.get("https://me.berkeley.edu/faculty/", timeout=60).text
    soup = BeautifulSoup(html, "lxml")
    rows, cat = [], None
    for el in soup.find_all(["h2", "h3"]):
        if el.name == "h2":
            cat = el.get_text(strip=True)
        elif cat:
            a = el.find("a") or el.find_parent(["article", "li", "div"]).find("a", href=re.compile("/people/"))
            if a and "/people/" in a.get("href", ""):
                rows.append({"cat": cat, "name": el.get_text(strip=True), "url": a["href"]})
    profiles = {}
    for r in rows:
        slug = r["url"].rstrip("/").split("/")[-1]
        p = BeautifulSoup(S.get(r["url"], timeout=60).text, "lxml")
        h1 = p.find("h1"); root = h1
        for _ in range(6):
            if root.parent and root.parent.name != "body":
                root = root.parent
            if "Research Description" in root.get_text() or "Email" in root.get_text():
                break
        t = re.sub(r"\s+", " ", root.get_text(" "))
        t = t[t.find(h1.get_text(strip=True)):]
        cut = t.find("Resources for Current Students")
        if cut > 0:
            t = t[:cut]
        links = [[a.get_text(strip=True)[:40], a["href"]] for a in root.find_all("a", href=True) if not re.search(r"me\.berkeley\.edu|berkeley\.edu/?$|classes\.berkeley|^mailto", a["href"])][:8]
        profiles[slug] = {"cat": r["cat"], "name": r["name"], "t": t[:2600], "links": links}
        print(slug, r["cat"])
        time.sleep(0.3)
    json.dump(profiles, open(RAW / "me_faculty_profiles.json", "w"), ensure_ascii=False)
    roster = []
    for slug, v in profiles.items():
        a = unicodedata.normalize("NFKD", v["name"]).encode("ascii", "ignore").decode()
        parts = a.replace(".", "").split()
        m = re.search(re.escape(v["name"]) + r"\s*(.*?)\s*(Email:|Phone:|Office:|Links:|Research Description:|$)", v["t"])
        roster.append({"slug": slug, "name": v["name"], "cat": v["cat"], "title": m.group(1).strip() if m else "", "q": sorted({a, f"{parts[0]} {parts[-1]}"}), "last": parts[-1], "orcid": None, "old_id": ""})
    json.dump(roster, open(RAW / "roster.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(roster)} faculty")


def slim_author(a):
    return {"id": a["id"].split("/")[-1], "name": a["display_name"], "alts": (a.get("display_name_alternatives") or [])[:6], "orcid": a.get("orcid"), "works": a.get("works_count"), "cited": a.get("cited_by_count"),
            "h": (a.get("summary_stats") or {}).get("h_index"), "aff": [[x["institution"]["display_name"], f"{min(x['years'])}-{max(x['years'])}" if x.get("years") else ""] for x in (a.get("affiliations") or [])[:8]],
            "last": [i["display_name"] for i in a.get("last_known_institutions") or []], "topics": [[t["display_name"], t["count"]] for t in (a.get("topics") or [])[:8]]}


def step_candidates():
    roster = json.load(open(RAW / "roster.json"))
    out = {}
    for r in roster:
        seen = {}
        for q in r["q"]:
            for a in get("/authors", search=q, per_page=10, select=ASEL).get("results", []):
                s = slim_author(a); seen[s["id"]] = s
        # Berkeley-affiliated namesakes (last name only)
        for a in get("/authors", filter=f"display_name.search:{r['last']},affiliations.institution.id:{UCB}", per_page=10, select=ASEL).get("results", []):
            s = slim_author(a); seen[s["id"]] = s
        out[r["slug"]] = sorted(seen.values(), key=lambda s: -(1e6 * any("Berkeley" in x[0] for x in s["aff"]) + (s["works"] or 0)))
        print(r["name"], "->", [(s["id"], s["name"], s["works"]) for s in out[r["slug"]][:3]])
    json.dump(out, open(RAW / "candidates.json", "w"), indent=1, ensure_ascii=False)
    print("Review data/raw/candidates.json and fill data/raw/author_map.json")


def confirmed_ids():
    amap = json.load(open(RAW / "author_map.json"))
    return sorted({i for k, v in amap.items() if not k.startswith("_") for i in v["ids"]})


def step_works():
    ids = confirmed_ids(); works = {}
    for g in range(0, len(ids), 40):
        group = ids[g:g + 40]; cursor = "*"
        while cursor:
            j = get("/works", filter="authorships.author.id:" + "|".join(group), per_page=200, cursor=cursor, select=WSEL)
            for w in j["results"]:
                works[w["id"]] = slim_work(w)
            cursor = j["meta"].get("next_cursor") if j["results"] else None
            print(f"  {len(works)} works", end="\r")
    for fn in RAW.glob("works_*.json"):
        fn.unlink()
    items = list(works.items())
    for k in range(4):
        part = dict(items[k * len(items) // 4:(k + 1) * len(items) // 4])
        json.dump(part, open(RAW / f"works_{k}.json", "w"), ensure_ascii=False)
    print(f"\n{len(works)} works written to data/raw/works_*.json")


def step_authors():
    out = {i: get(f"/authors/{i}", select=ASEL) for i in confirmed_ids()}
    json.dump(out, open(RAW / "authors.json", "w"), ensure_ascii=False)
    print(f"{len(out)} author records")


if __name__ == "__main__":
    steps = {"roster": step_roster, "candidates": step_candidates, "works": step_works, "authors": step_authors}
    for s in sys.argv[1:] or ["works", "authors"]:
        steps[s]()
