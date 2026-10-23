"""The ग्रहचार rail and the राशि प्रवेश box against the 2083 book.

data/book_rail.csv: every planet line of the rail, read off 2083 pp2-27
(PDF page = book page; the Sun's lines are in test_panchanga):
  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
`kind` is pada (Mars, Jupiter, Saturn, Rahu), nakshatra or sign (Mercury,
Venus), abhijit, station (वक्री/मार्गी) or heliacal (उदय/अस्त, not computed
yet); `detail` is what the line names, `again` the पुनः of a re-entry.
"""

import csv
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import panchanga
import render

DATA = Path(__file__).resolve().parent / "data" / "book_rail.csv"

# The rail's times follow the स्पष्ट ग्रह values, so a planet off by a few
# arc-seconds is off by (arc-seconds / its speed) in time: Mars near its
# January 2027 station moves 3′ a day. Allowed: POSITION arc-seconds at the
# planet's speed that day, and at least MINUTES. Near stations the tables'
# kinks leave Ketaki up to ~2′ from the book (Mars on 2027-02-03, 2083 p22,
# is 141 minutes at 12′ a day); Mercury has a few arc-minute misses of its
# own (docs/CALIBRATION.md section 5).
POSITION = 120
MINUTES = {"mercury": 60}
# The book's own Mars runs 40.2′ a day from 2026-09-05 to 09-13 (2083 pp12-13)
# against Ketaki's 37.3′, 26′ ahead by 09-13, then jumps back on 09-16: a
# daily motion carried forward and corrected. Its rail lines there inherit it.
BOOK_ANOMALIES = {(12, "mars", "पुनर्वसु|2"), (13, "mars", "पुनर्वसु|3")}
# उदय/अस्त the arcs don't reproduce (ours − book, days): Jupiter p9 −1, p10
# +5; Mercury p9 −1 (at its station, elongation 13.0°), p11 −5, p13 −1, p19
# −3, p21 +8, p24 −2; Venus p15 +5, p16 +2.
# The book's Mercury arcs around one superior conjunction are 14° (pp3, 5),
# around others 9.4°/14.75° (pp11, 13) and 12.5°/8.9° (pp19, 21).
HELIACAL_OPEN = {(9, "jupiter"), (10, "jupiter"), (9, "mercury"), (11, "mercury"), (13, "mercury"), (19, "mercury"),
                 (21, "mercury"), (24, "mercury"), (15, "venus"), (16, "venus")}

# The book's own राशि प्रवेश boxes, 2083.
BOXES = {
    2: "१सू.१", 3: "१७बु.१, ६शु.२", 4: "१सू.२, २८मं.१, ३१बु.२, ३०शु.३", 5: "१५बु.३",
    6: "१सू.३, १८बृ.४, २४शु.४", 8: "२०बु.३, १९शु.५", 9: "१सू.४", 10: "१८मं.३, २०बु.४, १५शु.६",
    11: "१सू.५, ६बु.५", 12: "२२बु.६, १७शु.७", 13: "१सू.६, २मं.४, ९बु.७", 15: "१सू.७",
    16: "१२बृ.५, २२शु.६", 17: "१सू.८, २६मं.५, २६शु.७", 19: "१सू.९, ७बु.९", 23: "१सू.११", 26: "२२बु.१२",
    24: "११बु.१०, १२शु.१०", 25: "१सू.१२, २५मं.४, २६बु.११, ७शु.११",
}
# Where the book's box disagrees with its own rail: p18 "१७बु.८" against the
# rail's "१६ वृश्चिकमा बुध"; p21 and p22 leave out Mercury's and Jupiter's
# entries that their rails print; p20 "१७सू.८" for the rail's "१७ वृश्चिकमा शुक्र".
BOXES_DIFFERENT = {18: "१७बु.८, १९रा.१०के.४", 20: "१७सू.८", 21: "३०सू.१०", 22: "१४बु.११, १५शु.९"}

# The kundali on each page, as printed: each planet's sign, 1 = मेष (2083,
# 21 pages read; a planet missing was illegible). The book has no Moon.
KUNDALIS = {
    3: {"sun": 1, "venus": 2, "mars": 12, "mercury": 12, "saturn": 12, "rahu": 11, "jupiter": 3, "ketu": 5},
    4: {"sun": 1, "mercury": 1, "venus": 2, "mars": 12, "saturn": 12, "rahu": 11, "jupiter": 3, "ketu": 5},
    6: {"sun": 2, "mercury": 3, "venus": 3, "mars": 1, "saturn": 12, "rahu": 11, "jupiter": 4, "ketu": 5},
    7: {"sun": 3, "mercury": 3, "jupiter": 4, "venus": 4, "ketu": 5, "mars": 1, "saturn": 12, "rahu": 11},
    9: {"sun": 4, "jupiter": 4, "venus": 5, "ketu": 5, "mercury": 3, "mars": 2, "saturn": 12, "rahu": 11},
    10: {"sun": 4, "jupiter": 4, "ketu": 5, "mars": 3, "mercury": 3, "venus": 6},
    11: {"sun": 5, "ketu": 5, "venus": 6, "mercury": 4, "jupiter": 4, "mars": 3},
    12: {"sun": 5, "mercury": 5, "ketu": 5, "venus": 6, "jupiter": 4, "mars": 3, "rahu": 11, "saturn": 12},
    13: {"sun": 5, "ketu": 5, "mercury": 6, "venus": 7, "jupiter": 4, "mars": 3, "rahu": 11, "saturn": 12},
    14: {"sun": 6, "mercury": 7, "venus": 7, "ketu": 5, "mars": 4, "jupiter": 4, "saturn": 12, "rahu": 11},
    15: {"sun": 6, "mercury": 7, "venus": 7, "ketu": 5, "mars": 4, "jupiter": 4, "saturn": 12, "rahu": 11},
    16: {"sun": 7, "mercury": 7, "venus": 7, "mars": 4, "jupiter": 4, "rahu": 11, "saturn": 12},
    17: {"sun": 8, "mercury": 7, "venus": 7, "mars": 5, "jupiter": 5, "ketu": 5, "rahu": 11, "saturn": 12},
    18: {"sun": 8, "mercury": 7, "venus": 7, "mars": 5, "jupiter": 5, "ketu": 5, "rahu": 11, "saturn": 12},
    19: {"sun": 8, "mercury": 8, "venus": 7, "mars": 5, "jupiter": 5, "ketu": 4, "rahu": 10, "saturn": 12},
    20: {"sun": 9, "mercury": 9, "venus": 7, "mars": 5, "jupiter": 5, "ketu": 4, "rahu": 10, "saturn": 12},
    21: {"sun": 9, "mercury": 10, "rahu": 10, "venus": 8, "saturn": 12, "mars": 5, "jupiter": 5, "ketu": 4},
    22: {"sun": 10, "mercury": 10, "rahu": 10, "jupiter": 4, "ketu": 4, "mars": 5, "saturn": 12},
    23: {"sun": 10, "rahu": 10, "mercury": 11, "venus": 9, "saturn": 12},
    24: {"sun": 11, "mercury": 11, "saturn": 12, "rahu": 10, "venus": 9, "mars": 5},
    26: {"sun": 12, "saturn": 12, "mercury": 11, "venus": 11, "rahu": 10, "mars": 4, "jupiter": 4, "ketu": 4},
}
# Charts no single moment of ours reproduces: a planet changes sign in the
# fortnight and the book draws it at one end. p16 Jupiter, still in Cancer
# (enters Leo Oct 29, ours Oct 31), and p24 Mercury and Venus, still in
# Aquarius and Sagittarius (both enter Capricorn Feb 24, ours Feb 26), are at
# the start; p17 the Sun, already in Scorpio (enters Nov 17, ours Nov 15), at
# the end.
KUNDALI_DIFFERENT = {16: {"jupiter"}, 17: {"sun"}, 24: {"mercury", "venus"}}


def describe(entry: dict) -> tuple[str, str]:
    if "heliacal" in entry:
        return "heliacal", f"{entry['side']}|{entry['heliacal']}"
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
    @staticmethod
    def speed(body: str, day: date) -> float:
        """Arc-seconds a minute, from the day's स्पष्ट ग्रह to the next's."""
        a, b = panchanga._planet_longitude(body, day), panchanga._planet_longitude(body, day + timedelta(days=1))
        return max(abs((b - a + 180) % 360 - 180) * 3600 / 1440, 1e-6)

    @classmethod
    def setUpClass(cls):
        cls.pages = {p["page"]: p for p in panchanga.year(2083)}
        with open(DATA, newline="") as f:
            cls.lines = list(csv.DictReader(f))

    def test_every_line(self):
        for line in self.lines:
            page = int(line["page"])
            if (page, line["body"], line["detail"]) in BOOK_ANOMALIES:
                continue
            if line["kind"] == "heliacal" and (page, line["body"]) in HELIACAL_OPEN:
                continue
            with self.subTest(page=page, gate=line["gate"], body=line["body"], detail=line["detail"]):
                # A planet at its station barely moves, so the turn by the
                # tables can fall either side of a sunrise, even onto the
                # next page.
                nearby = (page - 1, page, page + 1) if line["kind"] in ("station", "heliacal") else (page,)
                found = [(row, e) for p in nearby if p in self.pages for row in self.pages[p]["rows"]
                         for e in row["planet_events"]
                         if e["body"] == line["body"] and describe(e) == (line["kind"], line["detail"])
                         and bool(e.get("again")) == (line["again"] == "1")]
                if line["kind"] == "station":
                    self.assertTrue(found)
                    continue
                if line["kind"] == "heliacal":
                    # Within an hour of the book's moment, which may be on the next page.
                    hours, minutes = map(int, line["clock"].split(":"))
                    printed = next(r for r in self.pages[page]["rows"] if r["gate"] == int(line["gate"]))
                    midnight = datetime.fromisoformat(f"{printed['date']}T00:00:00+05:45")
                    gap = min(abs((datetime.fromisoformat(e["at"]) - midnight).total_seconds() / 60 - (hours * 60 + minutes))
                              for _, e in found)
                    self.assertLessEqual(gap, 60)
                    continue
                self.assertEqual(len(found), 1)
                row, entry = found[0]
                self.assertEqual(row["gate"], int(line["gate"]))
                hours, minutes = map(int, line["clock"].split(":"))
                ours = entry["clock"][0] * 60 + entry["clock"][1]
                speed = self.speed(line["body"], date.fromisoformat(row["date"]))
                allowed = max(MINUTES.get(line["body"], 20), POSITION / speed)
                self.assertLessEqual(abs(ours - (hours * 60 + minutes)), allowed)

    def test_boxes(self):
        for page, printed in BOXES.items():
            with self.subTest(page=page):
                self.assertEqual(render.rashi_pravesh(self.pages[page]["header"]["sign_entries"]), printed)

    def test_box_differences_still_differ(self):
        for page, printed in BOXES_DIFFERENT.items():
            with self.subTest(page=page):
                self.assertNotEqual(render.rashi_pravesh(self.pages[page]["header"]["sign_entries"]), printed)

    def test_status_boxes(self):
        # 2083 pp2 and 27.
        for page, printed in ((2, "मं.मा.उ., बु.मा.उ., बृ.मा.उ., शु.मा.उ., शं.मा.उ."),
                              (27, "मं.मा.उ., बु.मा.उ., बृ.व.उ., शु.मा.उ., शं.मा.अ.")):
            with self.subTest(page=page):
                self.assertIn(printed, render.status_box(self.pages[page]["header"]["planet_status"]))

    def test_kundali(self):
        for page, printed in KUNDALIS.items():
            with self.subTest(page=page):
                signs = self.pages[page]["header"]["kundali"]["signs"]
                wrong = {body for body, sign in printed.items() if signs[body] + 1 != sign}
                self.assertEqual(wrong, KUNDALI_DIFFERENT.get(page, set()))

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
