import json
from datetime import date
from collections import Counter
from rule import cache, start
d = json.load(open("starts.json"))
c = Counter()
for (y, m), (table, t) in cache.items():
    if y < 2084 or not d[str(y)]["pn"]: continue
    ours = start(t, m)
    nd = date.fromisoformat(d[str(y)]["nd"][m - 1]); pn = date.fromisoformat(d[str(y)]["pn"][m - 1])
    c[("ours=nd" if ours == nd else "ours≠nd", "ours=pn" if ours == pn else "ours≠pn", "nd=pn" if nd == pn else "nd≠pn")] += 1
for k, v in sorted(c.items(), key=lambda x: -x[1]): print(v, k)
for lo, hi in [(2000, 2083), (2084, 2099)]:
    n = sum(1 for (y, m), (tb, t) in cache.items() if lo <= y <= hi and d[str(y)]["pn"] and start(t, m) == date.fromisoformat(d[str(y)]["pn"][m-1]))
    print(f"ours vs py-nepali BS {lo}-{hi}: {n}/{(hi-lo+1)*12}")
