# SAMBR 2027: Plankton Expert Network

Code, derived data and web portal for the CAFF CBMP-Marine **Plankton Expert Network** contribution to the
*State of the Arctic Marine Biodiversity Report* (SAMBR) 2027 update.

Portal: **https://cryomics.org/SAMBR2027/**

## Contents
| Path | What |
|---|---|
| `code/geo/compile_geo.py` | Compiles agent-extracted sampling coordinates into per-FEC tables, FEC × LME matrices, GeoJSON for the map |
| `code/ods/expand_plankton_fecs.py` | Copies the CAFF "Status of Monitoring by LME" expert-input `.ods` with the Plankton FECs expanded + a literature-evidence sheet (the CAFF sheet itself is internal and not in this repo) |
| `data/geo/` | `plankton_sites.csv` (one row per site), `plankton_papers_geo.csv` (one row per paper), `plankton_geo_by_FEC.xlsx`, `fec_lme_matrix.csv` |
| `web/` | Static portal (D3 polar map); `./deploy.sh` rsyncs it to cryomics.org |

## Geography of the literature
- Papers: relevance score 4–5 papers from the Plankton EN annotated bibliography (2017–2026 plus baselines), all
  with full text.
- Sampling locations were extracted from the full text by LLM agents in two passes: snippets first, then station
  tables in the PDF and supplements (PANGAEA, publisher supplementary files) for field studies without exact positions.
- `coord_flag` records how precise each location is:
  - `exact`: printed in the paper or supplement.
  - `approx`: read off a map, or given as a range or box.
  - `estimated`: inferred from a place name.
- **LMEs:** sites are assigned by point-in-polygon against the interim 2013 PAME Arctic LME polygons (18 LMEs, numbered as in the CAFF sheet). Points within 50 km of a polygon snap to it. These polygons will be replaced by the CAFF shapefiles.
- **FECs (expanded):**
  - 01 Bacteria & Archaea
  - 02 Viruses
  - 03 Microbial eukaryotes
  - 04 Phytoplankton & larger protists
  - 05 Zooplankton
  - 06 Cross-cutting (drivers, biogeochemistry, syntheses; not an FEC in the CAFF sheet)
- **Observation span** (`obs_duration`: 1yr / 2yr / 3plus) is the field-observation duration classified from the abstract and methods.

PDFs are not in this repository.
