"""Turn OCR rows into {date: {planet: degrees}} using the Moon column to find each row's day."""
import json, re, sys
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta
COLS = ["moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu"]
def parse(t):
    m = re.fullmatch(r"\D*(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2})\D*", t or "")
    if not m: return None
    s, d, mi, se = map(int, m.groups())
    if s > 11 or d > 29 or mi > 59 or se > 59: return None
    return s * 30 + d + mi / 60 + se / 3600
def diffm(a, b): return ((a - b + 180) % 360 - 180) * 60
def load(book, bs):
    raw = json.load(open(f"ocr-{book}.json"))
    starts = panchanga.month_starts(bs)
    days = [starts[0] + timedelta(i) for i in range((starts[12] - starts[0]).days)]
    moons = {d: surya.true_moon(surya.sunrise(d)) for d in days}
    out = {}
    for p, rows in raw.items():
        if not isinstance(rows, list): continue
        votes = {}
        for row in rows:
            for i, c in enumerate(row):
                if re.fullmatch(r"[-+]*\d{1,2}:\d{1,2}", c or "") and i >= 7:
                    votes[i] = votes.get(i, 0) + 1
        if not votes: continue
        bel = max(votes, key=votes.get)
        for row in rows:
            vals = [parse(c) for c in row[bel - 7:bel]]
            if vals[0] is None: continue
            best = min(days, key=lambda d: abs(diffm(vals[0], moons[d])))
            if abs(diffm(vals[0], moons[best])) > 20: continue
            out[best] = dict(zip(COLS, vals))
    return out
if __name__ == "__main__":
    for book, bs in (("b83", 2083), ("b82", 2082)):
        o = load(book, bs)
        n = len(o); good = {c: sum(1 for v in o.values() if v[c] is not None) for c in COLS[1:]}
        print(book, n, "days;", good)
