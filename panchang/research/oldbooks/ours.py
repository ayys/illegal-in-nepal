import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta

starts = json.load(open(__import__("pathlib").Path(__file__).resolve().parent.parent / "bscmp/starts.json"))
MONTHS = "बै जे अ श्रा भा आ का मं पु मा फा चै".split()


def ghati(days):
    g = days * 60
    return f"{int(g):2d}:{round(g % 1 * 60):02d}"


def rows(y):
    s, e = panchanga._gregorian_jd(y - 57, 4, 1), panchanga._gregorian_jd(y - 56, 4, 30)
    for i, (ended, jd) in enumerate(surya.crossings(surya.true_sun, 30, s, e)[:13]):
        day = surya.from_julian_day(jd).date()
        if jd < surya.sunrise(day):
            day -= timedelta(days=1)
        dm = surya.day_length(day) / 1440
        yield i, jd, day, (jd - surya.sunrise(day)), dm


if __name__ == "__main__":
    for y in map(int, sys.argv[1:]):
        print("==", y)
        for i, jd, day, g, dm in rows(y):
            t = starts.get(str(y), {}).get("nd")
            print(f"{MONTHS[i % 12]:4} {surya.from_julian_day(jd):%m-%d %H:%M} NST  sunrise-day {day}"
                  f"  ghati {ghati(g)}  dinamana {ghati(dm)}  nishitha {ghati(0.5 + dm / 2)}"
                  f"  table {t[i] if t and i < 12 else '-'}")
