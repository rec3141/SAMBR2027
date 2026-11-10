# Coordinate extraction: Arctic plankton papers (SAMBR 2027)

Goal: for every paper, record WHERE the plankton data come from (sampling sites / stations / study area),
so we can map literature coverage per Focal Ecosystem Component (FEC) and per Arctic Large Marine Ecosystem (LME).

## Input
`snippets/geo_partNN.jsonl` — one paper per line with: citekey, fec, title, duration_class, years, abstract,
study_area (text after a methods/study-area heading, often empty), coord_lines (lines containing coordinates or
lat/lon words, with 1 line of context), map_captions, supplement_mentions, pdf (filename).

Full PDFs: `/Users/ericcollins/Documents/Research/Projects/2026-SAMBR/2_data/literature/pdfs/plankton/<pdf>`.
When snippets are not enough (no coordinates, truncated station table, unclear study area), read the PDF text with
`pdftotext -layout <pdf> - | sed -n 'A,Bp'` or `grep -n -i -E 'station|lat|°N|study area' ` — read only what you need.
Do NOT fetch anything from the internet. Do NOT modify or create files anywhere except your own output file.

## Output
Write exactly one JSON object per paper (same order as input) as JSON Lines to
`agent_out/geo_partNN.out.jsonl` (NN = your part). Write the file with a single heredoc or Python at the end, or
append per paper — but make sure every input citekey appears exactly once. Schema:

```json
{"citekey": "...", "fec": "04",
 "study_type": "field|time_series|mooring|remote_sensing|model|lab|review|data_compilation|other",
 "region_text": "free-text study region as the paper states it, e.g. 'Kongsfjorden, W Spitsbergen'",
 "sites": [
   {"name": "station/site/area name", "lat": 78.95, "lon": 11.93,
    "geom": "point|bbox|transect",
    "lat_min": null, "lat_max": null, "lon_min": null, "lon_max": null,
    "n_stations": 1,
    "flag": "exact|approx|estimated",
    "source": "text|table|figure|supplement|place_name"}
 ],
 "coords_in_supplement": false,
 "supplement_note": "",
 "lme_guess": ["Barents Sea"],
 "notes": "short, only if something is odd"}
```

Rules
- Decimal degrees, WGS84. South and West are NEGATIVE (e.g. 150°W → -150). Convert DMS / degrees-decimal-minutes
  carefully (74°30'N = 74.5). Round to 3 decimals.
- `flag`: **exact** = coordinates printed in the paper (text/table); **approx** = read off a map figure, or the
  paper gives a coordinate range/box; **estimated** = you inferred from a place name or region description
  (e.g. 'Disko Bay' → 69.2, -52.5). Estimates are welcome — always flag them.
- Many stations: list up to ~25 individual points if the paper tabulates them; beyond that give a `bbox`
  (lat/lon min/max, `n_stations` = count) plus a few representative points. A cruise transect may be a
  `transect` with lat/lon of start in lat/lon and the extent in the min/max fields.
- Time series / single fixed site: one point with the exact position.
- Remote sensing, models, compilations, pan-Arctic syntheses: give a bbox of the domain (e.g. pan-Arctic >66°N:
  lat_min 66, lat_max 90, lon_min -180, lon_max 180) flagged `approx` or `estimated`, and set study_type.
- Lab/culture studies: use the isolation/collection site if stated, else empty `sites` and say so in notes.
- `coords_in_supplement`: true when the paper says station positions/metadata are in a supplement / appendix /
  data repository (PANGAEA etc.) and the main text lacks them; put the pointer (e.g. 'Table S1', PANGAEA DOI) in
  supplement_note. Still provide your best estimate of the sites from the main text/map, flagged.
- `lme_guess`: one or more of these 18 names exactly: Faroe Plateau, Iceland Shelf, Greenland Sea-East Greenland,
  Norwegian Sea, Barents Sea, Kara Sea, Laptev Sea, East Siberian Sea, East Bering Sea, Aleutian Islands,
  West Bering Sea, Northern Bering-Chukchi Sea, Central Arctic Ocean, Beaufort Sea,
  Canadian High Arctic-North Greenland, Baffin Bay, Hudson Bay, Labrador-Newfoundland; or "outside" (non-Arctic).
  (Svalbard fjords → Barents Sea unless clearly Greenland Sea/Fram Strait side; Fram Strait → Greenland Sea-East
  Greenland; Canadian Arctic Archipelago & Nares Strait → Canadian High Arctic-North Greenland; Disko Bay & West
  Greenland → Baffin Bay; Chukchi Sea & Bering Strait → Northern Bering-Chukchi Sea.)
- Be accurate over fast. Never invent "exact" coordinates.

When done, reply with only: part number, papers written, counts by flag of the best site per paper
(exact/approx/estimated/none), and the citekeys you were unsure about.
