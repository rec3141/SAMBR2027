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
- **Domain-scale sites** (boxes or transects spanning >90° longitude or >30° latitude, or touching >6 LMEs: pan-Arctic/global models, remote sensing, compilations) are not assigned to individual LMEs; those papers are counted in a separate **Pan-Arctic / multi-LME** column.
- **LMEs:** sites are assigned by point-in-polygon against CAFF's Arctic LME layer (ABDS `abds:lme_arctic`, 18 LMEs, numbered and labelled as in the CAFF expert-input sheet; CAFF names such as "Hudson Bay Complex" map to the sheet labels). Until 2026-11-12 the interim layer was PAME 2013, whose East/West Bering Sea labels are swapped. Points within 50 km of a polygon snap to it. Boxes/transects count for an LME only if it holds ≥15% of the box's area within LMEs (equal-area polar projection; box edges follow parallels), plus the LME of the box's representative point. `data/geo/lme_ama_crosswalk_pct.csv` gives the % of each LME's area in each of the 8 CBMP Arctic Marine Areas used in SAMBR 2017.
- **FECs (expanded):**
  - 01 Bacteria & Archaea
  - 02 Viruses
  - 03 Microbial eukaryotes
  - 04 Phytoplankton & larger protists
  - 05 Zooplankton
  - 06 Cross-cutting (drivers, biogeochemistry, syntheses; not an FEC in the CAFF sheet)
- **Observation span** (`obs_duration`: 1yr / 2yr / 3plus) is the field-observation duration classified from the abstract and methods.

PDFs are not in this repository.
