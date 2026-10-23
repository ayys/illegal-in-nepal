import sys, statistics; sys.path.insert(0, "../.."); import surya, ketaki, ahargana
from datetime import date
from vsbook import clean, diff
ketaki.mean = ahargana.make_mean("cycles")
def by_kendra(b, which="shighra", width=5, cap=600):
    bins = {}
    for d, v in clean[b].items():
        jd = surya.sunrise(date.fromisoformat(d))
        r = diff(v, ketaki.geocentric(b, jd))
        if abs(r) > cap: continue
        h, ph, k = ketaki.heliocentric(b, jd)
        key = (h - ketaki.true_sun(jd)) % 360 if which == "shighra" else k
        bins.setdefault(int(key // width) * width, []).append(r)
    return {k: (statistics.median(v), len(v)) for k, v in sorted(bins.items())}
if __name__ == "__main__":
    for b in sys.argv[1:]:
        for which in ("shighra", "manda"):
            print(b, which, " ".join(f"{k}:{m:+.0f}" for k, (m, n) in by_kendra(b, which, 10).items()))
