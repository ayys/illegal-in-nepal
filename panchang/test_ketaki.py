"""Mars to Saturn (ketaki.py) against Ketaki's worked example and the books.

data/book_planets.csv holds the स्पष्ट ग्रह the 2082 and 2083 books print at
Kathmandu sunrise, each with its book and PDF page:
  2082  https://giwmscdnone.gov.np/media/pages/files/npnbs_2082_ussfian.pdf
  2083  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
`hand` rows are read off the page: all five planets on 2083 p21, Mercury on
2082 pp6-8 and 12. `ocr` rows are cells two independent OCR passes read the same
(research/planets/book-ocr/), less 20 that are more than 15′ off, gross
misreads of a sign or degree digit.
"""

import csv
import statistics
import unittest
from datetime import date
from pathlib import Path

import ketaki
import surya

DATA = Path(__file__).resolve().parent / "data" / "book_planets.csv"


def degrees(text: str) -> float:
    sign, degree, minute, second = map(int, text.split(":"))
    return sign * 30 + degree + minute / 60 + second / 3600


def seconds(a: float, b: float) -> float:
    return ((a - b + 180) % 360 - 180) * 3600


def residuals(source: str) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    with open(DATA, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row["source"] != source:
            continue
        day = date.fromisoformat(row["date"])
        out.setdefault(row["body"], []).append(
            (row["date"], seconds(degrees(row["longitude"]), ketaki.at_sunrise(row["body"], day))))
    return out


class WorkedExampleTest(unittest.TestCase):
    # Ketaki p158-159: Shaka 1815 चैत्र शुक्ल १५ (1893-04-01), ahargana 5477,
    # Bagalkot mean morning (on the Ujjain meridian, so the epoch moment).
    jd = ketaki.EPOCH + 5477

    def test_mean_longitudes(self):
        for body, printed in (("mars", "1:29:19:37"), ("mercury", "4:26:14:0"), ("venus", "11:0:19:50")):
            with self.subTest(body=body):
                self.assertLessEqual(abs(seconds(ketaki.mean(body, self.jd), degrees(printed))), 1)

    def test_heliocentric(self):
        # मन्दस्पष्ट, p158-159; Mercury's row in the commentary's example is
        # the series, ours the verse (12″ apart).
        for body, printed in (("mars", "2:9:5:31"), ("mercury", "5:18:47:50"), ("jupiter", "0:13:5:50"),
                              ("venus", "10:29:48:14"), ("saturn", "5:17:19:20")):
            with self.subTest(body=body):
                self.assertLessEqual(abs(seconds(ketaki.heliocentric(body, self.jd)[0], degrees(printed))), 20)

    def test_karsha(self):
        jupiter, saturn = ketaki.karsha(self.jd)
        self.assertAlmostEqual(jupiter * 60, 15 + 51 / 60, delta=0.02)
        self.assertAlmostEqual(saturn * 60, -(39 + 39 / 60), delta=0.02)

    def test_shaka(self):
        self.assertEqual(ketaki.shaka(self.jd), 1815)
        self.assertEqual(ketaki.shaka(surya.sunrise(date(2026, 3, 18))), 1947)
        self.assertEqual(ketaki.shaka(surya.sunrise(date(2026, 3, 20))), 1948)


class BookTest(unittest.TestCase):
    # Hand-read values, arc-seconds: the books print whole seconds.
    TOLERANCE = 4

    def test_hand_read(self):
        for body, values in residuals("hand").items():
            for day, error in values:
                with self.subTest(body=body, day=day):
                    self.assertLessEqual(abs(error), self.TOLERANCE)

    def test_ocr(self):
        # (median, 90th percentile) bounds, arc-seconds, over two years.
        bounds = {"saturn": (1, 1), "jupiter": (1, 1), "mars": (1.5, 3), "venus": (2, 7), "mercury": (3, 6)}
        for body, values in residuals("ocr").items():
            errors = sorted(abs(e) for _, e in values)
            with self.subTest(body=body, n=len(errors)):
                self.assertGreater(len(errors), 300)
                self.assertLessEqual(statistics.median(errors), bounds[body][0])
                self.assertLessEqual(errors[int(len(errors) * 0.9)], bounds[body][1])


class InterpolationTest(unittest.TestCase):
    def test_table_longitude_matches_rows(self):
        # At the printed sunrise it is the स्पष्ट ग्रह row itself.
        for day in (date(2025, 7, 21), date(2026, 10, 24), date(2027, 1, 10)):
            for body in ketaki.PLANETS:
                with self.subTest(day=day, body=body):
                    self.assertAlmostEqual(
                        seconds(ketaki.table_longitude(body, surya.sunrise(day)), ketaki.at_sunrise(body, day)), 0, delta=0.01)

    def test_sun_equation(self):
        # 115.2′ sin k + 1.2′ sin 2k, not the whole-कला table: at k = 45° the
        # two differ by 1.2′.
        self.assertEqual(ketaki.SUN_EQUATION, (115.2, 1.2))
        self.assertEqual(ketaki.MANDA["mercury"][3], 96)

    def test_longitude_matches_sunrise_values(self):
        day = date(2027, 1, 10)
        rise, after = ketaki.sunrise(day), ketaki.sunrise(date(2027, 1, 11))
        for body in ketaki.PLANETS:
            with self.subTest(body=body):
                self.assertAlmostEqual(seconds(ketaki.longitude(body, rise), ketaki.geocentric(body, rise)), 0, delta=0.01)
                mid = ketaki.longitude(body, (rise + after) / 2)
                a, b = ketaki.geocentric(body, rise), ketaki.geocentric(body, after)
                self.assertAlmostEqual(seconds(mid, a + seconds(b, a) / 7200), 0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
