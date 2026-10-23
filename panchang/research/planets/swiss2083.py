"""Compare the 2083 book's Mars–Saturn spashta (page 21) with Swiss Ephemeris."""
import sys
from datetime import date
sys.path.insert(0, "../..")
import swisseph as swe
import surya

# sign:deg:min:sec, 2083 book page 21 (Jan 8–12, 2027)
BOOK = {
    date(2027, 1, 8): ("4:16:26:41", "8:27:14:47", "4:1:59:27", "7:7:9:35", "11:14:16:50"),
    date(2027, 1, 9): ("4:16:29:31", "8:28:53:43", "4:1:55:10", "7:8:11:24", "11:14:20:4"),
    date(2027, 1, 10): ("4:16:32:24", "9:0:31:53", "4:1:50:50", "7:9:13:12", "11:14:23:17"),
    date(2027, 1, 11): ("4:16:35:19", "9:2:10:37", "4:1:44:18", "7:10:15:1", "11:14:26:31"),
    date(2027, 1, 12): ("4:16:38:17", "9:3:49:25", "4:1:37:47", "7:11:16:49", "11:14:29:45"),
}
BODIES = [("mars", swe.MARS), ("mercury", swe.MERCURY), ("jupiter", swe.JUPITER),
          ("venus", swe.VENUS), ("saturn", swe.SATURN)]


def deg(text):
    s, d, m, x = map(int, text.split(":"))
    return s * 30 + d + m / 60 + x / 3600


def diff(a, b):
    return ((a - b + 180) % 360 - 180) * 60  # arcmin


if __name__ == "__main__":
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    for label, when in (("Kathmandu sunrise", lambda d: surya.sunrise(d)),
                        ("Ujjain mean sunrise", surya.ujjain_mean_sunrise)):
        print(f"\nbook − Swiss (sidereal Lahiri, apparent), arcmin, at {label}")
        for day, row in BOOK.items():
            jd = when(day)
            jd_tt = jd + swe.deltat(jd)
            out = []
            for (name, body), text in zip(BODIES, row):
                lon = swe.calc(jd_tt, body, swe.FLG_SIDEREAL | swe.FLG_SWIEPH)[0][0]
                out.append(f"{name} {diff(deg(text), lon):+7.2f}")
            print(day, "  ".join(out))
