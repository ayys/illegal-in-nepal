import json, math, itertools
from fitsin import past, future, evaluate
res = []
rng = [x for x in range(-30, 31)]
for a, p, q in itertools.product(rng, rng, rng):
    bad, margin = evaluate(a, p, q, 0, past)
    res.append((bad, -margin, a, p, q))
res.sort()
print("fewest past misses:", res[:5])
bad, _, a, p, q = res[0]
for y, m, sign, jd, bnd, need in past:
    lam = math.radians(sign * 30); d = a + p*math.sin(lam) + q*math.cos(lam)
    if ((jd - bnd) * 1440 + d) * need <= 0: print("  still miss", y, m)
