"""Find the moment a printed table is for, from its Sun, then compare planets.

Usage: python epoch.py   (edits READINGS below)
"""
import sys
from datetime import date
sys.path.insert(0, "../..")
import swisseph as swe
import surya
import ss_planets as ss

BODY = {"sun": None, "moon": None, "mars": swe.MARS, "mercury": swe.MERCURY, "jupiter": swe.JUPITER,
        "venus": swe.VENUS, "saturn": swe.SATURN}


def deg(text):
    s, d, m, x = map(int, text.split(":"))
    return s * 30 + d + m / 60 + x / 3600


def diff(a, b):
    return ((a - b + 180) % 360 - 180) * 60


def sun_moment(day, sun_text):
    """JD near Kathmandu sunrise of `day` where the SS true Sun equals the printed value."""
    jd = surya.sunrise(day)
    target = deg(sun_text)
    for _ in range(8):
        jd += diff(target, surya.true_sun(jd)) / 60 / 0.9856
    return jd


swe.set_sid_mode(swe.SIDM_LAHIRI)


def report(day, row):
    """row: dict body -> 's:d:m:s'."""
    rise = surya.sunrise(day)
    jd = sun_moment(day, row["sun"]) if "sun" in row else rise
    hours = (jd - rise) * 24
    print(f"{day}  Sun says {hours:+.2f} h from Kathmandu sunrise ({hours * 2.5:+.1f} ghati)")
    for body, text in row.items():
        if body in ("sun", "moon", "rahu"):
            continue
        swiss = swe.calc(jd + swe.deltat(jd), BODY[body], swe.FLG_SIDEREAL)[0][0]
        print(f"   {body:8s} book−SS {diff(deg(text), ss.true_planet(jd, body)):+8.1f}′   book−Swiss/Lahiri {diff(deg(text), swiss):+7.1f}′")


READINGS = {
    # 2076 book p12 (Himal), "भाद्र १५ रवौ २७।१३" and "भाद्र २२ रवौ २७।५"
    date(2019, 9, 1): {"sun": "4:13:58:56", "mars": "4:14:10:46", "mercury": "4:13:56:26",
                       "jupiter": "7:22:21:11", "venus": "4:20:41:41", "saturn": "8:16:45:45"},
    date(2019, 9, 8): {"sun": "4:20:45:39", "mars": "4:18:38:25", "mercury": "4:26:32:26",
                       "jupiter": "7:22:50:9", "venus": "4:29:20:20", "saturn": "8:16:37:28"},
}

if __name__ == "__main__":
    for day, row in READINGS.items():
        report(day, row)
