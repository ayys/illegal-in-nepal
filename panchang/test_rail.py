"""The ग्रहचार rail and the राशि प्रवेश box against the 2083 book.

data/book_rail.csv: every planet line of the rail, read off 2083 pp2-9, 18,
21 and 22 (PDF page = book page):
  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
`kind` is pada (Mars, Jupiter, Saturn, Rahu), nakshatra or sign (Mercury,
Venus), abhijit, station (वक्री/मार्गी) or heliacal (उदय/अस्त, not computed
yet); `detail` is what the line names, `again` the पुनः of a re-entry.
"""

import csv
import unittest
from pathlib import Path

import panchanga
import render

DATA = Path(__file__).resolve().parent / "data" / "book_rail.csv"

# Minutes. The rail's times follow the स्पष्ट ग्रह values, so a planet a few
# arc-seconds off is off by (arc-seconds / its speed): Mars near its January
# 2027 station moves 3′ a day, and Mercury has a few arc-minute misses
# (docs/CALIBRATION.md section 5).
TOLERANCE = {"mars": 150, "mercury": 60, "venus": 30, "jupiter": 30, "saturn": 30, "rahu": 30}

# The book's own राशि प्रवेश boxes, 2083.
BOXES = {
    2: "१सू.१", 3: "१७बु.१, ६शु.२", 4: "१सू.२, २८मं.१, ३१बु.२, ३०शु.३", 5: "१५बु.३",
    6: "१सू.३, १८बृ.४, २४शु.४", 8: "२०बु.३, १९शु.५", 9: "१सू.४", 10: "१८मं.३, २०बु.४, १५शु.६",
    11: "१सू.५, ६बु.५", 15: "१सू.७", 16: "१२बृ.५, २२शु.६", 23: "१सू.११",
    24: "११बु.१०, १२शु.१०", 25: "१सू.१२, २५मं.४, २६बु.११, ७शु.११",
}
# Where the book's box disagrees with its own rail: p18 "१७बु.८" against the
# rail's "१६ वृश्चिकमा बुध"; p21 and p22 leave out Mercury's and Jupiter's
# entries that their rails print.
BOXES_DIFFERENT = {18: "१७बु.८, १९रा.१०के.४", 21: "३०सू.१०", 22: "१४बु.११, १५शु.९"}


def describe(entry: dict) -> tuple[str, str]:
    if "station" in entry:
        return "station", entry["station"]
    if entry["body"] in ("mercury", "venus"):
        if entry.get("abhijit"):
            return "abhijit", entry["abhijit"]
        if entry.get("nakshatra"):
            return "nakshatra", entry["nakshatra"] + (f"|{entry['enters']}" if entry.get("enters") else "")
        return "sign", entry["enters"]
    return "pada", f"{entry['nakshatra']}|{entry['pada']}" + (f"|{entry['enters']}" if entry.get("enters") else "")


class RailTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {p["page"]: p for p in panchanga.year(2083)}
        with open(DATA, newline="") as f:
            cls.lines = list(csv.DictReader(f))

    def test_every_line(self):
        for line in self.lines:
            if line["kind"] == "heliacal":
                continue
            with self.subTest(page=line["page"], gate=line["gate"], body=line["body"], detail=line["detail"]):
                found = [(row, e) for row in self.pages[int(line["page"])]["rows"] for e in row["planet_events"]
                         if e["body"] == line["body"] and describe(e) == (line["kind"], line["detail"])
                         and bool(e.get("again")) == (line["again"] == "1")]
                self.assertEqual(len(found), 1)
                row, entry = found[0]
                if line["kind"] == "station":
                    # A planet at its station barely moves, so the turn by
                    # the tables can fall either side of a sunrise.
                    self.assertLessEqual(abs(row["gate"] - int(line["gate"])), 1)
                    continue
                self.assertEqual(row["gate"], int(line["gate"]))
                hours, minutes = map(int, line["clock"].split(":"))
                ours = entry["clock"][0] * 60 + entry["clock"][1]
                self.assertLessEqual(abs(ours - (hours * 60 + minutes)), TOLERANCE[line["body"]])

    def test_boxes(self):
        for page, printed in BOXES.items():
            with self.subTest(page=page):
                self.assertEqual(render.rashi_pravesh(self.pages[page]["header"]["sign_entries"]), printed)

    def test_box_differences_still_differ(self):
        for page, printed in BOXES_DIFFERENT.items():
            with self.subTest(page=page):
                self.assertNotEqual(render.rashi_pravesh(self.pages[page]["header"]["sign_entries"]), printed)

    def test_rail_text(self):
        # The wording, against lines as printed.
        rows = {r["gate"]: r for r in self.pages[21]["rows"]}
        texts = [render.rail_text(gate, e) for gate, row in rows.items() for e in row["planet_events"] if "station" not in e]
        for printed in ("२५ मकरमा बुध", "२९ अभिजितमा बुध", "१ श्रवणमा बुध", "२ अभिजितत्याग बुध",
                        "३ ज्येष्ठामा शुक्र", "२८ पू.फा. २ मा मंगल", "२ पुनःपू.फा. १ मा मंगल"):
            with self.subTest(line=printed):
                self.assertTrue(any(t.startswith(printed) for t in texts))


if __name__ == "__main__":
    unittest.main()
