import sys, json, math
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta
d = json.load(open("starts.json"))

def nearest_boundary(sign, jd):
    """(minutes from the deciding boundary, +1 if 'after' means later day)."""
    day = surya.civil_time(jd).date()
    cands = []
    for D in (day - timedelta(days=1), day, day + timedelta(days=1)):
        off = surya.civil_time(surya.local_julian_day(D, 12)).utcoffset().total_seconds() / 3600
        if sign == panchanga.KARKA: b = surya.sunrise(D)
        elif sign == panchanga.MAKARA: b = surya.sunset(D)
        else: b = surya.local_julian_day(D, 5.75 - off)
        cands.append(b)
    b = min(cands, key=lambda b: abs(b - jd))
    return (jd - b) * 1440

rows = []
for y in range(1975, 2074):
    s, e = panchanga._gregorian_jd(y - 57, 4, 1), panchanga._gregorian_jd(y - 56, 4, 30)
    for i, (ended, jd) in enumerate(surya.crossings(surya.true_sun, 30, s, e)[:12]):
        sign = (ended + 1) % 12
        slack = nearest_boundary(sign, jd)
        if abs(slack) > 90: continue
        ours = panchanga.month_starts(y)[i]
        table = date.fromisoformat(d[str(y)]["nd"][i])
        same = ours == table
        # if table agrees, the table's time is on the same side as ours; else opposite side
        side = (1 if slack > 0 else -1) * (1 if same else -1)
        rows.append((y, sign, slack, side))
print(len(rows), "months within 90 min of a boundary;", sum(1 for r in rows if (r[2] > 0) != (r[3] > 0)), "of them misses")

def feasible(p, q, b):
    lo, hi = -1e9, 1e9
    for y, sign, slack, side in rows:
        lam = math.radians(sign * 30)
        k = slack + p * math.sin(lam) + q * math.cos(lam) + b * (y - 2025) / 10
        # need (k + a) * side > 0
        if side > 0: lo = max(lo, -k)
        else: hi = min(hi, -k)
    return hi - lo, lo, hi

best = max(((feasible(p, q, b), p, q, b) for p in range(-40, 41, 2) for q in range(-40, 41, 2) for b in range(-20, 21, 2)),
           key=lambda r: r[0][0])
(gap, lo, hi), p, q, b = best
print(f"best: width {gap:.1f} min (positive = all months explained) with sin {p:+d}, cos {q:+d}, drift {b:+d} min/decade, offset in [{lo:.1f}, {hi:.1f}]")
# fewest misses for best smooth model
def misses(a, p, q, b):
    out = []
    for y, sign, slack, side in rows:
        lam = math.radians(sign * 30)
        if (slack + a + p * math.sin(lam) + q * math.cos(lam) + b * (y - 2025) / 10) * side <= 0: out.append((y, sign))
    return out
fewest = min(((len(misses(a, p, q, b)), a, p, q, b) for a in range(-30, 31, 3) for p in range(-30, 31, 3)
              for q in range(-30, 31, 3) for b in range(-15, 16, 3)), key=lambda r: r[0])
print("fewest misses with any smooth correction:", fewest[0], "with offset/sin/cos/drift", fewest[1:], "(no correction: 8)")
