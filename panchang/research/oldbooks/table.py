from shift import cache, start
import math
TABLE = [-0.58, -2.48, -2.05, -2.93, -1.95, -1.25, -0.95, 0.30, 0.47, 1.10, 0.07, -0.22]
cosm = lambda i: -0.55 + 1.0 * math.cos(math.radians(30 * i - 270))
for lo, hi in [(2000, 2023), (2024, 2030), (2031, 2035), (2036, 2040), (2041, 2045)]:
    items = [(y, *c) for y in range(lo, hi + 1) for c in cache[y]]
    t = [(y, i) for y, i, g, d, dm, w in items if start(i, g, d, dm, TABLE[i]) != w]
    c = [(y, i) for y, i, g, d, dm, w in items if start(i, g, d, dm, cosm(i)) != w]
    print(lo, hi, len(items), "table misses", t, "cos misses", c)
