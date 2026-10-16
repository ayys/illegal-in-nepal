import json
from datetime import date
from collections import Counter
d = json.load(open("starts.json"))
def diff(a, b): return (date.fromisoformat(a) - date.fromisoformat(b)).days
pn_years = [y for y in d if d[y]["pn"]]
print("py-nepali range:", pn_years[0], "-", pn_years[-1])
lib_disagree = [(y, m) for y in pn_years for m in range(12) if d[y]["nd"][m] != d[y]["pn"][m]]
print("tables disagree with each other on", len(lib_disagree), "month starts:", lib_disagree[:20])
by_decade = {}
bad = []
for y, v in d.items():
    for m in range(12):
        x = diff(v["ours"][m], v["nd"][m])
        dec = int(y) // 10 * 10
        c = by_decade.setdefault(dec, Counter()); c[x] += 1
        if x: bad.append((int(y), m + 1, x))
for dec, c in sorted(by_decade.items()):
    tot = sum(c.values())
    print(f"{dec}s: {c[0]:3}/{tot} match  {dict(sorted(c.items()))}")
print("mismatches by month:", sorted(Counter(m for _, m, _ in bad).items()))
print("mismatches 2070-2090:", [b for b in bad if 2070 <= b[0] <= 2090])
json.dump(bad, open("bad.json", "w"))
