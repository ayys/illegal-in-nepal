import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import swisseph as swe, surya, panchanga
from datetime import date, datetime, timedelta, time, timezone
swe.set_sid_mode(swe.SIDM_LAHIRI)
d = json.load(open("starts.json"))
def drik_sun(jd): return swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL | swe.FLG_SWIEPH)[0][0]

def crossing(fn, target, jd0):
    lo = jd0
    while ((fn(lo + 1) - target + 180) % 360 - 180) < 0: lo += 1
    hi = lo + 1
    for _ in range(40):
        mid = (lo + hi) / 2
        if ((fn(mid) - target + 180) % 360 - 180) < 0: lo = mid
        else: hi = mid
    return hi

# check against Drik's published moments
for name, sign, y, m, dd, want in [("kumbha", 10, 2017, 2, 12, "21:06"), ("meena", 11, 2010, 3, 14, "22:47"),
                                    ("karka", 3, 1967, 7, 16, "21:00 (+5:30)"), ("dhanu", 8, 2019, 12, 16, "15:58")]:
    jd = crossing(drik_sun, sign * 30.0, surya.julian_day(datetime(y, m, dd - 3, tzinfo=surya.NST)))
    print(f"{name} {y}: swe {surya.civil_time(jd):%Y-%m-%d %H:%M}  drik site {want}")

ss_ok = drik_ok = 0
rows = []
for y in range(1975, 2084):
    s_ok = k_ok = 0
    for i in range(12):
        sign = i
        table = date.fromisoformat(d[str(y)]["nd"][i])
        guess = surya.julian_day(datetime.combine(table - timedelta(days=4), time(), surya.NST))
        jd_d = crossing(drik_sun, sign * 30.0, guess)
        drik_day = panchanga._month_start(sign, jd_d)
        ss_day = panchanga.month_starts(y)[i]
        s_ok += ss_day == table; k_ok += drik_day == table
    rows.append((y, s_ok, k_ok))
print("\nyears where the modern Sun fits the table at least as well as SS:")
for y, s, k in rows:
    if k >= s: print(f"  BS {y}: SS {s}/12, modern {k}/12")
print("totals: SS", sum(r[1] for r in rows), " modern", sum(r[2] for r in rows), "of", 12 * len(rows))
