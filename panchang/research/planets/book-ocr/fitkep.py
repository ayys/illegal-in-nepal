import sys, json, math, numpy as np
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from datetime import date
import kep
clean = json.load(open("clean.json"))
PL = ["mars", "jupiter", "venus", "saturn"]
# parameters: per body (incl. earth): dL, de, dperi (deg)  + global ayanamsha shift
names = [(b, k) for b in ["earth", "mars", "mercury", "jupiter", "venus", "saturn"] for k in ("L", "e", "w")]
def model(p, body, jd):
    base = {b: [list(x) for x in kep.EL[b]] for b in kep.EL}
    for (b, k), v in zip(names, p):
        if b == "all": continue
        i = {"L": 3, "e": 1, "w": 4}[k]
        base[b][0][i] += v if k != "e" else v / 100
        if k == "w": base[b][0][3] += 0  # L independent
    saved = kep.EL; kep.EL = {b: (tuple(v[0]), tuple(v[1])) for b, v in base.items()}
    t = (jd - 2451545) / 36525
    ex, ey, _ = kep.helio("earth", t); px, py, _ = kep.helio(body, t)
    kep.EL = saved
    return (math.degrees(math.atan2(py - ey, px - ex)) - 23.857092 ) % 360
obs = [(b, surya.sunrise(date.fromisoformat(d)), v) for b in PL for d, v in clean[b].items()]
def resid(p): return np.array([((v - model(p, b, jd) + 180) % 360 - 180) * 60 for b, jd, v in obs])
p = np.zeros(len(names))
for it in range(12):
    r = resid(p); J = np.zeros((len(r), len(p)))
    for j in range(len(p)):
        q = p.copy(); q[j] += 1e-4; J[:, j] = (resid(q) - r) / 1e-4
    w = 1 / np.maximum(1, abs(r) / 3)   # Huber-ish: down-weight >3′ misses (OCR slips)
    step, *_ = np.linalg.lstsq(J * w[:, None], -r * w, rcond=None); p += step
    print(it, "rms'", round(float(np.sqrt((r ** 2).mean())), 3))
r = resid(p)
for b in PL:
    rb = np.array([x for (bb, _, _), x in zip(obs, r) if bb == b])
    print(b, "rms′", round(float(np.sqrt((rb ** 2).mean())), 2), "max′", round(float(abs(rb).max()), 2))
for n, v in zip(names, p): print(n, round(float(v), 4))
json.dump(list(p), open("fitkep.json", "w"))
