#!/usr/bin/env python3
"""Make a copy of the CAFF 'Status of Monitoring by LME' .ods with the Plankton sheet's FEC rows
expanded to the Plankton EN's FECs, plus an evidence sheet (papers per FEC x LME from the literature
geography). Ratings are left blank for the experts.

Usage: expand_plankton_fecs.py <in.ods> <out.ods> [fec_lme_matrix.csv]
Edits content.xml directly (no LibreOffice needed); everything else in the package is copied unchanged.
"""
import csv, html, re, sys, zipfile

src, dst = sys.argv[1], sys.argv[2]
matrix = sys.argv[3] if len(sys.argv) > 3 else None

NEW_FECS = ["Bacteria and Archaea", "Viruses", "Microbial eukaryotes (heterotrophic and mixotrophic protists)",
            "Phytoplankton and larger protists", "Zooplankton"]

z = zipfile.ZipFile(src)
xml = z.read("content.xml").decode("utf-8")

i = xml.find('table:name="Plankton"')
j = xml.find("</table:table>", i)
seg = xml[i:j]
rows = list(re.finditer(r"<table:table-row\b.*?</table:table-row>", seg, re.S))
fec_rows = [m for m in rows if re.search(r"<text:p>(Bacteria and Archaea|Microbial eukaryotes|Phytoplankton|Zooplankton)</text:p>", m.group(0))]
assert len(fec_rows) == 4, f"expected 4 FEC rows, found {len(fec_rows)}"
template = fec_rows[0].group(0)
new_rows = "".join(template.replace("<text:p>Bacteria and Archaea</text:p>", f"<text:p>{html.escape(n)}</text:p>") for n in NEW_FECS)
seg2 = seg[: fec_rows[0].start()] + new_rows + seg[fec_rows[-1].end():]
seg2 = seg2.replace("FEC list from SAMBR 2017 (no 2027 Plankton chapter yet) - please correct it if it has changed.",
                    "FEC list expanded by the Plankton EN (2027): viruses added; phytoplankton includes larger protists.")
xml = xml[:i] + seg2 + xml[j:]

if matrix:
    # evidence sheet: copy of the matrix as plain cells, appended as a new table before </office:spreadsheet>
    def cell(v):
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
            return f'<table:table-cell office:value-type="float" office:value="{v}"><text:p>{v}</text:p></table:table-cell>'
        return f'<table:table-cell office:value-type="string"><text:p>{html.escape(str(v))}</text:p></table:table-cell>'
    rows_out = [["Plankton literature evidence: number of score-4/5 papers (2017-2026 + baselines) with sampling sites in each LME, by FEC"],
                ["Not a rating - for the experts filling in the 'Plankton' sheet. 'obs_3plus' = observational studies spanning 3 or more years. Source: github.com/rec3141/SAMBR2027"],
                []]
    with open(matrix) as f:
        r = list(csv.reader(f))
    header, body = r[0], r[1:]
    last = None
    for row in body:
        if row[0] != last:
            rows_out += [[], [f"Papers: {row[0]}"] , ["Focal Ecosystem Component"] + header[2:]]
            last = row[0]
        rows_out.append(row[1:])
    t = '<table:table table:name="Plankton_literature_evidence">' + "".join(
        "<table:table-row>" + ("".join(cell(v) for v in rr) or "<table:table-cell/>") + "</table:table-row>" for rr in rows_out) + "</table:table>"
    k = xml.rfind("</office:spreadsheet>")
    # keep named expressions etc. after the last table
    last_table_end = xml.rfind("</table:table>", 0, k) + len("</table:table>")
    xml = xml[:last_table_end] + t + xml[last_table_end:]

with zipfile.ZipFile(dst, "w") as out:
    out.writestr(zipfile.ZipInfo("mimetype"), z.read("mimetype"), compress_type=zipfile.ZIP_STORED)
    for item in z.infolist():
        if item.filename == "mimetype":
            continue
        data = xml.encode("utf-8") if item.filename == "content.xml" else z.read(item.filename)
        out.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED)
print("wrote", dst)
