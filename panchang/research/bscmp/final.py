import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import panchanga
from collections import Counter
d = json.load(open("starts.json"))
for key, lo, hi in [("nd", 1975, 2083), ("pn", 2000, 2083), ("pn", 2084, 2099), ("nd", 2084, 2100)]:
    n = tot = 0
    for y in range(lo, hi + 1):
        ours = [x.isoformat() for x in panchanga.month_starts(y)[:12]]
        n += sum(a == b for a, b in zip(ours, d[str(y)][key])); tot += 12
    print(f"{key} BS {lo}-{hi}: {n}/{tot}")
