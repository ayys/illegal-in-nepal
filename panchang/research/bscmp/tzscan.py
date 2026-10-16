from misses import cases, start, d, surya, NST
from datetime import datetime
def tz(y, jd):
    t = surya.from_julian_day(jd)
    if t < datetime(1920, 1, 1, tzinfo=NST): return 85.3167 / 15
    if t < datetime(1986, 1, 1, tzinfo=NST): return 5.5
    return 5.75
best = []
for s in range(-30, 16, 1):
    n = sum(start(jd, m, shift_min=s, tz_hours=tz(y, jd)) == table for y, m, table, jd in cases)
    best.append((n, s))
best.sort(reverse=True); print("tz history + shift: top", best[:6])
n, s = best[0]
for y, m, table, jd in cases:
    got = start(jd, m, shift_min=s, tz_hours=tz(y, jd))
    if got != table:
        t = surya.from_julian_day(jd).astimezone(surya.timezone(surya.timedelta(hours=tz(y, jd))))
        print(f"  BS {y}/{m:2}  local {t:%Y-%m-%d %H:%M} (UTC{tz(y, jd):+.2f})  ours {got}  table {table}")
