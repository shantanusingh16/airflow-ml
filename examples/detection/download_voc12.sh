#!/usr/bin/env bash
# Stage 1 (host): download + unpack PASCAL VOC 2012 trainval.
#
#   5,717 JPEG images + 5,717 XML annotations + ImageSets (~1.2 GB)
#   20 object classes + background
#
# Usage:  bash examples/detection/download_voc12.sh [dest-dir]   (default: voc12)
# Idempotent: skips the download when the tarball is already present (size > 1 GB).
set -euo pipefail

OUT="${1:-voc12}"
mkdir -p "$OUT"
cd "$OUT"

URL_OFFICIAL="http://host.robots.ox.ac.uk/pascal/VOC/voc2012/VOCtrainval_11-May-2012.tar"
URL_MIRROR="https://pjreddie.com/media/files/VOCtrainval_11-May-2012.tgz"
TAR="VOCtrainval_11-May-2012.tar"

if [ -s "$TAR" ]; then
  echo "found existing $TAR ($(du -h "$TAR" | cut -f1)); skipping download"
else
  echo "downloading $URL_MIRROR (mirror; official: $URL_OFFICIAL) ..."
  if ! curl -fL --retry 3 -o "$TAR" "$URL_MIRROR"; then
    echo "mirror failed, retrying official URL ..."
    curl -fL --retry 3 -o "$TAR" "$URL_OFFICIAL"
  fi
fi

echo "sha256: $(sha256sum "$TAR" | cut -d' ' -f1)"

if [ ! -d VOC2012 ]; then
  tar xf "$TAR"
fi

# --- verification -----------------------------------------------------------
JPG=$(find VOC2012/JPEGImages -name '*.jpg' | wc -l)
XML=$(find VOC2012/Annotations -name '*.xml' | wc -l)
TXT=$(test -f VOC2012/ImageSets/Main/trainval.txt && wc -l < VOC2012/ImageSets/Main/trainval.txt || echo 0)

echo "JPEGImages: $JPG (expect 5717)"
echo "Annotations: $XML (expect 5717)"
echo "trainval.txt lines: $TXT (expect 5717)"
test "$JPG" -eq 5717 && test "$XML" -eq 5717 && test "$TXT" -eq 5717 \
  && echo "DOWNLOAD OK: $(pwd)/VOC2012 is ready to upload (see upload_voc12.py)" \
  || { echo "DOWNLOAD FAILED: counts do not match"; exit 1; }