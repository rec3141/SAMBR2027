#!/usr/bin/env python3
"""Build per-paper geographic snippets (abstract, study-area/methods text, coordinate-bearing
lines, map/station figure captions, supplement mentions) for coordinate extraction agents.

Usage: geo_snippets.py <outdir> [papers_per_part=40]
Reads the score-4/5 paper list + FEC from 5_manuscript/plankton_pdf_duration_classes.csv and
PDFs from 2_data/literature/pdfs/plankton/<citekey>.pdf (prefers <citekey>_EN.pdf text when present).
Writes <outdir>/geo_partNN.jsonl and <outdir>/manifest.json.
"""
import csv, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PDFS = ROOT / "2_data/literature/pdfs/plankton"
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
PER = int(sys.argv[2]) if len(sys.argv) > 2 else 40

COORD = re.compile(
    r"\d{1,3}(?:[.,]\d+)?\s*[°º˚o]\s*\d{0,2}(?:[.,]\d+)?\s*['′’]?\s*\d{0,2}(?:[.,]\d+)?\s*[\"″”]?\s*[NSEW]\b"
    r"|\b\d{1,3}[.,]\d{2,}\s*°?\s*[NSEW]\b"
    r"|\b(?:lat(?:itude)?|lon(?:gitude)?)\b"
    r"|\b\d{2}[.,]\d{3,}\b\s+[-−]?\d{1,3}[.,]\d{3,}\b", re.I)
HEAD = re.compile(r"^\s*(?:\d[\d.]*\s*)?(study (?:area|site|region)s?|sampling(?: sites?| area| design| strategy)?|"
                  r"materials? and methods|methods|field (?:sampling|campaigns?|work)|data (?:and|&) methods|cruises?)\s*$", re.I | re.M)
CAP = re.compile(r"^\s*(?:Fig(?:ure)?\.?\s*\d+[a-z]?)[.:|\s].{0,40}", re.I | re.M)
CAPKEY = re.compile(r"map|station|stations|sampling (?:site|location)|study area|location|transect|cruise track|mooring", re.I)
SUPP = re.compile(r"(supplementar|supporting information|table s\d|fig(?:ure)?\.? s\d|appendix|pangaea|doi\.org/10\.1594)", re.I)
SUPPKEY = re.compile(r"station|coordinat|position|location|latitude|sampling site|metadata", re.I)


def text_of(pdf):
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, errors="ignore")
    return r.stdout


def snip(key):
    pdf = PDFS / f"{key}.pdf"
    for alt in (PDFS / f"{key}_EN.pdf", PDFS / f"{key}_fulltext.pdf"):
        if alt.exists() and (not pdf.exists() or "_EN" in alt.name):
            pdf = alt
            break
    if not pdf.exists():
        return None
    t = text_of(pdf)
    t = re.sub(r"[ \t]{3,}", "   ", t)
    lines = t.splitlines()
    out = {"abstract": re.sub(r"\s+", " ", t[:1800])}
    m = HEAD.search(t)
    out["study_area"] = re.sub(r"\s+", " ", t[m.start(): m.start() + 3000]) if m else ""
    coord, used, budget = [], set(), 5500
    for i, ln in enumerate(lines):
        if COORD.search(ln) and i not in used:
            blk = " / ".join(x.strip() for x in lines[max(0, i - 1): i + 2] if x.strip())
            used.update(range(i - 1, i + 2))
            coord.append(blk[:400]); budget -= len(blk[:400])
            if budget < 0:
                coord.append("[...more coordinate lines truncated]"); break
    out["coord_lines"] = coord
    caps = []
    for m in CAP.finditer(t):
        c = re.sub(r"\s+", " ", t[m.start(): m.start() + 450])
        if CAPKEY.search(c[:250]):
            caps.append(c)
        if len(caps) >= 4:
            break
    out["map_captions"] = caps
    sup = []
    for ln in lines:
        if SUPP.search(ln) and SUPPKEY.search(ln):
            sup.append(ln.strip()[:250])
        if len(sup) >= 6:
            break
    out["supplement_mentions"] = sup
    out["n_chars"] = len(t)
    out["pdf"] = pdf.name
    return out


rows = list(csv.DictReader(open(ROOT / "5_manuscript/plankton_pdf_duration_classes.csv")))
recs, missing = [], []
for r in rows:
    s = snip(r["citekey"])
    if s is None:
        missing.append(r["citekey"]); continue
    recs.append({"citekey": r["citekey"], "fec": r["fec"], "title": r["title"],
                 "duration_class": r["duration_class"], "years": r["years"], **s})
parts = [recs[i: i + PER] for i in range(0, len(recs), PER)]
for n, p in enumerate(parts, 1):
    with open(OUT / f"geo_part{n:02d}.jsonl", "w") as f:
        for x in p:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
json.dump({"n": len(recs), "parts": len(parts), "missing_pdf": missing}, open(OUT / "manifest.json", "w"), indent=1)
print(len(recs), "papers,", len(parts), "parts; missing PDF:", len(missing))
