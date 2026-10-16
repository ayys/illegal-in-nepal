import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from datetime import date, datetime, timedelta, time
from collections import Counter
d = json.load(open("starts.json"))

def sankranti(guess, m):
    jd = surya.julian_day(datetime.combine(guess - timedelta(days=4), time(), surya.NST))
    return surya._solve(surya.true_sun, (m - 1) * 30.0, jd)

def civil(jd): return surya.from_julian_day(jd).astimezone(surya.NST).date()

def start(t, m, karka_makara=True, nishitha=True):
    D = civil(t)
    rise, set_ = surya.sunrise(D), surya.sunset(D)
    if karka_makara and m == 4 and t < rise: return D - timedelta(days=1)
    if karka_makara and m == 10 and t > set_: return D + timedelta(days=1)
    if nishitha:
        prev_set = surya.sunset(D - timedelta(days=1))
        if t < rise and t < (prev_set + rise) / 2: return D - timedelta(days=1)
        next_rise = surya.sunrise(D + timedelta(days=1))
        if t > set_ and t >= (set_ + next_rise) / 2: return D + timedelta(days=1)
    return D

cache = {}
for y in range(1975, 2101):
    for m in range(1, 13):
        table = date.fromisoformat(d[str(y)]["nd"][m - 1])
        cache[(y, m)] = (table, sankranti(table, m))

for label, kw in [("clock date (current)", dict(karka_makara=False, nishitha=False)),
                  ("nishitha only", dict(karka_makara=False)),
                  ("nishitha + Karka/Makara night rule", {})]:
    for lo, hi in [(1975, 2083), (2084, 2100)]:
        c = Counter(); misses = []
        for (y, m), (table, t) in cache.items():
            if not lo <= y <= hi: continue
            x = (start(t, m, **kw) - table).days; c[x] += 1
            if x: misses.append((y, m, x, f"{surya.from_julian_day(t).astimezone(surya.NST):%Y-%m-%d %H:%M}"))
        print(f"{label:36} BS {lo}-{hi}: {c[0]}/{sum(c.values())}")
        if "Karka" in label and lo == 1975: print("   remaining misses:", misses)
