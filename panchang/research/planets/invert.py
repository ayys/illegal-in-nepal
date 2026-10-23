"""From each book value, solve for the heliocentric longitude the book used,
and so the मन्दफल it implies; compare with Ketaki's table."""
import sys, math, statistics
from datetime import date
sys.path.insert(0, "../.."); import surya, ketaki
from vsbook import clean, diff

def geo_from_helio(body, helio, jd, k_manda, phala):
    sun = ketaki.true_sun(jd)
    sk = (helio - sun) % 360
    value, sign = ketaki.table(ketaki.SHIGHRA[body], sk, 0.1)
    if body == "mars":
        r = ketaki.distance(body, k_manda, phala, rounded=False)
        karna = 100 + ketaki.MEAN_DISTANCE[body] - ketaki.table(ketaki.KARNANKA[body], sk, 1)[0]
        value = value * karna / (r + karna - ketaki.MEAN_DISTANCE[body])
    elif body == "mercury":
        value = value * ketaki.distance(body, k_manda, phala, rounded=False) / ketaki.MEAN_DISTANCE[body]
    return (sun + sign * value) % 360 if body in ("mercury", "venus") else (helio - sign * value) % 360

def implied(body, d, v):
    jd = surya.sunrise(date.fromisoformat(d))
    h0, phala, k = ketaki.heliocentric(body, jd, short=False)
    mean = (h0 - phala) % 360
    h = h0
    for _ in range(30):   # secant on helio
        g = diff(v, geo_from_helio(body, h, jd, k, phala)) / 3600
        g2 = diff(v, geo_from_helio(body, h + 0.01, jd, k, phala)) / 3600
        if abs(g2 - g) < 1e-12: break
        h -= g * 0.01 / (g2 - g)
        if abs(g) < 1e-7: break
    return k, ((h - mean + 180) % 360 - 180), phala

if __name__ == "__main__":
    body = sys.argv[1]
    bins = {}
    for d, v in clean[body].items():
        k, imp, ours = implied(body, d, v)
        bins.setdefault(round(k / 2) * 2, []).append((imp, ours))
    for k in sorted(bins):
        imp = statistics.median(x[0] for x in bins[k]); ours = statistics.median(x[1] for x in bins[k])
        print(f"k {k:3d}  book मन्दफल {imp:+8.4f}°  ours {ours:+8.4f}°  Δ {(imp-ours)*3600:+6.0f}″  n={len(bins[k])}")
