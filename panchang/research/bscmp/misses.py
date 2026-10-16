import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, datetime, timedelta, time
from collections import Counter
d = json.load(open("starts.json"))
NST = surya.NST

def sk(table, m):
    jd = surya.julian_day(datetime.combine(table - timedelta(days=4), time(), NST))
    return surya._solve(surya.true_sun, (m - 1) * 30.0, jd)

cases = []
for y in range(1975, 2084):
    for m in range(1, 13):
        table = date.fromisoformat(d[str(y)]["nd"][m - 1])
        cases.append((y, m, table, sk(table, m)))

def start(jd, m, shift_min=0.0, tz_hours=5.75):
    jd = jd + shift_min / 1440
    t = surya.from_julian_day(jd).astimezone(surya.timezone(timedelta(hours=tz_hours)))
    day = t.date()
    if m == 4 and jd < surya.sunrise(day): return day - timedelta(days=1)
    if m == 10 and jd > surya.sunset(day): return day + timedelta(days=1)
    return day

print("misses with current rule:")
for y, m, table, jd in cases:
    s = start(jd, m)
    if s != table:
        t = surya.from_julian_day(jd).astimezone(NST)
        both = d[str(y)]["pn"] and d[str(y)]["pn"][m - 1] == d[str(y)]["nd"][m - 1]
        print(f"  BS {y}/{m:2}  sankranti {t:%Y-%m-%d %H:%M}  ours {s}  table {table}  {'(both tables agree)' if both else '(pre-2000: nd only)' if not d[str(y)]['pn'] else ''}")

def score(**kw): return sum(start(jd, m, **kw) == table for y, m, table, jd in cases)
print("\nconstant shift of sankranti time (min):")
for s in range(-40, 41, 5): print(f"  {s:+3d}: {score(shift_min=s)}")
print("\nNepal time UTC+5:30 before 1986 (BS < 2043):",
      sum(start(jd, m, tz_hours=5.5 if (y < 2043) else 5.75) == table for y, m, table, jd in cases))
