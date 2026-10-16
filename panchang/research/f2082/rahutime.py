import sys, math
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from rahufit import pts, deg
from datetime import date
def spread(fn):
    ys = [((fn(d) - deg(v) + 180) % 360 - 180) * 3600 for d, v in pts]
    m = sum(ys) / len(ys)
    return max(abs(y - m) for y in ys), m, [round(y - m, 1) for y in ys]
print("at sunrise:", spread(lambda d: surya.rahu(surya.sunrise(d)))[:2])
for label, hours in [("00:00 NST", 0), ("05:45 NST (0h UT)", 5.75), ("06:00 NST", 6), ("Kathmandu mean 6:00 LMT", 6 - (85.3167/15 - 5.75)),
                     ("Ujjain 6:00 LMT", 6 + 5.75 - 75.7682/15), ("12:00 NST", 12)]:
    print(f"{label:24}", spread(lambda d, h=hours: surya.rahu(surya.local_julian_day(d, h))))
best = min((spread(lambda d, h=h/60: surya.rahu(surya.local_julian_day(d, h)))[0], h/60) for h in range(0, 24*60, 5))
print("best fixed NST hour", best)
