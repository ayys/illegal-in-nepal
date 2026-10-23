import sys, statistics; sys.path.insert(0, "../.."); import surya, ketaki, ahargana
from datetime import date
from vsbook import clean, diff
ketaki.mean = ahargana.make_mean("cycles")
def helio_errors(b):
    base = ketaki.MEAN0[b]; out = []
    for d, v in clean[b].items():
        jd = surya.sunrise(date.fromisoformat(d))
        g0 = ketaki.geocentric(b, jd)
        ketaki.MEAN0[b] = base + 60 / 3600; g1 = ketaki.geocentric(b, jd); ketaki.MEAN0[b] = base
        sens = diff(g1, g0) / 60; r = diff(v, g0)
        if abs(sens) < 0.3 or abs(r) > 600: continue
        h, ph, k = ketaki.heliocentric(b, jd)
        out.append((d, k, r / sens))
    return out
if __name__ == "__main__":
    b = sys.argv[1]
    bins = {}
    for d, k, e in helio_errors(b): bins.setdefault(int(k // 10) * 10, []).append(e)
    print(b, "heliocentric error by मन्दकेन्द्र:", " ".join(f"{k}:{statistics.median(v):+.0f}({len(v)})" for k, v in sorted(bins.items())))
