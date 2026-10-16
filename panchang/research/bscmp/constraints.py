import sys, json, math
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta
d = json.load(open("starts.json"))

def boundaries(sign, jd):
    """Return (boundary_jd, day_if_before, day_if_after) nearest the sankranti."""
    day = surya.civil_time(jd).date()
    c = []
    for D in (day - timedelta(days=1), day, day + timedelta(days=1)):
        off = surya.civil_time(surya.local_julian_day(D, 12)).utcoffset().total_seconds() / 3600
        midnight = surya.local_julian_day(D, 5.75 - off)  # civil midnight starting D
        c.append((midnight, D - timedelta(days=1), D))
        if sign == panchanga.KARKA:
            c.append((surya.sunrise(D), D - timedelta(days=1), D))
        if sign == panchanga.MAKARA:
            c.append((surya.sunset(D), D, D + timedelta(days=1)))
    return c

cons = []  # (y, m, sign, jd, boundary, need) need=+1: table sankranti must be after boundary
for y in range(2000, 2100):
    s, e = panchanga._gregorian_jd(y - 57, 4, 1), panchanga._gregorian_jd(y - 56, 4, 30)
    for i, (ended, jd) in enumerate(surya.crossings(surya.true_sun, 30, s, e)[:12]):
        sign = (ended + 1) % 12
        table = date.fromisoformat(d[str(y)]["pn"][i])
        for b, before, after in boundaries(sign, jd):
            if abs(jd - b) * 1440 < 60 and table in (before, after):
                # Karka/Makara: midnight is not a boundary for them
                if sign in (panchanga.KARKA, panchanga.MAKARA) and before == after - timedelta(days=1) and \
                   ((sign == panchanga.KARKA and abs(b - surya.sunrise(after)) > 0.01) or
                    (sign == panchanga.MAKARA and abs(b - surya.sunset(before)) > 0.01)):
                    continue
                cons.append((y, i + 1, sign, jd, b, +1 if table == after else -1))
json.dump([list(c) for c in cons], open("cons.json", "w"))
for y, m, sign, jd, b, need in cons:
    slack = (jd - b) * 1440
    ok = (slack > 0) == (need > 0)
    print(f"BS {y}/{m:2} sign {sign:2}  ours {slack:+6.1f} min from boundary  table says {'after' if need>0 else 'before'}  {'ok' if ok else 'MISS'}")
