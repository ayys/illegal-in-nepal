import math, sys
from shift import cache, start
def fit(lo, hi):
    items = [c for y in range(lo, hi + 1) for c in cache[y]]
    best = (0,)
    for a in [k / 20 for k in range(-40, 11)]:
        for amp in [k / 10 for k in range(0, 31)]:
            for ph in range(0, 360, 10):
                n = sum(start(i, g, d, dm, a + amp * math.cos(math.radians(i * 30 - ph))) == w for i, g, d, dm, w in items)
                if n > best[0] or (n == best[0] and amp < best[2]): best = (n, a, amp, ph)
    return best, len(items)
for lo, hi in [(2024, 2045), (2024, 2035), (2036, 2045), (2030, 2045), (2024, 2040)]:
    print(lo, hi, *fit(lo, hi))
