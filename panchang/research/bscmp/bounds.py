from rule import cache, civil, surya
from datetime import timedelta
groups = {"Karka (m4)": [4], "Makara (m10)": [10], "others": [1, 2, 3, 5, 6, 7, 8, 9, 11, 12]}
for name, ms in groups.items():
    pts = []
    for (y, m), (table, t) in cache.items():
        if m not in ms or y > 2083: continue
        local = surya.from_julian_day(t).astimezone(surya.NST)
        h = local.hour + local.minute / 60 + local.second / 3600
        pts.append((h, (table - civil(t)).days, y))
    pts.sort()
    # print transitions
    print(name)
    prev = None
    for h, off, y in pts:
        if off != prev:
            print(f"   from {int(h):02d}:{(h%1)*60:04.1f}  table = clock date {off:+d}   (BS {y})")
            prev = off
