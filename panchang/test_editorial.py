"""Samvatsara, पापर्क्षाणि and पापांश against the printed books.

Sources (PDF page = book page; page 1 is the cover, fortnights from page 2):

  2083  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
  2082  https://giwmscdnone.gov.np/media/pages/files/npnbs_2082_ussfian.pdf
  older https://archive.org/download/2081_20240828/{year}.pdf (scans; PDF page)

See docs/EDITORIAL.md for what each field is and how the rules were found.
"""

import unittest
from datetime import date

import editorial
import panchanga
import surya

# Shaka year -> samvatsara printed for it.
SAMVATSARAS = {
    1890: "दुर्मति",      # 2025 p1 preface: "रौद्रनाम संवत्सरो गतो दुर्मति नाम संवत्सरः प्राप्तः"
    1897: "विभव",        # 2032 p2, शुक्ल चैत्र notes: "विभव नाम संवत्सर"
    1900: "प्रजापति",     # 2035 p1: "प्रजापतिनाम संवत्सरः ५"
    1906: "ईश्वर",        # 2041 p1: "ईश्वर नाम संवत्सरः ११"
    1916: "सर्वजित्",      # 2051 p1: "सर्वजित्नाम संवत्सरः २१"
    1923: "जय",          # 2058 p1: "जयनाम संवत्सरः २८"
    1927: "विलम्बी",      # 2062 pp4-26 headers ("विलम्बनामक"), p1 "३२"
    1928: "विकारी",       # 2062 p27, 2063 pp7-20 headers
    1931: "शुभकृत्",      # 2066, चैत्र कृष्ण header
    1932: "शोभन",        # 2067 p13 header
    1938: "सौम्य",        # 2073 headers, p26
    1939: "साधारण",       # 2073 last page header
    1941: "परिधावी",      # 2076 pp5-26 headers
    1942: "प्रमादी",      # 2076 p28; 2077 pp2-23 headers
    1943: "राक्षस",       # 2078 p17 preface (आनन्द क्षय), pp24-46 headers
    1944: "नल",          # 2079 p1 "नलनामसंवत्सरः ५०", pp11-33 headers
    1945: "पिङ्गल",       # 2079 p34 (शुक्ल चैत्र) header
    1947: "सिद्धार्थि",    # 2082 pp2-24 headers
    1948: "रौद्र",        # 2082 pp25-26, 2083 pp2-26 headers
    1949: "दुर्मति",      # 2083 p27 header
}

# The header's पापर्क्षाणि, as printed. Book year -> {page: text}.
PAPAKSHANI = {
    2083: {
        2: "श.उभा.अश्वि", 3: "अश्वि.भ.म.पूफा.उफा.ह.स्वा", 4: "१७.२२.श.उभा.अश्वि.भ.कृ",
        5: "कृ.म.पूफा.उफा.स्वा.१७", 6: "अभि.२२.श.रे.भ.मृ", 7: "म.उफा.स्वा.१६.पूषा",
        8: "पूषा.श्र.२२.श.रे.भ.रो.पुन", 9: "म.उफा.स्वा.ज्ये.उषा.२२",
        10: "२२.श.रे.भ.मृ.अश्ले.९", 11: "अश्ले.९.म.उफा.वि.पूषा.२२.ध",
        12: "रे.अश्वि.भ.पुन.९.म.पूफा.उफा", 13: "उफा.वि.मू.२२.ध", 14: "रे.भ.ति.९.म.ह",
        15: "चि.वि.ज्ये.२२.ध.२३.पूभा.उभा.भ", 16: "भ.अश्ले.९.म.ह.वि",
        17: "वि.अनु.२२.ध.उभा.२.भ", 18: "९.अश्ले.म.ह.वि.अनु.ज्ये",
        19: "ज्ये.२२.ध.२३.उभा.अश्वि.पुन", 20: "पुन.९.अश्ले.पूफा.ह.वि.अनु.पूषा",
        21: "पूषा.२३.ध.उभा.अश्वि.मृ", 22: "९.अश्ले.१०.पूफा.ह.वि.अनु.श्र.२२.ध.२३",
        23: "ध.२३.रे.भ.९.अश्ले.म", 24: "म.उफा.स्वा.वि.अनु.२२.ध.२३.पूभा",
        25: "पूभा.रे.अश्ले.९.उफा.ह", 26: "ह.वि.अनु.ध.२३.रे", 27: "रे.कृ",
    },
    2082: {
        2: "ज्ये.पूभा.रे.अश्वि.भ", 3: "भ.ति.म.उफा.ह.चि.१६",
        4: "१६.अनु.श्र.पूभा.उभा.रे.रो", 5: "अश्ले.उफा.ह.चि",
        6: "उषा.२२.पूभा.उभा.रे.भ.आ", 7: "आ.म.पूफा.उफा.ह.चि.मू", 8: "पूभा.उभा.रे.अश्वि.ति",
        9: "ति.पूफा.उफा.ह.चि.अनु.२३", 10: "२३.पूभा.उभा.अश्वि.म.पूफा", 11: "पूफा.ह.चि.पूभा",
        12: "पूभा.उभा.अश्वि.पूफा.उफा", 13: "उफा.ह.चि.स्वा.श.पूभा.उभा.अश्वि",
        14: "अश्वि.पूफा.चि", 15: "वि.ध.श.पूभा.अश्वि.२", 16: "२.३.अश्ले.पूफा.चि.वि.अनु",
        17: "अनु.ज्ये.श.पूभा.अश्वि.२", 18: "पुन.ति.पूफा.चि.स्वा.मू", 19: "मू.श.पूभा.अश्वि.आ",
        20: "पूफा.चि.स्वा.उषा", 21: "उषा.श.उभा.अश्वि.कृ", 22: "१०.पूफा.ह.स्वा.वि.ध.श",
        23: "श.उभा.अश्वि.९.पूफा", 24: "पूफा.ह.चि.स्वा.श.पूभा.उभा", 25: "अश्वि.म.उफा.ह.चि",
        26: "चि.स्वा.२२.श",
    },
}
# The one page that differs: Mars is in आश्लेषा in the book's स्पष्ट ग्रह and
# ours, but the book leaves out २३ (2082 p4).
PAPAKSHANI_DIFFERENT = {(2082, 4)}

# The पापांश box, as printed, 2083 book.
PAPAMSHA = {
    2: "सू.१, ४सू.२, मं.६, २मं.७, शं.७, ४शं.८, रा.१०के.४",
    3: "सू.२, ८सू.३, ११सू.४, १४सू.५, १८सू.६, मं.७, ६मं.८, १०मं.९, १५मं.१०, शं.८, रा.१०के.४",
    4: "सू.६, २१सू.७, २५सू.८, २८सू.९, १सू.१०, मं.१०, १९मं.११, २४मं.१२, २८मं.१, १मं.२, "
       "शं.८, रा.१०के.४",
    6: "सू.२, १८सू.३, २२सू.४, २५सू.५, २९सू.६, १सू.७, मं.५, १९मं.६, २४मं.७, २८मं.८, "
       "शं.९, रा.९के.३",
    7: "सू.७, ५सू.८, ८सू.९, १२सू.१०, १५सू.११, मं.८, २मं.९, ७मं.१०, ११मं.११, शं.९, रा.९के.३",
    9: "सू.३, १सू.४, ४सू.५, ८सू.६, ११सू.७, मं.३, ३मं.४, ८मं.५, १३मं.६, शं.१०, रा.९के.३",
    10: "सू.७, १५सू.८, १८सू.९, २२सू.१०, २५सू.११, मं.६, १८मं.७, २३मं.८, शं.१०, रा.९के.३, "
        "१६रा.८के.२",
    11: "सू.११, २९सू.१२, १सू.१, ५सू.२, ८सू.३, १२सू.४, मं.८, २८मं.९, २मं.१०, ७मं.११, "
        "१२मं.१२, शं.१०, २८शं.९, रा.८के.२",
    12: "सू.४, १५सू.५, १९सू.६, २२सू.७, २५सू.८, मं.१२, १७मं.१, २२मं.२, शं.९, रा.८के.२",
    13: "सू.८, २९सू.९, १सू.१०, ५सू.११, ८सू.१२, मं.२, २७मं.३, २मं.४, ८मं.५, शं.९, रा.८के.२",
    14: "सू.१२, ११सू.१, १५सू.२, १८सू.३, २२सू.४, मं.५, १३मं.६, १९मं.७, शं.९, २१शं.८, "
        "रा.८के.२, १७रा.७के.१",
    15: "सू.४, २५सू.५, २८सू.६, १सू.७, ४सू.८, ७सू.९, मं.७, २५मं.८, ३१मं.९, ६मं.१०, शं.८, "
        "रा.७के.१",
    16: "सू.९, ११सू.१०, १४सू.११, १७सू.१२, २१सू.१, मं.१०, १२मं.११, १९मं.१२, शं.८, रा.७के.१",
    17: "सू.१, २४सू.२, २७सू.३, १सू.४, ४सू.५, ७सू.६, मं.१२, २६मं.१, ३मं.२, शं.८, रा.७के.१",
    18: "सू.६, १०सू.७, १४सू.८, १७सू.९, २०सू.१०, मं.२, ११मं.३, २०मं.४, शं.८, रा.७के.१, "
        "१९रा.६के.१२",
    19: "सू.१०, २४सू.११, २७सू.१२, १सू.१, ४सू.२, ८सू.३, मं.४, २मं.५, शं.८, रा.६के.१२",
    20: "सू.३, ११सू.४, १४सू.५, १७सू.६, २१सू.७, मं.५, शं.८, रा.६के.१२",
    21: "सू.७, २४सू.८, २७सू.९, ३०सू.१०, ४सू.११, ७सू.१२, मं.५, २८मं.६, २मं.५, शं.८, "
        "रा.६के.१२",
    22: "सू.१२, १०सू.१, १३सू.२, १७सू.३, २०सू.४, २३सू.५, मं.५, १९मं.४, शं.८, रा.६के.१२, "
        "२३रा.५के.११",
    23: "सू.५, २७सू.६, १सू.७, ४सू.८, ७सू.९, मं.४, २८मं.३, ७मं.२, शं.८, २५शं.९, रा.५के.११",
    24: "सू.९, ११सू.१०, १४सू.११, १७सू.१२, २१सू.१, २४सू.२, मं.२, १६मं.१, शं.९, रा.५के.११",
    25: "सू.२, २७सू.३, १सू.४, ४सू.५, ७सू.६, मं.१, २५मं.१२, शं.९, २८शं.१०, रा.५के.११",
    26: "सू.६, ११सू.७, १४सू.८, १७सू.९, २१सू.१०, मं.१२, शं.१०, २४शं.११, रा.५के.११",
}
# 2082 book, pp2, 20 and 21.
PAPAMSHA_2082 = {
    2: "सू.१, ४सू.२, ७सू.३, ११सू.४, १४सू.५, मं.५, ६मं.६, १३मं.७, शं.४, रा.४के.१०",
    20: "सू.६, २०सू.७, २४सू.८, २७सू.९, ३०सू.१०, ३सू.११, मं.७, २३मं.८, २७मं.९, १मं.१०, "
        "शं.४, रा.१२के.६",
    21: "सू.११, ७सू.१२, १०सू.१, १३सू.२, १६सू.३, मं.१०, ६मं.११, १०मं.१२, १४मं.१, १८मं.२, "
        "शं.४, ७शं.५, रा.१२के.६, १०रा.११के.५",
}
# Pages whose whole box we reproduce. The others differ only in the
# entries of PAPAMSHA_DIFFERENT, or in an entry after the page's last day
# (2083 p27 "१सू.१", बैशाख 1 of the next year).
PAPAMSHA_EXACT = ({(2083, p) for p in (2, 3, 4, 6, 7, 9, 10, 11, *range(14, 26))}
                  | {(2082, p) for p in (2, 20, 21)})
# The book dates these a day or more before its own स्पष्ट ग्रह cross the
# navamsha: Mars is still 13.8′ short at sunrise of गते 28 (2083 p13), and
# Saturn needs 2.4 more days after गते 23 (2083 p26). On p12 the book's own
# Mars is the one that runs 26′ fast over pp12-13 (test_rail.BOOK_ANOMALIES):
# it crosses 83°20′ by गते 23's sunrise, Ketaki's only 0.7″ after it.
PAPAMSHA_DIFFERENT = {(2083, 12, "२२मं.२"), (2083, 13, "२७मं.३"), (2083, 26, "२४शं.११")}

DIGITS = "०१२३४५६७८९"


def entries(text: str) -> list[str]:
    return [e.strip() for e in text.split(",")]


def by_body(text: str, label: str) -> list[str]:
    return [e for e in entries(text) if label in e]


def canonical(text: str) -> list[tuple[int, frozenset]]:
    """पापर्क्षाणि as [(28-nakshatra index, {"name", "number"})], merging a
    name and a number for the same nakshatra, whose order varies in print."""
    result = []
    for token in text.strip(".").split("."):
        if token[0] in DIGITS:
            n = int("".join(str(DIGITS.index(c)) for c in token)) - 1
            item = (n if n <= 20 else n + 1, "number")
        else:
            item = (editorial.ABBREVIATIONS.index(token), "name")
        if result and result[-1][0] == item[0]:
            result[-1] = (item[0], result[-1][1] | {item[1]})
        else:
            result.append((item[0], frozenset({item[1]})))
    return result


class TestSamvatsara(unittest.TestCase):
    def test_printed_names(self):
        for shaka, name in SAMVATSARAS.items():
            with self.subTest(shaka=shaka, bs=shaka + 135):
                self.assertEqual(editorial.samvatsara(shaka), name)

    def test_page_headers_switch_at_shukla_chaitra(self):
        # 2083: रौद्र on pp2-26, दुर्मति on p27 (शुक्ल चैत्र, Shaka 1949).
        for page in panchanga.year(2083):
            expected = "दुर्मति" if page["page"] == 27 else "रौद्र"
            self.assertEqual(editorial.samvatsara(page["header"]["shaka"]), expected)

    def test_kshaya(self):
        # 2078 p17: "प्रमादीनामसंवत्सरो गतः अपर आनन्दनाम संवत्सरस्य क्षयत्वात्".
        self.assertEqual(editorial.kshaya_samvatsaras(1930, 1960), [(1943, "आनन्द")])

    def test_jovian_year_at_mesha(self):
        # 2079 p5 preface: नल had run 0 months 16 days 55 ghati 12 pala of
        # its 12 × 30 Jovian days at the Mesha sankranti ("मेषार्कात्
        # प्राग्भुक्त मासादयः ०।१६।५५।१२"). The 2078 preface (p17) gives 12 days 42
        # ghati 0 pala for राक्षस in 2021 ("०।१२।४२।०").
        for year, index, elapsed in ((2022, 49, 16 + 55 / 60 + 12 / 3600), (2021, 48, 12 + 42 / 60)):
            start = surya.local_julian_day(date(year, 4, 1), 0)
            end = surya.local_julian_day(date(year, 4, 30), 0)
            mesha = next(jd for i, jd in surya.crossings(surya.true_sun, 30, start, end) if i == 11)
            (found, began), = editorial.jovian_starts(mesha - 40, mesha)
            jovian_day = surya.MAHAYUGA_DAYS / editorial.JUPITER_REVOLUTIONS / 12 / 360
            self.assertEqual(found, index)
            self.assertAlmostEqual((mesha - began) / jovian_day, elapsed, delta=0.1)


class TestPapakshani(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {y: {p["page"]: p["rows"] for p in panchanga.year(y)} for y in PAPAKSHANI}

    def test_pages(self):
        for year, pages in PAPAKSHANI.items():
            for page, printed in pages.items():
                if (year, page) in PAPAKSHANI_DIFFERENT:
                    continue
                with self.subTest(year=year, page=page):
                    ours = editorial.papakshani(self.pages[year][page])
                    self.assertEqual(canonical(ours), canonical(printed))

    def test_known_differences_still_differ(self):
        for year, page in PAPAKSHANI_DIFFERENT:
            ours = editorial.papakshani(self.pages[year][page])
            self.assertNotEqual(canonical(ours), canonical(PAPAKSHANI[year][page]))

    def test_vedha_pairs(self):
        # Each nakshatra is on exactly one सप्तशलाका line.
        self.assertEqual(len(editorial.SAPTASHALAKA), 28)
        for a, b in editorial.SAPTASHALAKA.items():
            self.assertEqual(editorial.SAPTASHALAKA[b], a)


class TestPapamsha(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {y: {p["page"]: p["rows"] for p in panchanga.year(y)} for y in (2082, 2083)}

    def ours(self, year, page):
        return editorial.papamsha_text(editorial.papamsha(self.pages[year][page]))

    def test_read_from_the_spashta_column(self):
        # The box is read off the स्पष्ट ग्रह table on the same page: the Sun,
        # Mars, Saturn and Rahu it uses are the row's values (Rahu at Ujjain
        # mean sunrise, Mars and Saturn at the geometric sunrise).
        for row in (r for rows in self.pages[2083].values() for r in rows):
            day = date.fromisoformat(row["date"])
            found = editorial._malefics_at_sunrise(day)
            for body in ("sun", "mars", "saturn", "rahu"):
                with self.subTest(day=day, body=body):
                    self.assertEqual(panchanga.arc(found[body]), row["spashta"][body])

    def test_navamsha(self):
        # अश्विनी 2 is वृष; उत्तरभाद्रपदा 3 is तुला (2083 p2: Mars "२मं.७").
        self.assertEqual(editorial.navamsha(5.0), 2)
        self.assertEqual(editorial.navamsha(333 + 1 / 3 + 7), 7)

    def test_sun_and_nodes(self):
        # The SS Sun and the mean node are the book's own: every entry matches.
        for year, printed in [(2083, PAPAMSHA), (2082, PAPAMSHA_2082)]:
            for page, text in printed.items():
                ours = self.ours(year, page)
                for label in ("सू.", "रा."):
                    with self.subTest(year=year, page=page, body=label):
                        self.assertEqual(by_body(ours, label), by_body(text, label))

    def test_whole_box(self):
        for year, page in PAPAMSHA_EXACT:
            printed = (PAPAMSHA if year == 2083 else PAPAMSHA_2082)[page]
            with self.subTest(year=year, page=page):
                self.assertEqual(self.ours(year, page), printed)

    def test_mars_and_saturn(self):
        # Mars and Saturn are the Ketaki स्पष्ट ग्रह (ketaki.py), as in the
        # book: every printed entry matches but those in PAPAMSHA_DIFFERENT.
        for year, printed in [(2083, PAPAMSHA), (2082, PAPAMSHA_2082)]:
            for page, text in printed.items():
                ours = entries(self.ours(year, page))
                for label in ("मं.", "शं."):
                    for entry in by_body(text, label):
                        if (year, page, entry) in PAPAMSHA_DIFFERENT:
                            continue
                        with self.subTest(year=year, page=page, entry=entry):
                            self.assertIn(entry, ours)

if __name__ == "__main__":
    unittest.main()
