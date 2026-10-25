"""Mars to Saturn by the केतकी ग्रहगणितम्, as the राष्ट्रिय पञ्चाङ्ग applies it.

The committee's notices require the planets to be computed "केतकीय
ग्रहगणितबाट" (research/npns/). The text is V. B. Ketkar's karana of 1898,
read from the 2001 Chaukhamba reprint with Datta Raj's commentary:
  https://archive.org/details/KetakiGrahaGanitam   (PDF page = book page + 6)
Page numbers below are book pages.

The method, step by step:
1. Mean longitudes: the क्षेपक at Shaka 1800 elapsed (p48-49), whole 19-year
   चक्रs of 6940 days by ध्रुवक (p50-51), the days inside the current चक्र by
   the per-day formulas (p53-62). Heliocentric for the planets, geocentric
   for the Sun. Ketaki is sidereal in the Lahiri frame already: its epoch Sun
   and Moon equal the Lahiri mean Sun and Moon to 0.01°.
2. Jupiter and Saturn: the 918-year कर्ष (great inequality, p75).
3. मन्दफल: 10° tables of the मन्दकेन्द्र (mean − apogee), linear
   interpolation (Sun p95, planets p156-158).
4. शीघ्र केन्द्र = heliocentric planet − true Sun; शीघ्रफल from 10° tables,
   linear interpolation (p171-172). Mars and Mercury scale it by their
   distances (p180-181). Mercury and Venus: true Sun ± फल; Mars, Jupiter and
   Saturn: planet ∓ फल.

Five conventions are not in the text and were found from the books' स्पष्ट
ग्रह tables (docs/CALIBRATION.md, "Ketaki planets"): the planets at
Kathmandu sunrise without refraction but the Sun of step 4 at mean sunrise;
the Sun's मन्दफल by a two-term formula instead of its table; Saturn's optional short-period terms (p159)
left out; Mars's distance by the cosine of verse 8, unrounded; Mercury's by
the table of verses 11-13.

The tables are Ketkar's verses, decoded (भूतसंख्या, digits right to left);
where the commentary's digit list differs, the verse is used.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from functools import lru_cache

import surya

PLANETS = ["mars", "mercury", "jupiter", "venus", "saturn"]

# Days in the 19-year चक्र.
CYCLE = 6940


def _arc(sign: int, degree: int, minute: int = 0, second: float = 0) -> float:
    return sign * 30 + degree + minute / 60 + second / 3600


# Shaka 1800 elapsed, चैत्र शुक्ल प्रतिपदा = 1878-04-03, 06:00 Ujjain mean time.
EPOCH = surya.local_julian_day(date(1878, 4, 3), 6 - surya.UJJAIN_LONGITUDE / 15 + 5.75)

# p48-49: mean longitude and apogee (उच्च) at the epoch.
MEAN_AT_EPOCH = {
    "sun": _arc(11, 19, 5), "mars": _arc(2, 9, 12), "mercury": _arc(1, 22, 30),
    "jupiter": _arc(9, 5, 40), "venus": _arc(6, 15, 28), "saturn": _arc(11, 8, 21),
}
APOGEE_AT_EPOCH = {
    "sun": _arc(2, 18, 41), "mars": _arc(4, 11, 41), "mercury": _arc(7, 23, 26),
    "jupiter": _arc(5, 20, 13), "venus": _arc(9, 17, 40), "saturn": _arc(8, 8, 27),
}
# p48 क्षेपक, p51 ध्रुवक and p58 daily motion of राहु, the mean node:
# 9:27:37 at the epoch, 11:22:13:58 per चक्र, and A/19 degrees + A/46
# minutes taken away for A days (it moves backwards). The worked example,
# 5477 days, gives "राहोर्मध्यमा गतिः" 2:9:45:9.
RAHU_AT_EPOCH = _arc(9, 27, 37)
RAHU_PER_CYCLE = _arc(11, 22, 13, 58)
# The books' राहु is Ketaki's at 06:00 Kathmandu mean time, 16.2″ further
# on: 325 of the 363 printed values two OCR passes agree on (2082 and 2083)
# to the second, the rest within one, with no drift (−0.16″ a year). The
# Lahiri mean node of Meeus, used before, drifts 2.35″ a year against it.
RAHU_OFFSET = 16.2 / 3600

# p50-51 ध्रुवक: what each mean longitude gains in a चक्र beyond whole turns.
PER_CYCLE = {
    "sun": _arc(0, 0, 7, 38), "mars": _arc(1, 6, 47, 20), "mercury": _arc(10, 20, 49, 50),
    "jupiter": _arc(7, 6, 39, 12), "venus": _arc(10, 18, 47, 10), "saturn": _arc(7, 22, 12, 37),
}
# p53-62: degrees per day inside a चक्र, e.g. Mars "10A/19 भाग − 10A/73 कला".
PER_DAY = {
    "sun": 69 / 70 - 1 / (158 * 60),
    "mars": 10 / 19 - 10 / (73 * 60),
    "mercury": 3 * 30 / 22 + 1 / 700,
    "jupiter": 1 / 12 - 1 / (69 * 60),
    "venus": 8 / 5 + 1 / (8 * 60) + 1 / (6 * 3600),
    "saturn": 1 / 30 + 1 / (132 * 60),
}
# p51: apogee motion in arc-seconds per चक्र. Venus's moves backward (p52).
APOGEE_PER_CYCLE = {"sun": 225, "mars": 321, "mercury": 117, "jupiter": 126, "venus": -28.5, "saturn": 303}

# मन्दफल at 0°, 10°, … 180° of the मन्दकेन्द्र: the Sun in कला (p95), the
# planets in असु (0.1°, p156-158). Beyond 180° the row is read backwards with
# the sign reversed. Mercury's 30° entry is 96 ("ऽङ्गनिधयः", and the
# commentary's list, p157); read as 97 it put the books' Mercury up to 3′ off
# whenever the मन्दकेन्द्र passed 30° or 330°.
SUN_MANDA = [0, 20, 39, 57, 73, 87, 99, 108, 113, 115, 114, 109, 101, 89, 75, 59, 40, 20, 0]
# What the books use instead of SUN_MANDA, in कला: 115.2 sin k + 1.2 sin 2k
# of the मन्दकेन्द्र k. These are the first two terms of Kepler's equation of
# centre, 2e and 5e²/4, for e = 0.01676, the Earth's eccentricity when
# Ketaki was written. The table is the same curve rounded to whole कला at 10°
# steps and read the other way round; read as printed it is 1-2′ off, which
# is why reading it backwards from perigee looked right. Fitted to the 1841
# book values (docs/CALIBRATION.md, "Ketaki planets").
SUN_EQUATION = (115.2, 1.2)
MANDA = {
    "mars": [0, 17, 33, 48, 63, 76, 87, 96, 103, 106, 107, 104, 98, 88, 75, 59, 41, 21, 0],
    "mercury": [0, 32, 65, 96, 125, 153, 178, 199, 217, 229, 236, 236, 228, 211, 185, 149, 105, 54, 0],
    "jupiter": [0, 9, 18, 26, 34, 41, 46, 51, 54, 55, 55, 53, 49, 44, 37, 29, 20, 10, 0],
    "venus": [0, 1, 3, 4, 5, 6, 7, 7, 8, 8, 8, 7, 7, 6, 6, 5, 3, 1, 0],
    "saturn": [0, 10, 21, 30, 39, 47, 54, 59, 63, 64, 64, 62, 58, 52, 45, 34, 24, 12, 0],
}
# शीघ्रफल in असु at 0°, 10°, … 180° of the शीघ्र केन्द्र (p171-172). Each entry is
# the triangle with the mean distances, rounded.
SHIGHRA = {
    "mars": [0, 40, 79, 118, 157, 195, 232, 267, 301, 333, 361, 385, 402, 410, 403, 372, 304, 179, 0],
    "mercury": [0, 28, 55, 82, 109, 134, 157, 178, 197, 212, 222, 227, 226, 215, 195, 162, 118, 62, 0],
    "jupiter": [0, 16, 32, 47, 62, 75, 86, 96, 104, 109, 111, 109, 104, 95, 82, 66, 46, 24, 0],
    "venus": [0, 42, 84, 125, 167, 206, 247, 286, 323, 359, 392, 421, 445, 460, 462, 441, 377, 236, 0],
    "saturn": [0, 9, 19, 28, 36, 43, 49, 54, 58, 60, 60, 58, 55, 49, 42, 33, 23, 12, 0],
}
# शीघ्रकर्णांक for Mars (p173): शीघ्रकर्ण = 100 + 152 − this.
MARS_KARNANKA = [0, 1, 3, 8, 16, 22, 32, 43, 56, 70, 85, 101, 118, 135, 153, 169, 184, 195, 200]
# Mercury's स्पष्ट मन्दकर्ण at 0°, 10°, … 180° of the मन्दकेन्द्र, verses 11-13
# (p167). The books interpolate it: their Mercury's distance moves in steps
# of exactly 1 or 2 units per 10°.
MERCURY_DISTANCE = [47, 47, 46, 46, 45, 45, 44, 43, 42, 40, 39, 38, 37, 35, 33, 32, 32, 31, 31]
# Mean distances (Sun to Earth = 100) and Mars's केन्द्रच्युति, p159 and p163.
MEAN_DISTANCE = {"mars": 152, "mercury": 39}
MARS_ECCENTRIC = 14


def _row(row: list[int], k: float) -> tuple[float, int]:
    """Linear interpolation in a 10° row over 0-180°; beyond 180° the row is
    read backwards. Returns (value, +1 below 180° / −1 above)."""
    k = surya.norm(k)
    sign = 1
    if k > 180:
        k, sign = 360 - k, -1
    i = min(int(k // 10), 17)
    return row[i] + (row[i + 1] - row[i]) * (k - 10 * i) / 10, sign


def mean(body: str, jd: float) -> float:
    """Whole चक्रs by ध्रुवक, the days left by the per-day formula (p51: "यावंति
    चक्राणि भुक्तानि तेषां ग्रहा आनीय क्षेपकेषु योज्याः")."""
    cycles, days = divmod(jd - EPOCH, CYCLE)
    return surya.norm(MEAN_AT_EPOCH[body] + cycles * PER_CYCLE[body] + PER_DAY[body] * days)


def rahu(jd: float) -> float:
    """Ketaki's mean राहु at `jd`, with the books' RAHU_OFFSET."""
    cycles, days = divmod(jd - EPOCH, CYCLE)
    return surya.norm(RAHU_AT_EPOCH + cycles * RAHU_PER_CYCLE - (days / 19 + days / 46 / 60) + RAHU_OFFSET)


def rahu_of_day(day: date) -> float:
    """The स्पष्ट ग्रह table's राहु for `day`: at 06:00 Kathmandu mean time."""
    return rahu(mean_sunrise(sunrise(day)))


def apogee(body: str, jd: float) -> float:
    return surya.norm(APOGEE_AT_EPOCH[body] + APOGEE_PER_CYCLE[body] / 3600 / CYCLE * (jd - EPOCH))


def sunrise(day: date) -> float:
    """The moment the books' स्पष्ट ग्रह are for: Kathmandu sunrise without
    refraction (the Sun's centre on the horizon), 2.7-2.8 minutes after the
    refracted sunrise the book prints. Against 1841 printed values this
    beats the refracted sunrise for every planet (Mercury 90%: 43″ → 37″)."""
    return surya.sunrise(day, surya.GEOMETRIC)


def at_sunrise(body: str, day: date) -> float:
    """The स्पष्ट ग्रह of `day`."""
    return geocentric(body, sunrise(day))


def mean_sunrise(jd: float) -> float:
    """06:00 Kathmandu mean time on the civil day of `jd`."""
    day = surya.from_julian_day(jd).date()
    return surya.local_julian_day(day, 6 + 5.75 - surya.LONGITUDE / 15)


def _sun(moment: float) -> float:
    k = math.radians(mean("sun", moment) - apogee("sun", moment))
    first, second = SUN_EQUATION
    return surya.norm(mean("sun", moment) - (first * math.sin(k) + second * math.sin(2 * k)) / 60)


def true_sun(jd: float) -> float:
    """Ketaki's स्पष्ट रवि, as the books use it in the शीघ्र step.

    Two departures from the text. It is taken at the day's mean sunrise, not
    at `jd`. And the मन्दफल is not the 10° table of whole कला (p95) but the
    smooth SUN_EQUATION, which takes the books' Mercury from a 15″ to a 2″
    median error and every planet below its table residual.
    """
    return _sun(mean_sunrise(jd))


@lru_cache(maxsize=None)
def _shaka_new_year(year: int) -> float:
    """चैत्र शुक्ल प्रतिपदा of Gregorian `year`: the new moon before the Mesha
    sankranti."""
    start = surya.local_julian_day(date(year, 3, 1), 0)
    (_, mesha), = [c for c in surya.crossings(surya.true_sun, 30, start, start + 70) if c[0] == 11]
    return [jd for _, jd in surya.crossings(surya.elongation, 360, mesha - 35, mesha)][-1]


def shaka(jd: float) -> int:
    """Elapsed Shaka year at `jd`."""
    year = surya.from_julian_day(jd).year
    return year - 78 - (jd < _shaka_new_year(year))


def _bhuja(k: float) -> float:
    k = surya.norm(k)
    return min(k, abs(180 - k), 360 - k)


def karsha(jd: float) -> tuple[float, float]:
    """(Jupiter, Saturn) corrections to the mean longitude in degrees, p75:
    the केन्द्र is (Shaka − 1481) mod 918 years at 2/153 sign a year; with b
    its भुज in degrees, f = (b/9)(20 − b/9) कला; Jupiter gets +f/5, Saturn
    −f/2, signs reversed past 180°. Ketaki's example: +15′51″, −39′39″."""
    k = ((shaka(jd) - 1481) % 918) * 2 / 153 * 30
    b = _bhuja(k)
    f = (b / 9) * (20 - b / 9)
    s = 1 if k < 180 else -1
    return s * f / 5 / 60, -s * f / 2 / 60


def heliocentric(body: str, jd: float) -> tuple[float, float, float]:
    """(मन्दस्पष्ट longitude, signed मन्दफल, मन्दकेन्द्र), degrees."""
    m = mean(body, jd)
    if body == "jupiter":
        m += karsha(jd)[0]
    elif body == "saturn":
        m += karsha(jd)[1]
    k = surya.norm(m - apogee(body, jd))
    value, sign = _row(MANDA[body], k)
    phala = -sign * value / 10
    return surya.norm(m + phala), phala, k


def geocentric(body: str, jd: float) -> float:
    """Sidereal longitude of `body` at `jd`, meant to be a sunrise (see
    `sunrise`): the शीघ्र step uses that day's mean-sunrise Sun. For other
    moments use `table_longitude` or `longitude`."""
    return _shighra(body, jd, true_sun(jd))


def _shighra(body: str, jd: float, sun: float) -> float:
    """The heliocentric planet at `jd` seen from the Earth, with the Sun at
    `sun`."""
    helio, phala, k = heliocentric(body, jd)
    kendra = surya.norm(helio - sun)
    value, sign = _row(SHIGHRA[body], kendra)
    value /= 10
    if body == "mars":
        # p181: फल × शीघ्रकर्ण / (स्पष्ट मन्दकर्ण + शीघ्रकर्ण − 152), with the
        # स्पष्ट मन्दकर्ण by verse 8 (152 + 14 cos(केन्द्र + मन्दफल/2)).
        r = MEAN_DISTANCE["mars"] + MARS_ECCENTRIC * math.cos(math.radians(k + phala / 2))
        karna = 100 + MEAN_DISTANCE["mars"] - _row(MARS_KARNANKA, kendra)[0]
        value *= karna / (r + karna - MEAN_DISTANCE["mars"])
    elif body == "mercury":
        value *= _row(MERCURY_DISTANCE, k)[0] / MEAN_DISTANCE["mercury"]
    if body in ("mercury", "venus"):
        return surya.norm(sun + sign * value)
    return surya.norm(helio - sign * value)


def table_longitude(body: str, jd: float) -> float:
    """`body` at any moment as the books time the rail's entries: the day
    runs from the printed (refracted) sunrise, the स्पष्ट ग्रह row is its value
    there, and in between the formulas run on, the planet from the geometric
    sunrise and the Sun from the mean sunrise. So it keeps the tables' kinks.
    Timed this way, 134 of the 154 Mars to Saturn rail lines in the 2083 book
    are within a minute; linear between geometric sunrises, 17 (2-3 minutes
    late)."""
    day = surya.from_julian_day(jd).date()
    printed = surya.sunrise(day)
    if jd < printed:
        day -= timedelta(days=1)
        printed = surya.sunrise(day)
    rise = sunrise(day)
    return _shighra(body, jd + rise - printed, _sun(mean_sunrise(rise) + jd - printed))


def longitude(body: str, jd: float) -> float:
    """`body` at any moment: linear between the स्पष्ट ग्रह of the sunrises
    either side, as a panchangakar reads the daily table. (geocentric() itself
    would freeze the Sun at mean sunrise and bend the planet within the day.)"""
    day = surya.from_julian_day(jd).date()
    rise = sunrise(day)
    if jd < rise:
        day -= timedelta(days=1)
        rise = sunrise(day)
    after = sunrise(day + timedelta(days=1))
    a, b = geocentric(body, rise), geocentric(body, after)
    step = (b - a + 180) % 360 - 180
    return surya.norm(a + step * (jd - rise) / (after - rise))


def continuous(body: str, jd: float) -> float:
    """`body` at any moment by the tables themselves: the heliocentric planet
    at `jd`, the Sun linear between the sunrises either side. Unlike
    `longitude` this keeps the kinks where a केन्द्र crosses a 10° row, which
    is where the tables turn a planet वक्री or मार्गी."""
    day = surya.from_julian_day(jd).date()
    rise = sunrise(day)
    if jd < rise:
        day -= timedelta(days=1)
        rise = sunrise(day)
    after = sunrise(day + timedelta(days=1))
    s0, s1 = true_sun(rise), true_sun(after)
    sun = surya.norm(s0 + ((s1 - s0 + 180) % 360 - 180) * (jd - rise) / (after - rise))
    return _shighra(body, jd, sun)


def station(body: str, start: float, end: float) -> tuple[float, str] | None:
    """The moment in [start, end) where `body` turns वक्री (retrograde) or
    मार्गी (direct) by the tables, to five minutes then refined. 2083 p21
    prints "१ वक्री मङ्गल २८:२२"; this gives 28:15."""
    step = 5 / 1440
    samples = []
    t = start
    while t <= end:
        samples.append((t, continuous(body, t)))
        t += step
    motions = [((b - a + 180) % 360 - 180) for (_, a), (_, b) in zip(samples, samples[1:])]
    # The net turn: first motion's sign to the last's, at the extreme value.
    if motions[0] * motions[-1] >= 0:
        return None
    base = samples[0][1]
    offsets = [((v - base + 180) % 360 - 180) for _, v in samples]
    pick = max if motions[0] > 0 else min
    i = offsets.index(pick(offsets))
    return samples[i][0], "वक्री" if motions[0] > 0 else "मार्गी"
