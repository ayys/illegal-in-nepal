"""Surya Siddhanta true longitudes of Mars–Saturn (Burgess, chapters 1–2).

Research version: the constants are the textbook SS values, with optional
bija (per-mahayuga revolution corrections) to test against the books.
"""
import math
import sys
from fractions import Fraction
sys.path.insert(0, "../..")
import surya
from surya import _jya, _inverse_jya, norm, RADIUS, KALI_JD, MAHAYUGA_DAYS, KALPA_DAYS, CREATION_TO_KALI_DAYS

# Revolutions per mahayuga. Mercury and Venus: their शीघ्रोच्च; their mean
# place is the mean Sun.
REVOLUTIONS = {
    "mars": 2_296_832,
    "mercury": 17_937_060,
    "jupiter": 364_220,
    "venus": 7_022_376,
    "saturn": 146_568,
}
# मन्दोच्च revolutions per kalpa.
APOGEE_KALPA = {"mars": 204, "mercury": 368, "jupiter": 900, "venus": 535, "saturn": 39}
# Epicycle circumferences (degrees): (even quadrant end, odd quadrant end).
MANDA = {"mars": (75, 72), "mercury": (30, 28), "jupiter": (33, 32), "venus": (12, 11), "saturn": (49, 48)}
SHIGHRA = {"mars": (235, 232), "mercury": (133, 132), "jupiter": (70, 72), "venus": (262, 260), "saturn": (39, 40)}

BIJA = {}  # body -> extra revolutions per mahayuga


def _fraction_turns(days, revolutions, period):
    turns = Fraction(days) * revolutions / period if isinstance(days, Fraction) else days * revolutions / period
    return turns - math.floor(turns)


def mean_body(jd, body):
    revolutions = REVOLUTIONS[body] + BIJA.get(body, 0)
    turns = (jd - KALI_JD) * revolutions / MAHAYUGA_DAYS
    return norm(360 * (turns - math.floor(turns)))


def apogee(jd, body):
    at_kali = CREATION_TO_KALI_DAYS * APOGEE_KALPA[body] / KALPA_DAYS
    at_kali = float((at_kali - math.floor(at_kali)) * 360)
    return norm(at_kali + (jd - KALI_JD) * APOGEE_KALPA[body] * 360 / KALPA_DAYS)


def _circumference(pair, sine):
    even, odd = pair
    return even + (odd - even) * abs(sine) / RADIUS


def manda_equation(longitude, apogee_, pair):
    """Correction to add (negative after the apogee)."""
    sine = _jya(norm(longitude - apogee_))
    return -_inverse_jya(_circumference(pair, sine) / 360 * sine)


def shighra_equation(longitude, shighrocca, pair):
    anomaly = norm(shighrocca - longitude)
    sine, cosine = _jya(anomaly), _jya(anomaly + 90)
    c = _circumference(pair, sine) / 360
    bhuja, koti = c * sine, c * cosine
    hyp = math.hypot(RADIUS + koti, bhuja)
    return _inverse_jya(RADIUS * bhuja / hyp)


def true_planet(jd, body):
    mean_sun = surya.mean_sun(jd)
    if body in ("mercury", "venus"):
        mean, shighrocca = mean_sun, mean_body(jd, body)
    else:
        mean, shighrocca = mean_body(jd, body), mean_sun
    ap = apogee(jd, body)
    p1 = norm(mean + shighra_equation(mean, shighrocca, SHIGHRA[body]) / 2)
    p2 = norm(p1 + manda_equation(p1, ap, MANDA[body]) / 2)
    p3 = norm(mean + manda_equation(p2, ap, MANDA[body]))
    return norm(p3 + shighra_equation(p3, shighrocca, SHIGHRA[body]))


ORDER = ["mars", "mercury", "jupiter", "venus", "saturn"]
