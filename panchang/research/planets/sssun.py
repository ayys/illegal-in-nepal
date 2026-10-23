import math, sys
sys.path.insert(0, "../..")
import surya
from kepler import helio, ORDER
from swiss2083 import BOOK, deg, diff

def geo(body, jd, sun_shift=0.0):
    t = (jd - 2451545.0) / 36525
    ex, ey, _ = helio("earth", t)
    r = math.hypot(ex, ey)
    # Earth opposite the SS Sun (sidereal -> J2000 by adding Lahiri at J2000)
    sun = math.radians(surya.true_sun(jd) + 23.857092 + sun_shift)
    ex, ey = -r * math.cos(sun), -r * math.sin(sun)
    px, py, _ = helio(body, t)
    return (math.degrees(math.atan2(py - ey, px - ex)) - 23.857092) % 360

t0 = surya.sunrise(list(BOOK)[0])
mod = (math.degrees(math.atan2(*reversed(helio("earth", (t0-2451545)/36525)[:2]))) + 180 - 23.857092) % 360
print("SS sun - Kepler sun (arcmin):", round(diff(surya.true_sun(t0), mod), 2))
for day, row in BOOK.items():
    jd = surya.sunrise(day)
    print(day, "  ".join(f"{b} {diff(deg(x), geo(b, jd)):+7.2f}" for b, x in zip(ORDER, row)))
