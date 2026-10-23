#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "weasyprint",
# ]
# ///
"""Compute a Bikram Sambat year of the राष्ट्रिय पञ्चाङ्ग and write JSON and PDF.

    ./generate.py 2083                     # every fortnight
    ./generate.py 2083 --page 21           # one fortnight (pages number from 2, as in the book)
    ./generate.py 2083 --config 2083.json  # festival notes; overrides for computed fields
"""

import argparse
import json
import sys
from pathlib import Path

import panchanga
import render


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("year", type=int, help="Bikram Sambat year, e.g. 2083")
    parser.add_argument("--page", type=int, action="append", help="book page (2 onwards)")
    parser.add_argument("--config", type=Path, help="JSON with editorial fields")
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()

    if args.year < panchanga.VERIFIED_FROM:
        print(f"warning: BS {args.year} is before {panchanga.VERIFIED_FROM}; "
              "month starts are not verified for it", file=sys.stderr)
    config = json.loads(args.config.read_text()) if args.config else {}
    pages = panchanga.year(args.year, config)
    if args.page:
        pages = [p for p in pages if p["page"] in args.page]

    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"panchang-{args.year}" + (
        "-" + "-".join(str(p) for p in sorted(args.page)) if args.page else "")
    json_path = args.out / f"{stem}.json"
    json_path.write_text(json.dumps(pages, ensure_ascii=False, indent=1))
    print(json_path)
    if not args.no_pdf:
        pdf_path = args.out / f"{stem}.pdf"
        render.write_pdf(pages, str(pdf_path), config)
        print(pdf_path)


if __name__ == "__main__":
    main()
