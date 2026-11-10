#!/usr/bin/env python3
"""Compile agent-extracted sampling coordinates into per-FEC tables, an FEC x LME matrix and GeoJSON.

Usage: compile_geo.py [--lme <polygon shapefile>] [--lme-field <name field>]
Inputs : $SAMBR_PROJECT/2_data/literature/plankton/geo/agent_out/geo_part*.out.jsonl
         $SAMBR_PROJECT/5_manuscript/plankton_pdf_duration_classes.csv (FEC, duration)
Outputs: data/geo/plankton_sites.csv          one row per site
         data/geo/plankton_papers_geo.csv     one row per paper (LMEs from polygons + agent guess)
         data/geo/plankton_geo_by_FEC.xlsx    one sheet per FEC (sites), + FEC_x_LME matrices
         data/geo/fec_lme_matrix.csv
         web/data/sites.geojson, web/data/lme.geojson

LME assignment: point-in-polygon on the interim 2013 PAME Arctic LME polygons (18 LMEs); points
within 50 km of a polygon snap to it (coastline mismatch); bboxes use every LME they intersect.
Swap in the CAFF shapefiles with --lme when they arrive.
"""
import argparse, csv, json, os, pathlib, re
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box, LineString

REPO = pathlib.Path(__file__).resolve().parents[2]
PROJ = pathlib.Path(os.environ.get("SAMBR_PROJECT", pathlib.Path.home() / "Documents/Research/Projects/2026-SAMBR"))
ap = argparse.ArgumentParser()
ap.add_argument("--lme", default=str(PROJ / "2_data/raw/lme/LME_2013_polygon.shp"))
ap.add_argument("--lme-field", default="LME")
ap.add_argument("--no-bering-swap", action="store_true",
                help="the 2013 PAME file has the East/West Bering Sea labels swapped; we swap them back unless this is set")
args = ap.parse_args()

# canonical 18 Arctic LMEs, numbered as in the CAFF expert-input sheet
LMES = ["Faroe Plateau", "Iceland Shelf", "Greenland Sea-East Greenland", "Norwegian Sea", "Barents Sea",
        "Kara Sea", "Laptev Sea", "East Siberian Sea", "East Bering Sea", "Aleutian Islands", "West Bering Sea",
        "Northern Bering-Chukchi Sea", "Central Arctic Ocean", "Beaufort Sea", "Canadian High Arctic-North Greenland",
        "Baffin Bay", "Hudson Bay", "Labrador-Newfoundland"]
ODS_LABEL = {l: f"{i}. {n}" for i, (l, n) in enumerate(zip(LMES, [
    "Faroe Islands", "Iceland Shelf", "Greenland Sea - East Greenland", "Norwegian Sea", "Barents Sea", "Kara Sea",
    "Laptev Sea", "East Siberian Sea", "East Bering Sea", "Aleutian Islands", "West Bering Sea",
    "Northern Bering-Chukchi Sea", "Central Arctic Ocean", "Beaufort Sea", "Canadian High Arctic-North Greenland",
    "Baffin Bay", "Hudson Bay", "Labrador-Newfoundland"]), 1)}
ALIAS = {"fareo plateau": "Faroe Plateau", "faroe plateau": "Faroe Plateau", "iceland": "Iceland Shelf",
         "greenland sea": "Greenland Sea-East Greenland", "norwegain sea": "Norwegian Sea", "norwegian sea": "Norwegian Sea",
         "alutian islands": "Aleutian Islands", "aleutian islands": "Aleutian Islands", "chukchi sea": "Northern Bering-Chukchi Sea",
         "northern canadian archipelago": "Canadian High Arctic-North Greenland", "central arctic": "Central Arctic Ocean",
         "labrador sea": "Labrador-Newfoundland"}
FECS = {"01": "Bacteria and Archaea", "02": "Viruses", "03": "Microbial eukaryotes",
        "04": "Phytoplankton and larger protists", "05": "Zooplankton", "06": "Cross-cutting (drivers, biogeochemistry, syntheses)"}


def canon(name):
    n = re.sub(r"\s*LME$", "", str(name)).strip()
    return ALIAS.get(n.lower(), n if n in LMES else n)


lme_src = gpd.read_file(args.lme)
lme_src["lme"] = lme_src[args.lme_field].map(canon)
if not args.no_bering_swap and "2013" in pathlib.Path(args.lme).name:
    lme_src["lme"] = lme_src["lme"].replace({"East Bering Sea": "West Bering Sea", "West Bering Sea": "East Bering Sea"})
lme_p = lme_src.to_crs(3995)  # Arctic polar stereographic: no antimeridian problems for point-in-polygon


def split_antimeridian(g):
    """Cut a polar-stereographic (EPSG:3995) geometry along lon=180 (x=0, y>0) so it reprojects cleanly to lon/lat."""
    from shapely.geometry import box as sbox
    from shapely.ops import transform
    from pyproj import Transformer
    tf = Transformer.from_crs(3995, 4326, always_xy=True)
    R = 2e7
    parts = []
    for half, sign in ((sbox(0, -R, R, R), 1), (sbox(-R, -R, 0, R), -1)):
        piece = g.intersection(half)
        if piece.is_empty:
            continue
        def f(x, y, z=None, sign=sign):
            lon, lat = tf.transform(x, y)
            import numpy as np
            lon = np.where(np.abs(np.abs(lon) - 180) < 1e-6, 180 * sign, lon)
            lon = np.where((sign > 0) & (lon < -179.0), 180, lon)
            lon = np.where((sign < 0) & (lon > 179.0), -180, lon)
            return lon, lat
        parts.append(transform(f, piece))
    from shapely.ops import unary_union
    from shapely.geometry import MultiPolygon, Polygon
    polys = []
    for pc in parts:
        polys += list(pc.geoms) if hasattr(pc, "geoms") else [pc]
    return MultiPolygon([q for q in polys if isinstance(q, Polygon) and not q.is_empty])


lme = gpd.GeoDataFrame({"lme": lme_p["lme"].values}, geometry=[split_antimeridian(g) for g in lme_p.geometry], crs=4326)

dur = {r["citekey"]: r for r in csv.DictReader(open(PROJ / "5_manuscript/plankton_pdf_duration_classes.csv"))}
lib = {r["citekey"]: r for r in csv.DictReader(open(PROJ / "5_manuscript/plankton_library_scored.csv"))}
# full author lists come from the bib (the scored CSV truncates after six names)
BIB_AUTH = {}
for _k, _b in re.findall(r"@\w+\{([^,\s]+),(.*?)\n\}", open(PROJ / "2_data/literature/references_plankton_v2.bib").read(), re.S):
    _m = re.search(r"\bauthor\s*=\s*\{(.*?)\},?\s*\n", _b, re.S)
    if _m:
        _a = re.sub(r"\s+", " ", _m.group(1)).replace("{", "").replace("}", "")
        BIB_AUTH[_k.strip()] = "; ".join(x.strip() for x in _a.split(" and ") if x.strip() and x.strip() != "others")
_drive_f = PROJ / "2_data/literature/plankton/geo/drive_pdf_ids.json"
drive = json.load(open(_drive_f)) if _drive_f.exists() else {}
drive = {re.sub(r"-[123]YO", "", k): v for k, v in drive.items()}
GEO = PROJ / "2_data/literature/plankton/geo"
recs = {}
for pat in ("agent_out/geo_part*.out.jsonl", "agent_out_refine/refine_*.out.jsonl"):  # refine overrides first pass
    for f in sorted(GEO.glob(pat)):
        for ln in open(f):
            ln = ln.strip()
            if ln:
                try:
                    r = json.loads(ln)
                except json.JSONDecodeError:
                    print("bad line in", f.name); continue
                r["_refined"] = "refine" in f.name
                recs[r["citekey"]] = r
recs = list(recs.values())


def num(x):
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def geom_of(s):
    lat, lon = num(s.get("lat")), num(s.get("lon"))
    la0, la1, lo0, lo1 = (num(s.get(k)) for k in ("lat_min", "lat_max", "lon_min", "lon_max"))
    if None not in (la0, la1, lo0, lo1) and (la0 != la1 or lo0 != lo1):
        if s.get("geom") == "transect":
            return LineString([(lo0, la0), (lo1, la1)])
        if lo0 > lo1:
            # either a dateline-crossing box or swapped bounds: take the reading with the smaller span
            if (180 - lo0) + (lo1 + 180) < lo0 - lo1:
                return box(lo0, la0, 180, la1).union(box(-180, la0, lo1, la1))
            lo0, lo1 = lo1, lo0
            s["lon_min"], s["lon_max"] = lo0, lo1
        return box(lo0, la0, lo1, la1)
    if lat is not None and lon is not None:
        return Point(lon, lat)
    return None


def lmes_for(g):
    if g is None:
        return []
    gp = gpd.GeoSeries([g], crs=4326).to_crs(3995).iloc[0]
    hit = lme_p[lme_p.intersects(gp)]["lme"].tolist()
    if hit or g.geom_type != "Point":
        return sorted(set(hit), key=LMES.index if all(h in LMES for h in hit) else str)
    d = lme_p.distance(gp)
    return [lme_p.loc[d.idxmin(), "lme"]] if d.min() < 50_000 else []


site_rows, paper_rows = [], []
for r in recs:
    k = r["citekey"]
    d = dur.get(k, {})
    fec = r.get("fec") or d.get("fec", "")
    plmes, best = set(), "none"
    rank = {"exact": 3, "approx": 2, "estimated": 1}
    for i, s in enumerate(r.get("sites") or []):
        g = geom_of(s)
        ls = lmes_for(g)
        plmes.update(ls)
        fl = s.get("flag", "")
        if rank.get(fl, 0) > rank.get(best, 0):
            best = fl
        site_rows.append({
            "citekey": k, "fec": fec, "fec_name": FECS.get(fec, ""), "site_no": i + 1, "site": s.get("name", ""),
            "lat": num(s.get("lat")), "lon": num(s.get("lon")), "geom": s.get("geom", "point"),
            "lat_min": num(s.get("lat_min")), "lat_max": num(s.get("lat_max")),
            "lon_min": num(s.get("lon_min")), "lon_max": num(s.get("lon_max")),
            "n_stations": s.get("n_stations"), "coord_flag": fl, "coord_source": s.get("source", ""),
            "lme_polygon": "; ".join(ls), "study_type": r.get("study_type", ""),
            "obs_duration": d.get("duration_class", ""), "obs_years": d.get("years", ""),
            "title": d.get("title", ""), "_geom": g})
    guess = [canon(x) for x in (r.get("lme_guess") or [])]
    paper_rows.append({
        "citekey": k, "fec": fec, "fec_name": FECS.get(fec, ""), "title": d.get("title", ""),
        "study_type": r.get("study_type", ""), "region_text": r.get("region_text", ""),
        "n_sites": len(r.get("sites") or []), "best_coord_flag": best,
        "coords_in_supplement": bool(r.get("coords_in_supplement")), "supplement_note": r.get("supplement_note", ""),
        "lme_polygon": "; ".join(sorted(plmes, key=lambda x: LMES.index(x) if x in LMES else 99)),
        "lme_agent_guess": "; ".join(guess),
        "lme_disagree": bool(plmes) and bool(set(guess) - {"outside"}) and not (set(guess) & plmes),
        "obs_duration": d.get("duration_class", ""), "obs_years": d.get("years", ""), "notes": r.get("notes", ""),
        "refined": r.get("_refined", False), "refine_note": r.get("refine_note", ""),
        "authors": BIB_AUTH.get(k) or (lib.get(k, {}).get("authors") or "").strip(), "year": lib.get(k, {}).get("year", ""),
        "journal": lib.get(k, {}).get("journal", ""), "doi": (lib.get(k, {}).get("doi") or "").strip(),
        "drive_pdf": f"https://drive.google.com/file/d/{drive[k]['id']}/view" if isinstance(drive.get(k), dict) else "",
        "drive_pdf_en": f"https://drive.google.com/file/d/{drive[k + '_EN']['id']}/view" if isinstance(drive.get(k + "_EN"), dict) else ""})

sites = pd.DataFrame(site_rows)
papers = pd.DataFrame(paper_rows)
out = REPO / "data/geo"; out.mkdir(parents=True, exist_ok=True)
sites.drop(columns="_geom").to_csv(out / "plankton_sites.csv", index=False)
papers.to_csv(out / "plankton_papers_geo.csv", index=False)


def paper_lmes(row):
    ls = [x for x in row["lme_polygon"].split("; ") if x]
    if not ls:  # fall back to the agent's guess (flag shows in lme_source)
        ls = [x for x in row["lme_agent_guess"].split("; ") if x in LMES]
    return ls


papers["lmes_final"] = papers.apply(paper_lmes, axis=1)
FIELD = {"field", "time_series", "mooring"}
fld = papers[papers.study_type.isin(FIELD)]
mats = {}
for label, sub in [("all", papers), ("field", fld), ("field_3plus", fld[fld.obs_duration == "3plus"]),
                   ("field_2yr", fld[fld.obs_duration == "2yr"]), ("field_1yr", fld[fld.obs_duration == "1yr"])]:
    m = pd.DataFrame(0, index=[FECS[f] for f in FECS], columns=[ODS_LABEL[l] for l in LMES])
    for _, p in sub.iterrows():
        for l in p["lmes_final"]:
            if p["fec"] in FECS:
                m.loc[FECS[p["fec"]], ODS_LABEL[l]] += 1
    mats[label] = m
long = pd.concat({k: v for k, v in mats.items()}, names=["papers", "fec"])
long.to_csv(out / "fec_lme_matrix.csv")

with pd.ExcelWriter(out / "plankton_geo_by_FEC.xlsx") as xw:
    readme = pd.DataFrame({"README": [
        "Sampling locations extracted from the full text of score-4/5 plankton papers (Sonnet agents, from text, tables, map figures).",
        "coord_flag: exact = printed in the paper; approx = read off a map or given as a range/box; estimated = inferred from a place name.",
        "lme_polygon: interim 2013 PAME Arctic LME polygons (to be replaced by CAFF shapefiles). Papers: lme_disagree = polygon vs agent guess differ.",
        "FEC_x_LME_*: number of papers per FEC with at least one site in each LME. all = every study type (pan-Arctic models/remote sensing count in every LME they cover); field = field surveys, time series and moorings only, also split by observation span.",
        "coords_in_supplement: station list only in a supplement/data repository — main-text estimate given; follow up there for exact positions."]})
    readme.to_excel(xw, sheet_name="README", index=False)
    for k, m in mats.items():
        m.to_excel(xw, sheet_name=f"FEC_x_LME_{k}")
    for f, name in FECS.items():
        sites[sites.fec == f].drop(columns="_geom").to_excel(xw, sheet_name=f"{f} sites", index=False)
        papers[papers.fec == f].drop(columns="lmes_final").to_excel(xw, sheet_name=f"{f} papers", index=False)

# GeoJSON for the web map: one feature per site; bbox/transect also carry their extent
web = REPO / "web/data"; web.mkdir(parents=True, exist_ok=True)
feats = []
for s in site_rows:
    g = s["_geom"]
    if g is None:
        continue
    pt = g if g.geom_type == "Point" else g.centroid if s["lat"] is None else Point(s["lon"], s["lat"])
    props = {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in s.items() if k != "_geom"}
    feats.append({"type": "Feature", "geometry": pt.__geo_interface__, "properties": props})
json.dump({"type": "FeatureCollection", "features": feats}, open(web / "sites.geojson", "w"))
lme_s = lme[["lme", "geometry"]].copy()
lme_s["geometry"] = lme_s.geometry.simplify(0.03)
lme_s["label"] = lme_s["lme"].map(ODS_LABEL)
open(web / "lme.geojson", "w").write(lme_s.to_json())
import shutil
for fn in ("plankton_sites.csv", "plankton_papers_geo.csv", "plankton_geo_by_FEC.xlsx", "fec_lme_matrix.csv"):
    shutil.copy2(out / fn, web / fn)
json.dump({"fecs": FECS, "lmes": [ODS_LABEL[l] for l in LMES],
           "matrices": {k: v.to_dict(orient="split") for k, v in mats.items()},
           "papers": papers.drop(columns="lmes_final").fillna("").to_dict(orient="records")},
          open(web / "summary.json", "w"))
print(f"{len(recs)} papers, {len(sites)} sites, {len(feats)} mapped; best flag:",
      papers.best_coord_flag.value_counts().to_dict(), "| no LME:", int((papers.lmes_final.str.len() == 0).sum()),
      "| polygon/guess disagree:", int(papers.lme_disagree.sum()))
