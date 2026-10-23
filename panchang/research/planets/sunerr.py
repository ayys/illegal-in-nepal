"""Book's Sun error vs the Sun's मन्दकेन्द्र, estimated from each planet."""
import sys, statistics; sys.path.insert(0, "../.."); import surya, ketaki, ahargana
from datetime import date
from vsbook import clean, diff
ketaki.mean = ahargana.make_mean("cycles")
def sun_kendra(jd): return (ketaki.mean("sun", jd) - ketaki.apogee("sun", jd)) % 360
def estimate(bodies, width=10):
    base = ketaki.MEAN0["sun"]; bins = {}
    for b in bodies:
        for d, v in clean[b].items():
            jd = surya.sunrise(date.fromisoformat(d))
            g0 = ketaki.geocentric(b, jd)
            ketaki.MEAN0["sun"] = base + 30 / 3600; g1 = ketaki.geocentric(b, jd); ketaki.MEAN0["sun"] = base
            s = diff(g1, g0) / 30
            r = diff(v, g0)
            if abs(r) > 600 or abs(s) < 0.5: continue
            bins.setdefault((b, int(sun_kendra(jd) // width) * width), []).append(r / s)
    return bins
if __name__ == "__main__":
    bins = estimate(("mercury", "venus", "mars"))
    for k in range(0, 360, 10):
        print(f"k {k:3d}", "  ".join(f"{b[:4]} {statistics.median(bins[(b, k)]):+5.0f}({len(bins[(b, k)]):2d})" if (b, k) in bins else f"{b[:4]}    --    " for b in ("mercury", "venus", "mars")))
