import sys, statistics, math; sys.path.insert(0, "../.."); import surya, ketaki, ahargana
from datetime import date
import numpy as np
from vsbook import clean, diff
from sunerr import sun_kendra
ketaki.mean = ahargana.make_mean("cycles")
def daily_sun_error(bodies=("mercury", "venus")):
    base = ketaki.MEAN0["sun"]; per_day = {}
    for b in bodies:
        for d, v in clean[b].items():
            jd = surya.sunrise(date.fromisoformat(d))
            g0 = ketaki.geocentric(b, jd)
            ketaki.MEAN0["sun"] = base + 30 / 3600; g1 = ketaki.geocentric(b, jd); ketaki.MEAN0["sun"] = base
            s = diff(g1, g0) / 30; r = diff(v, g0)
            if abs(r) < 600 and abs(s) > 0.5: per_day.setdefault(d, []).append(r / s)
    return sorted((d, statistics.mean(v)) for d, v in per_day.items())
if __name__ == "__main__":
    pts = daily_sun_error()
    K = np.array([math.radians(sun_kendra(surya.sunrise(date.fromisoformat(d)))) for d, _ in pts]); Y = np.array([y for _, y in pts])
    cols = [np.ones_like(K)] + [f(n * K) for n in (1, 2, 3) for f in (np.cos, np.sin)]
    A = np.vstack(cols).T; c, *_ = np.linalg.lstsq(A, Y, rcond=None)
    names = ["c0"] + [f"{f}{n}k" for n in (1, 2, 3) for f in ("cos", "sin")]
    print("n", len(Y), "fit:", "  ".join(f"{n} {v:+.0f}″" for n, v in zip(names, c)), " rms", round(float(np.sqrt(((A @ c - Y) ** 2).mean()))), " raw rms", round(float(np.sqrt((Y**2).mean()))))
    for d, y in pts:
        k = sun_kendra(surya.sunrise(date.fromisoformat(d)))
        if 172 < k < 190 or k > 354 or k < 6: print(d, f"k {k:6.2f}  δ {y:+5.0f}″")
