import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import swisseph as swe, surya
from datetime import date, datetime, timedelta, time
from collections import Counter
swe.set_sid_mode(swe.SIDM_LAHIRI)
d = json.load(open("starts.json"))

def lon(jd, flags):
    return swe.calc_ut(jd, swe.SUN, flags)[0][0]

def sankranti_date(guess, m, sunfn):
    target = (m - 1) * 30.0
    jd = surya.julian_day(datetime.combine(guess - timedelta(days=4), time(), surya.NST))
    for _ in range(3):
        pass
    # step to crossing then bisect
    lo = jd
    while ((sunfn(lo + 1) - target + 180) % 360 - 180) < 0: lo += 1
    hi = lo + 1
    for _ in range(40):
        mid = (lo + hi) / 2
        if ((sunfn(mid) - target + 180) % 360 - 180) < 0: lo = mid
        else: hi = mid
    return surya.from_julian_day(hi).astimezone(surya.NST)

models = {
    "SS true sun (current)": surya.true_sun,
    "Swiss + Lahiri (apparent)": lambda jd: lon(jd, swe.FLG_SIDEREAL | swe.FLG_SWIEPH),
}
for name, fn in models.items():
    for rule in ("clock date", "before sunrise -> prev day"):
        c = Counter(); per = Counter(); misses = []
        for y in range(1975, 2084):
            for m in range(1, 13):
                table = date.fromisoformat(d[str(y)]["nd"][m - 1])
                t = sankranti_date(table, m, fn)
                day = t.date()
                if rule != "clock date":
                    rise = surya.from_julian_day(surya.sunrise(day)).astimezone(surya.NST)
                    if t < rise: day -= timedelta(days=1)
                x = (day - table).days; c[x] += 1
                if x: per[m] += 1; misses.append((y, m, x, f"{t:%m-%d %H:%M}"))
        print(f"{name:28} {rule:28} match {c[0]}/{sum(c.values())}  {dict(c)}  by month {dict(sorted(per.items()))}")
        if name.startswith("Swiss") and rule == "clock date":
            print("   misses:", misses)
