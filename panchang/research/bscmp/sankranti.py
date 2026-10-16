import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from datetime import date, timedelta
from collections import Counter
d = json.load(open("starts.json")); bad = json.load(open("bad.json"))
print("2082:", "ours", d["2082"]["ours"][9], "nd", d["2082"]["nd"][9], "pn", d["2082"]["pn"][9])
print("2083 vs book (Baisakh Apr 14, Kartik Oct 18, Magh Jan 15):", d["2083"]["ours"][0], d["2083"]["ours"][6], d["2083"]["ours"][9])

def sankranti(month_start_guess, m):
    target = (m - 1) * 30.0
    start = surya.julian_day(__import__("datetime").datetime.combine(month_start_guess - timedelta(days=3), __import__("datetime").time(), surya.NST))
    jd = surya._solve(surya.true_sun, target, start)
    return surya.from_julian_day(jd).astimezone(surya.NST)

rows = []
for y in range(1975, 2084):
    for m in range(1, 13):
        ours = date.fromisoformat(d[str(y)]["ours"][m - 1]); table = date.fromisoformat(d[str(y)]["nd"][m - 1])
        t = sankranti(ours, m)
        rise = surya.from_julian_day(surya.sunrise(t.date())).astimezone(surya.NST)
        rows.append((y, m, (ours - table).days, t, rise))
print("\nmismatches <= 2083: (year, month, ours-table, sankranti NST, hours from midnight)")
for y, m, x, t, r in rows:
    if x:
        h = t.hour + t.minute / 60
        print(f"  {y} m{m:2} {x:+d}  {t:%Y-%m-%d %H:%M}  rise {r:%H:%M}")
# where do matched sankrantis fall?
print("\nmatched near-midnight cases (22:00–06:30):")
for y, m, x, t, r in rows:
    h = t.hour + t.minute / 60
    if not x and (h >= 22 or h < 6.5):
        print(f"  {y} m{m:2}  {t:%Y-%m-%d %H:%M}")
