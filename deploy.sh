#!/bin/sh
# Publish the static portal to cryomics.org/SAMBR2027 (DreamHost, ssh alias "dreamhost").
set -e
cd "$(dirname "$0")"
rsync -av --delete --exclude '.DS_Store' web/ dreamhost:cryomics.org/SAMBR2027/
echo "https://cryomics.org/SAMBR2027/"
