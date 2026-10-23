import json, sys
from datetime import date, timedelta
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import panchanga, surya
clean = json.load(open("clean.json"))
st = {}
for y in (2082, 2083):
    s = panchanga.month_starts(y)
    for m in range(12):
        for g in range((s[m+1]-s[m]).days): st[s[m]+timedelta(g)] = (m+1, g+1)
body, thr = sys.argv[1], float(sys.argv[2])
c = {date.fromisoformat(d): v for d, v in clean[body].items()}
out = []
for d in sorted(c):
    a, b = d - timedelta(1), d + timedelta(1)
    if a in c and b in c:
        s2 = (((c[b]-c[d]+180)%360-180) - ((c[d]-c[a]+180)%360-180)) * 3600
        if abs(s2) > thr: out.append(d)
prev = None
for d in out:
    tithi = int(surya.elongation(surya.sunrise(d)) // 12)
    print(d, "BS %d/%d" % st[d], "tithi", tithi + 1, "Δ%+d" % ((d - prev).days if prev else 0))
    prev = d
