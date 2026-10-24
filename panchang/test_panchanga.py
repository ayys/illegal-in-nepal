"""Regression tests against values printed in the national panchang books.

Sources (PDF page = book page; page 1 is the year's cover sheet, fortnights
start on page 2):

  2083  FORMAT-2083-A   https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
  2082  npnbs_2082      https://giwmscdnone.gov.np/media/pages/files/npnbs_2082_ussfian.pdf

Older books (BS 2031-2079 scans, one image per PDF page) are in the archive.org
item https://archive.org/details/2081_20240828; what was read from them lives
in data/book_sankrantis.csv and data/month_starts.csv, each row with its page.
See docs/SOURCES.md for the full list.
"""

import csv
import json
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import panchanga
import surya

DATA = Path(__file__).parent / "data"

# End times printed in the 2083 book: per day, the clock times (NST, hours
# past 24 for after midnight) at which the tithi, nakshatra and yoga end.
# None means the book prints अहोरात्र. Pages 2-3 (वैशाख), 16 (कार्तिक कृष्ण)
# and 21 (पौष शुक्ल).
BOOK = {
    date(2026, 4, 14): ("21:32", "13:36", "13:29"),
    date(2026, 4, 15): ("20:40", "13:34", "11:50"),
    date(2026, 4, 16): ("19:22", "13:06", "9:50"),
    date(2026, 4, 17): ("17:42", "12:15", ("7:30", "28:55")),
    date(2026, 4, 18): ("15:43", "11:5", "26:7"),
    date(2026, 4, 19): ("13:31", "9:41", "23:9"),
    date(2026, 4, 20): ("11:10", "8:6", "20:5"),
    date(2026, 4, 21): ("8:44", ("6:27", "28:47"), "16:59"),
    date(2026, 4, 22): (("6:18", "27:58"), "27:12", "13:55"),
    date(2026, 4, 23): ("25:48", "25:47", "10:58"),
    date(2026, 4, 24): ("23:53", "24:37", "8:9"),
    date(2026, 4, 27): ("20:13", "23:14", "23:35"),
    date(2026, 4, 28): ("19:54", "23:40", "22:19"),
    date(2026, 4, 29): ("20:5", "24:36", "21:28"),
    date(2026, 4, 30): ("20:47", "26:1", "21:0"),
    date(2026, 5, 1): ("21:57", "27:54", "20:55"),
    date(2026, 10, 27): ("8:24", "18:20", "14:6"),
    date(2026, 10, 28): (("6:33", "28:27"), "17:4", "11:23"),
    date(2026, 10, 29): ("26:10", "15:35", ("8:28", "29:25")),
    date(2026, 10, 30): ("23:48", "13:58", "26:18"),
    date(2026, 10, 31): ("21:24", "12:18", "23:10"),
    date(2026, 11, 1): ("19:5", "10:39", "20:6"),
    date(2026, 11, 2): ("16:55", "9:8", "17:9"),
    date(2026, 11, 3): ("14:58", "7:48", "14:23"),
    date(2026, 11, 4): ("13:19", ("6:45", "30:1"), "11:51"),
    date(2026, 11, 5): ("12:1", "29:42", "9:37"),
    date(2026, 11, 6): ("11:10", "29:51", ("7:42", "30:9")),
    date(2026, 11, 7): ("10:47", None, "29:0"),
    date(2026, 11, 8): ("10:54", "6:28", "28:14"),
    date(2026, 11, 9): ("11:33", "7:36", "27:52"),
    date(2027, 1, 8): ("27:31", "9:10", "15:45"),
    date(2027, 1, 9): ("29:30", "11:44", "16:13"),
    date(2027, 1, 10): (None, "14:5", "16:29"),
    date(2027, 1, 12): ("8:25", "17:41", "16:8"),
    date(2027, 1, 13): ("9:10", "18:47", "15:25"),
    date(2027, 1, 14): ("9:25", "19:22", "14:18"),
    date(2027, 1, 15): ("9:8", "19:29", "12:47"),
    date(2027, 1, 16): ("8:23", "19:9", "10:54"),
    date(2027, 1, 17): (("7:11", "29:36"), "18:24", ("8:40", "30:9")),
    date(2027, 1, 18): ("27:44", "17:20", "27:24"),
    date(2027, 1, 19): ("25:37", "15:59", "24:27"),
    date(2027, 1, 20): ("23:20", "14:27", "21:23"),
    date(2027, 1, 21): ("20:59", "12:49", "18:14"),
    date(2027, 1, 22): ("18:38", "11:8", "15:4"),
}
# Karana name at sunrise and the end times of the karanas that end that day
# (2083 book pages 2 and 21).
KARANAS = {
    date(2026, 4, 17): ("च.", ["6:34", "28:45"]),
    date(2027, 1, 8): ("किं.", ["14:27"]),
    date(2027, 1, 9): ("बा.", ["16:32"]),
    date(2027, 1, 10): ("तै.", ["18:23"]),
    date(2027, 1, 11): ("व.", ["19:51"]),
    date(2027, 1, 12): ("ब.", ["20:52"]),
    date(2027, 1, 17): ("तै.", ["18:26"]),
    date(2027, 1, 22): ("भ.", ["7:48", "29:29"]),
}
# आनन्दादि योग column (2083 book page 21).
ANANDADI = {
    date(2027, 1, 8): "प्रवर्द्ध", date(2027, 1, 9): "चर", date(2027, 1, 10): "गद",
    date(2027, 1, 11): "शुभ", date(2027, 1, 12): "मृत्यु", date(2027, 1, 13): "पद्म",
    date(2027, 1, 14): "छत्र", date(2027, 1, 15): "श्रीवत्स", date(2027, 1, 16): "सौम्य",
    date(2027, 1, 17): "काल", date(2027, 1, 18): "स्थिर", date(2027, 1, 19): "मातङ्ग",
    date(2027, 1, 20): "अमृत", date(2027, 1, 21): "काण", date(2027, 1, 22): "लुम्ब",
}
# सूर्योदय / सूर्यास्त clock (2083 book pages 2, 20 and 21).
SUN = {
    date(2026, 4, 14): ("5:43", "18:27"), date(2026, 4, 15): ("5:42", "18:28"),
    date(2026, 4, 16): ("5:41", "18:28"), date(2026, 4, 17): ("5:40", "18:29"),
    date(2026, 12, 25): ("6:54", "17:14"), date(2026, 12, 26): ("6:54", "17:14"),
    date(2026, 12, 27): ("6:54", "17:15"), date(2026, 12, 28): ("6:55", "17:15"),
    date(2026, 12, 29): ("6:55", "17:16"), date(2026, 12, 30): ("6:56", "17:17"),
    date(2026, 12, 31): ("6:56", "17:17"), date(2027, 1, 1): ("6:56", "17:18"),
    date(2027, 1, 2): ("6:56", "17:19"), date(2027, 1, 3): ("6:57", "17:19"),
    date(2027, 1, 4): ("6:57", "17:20"), date(2027, 1, 5): ("6:57", "17:21"),
    date(2027, 1, 6): ("6:57", "17:22"), date(2027, 1, 7): ("6:58", "17:22"),
    date(2027, 1, 8): ("6:58", "17:23"), date(2027, 1, 9): ("6:58", "17:24"),
    date(2027, 1, 10): ("6:58", "17:25"), date(2027, 1, 11): ("6:58", "17:26"),
    date(2027, 1, 12): ("6:58", "17:26"), date(2027, 1, 13): ("6:58", "17:27"),
    date(2027, 1, 14): ("6:58", "17:28"), date(2027, 1, 15): ("6:58", "17:29"),
    date(2027, 1, 16): ("6:58", "17:30"), date(2027, 1, 17): ("6:58", "17:30"),
    date(2027, 1, 18): ("6:57", "17:31"), date(2027, 1, 19): ("6:57", "17:32"),
    date(2027, 1, 20): ("6:57", "17:33"), date(2027, 1, 21): ("6:57", "17:34"),
    date(2027, 1, 22): ("6:57", "17:35"),
}
# Page header by 2083 book page: lunar month, paksha, Nepal Sambat year and
# month, Gregorian span, ritu.
HEADERS = {
    2: ("वैशाख", "कृष्ण", 1146, "चौलागा", "अप्रिल 2026", ["वसन्त"]),
    4: ("शुद्ध ज्येष्ठ", "कृष्ण", 1146, "वछलागा", "मे 2026", ["वसन्त", "ग्रीष्म"]),
    5: ("अधिक ज्येष्ठ", "शुक्ल", 1146, "अनलाथ्वः", "मे 2026", ["ग्रीष्म"]),
    6: ("अधिक ज्येष्ठ", "कृष्ण", 1146, "अनलागा", "जुन 2026", ["ग्रीष्म"]),
    7: ("शुद्ध ज्येष्ठ", "शुक्ल", 1146, "तछलाथ्वः", "जुन 2026", ["ग्रीष्म"]),
    20: ("पौष", "कृष्ण", 1147, "थिंल्लागा", "डिसेम्बर 2026 + जनवरी 2027", ["हेमन्त"]),
}
# Start of each lagna from मकर through धनु (the last one just before the next
# sunrise), 2083 book page 21.
LAGNA = {
    date(2027, 1, 8): "7:25 9:8 10:36 12:2 13:38 15:34 17:49 20:9 22:25 24:40 26:59 29:17",
    date(2027, 1, 9): "7:21 9:4 10:32 11:58 13:34 15:30 17:45 20:5 22:21 24:36 26:55 29:13",
    date(2027, 1, 12): "7:9 8:52 10:20 11:46 13:22 15:19 17:33 19:53 22:9 24:25 26:43 29:1",
}
# उदयकालिक स्पष्ट ग्रह: sun, moon and rahu as sign:degree:minute:second, and
# बेलान्तर (2083 book page 21).
SPASHTA = {
    date(2027, 1, 8): ("8:22:59:25", "8:25:33:40", "9:28:13:9", "+6:44"),
    date(2027, 1, 9): ("8:24:0:50", "9:7:35:59", "9:28:9:58", "+7:11"),
    date(2027, 1, 10): ("8:25:2:14", "9:19:42:57", "9:28:6:48", "+7:36"),
    date(2027, 1, 11): ("8:26:3:39", "10:1:57:45", "9:28:3:37", "+8:2"),
    date(2027, 1, 12): ("8:27:5:2", "10:14:23:12", "9:28:0:26", "+8:26"),
}
# Sun and Moon spashta in other seasons (2083 book pages 3, 16 and 21).
SUN_MOON = {
    date(2026, 4, 18): ("0:3:38:58", "0:10:8:29"), date(2026, 4, 19): ("0:4:37:30", "0:24:16:1"),
    date(2026, 4, 20): ("0:5:36:0", "1:8:30:50"), date(2026, 4, 21): ("0:6:34:28", "1:22:49:39"),
    date(2026, 4, 22): ("0:7:32:54", "2:7:8:41"), date(2026, 4, 23): ("0:8:31:18", "2:21:24:3"),
    date(2026, 4, 24): ("0:9:29:39", "3:5:32:28"),
    date(2026, 10, 27): ("6:8:47:54", "0:19:36:40"), date(2026, 10, 28): ("6:9:47:57", "1:3:36:36"),
    date(2026, 10, 29): ("6:10:48:3", "1:17:46:20"), date(2026, 10, 30): ("6:11:48:10", "2:2:2:54"),
    date(2026, 10, 31): ("6:12:48:20", "2:16:23:0"), date(2026, 11, 1): ("6:13:48:32", "3:0:42:42"),
    date(2026, 11, 2): ("6:14:48:46", "3:14:58:14"),
    date(2027, 1, 13): ("8:28:6:25", "10:27:1:33"), date(2027, 1, 14): ("8:29:7:47", "11:9:54:24"),
}
# ग्रह-सञ्चार: the Sun entering a nakshatra quarter (and sign / अभिजित्),
# 2083 book pages 2, 11, 17, 21 and 25.
SUN_PADAS = [
    # pp2, 11, 17 and 25 tell the SS's sine table from exact sines: the table
    # puts 13 of these 16 a minute late (surya._manda).
    (date(2026, 4, 14), "अश्विनी", 1, "मेष", "12:4"),
    (date(2026, 4, 17), "अश्विनी", 2, None, "21:53"),
    (date(2026, 8, 14), "अश्लेषा", 4, None, "11:59"),
    (date(2026, 8, 17), "मघा", 1, "सिंह", "23:28"),
    (date(2026, 8, 21), "मघा", 2, None, "10:48"),
    (date(2026, 8, 24), "मघा", 3, None, "22:0"),
    (date(2026, 8, 28), "मघा", 4, None, "9:3"),
    (date(2026, 11, 10), "विशाखा", 2, None, "17:33"),
    (date(2026, 11, 13), "विशाखा", 3, None, "24:50"),
    (date(2026, 11, 17), "विशाखा", 4, "वृश्चिक", "7:59"),
    (date(2026, 11, 20), "अनुराधा", 1, None, "15:1"),
    (date(2026, 11, 23), "अनुराधा", 2, None, "21:56"),
    (date(2027, 3, 11), "पू.भा.", 3, None, "25:42"),
    (date(2027, 3, 15), "पू.भा.", 4, "मीन", "9:48"),
    (date(2027, 3, 18), "उ.भा.", 1, None, "18:4"),
    (date(2027, 3, 21), "उ.भा.", 2, None, "26:30"),
    (date(2027, 1, 8), "पू.षा.", 4, None, "15:0"),
    (date(2027, 1, 11), "उ.षा.", 1, None, "21:11"),
    (date(2027, 1, 14), "उ.षा.", 2, "मकर", "27:23"),
    (date(2027, 1, 18), "उ.षा.", 3, None, "9:38"),
    (date(2027, 1, 21), "उ.षा.", 4, "अभिजित", "15:56"),
]
# The 2082 book, read the same way: वैशाख शुक्ल (page 3) and माघ कृष्ण (page 20).
BOOK_2082 = {
    date(2025, 4, 28): ("23:1", "23:34", "21:58"), date(2025, 4, 29): ("20:40", "22:0", "18:57"),
    date(2025, 4, 30): ("18:28", "20:35", "16:3"), date(2025, 5, 1): ("16:31", "19:24", "13:21"),
    date(2025, 5, 2): ("14:51", "18:33", "10:53"), date(2025, 5, 3): ("13:34", "18:4", "8:43"),
    date(2025, 5, 4): ("12:42", "18:1", "6:53"), date(2025, 5, 5): ("12:19", "18:27", ("5:25", "28:22")),
    date(2025, 5, 6): ("12:27", "19:22", "27:42"), date(2025, 5, 7): ("13:5", "20:48", "27:26"),
    date(2025, 5, 8): ("14:11", "22:40", "27:31"), date(2025, 5, 9): ("15:43", "24:55", "27:53"),
    date(2025, 5, 10): ("17:34", "27:25", "28:26"), date(2025, 5, 11): ("19:35", None, "29:5"),
    date(2025, 5, 12): ("21:37", "6:3", None),
    date(2026, 1, 4): ("14:22", "17:33", ("7:31", "28:54")), date(2026, 1, 5): ("12:46", "16:40", "26:34"),
    date(2026, 1, 6): ("11:33", "16:9", "24:33"), date(2026, 1, 7): ("10:46", "16:5", "22:54"),
    date(2026, 1, 8): ("10:27", "16:28", "21:38"), date(2026, 1, 9): ("10:40", "17:22", "20:46"),
    date(2026, 1, 10): ("11:23", "18:45", "20:17"), date(2026, 1, 11): ("12:36", "20:36", "20:10"),
    date(2026, 1, 12): ("14:15", "22:49", "20:20"), date(2026, 1, 13): ("16:13", "25:19", "20:45"),
    date(2026, 1, 14): ("18:22", "27:56", "21:16"), date(2026, 1, 15): ("20:33", "30:30", "21:47"),
    date(2026, 1, 16): ("22:33", None, "22:10"), date(2026, 1, 17): ("24:15", "8:51", "22:20"),
    date(2026, 1, 18): ("25:31", "10:52", "22:11"),
}
# 2082 book pages 3 and 20.
SPASHTA_2082 = {
    date(2025, 4, 28): ("0:13:37:48", "0:15:52:16", "11:1:4:31", "-1:32"),
    date(2025, 4, 29): ("0:14:35:59", "1:0:10:53", "11:1:1:21", "-1:41"),
    date(2025, 4, 30): ("0:15:34:7", "1:14:25:9", "11:0:58:10", "-1:49"),
    date(2026, 1, 4): ("8:19:9:35", "2:27:9:13", "10:17:46:26", "+5:1"),
    date(2026, 1, 5): ("8:20:11:2", "3:11:5:13", "10:17:43:15", "+5:29"),
    date(2026, 1, 6): ("8:21:12:28", "3:24:48:19", "10:17:40:4", "+5:57"),
    date(2026, 1, 7): ("8:22:13:53", "4:8:16:58", "10:17:36:54", "+6:24"),
    date(2026, 1, 8): ("8:23:15:19", "4:21:30:5", "10:17:33:43", "+6:51"),
    date(2026, 1, 9): ("8:24:16:43", "5:4:27:45", "10:17:30:32", "+7:17"),
}
# दिनमान as printed, घटी।पला for each row of a 2083 page, in order.
DINAMANA = {
    2: "31:52 31:56 31:59 32:3",
    5: "33:44 33:47 33:50 33:52 33:55 33:57 34:0 34:2 34:4 34:6 34:9 34:11 34:13 34:14 34:16",
    8: "34:32 34:32 34:31 34:30 34:29 34:28 34:26 34:25 34:24 34:22 34:21 34:19 34:17 34:16 34:14",
    11: "32:51 32:48 32:44 32:41 32:37 32:34 32:30 32:26 32:23 32:19 32:15 32:11 32:8 32:4 32:0 31:56",
    14: "29:56 29:52 29:48 29:44 29:40 29:36 29:31 29:27 29:23 29:19 29:15 29:11 29:7 29:3",
    21: "26:4 26:6 26:7 26:9 26:11 26:13 26:15 26:18 26:20 26:22 26:25 26:27 26:30 26:32 26:35",
}
TOLERANCE_MINUTES = 1
# The घ.प. columns as printed, घटी:पला, in the order tithi, nakshatra, yoga,
# karana; "" is अहोरात्र, two values a stacked cell. 2083 pp2 and 21.
GHATI = {
    date(2026, 4, 14): ("39:33", "19:43", "19:27", "10:12"),
    date(2026, 4, 15): ("37:25", "19:41", "15:21", "8:39"),
    date(2026, 4, 16): ("34:13", "18:33", "10:23", "5:58"),
    date(2026, 4, 17): ("30:5", "16:28", "4:37 58:8", "2:16 57:42"),
    date(2027, 1, 8): ("51:23", "5:31", "22:0", "18:42"),
    date(2027, 1, 9): ("56:21", "11:56", "23:8", "23:56"),
    date(2027, 1, 10): ("", "17:48", "23:48", "28:32"),
    date(2027, 1, 11): ("0:31", "22:50", "23:48", "32:13"),
    date(2027, 1, 12): ("3:38", "26:47", "22:56", "34:44"),
    date(2027, 1, 13): ("5:31", "29:32", "21:8", "35:59"),
    date(2027, 1, 14): ("6:7", "31:1", "18:19", "35:56"),
    date(2027, 1, 15): ("5:26", "31:18", "14:32", "34:37"),
    date(2027, 1, 16): ("3:32", "30:27", "9:50", "32:10"),
    date(2027, 1, 17): ("0:33 56:26", "28:36", "4:17 57:58", "28:41"),
    date(2027, 1, 18): ("51:56", "25:55", "51:6", "24:22"),
    date(2027, 1, 19): ("46:39", "22:35", "43:45", "19:21"),
    date(2027, 1, 20): ("40:58", "18:45", "36:4", "13:51"),
    date(2027, 1, 21): ("35:5", "14:39", "28:12", "8:3"),
    date(2027, 1, 22): ("29:13", "10:29", "20:19", "2:8 56:20"),
}
# A misprint: "५६।२६" beside its own clock २९:३६, which is ५६।३५ after that
# day's sunrise (2083 p21, पौष शुक्ल ९).
GHATI_MISPRINTS = {(date(2027, 1, 17), "tithi", 1)}


def minutes(clock: str) -> int:
    hours, mins = clock.split(":")
    return int(hours) * 60 + int(mins)


def computed(ends: list[dict]) -> list[int]:
    return [h * 60 + m for h, m in (e["clock"] for e in ends)]


def expected(value) -> list[int]:
    if value is None:
        return []
    return [minutes(v) for v in ((value,) if isinstance(value, str) else value)]


class BookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = panchanga.year(2083)
        cls.rows = {date.fromisoformat(r["date"]): r for p in cls.pages for r in p["rows"]}

    def assertTimes(self, label, got, want):
        self.assertEqual(len(got), len(want), f"{label}: {got} vs {want}")
        for g, w in zip(got, want):
            self.assertLessEqual(abs(g - w), TOLERANCE_MINUTES, f"{label}: {got} vs {want}")

    def test_page_count(self):
        self.assertEqual(len(self.pages), 26)

    def test_tithi_nakshatra_yoga(self):
        for day, ends in BOOK.items():
            row = self.rows[day]
            for limb, value in zip(("tithi", "nakshatra", "yoga"), ends):
                with self.subTest(day=day, limb=limb):
                    self.assertTimes(f"{day} {limb}", computed(row[limb]["ends"]), expected(value))

    def test_exact_minutes(self):
        # Within a minute is the floor; to the minute is the model. 226 of the
        # 228 ends in both books are exact, the other two 4 s past a half-minute.
        exact = 0
        for book in (BOOK, BOOK_2082):
            for day, ends in book.items():
                if not isinstance(day, date):
                    continue
                row = self.rows.get(day) or panchanga.day_row(day, 0, 1)
                for limb, value in zip(("tithi", "nakshatra", "yoga"), ends):
                    exact += sum(g == w for g, w in zip(computed(row[limb]["ends"]), expected(value)))
        self.assertGreaterEqual(exact, 226)

    def test_ghati_pala(self):
        # Counted from surya.ghati_origin: 71 of the 79 to the pala, 78 within
        # one, and 2027-01-17's second yoga end two off (ours 57।59.5, on a
        # rounding edge). From the printed sunrise only 33 match.
        exact = within = 0
        for day, columns in GHATI.items():
            row = self.rows[day]
            for limb, printed in zip(("tithi", "nakshatra", "yoga", "karana"), columns):
                want = [int(g) * 60 + int(p) for g, p in (v.split(":") for v in printed.split())]
                ends = row[limb]["ends"]
                self.assertEqual(len(ends), len(want), f"{day} {limb}")
                for k, (end, value) in enumerate(zip(ends, want)):
                    if (day, limb, k) in GHATI_MISPRINTS:
                        continue
                    with self.subTest(day=day, limb=limb, k=k):
                        got = end["ghati"] * 60 + end["pala"]
                        self.assertLessEqual(abs(got - value), 2)
                        exact += got == value
                        within += abs(got - value) <= 1
        self.assertGreaterEqual(exact, 71)
        self.assertGreaterEqual(within, 78)

    def test_karana(self):
        for day, (abbr, ends) in KARANAS.items():
            with self.subTest(day=day):
                karana = self.rows[day]["karana"]
                self.assertEqual(karana["abbr"], abbr)
                self.assertTimes(str(day), computed(karana["ends"]), expected(tuple(ends)))

    def test_anandadi(self):
        for day, name in ANANDADI.items():
            with self.subTest(day=day):
                self.assertEqual(self.rows[day]["anandadi"], name)

    def test_sunrise_sunset(self):
        exact = 0
        for day, (rise, set_) in SUN.items():
            row = self.rows[day]
            for clock, want in ((row["sunrise_clock"], rise), (row["sunset_clock"], set_)):
                got = clock[0] * 60 + clock[1]
                exact += got == minutes(want)
                with self.subTest(day=day, want=want):
                    self.assertLessEqual(abs(got - minutes(want)), 1)
        self.assertGreaterEqual(exact, 60)

    def test_dinamana(self):
        for page, printed in DINAMANA.items():
            rows = self.pages[page - 2]["rows"]
            self.assertEqual(len(rows), len(printed.split()))
            for row, value in zip(rows, printed.split()):
                with self.subTest(day=row["date"]):
                    self.assertEqual(row["dinamana"], [int(x) for x in value.split(":")])

    def test_headers(self):
        for page, (month, paksha, ns, ns_month, gregorian, ritu) in HEADERS.items():
            header = self.pages[page - 2]["header"]
            with self.subTest(page=page):
                self.assertEqual(
                    (header["lunar_month"], header["paksha"], header["nepal_samvat"],
                     header["nepal_samvat_month"], header["gregorian"], header["ritu"]),
                    (month, paksha, ns, ns_month, gregorian, ritu))

    def test_lagna(self):
        for day, starts in LAGNA.items():
            with self.subTest(day=day):
                got = [h * 60 + m for h, m in (l["clock"] for l in self.rows[day]["lagna"])]
                self.assertTimes(str(day), got, expected(tuple(starts.split())))

    def assertArc(self, label, got, want, tolerance):
        def seconds(arc):
            sign, deg, mins, secs = arc
            return ((sign * 30 + deg) * 60 + mins) * 60 + secs

        want = [int(x) for x in want.split(":")]
        self.assertLessEqual(abs(seconds(got) - seconds(want)), tolerance, f"{label}: {got}")

    def assertSpashta(self, rows, table, moon_tolerance):
        for day, (sun, moon, rahu, belantar) in table.items():
            spashta = rows[day]["spashta"]
            # Sun within 2″ (exact sines; the table is up to 3.7″ off).
            for body, want, tolerance in (("sun", sun, 2), ("moon", moon, moon_tolerance), ("rahu", rahu, 3)):
                with self.subTest(day=day, body=body):
                    self.assertArc(f"{day} {body}", spashta[body], want, tolerance)
            sign, mins, secs = belantar[0], *belantar[1:].split(":")
            with self.subTest(day=day, body="belantar"):
                seconds = (int(mins) * 60 + int(secs)) * (-1 if sign == "-" else 1)
                self.assertLessEqual(abs(rows[day]["belantar"] - seconds), 2)

    def test_spashta(self):
        self.assertSpashta(self.rows, SPASHTA, 15)

    def test_2082_tithi_nakshatra_yoga(self):
        for day, ends in BOOK_2082.items():
            row = panchanga.day_row(day, 0, 1)
            for limb, value in zip(("tithi", "nakshatra", "yoga"), ends):
                with self.subTest(day=day, limb=limb):
                    self.assertTimes(f"{day} {limb}", computed(row[limb]["ends"]), expected(value))

    def test_2082_spashta(self):
        rows = {day: panchanga.day_row(day, 0, 1) for day in SPASHTA_2082}
        self.assertSpashta(rows, SPASHTA_2082, 30)

    def test_sun_moon_across_seasons(self):
        for day, (sun, moon) in SUN_MOON.items():
            spashta = self.rows[day]["spashta"]
            with self.subTest(day=day):
                self.assertArc(f"{day} sun", spashta["sun"], sun, 2)
                self.assertArc(f"{day} moon", spashta["moon"], moon, 35)

    def test_sun_padas(self):
        for day, nakshatra, pada, enters, clock in SUN_PADAS:
            with self.subTest(day=day):
                [entry] = self.rows[day]["sun_padas"]
                self.assertEqual(
                    (entry["nakshatra"], entry["pada"], entry.get("enters")),
                    (nakshatra, pada, enters))
                # To the minute: the SS sine table puts 13 of these a minute late.
                self.assertEqual(computed([entry]), expected(clock))

    def test_month_starts(self):
        starts = panchanga.month_starts(2083)
        self.assertEqual(starts[0], date(2026, 4, 14))
        self.assertEqual(starts[6], date(2026, 10, 18))
        self.assertEqual(starts[9], date(2027, 1, 15))

def read_csv(name: str) -> list[dict]:
    with open(DATA / name, newline="") as f:
        return list(csv.DictReader(f))


def sankranti_after_sunrise(bs_year: int, sign: int) -> tuple[date, float]:
    """Day whose sunrise the book counts from, and the shifted sankranti in pala after it."""
    start = panchanga._gregorian_jd(bs_year - 57, 4, 1)
    _, jd = surya.crossings(surya.true_sun, panchanga.SIGN_WIDTH, start, start + 370)[sign]
    jd += panchanga._sankranti_shift(bs_year, sign)
    horizon = panchanga.book_horizon(bs_year)
    day = surya.from_julian_day(jd).date()
    if jd < surya.sunrise(day, horizon):
        day -= timedelta(days=1)
    return day, (jd - surya.sunrise(day, horizon)) * 3600


def sankranti_tolerance(bs_year: int) -> float:
    """Pala. Every era is measured from its books sign by sign; 4 pala
    covers each book's scatter about its era's values, the 2028 book's
    2-pala lean against the 2031-2044 books being typical."""
    return 4


# (book, day, दिनमान ghati, pala, PDF page), from
# https://archive.org/download/2081_20240828/{book}.pdf
BOOK_DINAMANA = [
    (2062, date(2005, 5, 14), 33, 23, 5),
    (2062, date(2005, 9, 13), 30, 43, 13),
    (2062, date(2006, 1, 14), 26, 3, 21),
    (2062, date(2006, 3, 14), 29, 32, 25),
    (2063, date(2007, 1, 20), 26, 17, 21),
    (2064, date(2008, 1, 8), 26, 3, 21),
    (2065, date(2009, 1, 5), 26, 0, 21),
    (2066, date(2009, 5, 14), 33, 36, 5),
    (2066, date(2009, 12, 22), 25, 50, 20),
]


class MonthStartTest(unittest.TestCase):
    def test_book_horizon(self):
        # The दिनमान each book prints fixes the sunrise it counts from:
        # geometric to 2063, refracted from 2064, in every season.
        for book, day, ghati, pala, page in BOOK_DINAMANA:
            with self.subTest(book=book, day=day, page=page):
                ours = surya.day_length(day, panchanga.book_horizon(book)) * 2.5
                self.assertLessEqual(abs(ours - (ghati * 60 + pala)), 2)

    def test_book_sankrantis(self):
        # data/book_sankrantis.csv: sankranti times as printed, ghati and pala
        # after the sunrise of `sunrise_day`, each with its book and PDF page.
        for row in read_csv("book_sankrantis.csv"):
            bs_year, sign = int(row["bs_year"]), int(row["sign"])
            with self.subTest(bs_year=bs_year, sign=row["sign_name"], page=row["pdf_page"]):
                day, pala = sankranti_after_sunrise(bs_year, sign)
                self.assertEqual(day.isoformat(), row["sunrise_day"])
                printed = int(row["ghati"]) * 60 + int(row["pala"])
                self.assertLessEqual(abs(pala - printed), sankranti_tolerance(bs_year))

    def test_era_offsets_are_the_books_mean(self):
        # Each era's per-sign offset is the mean of its books' readings, so
        # the mean residual per (era, sign) stays near zero: within 1 pala for
        # the fitted eras, 1.5 for the plain-SS one from 2063 (not fitted).
        starts = [era[0] for era in panchanga.SANKRANTI_ERAS]
        residuals = {}
        for row in read_csv("book_sankrantis.csv"):
            bs_year, sign = int(row["bs_year"]), int(row["sign"])
            era = max([y for y in starts if y <= bs_year] or starts[:1])
            _, pala = sankranti_after_sunrise(bs_year, sign)
            residuals.setdefault((era, sign), []).append(pala - (int(row["ghati"]) * 60 + int(row["pala"])))
        for (era, sign), values in residuals.items():
            with self.subTest(era=era, sign=sign, n=len(values)):
                self.assertLessEqual(abs(sum(values) / len(values)), 1.5 if era >= 2063 else 1.0)

    def test_documented_month_starts(self):
        # data/month_starts.csv: first days attested by a book page, by
        # drikpanchang.com, or by both library tables agreeing.
        for row in read_csv("month_starts.csv"):
            bs_year, month = int(row["bs_year"]), int(row["month"])
            with self.subTest(bs_year=bs_year, month=month, source=row["source"]):
                self.assertEqual(panchanga.month_starts(bs_year)[month - 1].isoformat(), row["first_day"])

    def test_month_starts_snapshot(self):
        # Every month start from 1970 to 2100, as generated when the sankranti
        # eras were last checked against all the books and tables. A change
        # here must be deliberate: re-check data/book_sankrantis.csv and the
        # library tables (build_status.py), then regenerate the file with
        #   python3 -c "import panchanga, json; print(json.dumps({y: [d.isoformat() for d in panchanga.month_starts(y)] for y in range(1970, 2101)}))" > data/month_starts_snapshot.json
        with open(DATA / "month_starts_snapshot.json") as f:
            snapshot = json.load(f)
        for year, starts in snapshot.items():
            with self.subTest(bs_year=year):
                self.assertEqual([d.isoformat() for d in panchanga.month_starts(int(year))], starts)

    def test_year_chains_into_the_next(self):
        # The 13th start (next वैशाख 1) must equal the next year's first, even
        # across a change of era in SANKRANTI_ERAS.
        for bs_year in range(1970, 2100):
            with self.subTest(bs_year=bs_year):
                self.assertEqual(panchanga.month_starts(bs_year)[12], panchanga.month_starts(bs_year + 1)[0])

    def test_month_and_year_lengths(self):
        for bs_year in range(1970, 2101):
            starts = panchanga.month_starts(bs_year)
            with self.subTest(bs_year=bs_year):
                self.assertEqual(len(starts), 13)
                self.assertIn((starts[12] - starts[0]).days, (365, 366))
                for k in range(12):
                    self.assertIn((starts[k + 1] - starts[k]).days, (29, 30, 31, 32))

    def test_new_year_near_mid_april(self):
        for bs_year in range(1970, 2101):
            first = panchanga.month_starts(bs_year)[0]
            with self.subTest(bs_year=bs_year):
                self.assertEqual((first.year, first.month), (bs_year - 57, 4))
                self.assertIn(first.day, range(12, 16))

    def test_eras(self):
        years = [start for start, _ in panchanga.SANKRANTI_ERAS]
        self.assertEqual(years, sorted(years))
        for start, offsets in panchanga.SANKRANTI_ERAS:
            with self.subTest(era=start):
                self.assertEqual(len(offsets), 12)
                self.assertTrue(all(abs(v) < 3.5 for v in offsets))
        for sign in range(12):
            # The current era is plain SS but for a few pala in Mesha and Mina.
            self.assertLessEqual(abs(panchanga._sankranti_shift(2083, sign)) * 60, 0.06)
            self.assertEqual(panchanga._sankranti_shift(1900, sign),
                             panchanga._sankranti_shift(panchanga.VERIFIED_FROM, sign))

    def test_karka_and_makara_rules(self):
        # A Karka sankranti just before sunrise counts for the previous day;
        # a Makara one just after sunset for the next. Other signs at the same
        # moments follow the night-midpoint rule.
        day = date(2026, 7, 16)
        rise, set_ = surya.sunrise(day), surya.sunset(day)
        just = 1 / 1440
        self.assertEqual(panchanga._month_start(2083, panchanga.KARKA, rise - just), day - timedelta(days=1))
        self.assertEqual(panchanga._month_start(2083, panchanga.KARKA, rise + just), day)
        self.assertEqual(panchanga._month_start(2083, panchanga.MAKARA, set_ - just), day)
        self.assertEqual(panchanga._month_start(2083, panchanga.MAKARA, set_ + just), day + timedelta(days=1))
        self.assertEqual(panchanga._month_start(2083, 0, set_ + just), day)
        self.assertEqual(panchanga._month_start(2083, 0, rise - just), day)

    def test_night_midpoint_boundary(self):
        # 30 ghati plus half the दिनमान after sunrise; a tie goes to the earlier day.
        day = date(2026, 10, 17)
        midpoint = surya.sunrise(day) + 0.5 + surya.day_length(day) / 2880
        self.assertEqual(panchanga._month_start(2083, 6, midpoint), day)
        self.assertEqual(panchanga._month_start(2083, 6, midpoint + 1 / 86400), day + timedelta(days=1))
        self.assertEqual(panchanga._month_start(2083, 6, midpoint - 1 / 1440), day)


class DayRowTest(unittest.TestCase):
    def test_karana_names(self):
        self.assertEqual(panchanga.karana(0)[0], "किंस्तुघ्न")
        self.assertEqual([panchanga.karana(h)[0] for h in (57, 58, 59)], ["शकुनि", "चतुष्पद", "नाग"])
        movable = [name for name, _ in panchanga.MOVABLE_KARANAS]
        self.assertEqual([panchanga.karana(h)[0] for h in range(1, 57)], movable * 8)

    def test_nakshatra28(self):
        start, end = panchanga.ABHIJIT
        self.assertEqual(panchanga.nakshatra28(start - 1e-6), 20)
        self.assertEqual(panchanga.nakshatra28(start), 21)
        self.assertEqual(panchanga.nakshatra28(end - 1e-6), 21)
        self.assertEqual(panchanga.nakshatra28(end), 22)
        self.assertEqual(panchanga.nakshatra28(359.9), 27)
        self.assertEqual(panchanga.nakshatra28(0), 0)

    def test_arc(self):
        self.assertEqual(panchanga.arc(0), [0, 0, 0, 0])
        self.assertEqual(panchanga.arc(30.5), [1, 0, 30, 0])
        self.assertEqual(panchanga.arc(359 + 59 / 60 + 59.6 / 3600), [0, 0, 0, 0])
        self.assertEqual(panchanga.arc(262 + 59 / 60 + 25 / 3600), [8, 22, 59, 25])

    def test_tithi_numbering(self):
        row = panchanga.day_row(date(2027, 1, 8), 8, 24)
        tithi = row["tithi"]
        self.assertEqual(tithi["paksha"], "शुक्ल" if tithi["index"] < 15 else "कृष्ण")
        expected_number = 30 if tithi["index"] == 29 else tithi["index"] % 15 + 1
        self.assertEqual(tithi["number"], expected_number)

    def test_end_times_fall_inside_the_day(self):
        for day in (date(2026, 4, 14), date(2026, 7, 16), date(2027, 1, 8)):
            row = panchanga.day_row(day, 0, 1)
            rise, next_rise = surya.sunrise(day), surya.sunrise(day + timedelta(days=1))
            for limb in ("tithi", "nakshatra", "yoga", "karana", "moon_sign"):
                for end in row[limb]["ends"]:
                    with self.subTest(day=day, limb=limb):
                        jd = surya.julian_day(datetime.fromisoformat(end["at"]))
                        self.assertTrue(rise - 1e-6 <= jd < next_rise)
                        self.assertEqual(end["ghati"] * 60 + end["pala"],
                                         round((jd - surya.ghati_origin(day)) * 3600))

    def test_lagna_order(self):
        lagnas = panchanga.day_row(date(2027, 1, 8), 8, 24)["lagna"]
        self.assertEqual(len(lagnas), 12)
        signs = [l["sign"] for l in lagnas]
        self.assertEqual(sorted(signs), list(range(12)))
        for a, b in zip(signs, signs[1:]):
            self.assertEqual(b, (a + 1) % 12)


class YearLayoutTest(unittest.TestCase):
    def test_row_paksha_is_the_pages(self):
        # Each page holds one paksha, and its rows' tithis say the same.
        for page in panchanga.year(2083):
            for row in page["rows"]:
                with self.subTest(date=row["date"]):
                    self.assertEqual(row["tithi"]["paksha"], page["header"]["paksha"])


    @classmethod
    def setUpClass(cls):
        cls.pages = panchanga.year(2083)
        cls.rows = [r for p in cls.pages for r in p["rows"]]

    def test_every_day_once(self):
        days = [date.fromisoformat(r["date"]) for r in self.rows]
        starts = panchanga.month_starts(2083)
        self.assertEqual(days[0], starts[0])
        self.assertEqual(len(days), (starts[12] - starts[0]).days)
        for a, b in zip(days, days[1:]):
            self.assertEqual((b - a).days, 1)

    def test_gates_restart_each_month(self):
        starts = panchanga.month_starts(2083)
        for row in self.rows:
            day = date.fromisoformat(row["date"])
            month = max(k for k in range(12) if starts[k] <= day)
            with self.subTest(day=day):
                self.assertEqual(row["bs_month"], month)
                self.assertEqual(row["gate"], (day - starts[month]).days + 1)

    def test_one_paksha_per_page(self):
        for page in self.pages:
            with self.subTest(page=page["page"]):
                halves = {r["tithi"]["index"] < 15 for r in page["rows"]}
                self.assertEqual(len(halves), 1)
                self.assertEqual(page["header"]["paksha"], "शुक्ल" if halves.pop() else "कृष्ण")

    def test_pages_number_from_two(self):
        self.assertEqual([p["page"] for p in self.pages], list(range(2, 2 + len(self.pages))))


if __name__ == "__main__":
    unittest.main()
