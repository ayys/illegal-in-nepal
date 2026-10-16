import sys
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from datetime import date
def deg(s): a, b, c, d = map(int, s.split(":")); return a * 30 + b + c / 60 + d / 3600
pts = [(date(2025, 4, 28), "11:1:4:31"), (date(2025, 4, 29), "11:1:1:21"), (date(2025, 4, 30), "11:0:58:10"),
       (date(2026, 1, 4), "10:17:46:26"), (date(2026, 1, 6), "10:17:40:4"), (date(2026, 1, 9), "10:17:30:32"),
       (date(2027, 1, 8), "9:28:13:9"), (date(2027, 1, 10), "9:28:6:48"), (date(2027, 1, 12), "9:28:0:26")]
def res(h): return [((surya.rahu(surya.local_julian_day(d, h)) - deg(v) + 180) % 360 - 180) * 3600 for d, v in pts]
r0 = res(0); mean0 = sum(r0) / len(r0)
rate = (sum(res(1)) - sum(r0)) / len(r0)
print(f"no-offset residual at 00:00 NST {mean0:+.1f}\", {rate:+.2f}\"/h, zero at {-mean0/rate:.2f} h NST")
for label, h in [("Kathmandu mean noon", 12 + 5.75 - 85.3167 / 15), ("Ujjain mean noon", 12 + 5.75 - 75.7682 / 15),
                 ("Lanka/Ujjain 6:00 LMT", 6 + 5.75 - 75.7682 / 15), ("NST noon", 12), ("05:45 NST (0h UT)", 5.75)]:
    r = res(h); print(f"{label:22} {h:5.2f} h  mean {sum(r)/len(r):+6.1f}\"  max {max(map(abs, r)):.1f}\"")
