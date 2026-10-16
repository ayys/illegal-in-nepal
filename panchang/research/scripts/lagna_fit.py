import math, surya, itertools
from datetime import date
def ascendant_factory(ayan_lagna, obl, lat):
    def asc(jd):
        shift = surya.ayanamsha(jd)
        lam = math.radians(surya.norm(surya.true_sun(jd) + shift)); e = math.radians(surya.OBLIQUITY)
        ra = math.degrees(math.atan2(math.cos(e)*math.sin(lam), math.cos(lam)))
        eot = ((surya.norm(surya.mean_sun(jd) + shift - ra) + 180) % 360 - 180) * 4
        local = (jd - surya.local_julian_day(date(2027,1,1), 0)) * 1440
        noon_offset = -eot + (86.25 - surya.LONGITUDE) * 4
        H = ((local - noon_offset - 720) % 1440) / 4
        ramc = math.radians(ra + H)
        eo = math.radians(obl); phi = math.radians(lat)
        a = math.degrees(math.atan2(math.cos(ramc), -(math.sin(ramc)*math.cos(eo) + math.tan(phi)*math.sin(eo))))
        a_ = ayan_lagna(jd) if callable(ayan_lagna) else ayan_lagna
        return surya.norm(a - a_)
    return asc
book = {  # Jan 8..12 starts: makara kumbha meena mesha vrisha mithuna karka simha kanya tula vrischika dhanu(next morning)
 date(2027,1,8): "7:25 9:8 10:36 12:2 13:38 15:34 17:49 20:9 22:25 24:40 26:59 29:17",
 date(2027,1,9): "7:21 9:4 10:32 11:58 13:34 15:30 17:45 20:5 22:21 24:36 26:55 29:13",
 date(2027,1,12): "7:9 8:52 10:20 11:46 13:22 15:19 17:33 19:53 22:9 24:25 26:43 29:1",
}
def mins(s): h, m = s.split(":"); return int(h)*60+int(m)
def run(ayan, obl, lat, show=False):
    f = ascendant_factory(ayan, obl, lat); err = []
    for d, s in book.items():
        want = [mins(x) for x in s.split()]
        start = surya.local_julian_day(d, 6.5)
        got = []
        for idx, jd in surya.crossings(f, 30, start, start + 1):
            got.append((jd - surya.local_julian_day(d, 0)) * 1440)
        got = got[:12]
        err += [g - w for g, w in zip(got, want)]
        if show: print(d, " ".join(f"{g-w:+.1f}" for g, w in zip(got, want)))
    return (sum(e*e for e in err)/len(err))**.5, sum(err)/len(err)
res = []
for ay, obl, lat in itertools.product(["ss", 23.0, 23.5, 24.0, 24.2, 24.5, 25.0], [24.0, 23.44], [27.7]):
    a = (lambda jd: surya.ayanamsha(jd)) if ay == "ss" else ay
    rms, mean = run(a, obl, lat)
    res.append((rms, mean, ay, obl, lat))
for r in sorted(res, key=lambda r: r[0])[:6]: print(r)
best = sorted(res, key=lambda r: r[0])[0]
run((lambda jd: surya.ayanamsha(jd)) if best[2]=="ss" else best[2], best[3], best[4], True)
