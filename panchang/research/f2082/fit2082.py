import sys
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta
from collections import Counter

BOOK = {  # Jan 4..18 2026: tithi, nakshatra, yoga
 4: ("14:22", "17:33", ("7:31", "28:54")), 5: ("12:46", "16:40", "26:34"), 6: ("11:33", "16:9", "24:33"),
 7: ("10:46", "16:5", "22:54"), 8: ("10:27", "16:28", "21:38"), 9: ("10:40", "17:22", "20:46"),
 10: ("11:23", "18:45", "20:17"), 11: ("12:36", "20:36", "20:10"), 12: ("14:15", "22:49", "20:20"),
 13: ("16:13", "25:19", "20:45"), 14: ("18:22", "27:56", "21:16"), 15: ("20:33", "30:30", "21:47"),
 16: ("22:33", None, "22:10"), 17: ("24:15", "8:51", "22:20"), 18: ("25:31", "10:52", "22:11"),
}
SPASHTA = {  # sun, moon, rahu, belantar
 4: ("8:19:9:35", "2:27:9:13", "10:17:46:26", "+5:1"), 5: ("8:20:11:2", "3:11:5:13", "10:17:43:15", "+5:29"),
 6: ("8:21:12:28", "3:24:48:19", "10:17:40:4", "+5:57"), 7: ("8:22:13:53", "4:8:16:58", "10:17:36:54", "+6:24"),
 8: ("8:23:15:19", "4:21:30:5", "10:17:33:43", "+6:51"), 9: ("8:24:16:43", "5:4:27:45", "10:17:30:32", "+7:17"),
}
def mins(s): h, m = s.split(":"); return int(h) * 60 + int(m)
def deg(s): a, b, c, d = map(int, s.split(":")); return a * 30 + b + c / 60 + d / 3600
def want(v): return [] if v is None else [mins(x) for x in ((v,) if isinstance(v, str) else v)]

def limb_score(shift):
    surya.MOON_APOGEE_CORRECTION = shift
    hist = Counter(); bad = 0
    for d, ends in BOOK.items():
        row = panchanga.day_row(date(2026, 1, d), 8, 1)
        for limb, v in zip(("tithi", "nakshatra", "yoga"), ends):
            got = [h * 60 + m for h, m in (e["clock"] for e in row[limb]["ends"])]
            w = want(v)
            if len(got) != len(w): bad += 1; continue
            for g, x in zip(got, w): hist[g - x] += 1
    return hist, bad

print("apogee correction scan on 2082 (Jan 2026):")
for shift in [x / 100 for x in range(-200, -139, 5)]:
    hist, bad = limb_score(shift)
    n = sum(hist.values())
    print(f"  {shift:+.2f}  exact {hist[0]:2}/{n}  {dict(sorted(hist.items()))}  count-mismatch {bad}")

surya.MOON_APOGEE_CORRECTION = -1.7
print("\nspashta at sunrise with 2083 constants:")
for d, (sun, moon, rahu, bel) in SPASHTA.items():
    day = date(2026, 1, d); r = surya.sunrise(day)
    m_, s_ = bel[1:].split(":")
    print(f"  Jan {d}: sun {(surya.true_sun(r) - deg(sun)) * 3600:+5.1f}\"  moon {(surya.true_moon(r) - deg(moon)) * 3600:+6.1f}\""
          f"  rahu {(surya.rahu(r) - deg(rahu)) * 3600:+6.1f}\"  belantar {surya.equation_of_time(day) * 60 - (int(m_) * 60 + int(s_)):+5.1f}s")
