"""Surya Siddhanta positions and sunrise, tuned to the राष्ट्रिय पञ्चाङ्ग.

The Sun and Moon come from the Surya Siddhanta (SS), chapters 1-2: mean
motions counted from the Kali epoch, then one manda (equation of centre)
correction. The SS is sidereal, so its longitudes can be used directly for
tithi, nakshatra, yoga, karana and sankranti.

Everything that needs the equinox (sunrise, sunset, lagna, बेलान्तर, राहु)
follows the Ketaki side of the book: Chitrapaksha (Lahiri) ayanamsha and the
modern obliquity, on top of the SS Sun.

The reference values are the printed tables of the 2082 and 2083 books:
  https://giwmscdnone.gov.np/media/pages/files/npnbs_2082_ussfian.pdf
  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
See docs/ALGORITHM.md for the derivation and docs/CALIBRATION.md for how the
fitted constants below were found.

Times are Julian days (UT) throughout; civil output is Nepal Standard Time.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction

NST = timezone(timedelta(hours=5, minutes=45), "NST")
# Kathmandu, the place the book's sunrise and lagna tables are computed for.
LATITUDE = 27.7
LONGITUDE = 85.3167
# The SS prime meridian (Lanka-Ujjain line). Days are counted from Ujjain
# midnight.
UJJAIN_LONGITUDE = 75.7682

# SS chapter 1: civil days and revolutions in a mahayuga (4,320,000 years).
# Mean motion = revolutions / days; nothing else enters the mean positions.
MAHAYUGA_DAYS = 1_577_917_828
MAHAYUGA_REVOLUTIONS = {
    "sun": 4_320_000,
    "moon": 57_753_336,
    "moon_apogee": 488_203,
}
# SS chapter 1: the Sun's apogee is so slow its revolutions are given per
# kalpa (1000 mahayugas), and it is not at 0 at the Kali epoch, so its
# position is counted from creation.
KALPA_DAYS = MAHAYUGA_DAYS * 1000
SUN_APOGEE_KALPA_REVOLUTIONS = 387
# SS chapter 1: 1,955,880,000 solar years elapsed from creation to the Kali epoch,
# each MAHAYUGA_DAYS / 4,320,000 civil days long.
CREATION_TO_KALI_DAYS = 1_955_880_000 * Fraction(MAHAYUGA_DAYS, 4_320_000)
# Kali epoch: midnight at Ujjain beginning 18 Feb 3102 BCE (Julian).
# JD 588465.5 is Greenwich midnight; Ujjain is 75.77° east, so earlier.
KALI_JD = 588465.5 - UJJAIN_LONGITUDE / 360

# Counted from creation, every mean longitude is 0 at the Kali epoch
# except the apogees. The Moon's apogee starts a quarter turn ahead.
KALI_MOON_APOGEE = 90.0

# The printed end times only fit with the Moon's apogee 1.7° behind the
# textbook value. Fortnights from Apr 2025 to Jan 2027 (books 2082 and 2083)
# each fit best between −1.74° and −1.70°, with no trend.
# Evidence: docs/CALIBRATION.md, "Moon's apogee".
MOON_APOGEE_CORRECTION = -1.7

# Refraction only, for the centre of the disc. The book's sunrise is the
# centre on the refracted horizon, with no semidiameter and no dip.
# Checked against the सूर्योदय column, 2083 book p21. Older books leave
# refraction out (GEOMETRIC): the 2062 book's दिनमान matches a 0° horizon to
# half a pala and is ~14 pala shorter than ours (2062 book p5, 14 May 2005).
HORIZON = -34 / 60
GEOMETRIC = 0.0
# The book's राहु follows a fixed daily moment, not local sunrise: at sunrise
# the residual swings ~10″ between April and January. At Ujjain mean sunrise
# it sits this far behind the Lahiri mean node in both 2082 and 2083.
# Evidence: the स्पष्ट ग्रह table, 2082 book p20 and 2083 book p21.
RAHU_OFFSET = -50.4 / 3600
# Mean solar days per sidereal rotation; the lagna advances 360° in this.
SIDEREAL_DAY = 0.99726957

# SS chapter 2: 24 tabulated sines (jya) at 3.75° steps, radius 3438
# (the number of arc-minutes in a radian). Interpolated linearly between rows.
# This table, not math.sin, is what the manda correction uses; it differs from
# 3438·sin by up to 1.7 units.
RADIUS = 3438
SINES = [
    225, 449, 671, 890, 1105, 1315, 1520, 1719, 1910, 2093, 2267, 2431,
    2585, 2728, 2859, 2978, 3084, 3177, 3256, 3321, 3372, 3409, 3431, 3438,
]


def norm(angle: float) -> float:
    return angle % 360.0


def julian_day(moment: datetime) -> float:
    # JD 2440587.5 is the Unix epoch. No ΔT: the SS counts civil days.
    return 2440587.5 + moment.timestamp() / 86400.0


def from_julian_day(jd: float) -> datetime:
    return datetime.fromtimestamp((jd - 2440587.5) * 86400.0, NST)


def local_julian_day(day: date, hours: float) -> float:
    midnight = datetime(day.year, day.month, day.day, tzinfo=NST)
    return julian_day(midnight) + hours / 24.0


# The ahargana (days since Kali) times revolutions per day. Only the fractional
# part matters; whole revolutions are dropped.
def _revolutions_since_kali(jd: float, body: str) -> float:
    return (jd - KALI_JD) * MAHAYUGA_REVOLUTIONS[body] / MAHAYUGA_DAYS


def _mean(jd: float, body: str, at_kali: float = 0.0) -> float:
    revolutions = _revolutions_since_kali(jd, body)
    return norm(at_kali + 360.0 * (revolutions - math.floor(revolutions)))


def _sun_apogee_at_kali() -> float:
    # Exact rational arithmetic: the integer part is ~7.5e5 revolutions, so a
    # float would lose the fraction we need.
    revolutions = CREATION_TO_KALI_DAYS * SUN_APOGEE_KALPA_REVOLUTIONS / KALPA_DAYS
    return float((revolutions - math.floor(revolutions)) * 360)


SUN_APOGEE_AT_KALI = _sun_apogee_at_kali()


def sun_apogee(jd: float) -> float:
    return SUN_APOGEE_AT_KALI + (jd - KALI_JD) * SUN_APOGEE_KALPA_REVOLUTIONS * 360 / KALPA_DAYS


def _jya(degrees: float) -> float:
    """Table sine (radius 3438) with linear interpolation, as in the siddhanta."""
    sign = 1
    degrees = norm(degrees)
    if degrees >= 180:
        degrees -= 180
        sign = -1
    if degrees > 90:
        degrees = 180 - degrees
    steps = degrees / 3.75
    i = int(steps)
    low = SINES[i - 1] if i else 0
    high = SINES[min(i, 23)]
    return sign * (low + (high - low) * (steps - i))


def _inverse_jya(value: float) -> float:
    sign = 1 if value >= 0 else -1
    value = abs(value)
    previous = 0
    for i, sine in enumerate(SINES):
        if value <= sine:
            return sign * 3.75 * (i + (value - previous) / (sine - previous))
        previous = sine
    return sign * 90.0


def _manda(mean_longitude: float, apogee: float, even: float, odd: float) -> float:
    """SS chapter 2: the equation of centre.

    The epicycle's circumference (in degrees, on a 360° deferent) shrinks from
    `even` at the apsides to `odd` at quadrature: Sun 14° → 13°40′, Moon
    32° → 31°40′. The correction is arcsin(circumference/360 · sin(anomaly)),
    using the table sine both ways, and it is subtracted: a body is slowest,
    and behind its mean place, after passing the apogee.
    """
    anomaly = norm(mean_longitude - apogee)
    sine = _jya(anomaly)
    circumference = even - (even - odd) * abs(sine) / RADIUS
    return norm(mean_longitude - _inverse_jya(circumference / 360 * sine))


def mean_sun(jd: float) -> float:
    return _mean(jd, "sun")


def true_sun(jd: float) -> float:
    """Sidereal SS longitude of the Sun. Sankrantis are its 30° crossings."""
    return _manda(mean_sun(jd), sun_apogee(jd), 14, 13 + 40 / 60)


def true_moon(jd: float) -> float:
    """Sidereal SS longitude of the Moon: mean Moon plus the manda correction
    about the (corrected) apogee."""
    apogee = _mean(jd, "moon_apogee", KALI_MOON_APOGEE) + MOON_APOGEE_CORRECTION
    return _manda(_mean(jd, "moon"), apogee, 32, 31 + 40 / 60)


def elongation(jd: float) -> float:
    """Moon minus Sun. A tithi is 12° of it, a karana 6°."""
    return norm(true_moon(jd) - true_sun(jd))


def yoga_angle(jd: float) -> float:
    """Moon plus Sun. A yoga is 13°20′ of it."""
    return norm(true_moon(jd) + true_sun(jd))


def _centuries(jd: float) -> float:
    return (jd - 2451545.0) / 36525


def lahiri(jd: float) -> float:
    """Chitrapaksha ayanamsha: the IAU 1976 general precession in longitude
    from 23°51′25.53″ at J2000 (the value Swiss Ephemeris uses for Lahiri).
    Tropical longitude = sidereal + lahiri."""
    t = _centuries(jd)
    return 23.857092 + (5029.0966 * t + 1.11113 * t * t) / 3600


def obliquity(jd: float) -> float:
    """Mean obliquity of the ecliptic (IAU, linear term), not the SS 24°."""
    return 23.439291 - 0.0130042 * _centuries(jd)


def _right_ascension(longitude: float, eps: float) -> float:
    lam, eps = math.radians(longitude), math.radians(eps)
    return norm(math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))))


def _declination(longitude: float, eps: float) -> float:
    return math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(longitude)))


def _oblique_ascension(longitude: float, eps: float) -> float:
    """Right ascension minus the ascensional difference (चरान्तर) at Kathmandu:
    the sidereal angle at which this ecliptic point rises."""
    ascensional = math.asin(
        math.tan(math.radians(LATITUDE)) * math.tan(_declination(longitude, eps)))
    return norm(_right_ascension(longitude, eps) - math.degrees(ascensional))


def _equation_of_time(jd: float) -> float:
    """Minutes from mean to apparent time.

    Mean Sun minus the true Sun's right ascension, both made tropical with the
    same Lahiri shift, 4 minutes of time per degree.
    """
    shift = lahiri(jd)
    right_ascension = _right_ascension(norm(true_sun(jd) + shift), obliquity(jd))
    return -((norm(mean_sun(jd) + shift - right_ascension) + 180) % 360 - 180) * 4


def equation_of_time(day: date) -> float:
    """The बेलान्तर column: equation of time at local noon, in minutes."""
    return _equation_of_time(local_julian_day(day, 12))


def _half_day(jd: float, horizon: float = HORIZON) -> float:
    """Minutes from sunrise to noon for the Sun's declination at `jd`."""
    lat = math.radians(LATITUDE)
    declination = _declination(norm(true_sun(jd) + lahiri(jd)), obliquity(jd))
    cos_hour = (
        math.sin(math.radians(horizon)) - math.sin(lat) * math.sin(declination)
    ) / (math.cos(lat) * math.cos(declination))
    return math.degrees(math.acos(cos_hour)) * 4


def _sun_event(day: date, rising: bool, horizon: float = HORIZON) -> float:
    """Sunrise or sunset at Kathmandu, iterated so the declination and the
    equation of time are taken at the event itself.

    Apparent noon in NST is 12:00 + equation of time + 4 min per degree that
    Kathmandu lies west of the 86.25° NST meridian; rise and set are half a
    day-arc either side.
    """
    jd = local_julian_day(day, 6.0 if rising else 18.0)
    for _ in range(6):
        half_day = _half_day(jd, horizon)
        noon = 12 * 60 + _equation_of_time(jd) + (86.25 - LONGITUDE) * 4
        jd = local_julian_day(day, (noon - half_day if rising else noon + half_day) / 60)
    return jd


def day_length(day: date, horizon: float = HORIZON) -> float:
    """दिनमान in minutes: twice the half-day arc at sunrise."""
    return 2 * _half_day(sunrise(day, horizon), horizon)


def sunrise(day: date, horizon: float = HORIZON) -> float:
    return _sun_event(day, True, horizon)


def sunset(day: date, horizon: float = HORIZON) -> float:
    return _sun_event(day, False, horizon)


def ujjain_mean_sunrise(day: date) -> float:
    """6:00 local mean time at Ujjain (6:42 NST), the SS's day start."""
    return local_julian_day(day, 6 + NST.utcoffset(None).total_seconds() / 3600 - UJJAIN_LONGITUDE / 15)


def rahu(jd: float) -> float:
    """Mean lunar node (Meeus, Astronomical Algorithms ch. 22), made
    sidereal with Lahiri, plus the fitted RAHU_OFFSET. Retrograde, ~3′11″/day."""
    t = _centuries(jd)
    node = 125.04452 - 1934.136261 * t + 0.0020708 * t * t + t ** 3 / 450000
    return norm(node - lahiri(jd) + RAHU_OFFSET)


def lagna_starts(day: date) -> list[tuple[int, float]]:
    """(sidereal sign, jd) for each lagna that begins between sunrise and the next.

    At sunrise the lagna is the Sun's own longitude; it then advances by
    oblique ascension at the sidereal rate.
    """
    rise = sunrise(day)
    shift = lahiri(rise)
    eps = obliquity(rise)
    sun = _oblique_ascension(norm(true_sun(rise) + shift), eps)
    starts = []
    for sign in range(12):
        ahead = (_oblique_ascension(norm(sign * 30 + shift), eps) - sun) % 360
        starts.append((sign, rise + ahead / 360 * SIDEREAL_DAY))
    return sorted(starts, key=lambda s: s[1])


# Root finding for "when does this angle reach that value": Newton's method on
# a wrapped angle, with the rate from a central difference.
def _rate(angle, jd: float) -> float:
    return ((angle(jd + 1e-3) - angle(jd - 1e-3) + 180) % 360 - 180) / 2e-3


def _solve(angle, target: float, jd: float) -> float:
    """First time at or after `jd` when `angle` reaches `target`."""
    jd += ((target - angle(jd)) % 360) / _rate(angle, jd)
    for _ in range(50):
        miss = (angle(jd) - target + 180) % 360 - 180
        if abs(miss) < 1e-9:
            break
        jd -= miss / _rate(angle, jd)
    return jd


def crossings(angle, width: float, start: float, end: float) -> list[tuple[int, float]]:
    """Every (index ending, jd) where `angle` passes a multiple of `width` in [start, end).

    `angle` must increase monotonically. crossings(elongation, 12, ...) gives
    tithi ends, crossings(true_sun, 30, ...) sankrantis, and so on. The index
    is the division that ends at `jd`: 0 for the first tithi, Mesha, Ashvini.
    """
    count = round(360 / width)
    found = []
    jd = start
    while True:
        index = math.floor(angle(jd) / width) % count
        moment = _solve(angle, (index + 1) * width % 360, jd)
        if moment >= end:
            return found
        found.append((index, moment))
        jd = moment + 1e-5
