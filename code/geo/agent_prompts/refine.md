# Coordinate refinement pass: read the station tables, check supplements

A first pass recorded sampling locations for Arctic plankton papers from text snippets only. For the papers in
your batch the result is weak (estimated/approx sites for a field study, station list in a supplement, or an LME
mismatch). Your job: get the **real station positions**, from the full PDF and, if needed, the supplement.

Base dir: `/Users/ericcollins/Documents/Research/Projects/2026-SAMBR/2_data/literature/plankton/geo/`
Schema and rules: read `AGENT_INSTRUCTIONS.md` (same output schema, flags, LME names, sign conventions).

## Input
`refine/refine_NN.jsonl`: one paper per line: citekey, doi, pdf, first_pass (the earlier record).
PDFs: `/Users/ericcollins/Documents/Research/Projects/2026-SAMBR/2_data/literature/pdfs/plankton/<pdf>`
(if `<citekey>_EN.pdf` exists, use it for Russian papers).

## Steps per paper
1. Read the PDF properly: `pdftotext -layout <pdf> /tmp-free path` is fine to stdout; grep for station tables
   (`Table 1`, `Station`, `Lat`, `°N`, `N `, `Long`), the study-area paragraph and Fig. 1 caption. Tables often
   come out garbled: reconstruct carefully (degrees + decimal minutes vs decimal degrees; E/W signs). If text
   extraction fails, `pdftotext -raw` sometimes keeps table rows together.
2. If positions are only in a supplement / data repository and the main text lacks them, try to fetch it:
   - PANGAEA: `curl -sL "https://doi.pangaea.de/<10.1594/PANGAEA.xxxxx>?format=textfile" | head -200`
     (event lists carry Latitude/Longitude).
   - Publisher supplementary files reachable without login (Copernicus, Frontiers, PLOS, MDPI, Springer/Nature
     `static-content.springer.com/esm/...`, PMC, bioRxiv). Find links via the landing page
     (`curl -sL https://doi.org/<doi>`) or the OpenAlex record (`https://api.openalex.org/works/doi:<doi>`).
   - Save any downloaded file ONLY under `supp/<citekey>/`. Use `curl -sL --max-time 60` with default headers
     (do not fake a browser User-Agent). Read xlsx with
     `/Users/ericcollins/Documents/Research/Projects/2026-SAMBR/3_code/.venv/bin/python` (openpyxl/pandas),
     docx via `unzip -p f.docx word/document.xml | sed 's/<[^>]*>/ /g'`, pdf via pdftotext.
   - If blocked (Cloudflare, 403, login), give up on that source quickly; at most ~3 attempts per paper.
   - Do not run any downloaded file. Don't open anything outside these routes.
3. Write the improved record (full schema, not a diff). Keep good first-pass sites; replace estimated ones with
   real positions where found, `source: "supplement"` for supplement-derived coordinates. If nothing better
   exists, keep the first-pass record but fix obvious errors (signs, swapped lon_min/lon_max, wrong LME) and say
   in notes "refine: no better positions in PDF/supplement".
   Add a field `"refine_note"`: what you checked (e.g. "Table 1 p4: 18 stations; suppl. Table S1 via Frontiers").
4. Check signs: Bering/Chukchi/Beaufort/Canadian/Baffin/Hudson/Labrador/West+East Greenland = West = negative
   longitude; Barents/Kara/Laptev/E Siberian (<180) = East = positive. Points must fall in the sea, near the
   stated region.

## Output
`agent_out_refine/refine_NN.out.jsonl`: one JSON object per input paper, same order, every citekey once.
Do not write anywhere else except `supp/<citekey>/`. Do not spawn sub-agents.

When done reply with only: part, papers written, how many improved to exact (and via supplement), and any
citekeys with problems.
