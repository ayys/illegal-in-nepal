import json, sys
from datetime import date, timedelta
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import panchanga
clean = json.load(open("clean.json"))
body = sys.argv[1]
c = {date.fromisoformat(d): v for d, v in clean[body].items()}
starts = set(panchanga.month_starts(2082)[:13] + panchanga.month_starts(2083)[:13])
prev = None
for d in sorted(c):
    if d - timedelta(1) in c:
        sp = ((c[d] - c[d - timedelta(1)] + 180) % 360 - 180) * 3600
        mark = " <- month start" if d in starts else ""
        jump = "" if prev is None else f"  Δ {sp - prev:+6.0f}"
        if prev is not None and abs(sp - prev) > float(sys.argv[2]) or mark:
            print(d, f"{sp:+8.0f}″/d{jump}{mark}")
        prev = sp
    else:
        prev = None
