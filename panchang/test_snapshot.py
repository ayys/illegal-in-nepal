"""Snapshots: the whole of 2083 as printed text, and Mars to Saturn and राहु
from 1970 to 2100.

The book tests check a few pages against print; these catch any change
anywhere else. The planet snapshot also pins the Ketaki table rows that the
2082 and 2083 books never reach (each planet's केन्द्रs sweep every 10° row
within the 130 years). A failure here is not an error by itself: if the
change is deliberate, and the book tests still pass, regenerate with

    python3 test_snapshot.py --update

and commit the new files with the change, so the diff shows what moved.
"""

import difflib
import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

import ketaki
import panchanga
import render

DATA = Path(__file__).resolve().parent / "data"


def _text(html: str) -> list[str]:
    """Rows of an HTML fragment as "cell|cell|…" lines, stacked cells joined
    by spaces."""
    lines = []
    for row in re.findall(r"<tr>(.*?)</tr>", html) or [html]:
        cells = []
        for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row) or [row]:
            spans = re.findall(r'<span class="stack">(.*?)</span>', cell)
            cells.append(" ".join(spans) if spans else re.sub(r"<[^>]+>", " ", cell).strip())
        lines.append("|".join(cells))
    return lines


def book_text(bs_year: int) -> list[str]:
    lines = []
    for page in panchanga.year(bs_year):
        rows, header = page["rows"], page["header"]
        lines.append(f"== page {page['page']}")
        lines.append(render.header_line(header))
        lines += _text(render.day_table(rows, {}))[1:]
        lines += [re.sub(r"\s+", " ", l).strip() for l in
                  re.sub(r"<[^>]+>", "\n", render.rail(rows)).split("\n") if l.strip()][1:]
        lines += _text(render.graha_table(rows))[1:]
        lines += _text(render.lagna_table(rows))
        lines.append("पापांश: " + __import__("editorial").papamsha_text(header["papamsha"]))
        lines.append("राशि प्रवेश: " + render.rashi_pravesh(header["sign_entries"]))
        lines.append("कुण्डली: " + " ".join(f"{b}={s + 1}" for b, s in sorted(header["kundali"]["signs"].items())))
        if header.get("planet_status"):
            lines.append("स्थिति: " + re.sub(r"<[^>]+>", "", render.status_box(header["planet_status"])))
    return lines


def planets_text() -> list[str]:
    lines = []
    day, end = date(1970, 1, 1), date(2100, 12, 31)
    while day <= end:
        values = [round(ketaki.at_sunrise(body, day) * 3600) for body in ketaki.PLANETS]
        values.append(round(ketaki.rahu_of_day(day) * 3600))
        lines.append(day.isoformat() + " " + " ".join(map(str, values)))
        day += timedelta(days=11)
    return lines


SNAPSHOTS = {"snapshot_2083.txt": lambda: book_text(2083), "snapshot_planets.txt": planets_text}


class SnapshotTest(unittest.TestCase):
    def check(self, name: str):
        want = (DATA / name).read_text().splitlines()
        got = SNAPSHOTS[name]()
        if got != want:
            diff = list(difflib.unified_diff(want, got, "snapshot", "now", lineterm="", n=1))
            self.fail(f"{name}: {sum(1 for d in diff if d.startswith('+') and not d.startswith('+++'))} lines "
                      f"changed\n" + "\n".join(diff[:40]))

    def test_book_2083(self):
        self.check("snapshot_2083.txt")

    def test_planets_1970_2100(self):
        self.check("snapshot_planets.txt")


if __name__ == "__main__":
    if "--update" in sys.argv:
        for name, make in SNAPSHOTS.items():
            (DATA / name).write_text("\n".join(make()) + "\n")
            print("wrote", DATA / name)
    else:
        unittest.main()
