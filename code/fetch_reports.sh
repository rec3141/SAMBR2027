#!/bin/sh
# Pull portal data-error reports from DreamHost into the project (not the repo: they may contain names/emails).
set -e
DEST="$HOME/Documents/Research/Projects/2026-SAMBR/2_data/literature/plankton/geo/portal_reports.jsonl"
scp -q dreamhost:sambr2027_reports/reports.jsonl "$DEST" && wc -l "$DEST"
