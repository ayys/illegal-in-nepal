#!/bin/bash
# fetch_ocr.sh YEAR... : download archive.org scans, extract page images, OCR to tsv/
cd "$(dirname "$0")"
for y in "$@"; do
  [ -s "$y.pdf" ] || curl -sL --retry 3 -o "$y.pdf" "https://archive.org/download/2081_20240828/$y.pdf"
  mkdir -p "h$y" tsv
  [ -e "h$y/i-000.jpg" ] || [ -e "h$y/i-000.png" ] || pdfimages -j "$y.pdf" "h$y/i"
  for img in h$y/i-*; do
    b=$(basename "${img%.*}")
    [ -s "tsv/$y-$b.tsv" ] || tesseract "$img" "tsv/$y-$b" -l nep tsv >/dev/null 2>&1
  done
  echo "done $y $(ls h$y | wc -l) pages"
done
