import sys, json, statistics
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import swisseph as swe, surya
from align import load, diffm
swe.set_sid_mode(swe.SIDM_LAHIRI)
B = {"mars": swe.MARS, "mercury": swe.MERCURY, "jupiter": swe.JUPITER, "venus": swe.VENUS, "saturn": swe.SATURN}
data = {**load("b82", 2082), **load("b83", 2083)}
days = sorted(data)
res = {b: {} for b in B}; sw = {b: {} for b in B}
for d in days:
    jd = surya.sunrise(d)
    for b, k in B.items():
        x = swe.calc(jd + swe.deltat(jd), k, swe.FLG_SIDEREAL | swe.FLG_SPEED)[0]
        sw[b][d] = (x[0], x[3])
        if data[d][b] is not None: res[b][d] = diffm(data[d][b], x[0])
clean = {}
for b in B:
    r = res[b]; ks = sorted(r); keep = {}
    for i, d in enumerate(ks):
        nb = [r[k] for k in ks[max(0, i-3):i+4] if k != d]
        if nb and abs(r[d] - statistics.median(nb)) < 3: keep[d] = data[d][b]
    clean[b] = keep
    print(b, len(r), "->", len(keep))
json.dump({b: {d.isoformat(): v for d, v in c.items()} for b, c in clean.items()}, open("clean.json", "w"), indent=0)
for b in B:
    print(f"\n{b}: book − Swiss (arcmin), every ~10 days, with Swiss speed '/d")
    ks = sorted(clean[b])
    print("  " + "  ".join(f"{d.strftime('%y%m%d')} {res[b][d]:+.0f}({sw[b][d][1]*60:+.0f})" for d in ks[::10]))
