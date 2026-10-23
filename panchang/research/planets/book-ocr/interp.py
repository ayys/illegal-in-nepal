"""Do the book's days follow interpolation between anchor days (गते 1, 12, 23)?"""
import json, sys
from datetime import date, timedelta
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import panchanga
clean = json.load(open("clean.json"))
def unwrap(a, ref): return ref + ((a - ref + 180) % 360 - 180)
anchors = []
for y in (2082, 2083):
    st = panchanga.month_starts(y)
    for m in range(12):
        for g in map(int, sys.argv[2].split(",")):
            anchors.append(st[m] + timedelta(g - 1))
anchors = sorted(set(a for a in anchors))
body = sys.argv[1]
c = {date.fromisoformat(d): v for d, v in clean[body].items()}
for mode in ("linear", "quad"):
    errs = []
    for i in range(len(anchors) - 2):
        a0, a1, a2 = anchors[i:i+3]
        if not all(a in c for a in (a0, a1, a2)): continue
        y0 = c[a0]; y1 = unwrap(c[a1], y0); y2 = unwrap(c[a2], y1)
        t1, t2 = (a1 - a0).days, (a2 - a0).days
        d = a0 + timedelta(1)
        while d < a1:
            if d in c:
                t = (d - a0).days
                if mode == "linear": p = y0 + (y1 - y0) * t / t1
                else:
                    p = (y0 * (t - t1) * (t - t2) / ((0 - t1) * (0 - t2)) + y1 * (t - 0) * (t - t2) / ((t1) * (t1 - t2))
                         + y2 * (t - 0) * (t - t1) / ((t2) * (t2 - t1)))
                errs.append((unwrap(c[d], p) - p) * 3600)
            d += timedelta(1)
    errs.sort(key=abs)
    n = len(errs)
    print(f"{body:8s} {mode:6s} n={n} median |err| {abs(errs[n//2]):.0f}″  90% {abs(errs[int(n*.9)]):.0f}″")
