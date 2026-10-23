"""Mars–Saturn by the केतकी ग्रहगणितम् (V. B. Ketkar, 1898), research version.

Read from the 2001 Chaukhamba reprint with Datta Raj's commentary:
  https://archive.org/details/KetakiGrahaGanitam   (PDF page = book page + 6)

The procedure, as the book gives it:
1. Mean longitudes (heliocentric; the Sun's geocentric) from the क्षेपक at
   Shaka 1800 elapsed, चैत्र शुक्ल प्रतिपदा, Ujjain mean sunrise (p48-49), and
   the motion per 19-year चक्र of 6940 days (ध्रुवक, p50-51).
2. Jupiter and Saturn: the 918-year कर्ष (great inequality, p75), and for
   Saturn two short terms (p159).
3. मन्दफल from 10° tables of the मन्दकेन्द्र (mean − apogee), linear
   interpolation (p94-95 for the Sun, p156-158 for the planets).
4. शीघ्र केन्द्र = heliocentric planet − true Sun; शीघ्रफल from 10° tables
   (p171-172). Mars and Mercury get a distance correction (p180-181).
   Mercury and Venus: true Sun ± फल; Mars, Jupiter, Saturn: planet ∓ फल.
Longitudes are sidereal; the epoch Sun and Moon agree with the Lahiri mean
Sun and Moon to 0.01°, so no ayanamsha step is needed.

How the national books apply it, found by fitting their स्पष्ट ग्रह tables
(see NOTES.md): planets at true Kathmandu sunrise; the Sun for step 4 at
mean sunrise, with its row read from perigee (true_sun_at); no Saturn short
terms; unrounded distances.
"""
from __future__ import annotations

import math
import sys
from datetime import date

sys.path.insert(0, "../..")
import panchanga
import surya

CYCLE = 6940  # days in the 19-year चक्र


def dms(s, d, m=0, x=0):
    return s * 30 + d + m / 60 + x / 3600


# Shaka 1800 elapsed, चैत्र शुक्ल प्रतिपदा = 1878-04-03, 06:00 Ujjain mean time.
EPOCH = surya.local_julian_day(date(1878, 4, 3), 6 - surya.UJJAIN_LONGITUDE / 15 + 5.75)

# p48-49 क्षेपक: mean longitude, apogee (उच्च).
MEAN0 = {"sun": dms(11, 19, 5), "mars": dms(2, 9, 12), "mercury": dms(1, 22, 30),
         "jupiter": dms(9, 5, 40), "venus": dms(6, 15, 28), "saturn": dms(11, 8, 21)}
APOGEE0 = {"sun": dms(2, 18, 41), "mars": dms(4, 11, 41), "mercury": dms(7, 23, 26),
           "jupiter": dms(5, 20, 13), "venus": dms(9, 17, 40), "saturn": dms(8, 8, 27)}
# p50-51 ध्रुवक: whole revolutions per चक्र (implied) and the remainder.
REVS = {"sun": 19, "mars": 10, "mercury": 78, "jupiter": 1, "venus": 30, "saturn": 0}
REMAINDER = {"sun": dms(0, 0, 7, 38), "mars": dms(1, 6, 47, 20), "mercury": dms(10, 20, 49, 50),
             "jupiter": dms(7, 6, 39, 12), "venus": dms(10, 18, 47, 10), "saturn": dms(7, 22, 12, 37)}
# Apogee motion, arc-seconds per चक्र; Venus's moves backward (p52 verse 15).
APOGEE_RATE = {"sun": 225, "mars": 321, "mercury": 117, "jupiter": 126, "venus": -28.5, "saturn": 303}

# Mean motion per day, p53-62: the formulas Ketaki gives for the days elapsed
# within the current चक्र (whole चक्रs go in as ध्रुवक). They are a hair off
# the ध्रुवक rates (Mercury 1e-6 °/day), which matters only inside a चक्र.
FORMULA = {
    "sun": 69 / 70 - 1 / (158 * 60),
    "mars": 10 / 19 - 10 / (73 * 60),
    "mercury": 3 * 30 / 22 + 1 / 700,
    "jupiter": 1 / 12 - 1 / (69 * 60),
    "venus": 8 / 5 + 1 / (8 * 60) + 1 / (6 * 3600),
    "saturn": 1 / 30 + 1 / (132 * 60),
}

# मन्दफल at 0°, 10°, … 180° of the मन्दकेन्द्र: the Sun in कला (p95), the
# planets in असु (0.1°, p156-158). Every row is checked against its verse
# (भूतसंख्या, digits read right to left); where the commentary's digit list
# and a low-resolution reading disagreed, the verse decides (Mercury:
# "ऽगनिधयः" 97, "त्रीष्विलाः" 153, "सप्तेंदुपक्षाः" 217, "षडग्निपक्षयुगलं"
# 236 twice, "शराष्टभूमयः" 185).
SUN_MANDA = [0, 20, 39, 57, 73, 87, 99, 108, 113, 115, 114, 109, 101, 89, 75, 59, 40, 20, 0]
MANDA = {
    "mars": [0, 17, 33, 48, 63, 76, 87, 96, 103, 106, 107, 104, 98, 88, 75, 59, 41, 21, 0],
    "jupiter": [0, 9, 18, 26, 34, 41, 46, 51, 54, 55, 55, 53, 49, 44, 37, 29, 20, 10, 0],
    "saturn": [0, 10, 21, 30, 39, 47, 54, 59, 63, 64, 64, 62, 58, 52, 45, 34, 24, 12, 0],
    "venus": [0, 1, 3, 4, 5, 6, 7, 7, 8, 8, 8, 7, 7, 6, 6, 5, 3, 1, 0],
    "mercury": [0, 32, 65, 97, 125, 153, 178, 199, 217, 229, 236, 236, 228, 211, 185, 149, 105, 54, 0],
}

# शीघ्रफल in असु at 0°, 10°, … 180° of the शीघ्र केन्द्र (p171-172). Venus 140°
# is "द्विषट्सागराः" 462.
SHIGHRA = {
    "mars": [0, 40, 79, 118, 157, 195, 232, 267, 301, 333, 361, 385, 402, 410, 403, 372, 304, 179, 0],
    "mercury": [0, 28, 55, 82, 109, 134, 157, 178, 197, 212, 222, 227, 226, 215, 195, 162, 118, 62, 0],
    "jupiter": [0, 16, 32, 47, 62, 75, 86, 96, 104, 109, 111, 109, 104, 95, 82, 66, 46, 24, 0],
    "venus": [0, 42, 84, 125, 167, 206, 247, 286, 323, 359, 392, 421, 445, 460, 462, 441, 377, 236, 0],
    "saturn": [0, 9, 19, 28, 36, 43, 49, 54, 58, 60, 60, 58, 55, 49, 42, 33, 23, 12, 0],
}
# शीघ्रकर्णांक (p173-174), for the Mars and Mercury distance correction.
KARNANKA = {
    "mars": [0, 1, 3, 8, 16, 22, 32, 43, 56, 70, 85, 101, 118, 135, 153, 169, 184, 195, 200],
    "mercury": [0, 1, 2, 4, 7, 11, 15, 20, 26, 32, 38, 45, 52, 58, 64, 70, 74, 77, 78],
}
MEAN_DISTANCE = {"mars": 152, "mercury": 39, "jupiter": 520, "venus": 72, "saturn": 954}  # Sun = 100
ECCENTRIC = {"mars": 14, "mercury": 8}  # केन्द्रच्युति, p163


def norm(x):
    return x % 360


def rate(body):
    return (REVS[body] * 360 + REMAINDER[body]) / CYCLE


def mean(body, jd):
    """Whole चक्रs by ध्रुवक, the rest by the day formula (p51-52: "यावंति
    चक्राणि भुक्तानि तेषां ग्रहा आनीय क्षेपकेषु योज्याः")."""
    cycles, rest = divmod(jd - EPOCH, CYCLE)
    return norm(MEAN0[body] + cycles * REMAINDER[body] + FORMULA[body] * rest)


def apogee(body, jd):
    return norm(APOGEE0[body] + APOGEE_RATE[body] / 3600 / CYCLE * (jd - EPOCH))


def table(row, k, scale):
    """Linear interpolation in a 10° row over 0-180°, mirrored and negated
    beyond 180°. Returns (magnitude in degrees, +1 below 180° / -1 above)."""
    k = norm(k)
    sign = 1
    if k > 180:
        k, sign = 360 - k, -1
    i = min(int(k // 10), 17)
    value = row[i] + (row[i + 1] - row[i]) * (k - 10 * i) / 10
    return value * scale, sign


def mean_sunrise(jd):
    """06:00 Kathmandu mean time on the civil day of `jd`."""
    day = surya.from_julian_day(jd).date()
    return surya.local_julian_day(day, 6 + 5.75 - surya.LONGITUDE / 15)


def true_sun(jd):
    """Ketaki's स्पष्ट रवि. The books take it at the day's mean sunrise
    (06:00 Kathmandu mean time) while the planets are at true sunrise: Sun
    at true sunrise, Mars's 90% error is 131″; at mean sunrise, 69″."""
    return true_sun_at(mean_sunrise(jd))


def true_sun_at(jd):
    """The books read the Sun's row from the other end: the केन्द्र counted
    from perigee, as if Ketaki's रवि-उच्च 2:18:41 were the Earth's (it is the
    Earth's perihelion, "सूर्यः स्थिरः भूर्भ्रमति"). The row is nearly
    symmetric, so this only flips its e² asymmetry, ±1-2′ at 45° and 135°.
    Read as printed, Mars's 90% error is 69″; reversed, 15″."""
    k = norm(mean("sun", jd) - apogee("sun", jd))
    value, sign = table(SUN_MANDA[::-1], k, 1 / 60)
    return norm(mean("sun", jd) - sign * value)


def shaka(jd):
    """Elapsed Shaka year at jd: it turns at चैत्र शुक्ल प्रतिपदा."""
    day = surya.from_julian_day(jd).date()
    year = day.year - 78
    months = panchanga.lunations(surya.local_julian_day(date(day.year, 2, 15), 0),
                                 surya.local_julian_day(date(day.year, 5, 15), 0))
    chaitra = next(l.start for l in months if l.month == 0 and not l.adhik)
    return year if jd >= chaitra else year - 1


def _parabola(b, divisor, top):
    return (b / divisor) * (top - b / divisor)


def bhuja(k):
    k = norm(k)
    return k if k <= 90 else 180 - k if k <= 180 else k - 180 if k <= 270 else 360 - k


def karsha(jd):
    """(Jupiter, Saturn) corrections to the mean longitude, degrees."""
    k = ((shaka(jd) - 1481) % 918) * 2 / 153 * 30
    f = _parabola(bhuja(k), 9, 20)
    s = 1 if norm(k) < 180 else -1
    return s * f / 5 / 60, -s * f / 2 / 60


def saturn_short(jupiter, saturn):
    k1 = norm(jupiter - 2 * saturn - 15)
    k2 = norm(2 * k1 + 90)
    total = 0.0
    for k, top in ((k1, 5), (k2, 7)):
        f = _parabola(bhuja(k), 32, top)
        total += -f if k < 180 else f
    return total / 60


def heliocentric(body, jd, short=False):
    """(मन्दस्पष्ट longitude, मन्दफल signed, मन्दकेन्द्र).

    `short` adds Saturn's two optional short-period terms (p159, "इच्छा चेदयं
    संस्कारोऽपि देयः"). The national books leave them out: with them Saturn
    is 4.6′ off, without them 6″.
    """
    m = mean(body, jd)
    if body in ("jupiter", "saturn"):
        dj, ds = karsha(jd)
        if body == "jupiter":
            m += dj
        else:
            m += ds
            if short:
                m += saturn_short(norm(mean("jupiter", jd) + dj), norm(mean("saturn", jd) + ds))
    k = norm(m - apogee(body, jd))
    value, sign = table(MANDA[body], k, 0.1)
    phala = -sign * value
    return norm(m + phala), phala, k


# स्पष्ट मन्दकर्ण at 0°, 10°, … 180° of the मन्दकेन्द्र, verses 11-13 (p167):
# Ketaki's own Mars example uses it (केन्द्र 288° → 72° → 158); the books use
# it for Mercury only (see distance).
DISTANCE = {
    "mars": [166, 166, 166, 165, 164, 162, 160, 158, 156, 154, 151, 149, 146, 144, 142, 140, 139, 138, 138],
    "mercury": [47, 47, 46, 46, 45, 45, 44, 43, 42, 40, 39, 38, 37, 35, 33, 32, 32, 31, 31],
}


def distance(body, k, phala, rounded=False):
    """स्पष्ट मन्दकर्ण. Mercury: the verse 11-13 table (median error 229″ →
    17″ against the books). Mars: the cosine of verse 8 (p165), unrounded;
    the table makes Mars worse (5″ → 63″)."""
    if body == "mercury":
        return table(DISTANCE[body], k, 1)[0]
    r = MEAN_DISTANCE[body] + ECCENTRIC[body] * math.cos(math.radians(k + phala / 2))
    return round(r) if rounded else r


def geocentric(body, jd, rounded=False, short=False):
    helio, phala, k = heliocentric(body, jd, short)
    sun = true_sun(jd)
    sk = norm(helio - sun)
    value, sign = table(SHIGHRA[body], sk, 0.1)
    if body == "mars":
        r = distance(body, k, phala, rounded)
        karna = 100 + MEAN_DISTANCE[body] - table(KARNANKA[body], sk, 1)[0]
        if rounded:
            karna = round(karna)
        value = value * karna / (r + karna - MEAN_DISTANCE[body])
    elif body == "mercury":
        value = value * distance(body, k, phala, rounded) / MEAN_DISTANCE[body]
    if body in ("mercury", "venus"):
        return norm(sun + sign * value)
    return norm(helio - sign * value)


ORDER = ["mars", "mercury", "jupiter", "venus", "saturn"]

if __name__ == "__main__":
    def show(x):
        x = norm(x)
        s, r = divmod(x, 30)
        d = int(r); m = (r - d) * 60
        return f"{int(s)}:{d}:{int(m)}:{round((m - int(m)) * 60)}"
    # Worked example, p158-159 and p177: Shaka 1815 चैत्र शुक्ल १५ (1893-04-01),
    # Bagalkot mean morning; ahargana 5477.
    jd = EPOCH + 5477
    print("ahargana", round(jd - EPOCH, 3), "shaka", shaka(jd))
    print("true sun", show(true_sun(jd)), "  book 11:19:10:37")
    book = {"mars": ("1:29:19:37", "2:9:5:31"), "mercury": ("4:26:14:0", "5:18:47:50"),
            "jupiter": ("0:11:1:28", "0:13:5:50"), "venus": ("11:0:19:50", "10:29:48:14"),
            "saturn": ("5:10:56:10", "5:17:19:20")}
    for b in ORDER:
        h, ph, k = heliocentric(b, jd)
        print(f"{b:8s} mean {show(mean(b, jd))}  helio {show(h)}  (book mean/karsha {book[b][0]}, helio {book[b][1]})"
              f"  geo {show(geocentric(b, jd, rounded=True))}")
    print("karsha J,S (′)", [round(x * 60, 2) for x in karsha(jd)], " book +15:51, -39:39")
