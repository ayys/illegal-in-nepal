"""Hand-read Mercury against Ketaki variants, day by day."""
import csv, math, sys
from datetime import date
sys.path.insert(0, "../.."); sys.path.insert(0, ".")
import surya, ketaki
def deg(t):
    s, d, m, x = map(int, t.split(":")); return s * 30 + d + m / 60 + x / 3600
def diff(a, b): return ((a - b + 180) % 360 - 180) * 3600
rows = list(csv.DictReader(open("mercury/hand.csv")))
c = lambda x: math.cos(math.radians(x))
VARIANTS = {
    "unrounded": None,
    "round r": lambda b, k, p, rounded=False: round(39 + 8 * c(k + p / 2)),
}
if __name__ == "__main__":
    prev = {}
    orig = ketaki.distance
    for r in rows:
        d = date.fromisoformat(r["date"]); jd = surya.sunrise(d); v = deg(r["mercury"])
        out = []
        for name, f in VARIANTS.items():
            ketaki.distance = f or orig
            g = ketaki.geocentric("mercury", jd)
            step = diff(g, prev[name]) / 60 if name in prev else 0
            prev[name] = g
            out.append(f"{name} Δ{diff(v, g):+6.0f}″ step {step:5.1f}′")
        ketaki.distance = orig
        bstep = diff(v, prev["book"]) / 60 if "book" in prev else 0; prev["book"] = v
        h, ph, k = ketaki.heliocentric("mercury", jd); sk = (h - ketaki.true_sun(jd)) % 360
        print(r["date"], f"book step {bstep:5.1f}′ |", " | ".join(out), f"| मन्दk {k:5.1f} शीघ्रk {sk:5.1f}")
