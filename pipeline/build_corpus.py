#!/usr/bin/env python3
"""
Build the cleaned publication corpus and faculty table from the raw OpenAlex works dump.

Inputs
  data/raw/roster.json           roster scraped from me.berkeley.edu (name, category, title, slug)
  data/raw/me_faculty_profiles.json  profile text (bio, research description) per slug
  data/raw/author_map.json       slug -> {ids: [...OpenAlex author ids], notes}
  data/raw/works_*.json          OpenAlex works (slim format produced by works_job_template.js)

Outputs
  data/works.jsonl               cleaned, deduplicated works with reconstructed abstracts
  data/faculty.json              faculty records incl. per-faculty work lists and audit stats
  data/audit_corpus.json         what was dropped and why

Cleaning rules (documented in README):
  * drop paratext, retracted works
  * drop types: erratum, editorial, letter (kept: article, book-chapter, book, preprint, review, dissertation, report, other)
  * drop non-English works when an English title is not available (SPECTER2 is English-only)
  * drop works with neither title nor abstract
  * dedupe by DOI (lower-cased), then by OpenAlex id; keep the record with the most citations
  * assign work -> faculty if any confirmed author id of that faculty appears in authorships
"""
import glob, json, re, sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import os
RAW = Path(os.environ.get("KG_RAW", ROOT / "data" / "raw"))
OUTD = Path(os.environ.get("KG_DATA", ROOT / "data"))
DROP_TYPES = {"erratum", "editorial", "letter", "paratext", "retraction", "peer-review", "grant"}


def reconstruct_abstract(aii):
    if not aii:
        return ""
    pos = []
    for word, idxs in aii.items():
        for i in idxs:
            pos.append((i, word))
    pos.sort()
    txt = " ".join(w for _, w in pos)
    txt = re.sub(r"\s+", " ", txt).strip()
    # strip common boilerplate prefixes
    txt = re.sub(r"^(Abstract|ABSTRACT|Summary)[:.\s]+", "", txt)
    return clean_abstract(txt)


BOILER = re.compile(r"^(abstract not|no abstract|international audience|abstract$|this document was prepared as an account|thesis \(ph|robotics institute$|this chapter contains sections titled)", re.I)


def clean_abstract(txt):
    """Strip markup and discard boilerplate 'abstracts'."""
    if not txt:
        return ""
    txt = re.sub(r"</?(jats|mml|xhtml)?:?[a-zA-Z][a-zA-Z0-9:\-]*(\s[^<>]{0,80})?>", " ", txt)  # html / jats / mathml tags
    txt = re.sub(r"&(amp|lt|gt|quot|nbsp|#\d+);", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) < 120 and BOILER.search(txt):
        return ""
    if len(txt) < 40:
        return ""
    return txt


def main():
    roster = json.load(open(ROOT / "data" / "raw" / "roster.json"))
    profiles = json.load(open(ROOT / "data" / "raw" / "me_faculty_profiles.json"))
    amap = json.load(open(ROOT / "data" / "raw" / "author_map.json"))

    id2slug = {}
    for slug, m in amap.items():
        if slug.startswith("_"):
            continue
        for aid in m["ids"]:
            if aid in id2slug and id2slug[aid] != slug:
                print(f"WARNING author id {aid} claimed by {id2slug[aid]} and {slug}")
            id2slug[aid] = slug

    raw = {}
    for fn in sorted(glob.glob(str(RAW / "works_*.json"))):
        chunk = json.load(open(fn))
        items = chunk.values() if isinstance(chunk, dict) else chunk
        for w in items:
            raw[w["id"]] = w
    print(f"{len(raw)} raw works from {len(glob.glob(str(RAW / 'works_*.json')))} files")

    audit = Counter()
    by_doi = {}
    kept = []
    for w in raw.values():
        reason = None
        if w.get("paratext"):
            reason = "paratext"
        elif w.get("retracted"):
            reason = "retracted"
        elif (w.get("type") or "") in DROP_TYPES:
            reason = "type:" + w["type"]
        title = (w.get("title") or "").strip()
        abstract = clean_abstract(w.get("abstract_text") or "") or reconstruct_abstract(w.get("aii"))
        if not reason and not title and not abstract:
            reason = "no_text"
        if not reason and w.get("lang") and w["lang"] != "en":
            # keep if the title looks like plain ASCII English (many 'lang' tags are wrong), else drop
            if not re.search(r"[A-Za-z]{3,}", title) or re.search(r"[぀-ヿ一-鿿Ѐ-ӿ]", title):
                reason = "non_english"
        if not reason and re.search(r"Powered by NICT|JST・京大機械翻訳", title):
            reason = "machine_translation"
        fac = set()
        for a in w.get("authors", []):
            slug = id2slug.get(a.get("id"))
            if not slug:
                continue
            rule = amap[slug]
            ok = True
            if rule.get("inst_filter"):
                names = a.get("inst_names") or []
                if names:
                    ok = any(pat.lower() in n.lower() for n in names for pat in rule["inst_filter"])
                else:
                    ok = bool(rule.get("allow_no_inst", False))
            if ok and rule.get("field_exclude"):
                fld = w["topics"][0][4] if w.get("topics") else None
                if fld in rule["field_exclude"]:
                    names = a.get("inst_names") or []
                    if not any(pat.lower() in n.lower() for n in names for pat in (rule.get("inst_filter") or ["Berkeley"])):
                        ok = False
            if ok and rule.get("topic_exclude"):
                tnames = " ".join(str(x) for t in (w.get("topics") or []) for x in t if x)
                if any(pat.lower() in tnames.lower() for pat in rule["topic_exclude"]):
                    ok = False
            if ok:
                fac.add(slug)
            else:
                audit["filtered:" + slug] += 1
        fac = sorted(fac)
        if not reason and not fac:
            reason = "no_faculty_author"
        if reason:
            audit[reason] += 1
            continue
        rec = {
            "id": w["id"], "doi": (w.get("doi") or "").lower().replace("https://doi.org/", "") or None,
            "title": title, "abstract": abstract, "year": w.get("year"), "date": w.get("date"),
            "type": w.get("type"), "cited": w.get("cited") or 0, "fwci": w.get("fwci"),
            "venue": w.get("venue"), "venue_type": w.get("venue_type"),
            "topics": w.get("topics") or [], "keywords": w.get("keywords") or [],
            "faculty": fac,
            "n_authors": len(w.get("authors", [])),
            "authors": [{"id": a.get("id"), "name": a.get("name"), "pos": a.get("pos"), "inst": a.get("inst", []), "inst_names": a.get("inst_names", [])} for a in w.get("authors", [])],
        }
        key = rec["doi"] or rec["id"]
        if key in by_doi:
            audit["duplicate"] += 1
            old = by_doi[key]
            if rec["cited"] > old["cited"] or (not old["abstract"] and rec["abstract"]):
                old.update({k: v for k, v in rec.items() if k != "faculty"})
            old["faculty"] = sorted(set(old["faculty"]) | set(rec["faculty"]))
            continue
        by_doi[key] = rec
        kept.append(rec)

    kept.sort(key=lambda r: (r["year"] or 0, r["id"]))
    with open(OUTD / "works.jsonl", "w") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"kept {len(kept)} works; dropped: {dict(audit)}")

    # faculty table
    fac_works = defaultdict(list)
    for r in kept:
        for s in r["faculty"]:
            fac_works[s].append(r)
    faculty = []
    for r in roster:
        slug = r["slug"]
        prof = profiles.get(slug, {})
        t = prof.get("t", "")
        rd = re.search(r"Research Description:\s*(.*?)(?:Key Publications:|$)", t)
        kp = re.search(r"Key Publications:\s*(.*)$", t)
        bio = ""
        m = re.search(r"Office:.*?\d{5}(?:-\d{4})?\s*(.*?)(?:Links:|Research Description:|Key Publications:|$)", t)
        if m:
            bio = m.group(1).strip()
        ws = fac_works.get(slug, [])
        years = [w["year"] for w in ws if w.get("year")]
        faculty.append({
            "slug": slug, "name": r["name"], "category": r["cat"], "title": r.get("title", ""),
            "profile_url": f"https://me.berkeley.edu/people/{slug}/",
            "openalex_ids": amap.get(slug, {}).get("ids", []),
            "match_notes": amap.get(slug, {}).get("notes", ""),
            "match_confidence": amap.get(slug, {}).get("confidence", ""),
            "research_description": rd.group(1).strip() if rd else "",
            "key_publications": kp.group(1).strip()[:1500] if kp else "",
            "bio": bio[:1200],
            "links": prof.get("links", []),
            "n_works": len(ws),
            "n_with_abstract": sum(1 for w in ws if w["abstract"]),
            "total_citations": sum(w["cited"] for w in ws),
            "first_year": min(years) if years else None,
            "last_year": max(years) if years else None,
            "works": [w["id"] for w in ws],
        })
    json.dump(faculty, open(OUTD / "faculty.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"dropped": dict(audit), "kept": len(kept), "raw": len(raw)}, open(OUTD / "audit_corpus.json", "w"), indent=1)
    for f in faculty:
        flag = "  <-- NO WORKS" if f["n_works"] == 0 else ""
        print(f"{f['name']:<28} {f['category']:<10} works={f['n_works']:>4} abs={f['n_with_abstract']:>4} cites={f['total_citations']:>6} {f['first_year']}-{f['last_year']}{flag}")


if __name__ == "__main__":
    main()
