"""Unit tests for the astronomy in surya.py: the Surya Siddhanta mean and true
motions, the sine table, the time scale, and the sunrise model.

See docs/ALGORITHM.md for the formulas these pin down.
"""

import math
import unittest
from datetime import date, datetime, timedelta, timezone

import surya

J2000 = 2451545.0


def wrap(angle: float) -> float:
    """Signed difference folded into [-180, 180)."""
    return (angle + 180) % 360 - 180


class TimeScaleTest(unittest.TestCase):
    def test_julian_day_epoch(self):
        self.assertEqual(surya.julian_day(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)), J2000)

    def test_round_trip(self):
        moment = datetime(2026, 4, 14, 5, 43, 7, tzinfo=surya.NST)
        self.assertAlmostEqual(surya.from_julian_day(surya.julian_day(moment)).timestamp(),
                               moment.timestamp(), places=3)

    def test_local_julian_day_is_nst(self):
        jd = surya.local_julian_day(date(2026, 4, 14), 0)
        self.assertAlmostEqual(surya.from_julian_day(jd).timestamp(),
                               datetime(2026, 4, 14, tzinfo=surya.NST).timestamp(), places=3)

    def test_kali_epoch(self):
        # Midnight at Ujjain starting 18 Feb 3102 BCE (proleptic Julian), JD 588465.5 at Greenwich.
        self.assertAlmostEqual(surya.KALI_JD, 588465.5 - 75.7682 / 360, places=9)
        self.assertEqual(surya._mean(surya.KALI_JD, "sun"), 0.0)
        self.assertEqual(surya._mean(surya.KALI_JD, "moon"), 0.0)


class MotionTest(unittest.TestCase):
    def test_sun_apogee_near_77_degrees(self):
        self.assertAlmostEqual(surya.sun_apogee(2461000.0), 77.3, delta=0.1)

    def test_equation_of_centre_bounds(self):
        sun = max(abs(wrap(surya._manda(m / 10, 0, 14, 13 + 40 / 60) - m / 10)) for m in range(3600))
        moon = max(abs(wrap(surya._manda(m / 10, 0, 32, 31 + 40 / 60) - m / 10)) for m in range(3600))
        self.assertAlmostEqual(sun, 2.175, delta=0.01)
        self.assertAlmostEqual(moon, 5.05, delta=0.01)

    def test_no_correction_at_apsides(self):
        self.assertAlmostEqual(surya._manda(100, 100, 14, 13 + 40 / 60), 100)
        self.assertAlmostEqual(surya._manda(280, 100, 14, 13 + 40 / 60), 280)

    def test_daily_motions(self):
        for jd in (2460000.0, 2461000.0, 2461200.0):
            with self.subTest(jd=jd):
                self.assertTrue(0.95 < wrap(surya.true_sun(jd + 1) - surya.true_sun(jd)) < 1.03)
                self.assertTrue(11.5 < wrap(surya.true_moon(jd + 1) - surya.true_moon(jd)) < 15.5)

    def test_lahiri(self):
        self.assertAlmostEqual(surya.lahiri(J2000), 23.857092, places=6)
        self.assertAlmostEqual(surya.lahiri(J2000 + 36525) - surya.lahiri(J2000), 5030.2 / 3600, places=3)


class CrossingTest(unittest.TestCase):
    def test_twelve_sankrantis_a_year(self):
        start = surya.local_julian_day(date(2026, 4, 1), 0)
        found = surya.crossings(surya.true_sun, 30, start, start + 365.2587)
        self.assertEqual(len(found), 12)
        self.assertEqual([i for i, _ in found], [(found[0][0] + k) % 12 for k in range(12)])
        for _, jd in found:
            self.assertAlmostEqual(surya.true_sun(jd) % 30 if surya.true_sun(jd) % 30 < 15
                                   else surya.true_sun(jd) % 30 - 30, 0, places=6)

    def test_thirty_tithis_per_lunation(self):
        start = surya.local_julian_day(date(2026, 1, 1), 0)
        [(_, new_moon)] = surya.crossings(surya.elongation, 360, start, start + 30)
        tithis = surya.crossings(surya.elongation, 12, new_moon + 1e-4, new_moon + 29.6)
        self.assertEqual(len(tithis), 29)
        [(_, next_new)] = surya.crossings(surya.elongation, 360, new_moon + 1, new_moon + 31)
        self.assertTrue(29.2 < next_new - new_moon < 29.9)

    def test_crossings_are_sorted_and_in_range(self):
        start = 2461000.0
        found = surya.crossings(surya.true_moon, 360 / 27, start, start + 60)
        moments = [jd for _, jd in found]
        self.assertEqual(moments, sorted(moments))
        self.assertTrue(all(start <= jd < start + 60 for jd in moments))


class SunriseTest(unittest.TestCase):
    def test_order(self):
        for day in (date(2026, 3, 20), date(2026, 6, 21), date(2026, 12, 21)):
            with self.subTest(day=day):
                self.assertLess(surya.sunrise(day), surya.sunset(day))
                self.assertAlmostEqual(surya.day_length(day), (surya.sunset(day) - surya.sunrise(day)) * 1440, delta=1)

    def test_seasons(self):
        # Refraction makes the equinox day ~4 minutes longer than 12 hours.
        self.assertAlmostEqual(surya.day_length(date(2026, 3, 20)), 724, delta=3)
        self.assertGreater(surya.day_length(date(2026, 6, 21)), 825)
        self.assertLess(surya.day_length(date(2026, 12, 21)), 625)

    def test_equation_of_time_range(self):
        values = [surya.equation_of_time(date(2026, 1, 1) + timedelta(days=k)) for k in range(365)]
        self.assertLess(max(map(abs, values)), 17.5)
        self.assertGreater(max(values) - min(values), 30)

    def test_sidereal_day(self):
        # Mean solar days per sidereal rotation (1 / 1.00273790935).
        self.assertAlmostEqual(surya.SIDEREAL_DAY, 1 / 1.00273790935, places=8)

    def test_lagna_starts(self):
        day = date(2027, 1, 8)
        starts = surya.lagna_starts(day)
        self.assertEqual(sorted(s for s, _ in starts), list(range(12)))
        rise = surya.sunrise(day)
        self.assertTrue(all(rise <= jd < rise + surya.SIDEREAL_DAY for _, jd in starts))
        self.assertEqual([jd for _, jd in starts], sorted(jd for _, jd in starts))


if __name__ == "__main__":
    unittest.main()
