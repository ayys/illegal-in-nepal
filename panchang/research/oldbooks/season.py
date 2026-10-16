import math, sys
from shift import cache, start
lo, hi = int(sys.argv[1]), int(sys.argv[2])
items = [(y, *c) for y in range(lo, hi + 1) for c in cache[y]]
best = []
for a in [k / 20 for k in range(-30, 11)]:
    for amp in [k / 10 for k in range(0, 31)]:
        for ph in range(0, 360, 15):
            n = sum(start(i, g, d, dm, a + amp * math.cos(math.radians(i * 30 - ph))) == w for y, i, g, d, dm, w in items)
            best.append((n, -amp, a, ph))
best.sort(reverse=True)
print(lo, hi, len(items))
for n, amp, a, ph in best[:8]:
    print(f"  {n}/{len(items)}  a={a:+.2f}  amp={-amp:.1f}  peak at sign {ph}°")
