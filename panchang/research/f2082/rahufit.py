import sys
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from datetime import date
def deg(s): a, b, c, d = map(int, s.split(":")); return a * 30 + b + c / 60 + d / 3600
pts = [(date(2025, 4, 28), "11:1:4:31"), (date(2025, 4, 29), "11:1:1:21"), (date(2025, 4, 30), "11:0:58:10"),
       (date(2026, 1, 4), "10:17:46:26"), (date(2026, 1, 6), "10:17:40:4"), (date(2026, 1, 9), "10:17:30:32"),
       (date(2027, 1, 8), "9:28:13:9"), (date(2027, 1, 10), "9:28:6:48"), (date(2027, 1, 12), "9:28:0:26")]
xs, ys = [], []
for d, v in pts:
    r = surya.sunrise(d)
    xs.append(r); ys.append(((surya.rahu(r) - deg(v) + 180) % 360 - 180) * 3600)
    print(d, f"{ys[-1]:+6.1f}\"")
n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
print(f"linear trend {b*365.25:+.1f}\"/yr; residuals",
      [round(y - my - b * (x - mx), 1) for x, y in zip(xs, ys)])
ss = 232238 * 360 / 1577917828
modern = (1934.136261 / 36525) + (5029.0966 / 3600 / 36525)
print(f"SS sidereal node rate {ss:.8f}°/d, modern-minus-Lahiri {modern:.8f}°/d, diff {(modern-ss)*3600*365.25:+.1f}\"/yr")
