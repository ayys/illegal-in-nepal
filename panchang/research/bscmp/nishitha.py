import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta
d = json.load(open("starts.json"))

def nishitha(day):  # middle of the night that ends on the morning of `day`
    return (surya.sunset(day - timedelta(days=1)) + surya.sunrise(day)) / 2

def start(sign, jd):
    day = surya.from_julian_day(jd).date()
    if sign == panchanga.KARKA:
        if jd < surya.sunrise(day): return day - timedelta(days=1)
        if jd > surya.sunset(day): return day
    if sign == panchanga.MAKARA:
        if jd > surya.sunset(day): return day + timedelta(days=1)
        if jd < surya.sunrise(day): return day
    # civil day runs from the night's midpoint before it to the one after
    for D in (day - timedelta(days=1), day, day + timedelta(days=1)):
        if nishitha(D) <= jd < nishitha(D + timedelta(days=1)): return D

def evaluate(key, lo, hi):
    ok = tot = 0; misses = []
    for y in range(lo, hi + 1):
        s, e = panchanga._gregorian_jd(y - 57, 4, 1), panchanga._gregorian_jd(y - 56, 4, 30)
        for i, (ended, jd) in enumerate(surya.crossings(surya.true_sun, 30, s, e)[:12]):
            want = date.fromisoformat(d[str(y)][key][i]); got = start((ended + 1) % 12, jd)
            tot += 1; ok += got == want
            if got != want: misses.append((y, i + 1, f"{surya.from_julian_day(jd):%m-%d %H:%M}", str(got), str(want)))
    return ok, tot, misses

for key, lo, hi in [("nd", 1975, 2083), ("pn", 2000, 2083), ("pn", 2084, 2099)]:
    ok, tot, misses = evaluate(key, lo, hi)
    print(f"{key} {lo}-{hi}: {ok}/{tot}", misses if len(misses) < 15 else len(misses))
