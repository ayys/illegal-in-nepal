import json, math, itertools
cons = json.load(open("cons.json"))
def slack(c): return (c[3] - c[4]) * 1440
past = [c for c in cons if c[0] <= 2083]
future = [c for c in cons if c[0] >= 2084]
def evaluate(a, p, q, b, rows):
    bad = 0; margin = 1e9
    for y, m, sign, jd, bnd, need in rows:
        lam = math.radians(sign * 30)
        delta = a + p * math.sin(lam) + q * math.cos(lam) + b * (y - 2040)
        m_ = (slack([0,0,0,jd,bnd]) + delta) * need
        if m_ <= 0: bad += 1
        margin = min(margin, m_)
    return bad, margin
if __name__ == "__main__":
  best = []
  rng = [x / 2 for x in range(-60, 61)]
  for a, p, q in itertools.product(rng, rng, rng):
      bad, margin = evaluate(a, p, q, 0, past)
      if bad == 0: best.append((margin, a, p, q))
  best.sort(reverse=True)
  print("feasible sinusoid fits for 2000-2083:", len(best))
  for margin, a, p, q in best[:5]:
      print(f"  a {a:+5.1f}  p(sin) {p:+5.1f}  q(cos) {q:+5.1f} min  margin {margin:.1f} min  future misses {evaluate(a,p,q,0,future)[0]}")
  