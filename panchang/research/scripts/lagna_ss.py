import math, surya, itertools
from datetime import date
exec(open(__import__("pathlib").Path(__file__).resolve().parent / "lagna_fit.py").read().split("def mins")[0].split("book = ")[1].join(["book = ", ""]) if False else "")
book = {
 date(2027,1,8): "7:25 9:8 10:36 12:2 13:38 15:34 17:49 20:9 22:25 24:40 26:59 29:17",
 date(2027,1,9): "7:21 9:4 10:32 11:58 13:34 15:30 17:45 20:5 22:21 24:36 26:55 29:13",
 date(2027,1,12): "7:9 8:52 10:20 11:46 13:22 15:19 17:33 19:53 22:9 24:25 26:43 29:1",
}
def mins(s): h, m = s.split(":"); return int(h)*60+int(m)
LANKA = [1670, 1795, 1935]
def rising_table(palabha):
    c = [10*palabha*6, 8*palabha*6, 10*palabha/3*6]   # asus
    first = [LANKA[i] - c[i] for i in range(3)]          # Mesha, Vrisha, Mithuna
    second = [LANKA[2-i] + c[2-i] for i in range(3)]     # Karka, Simha, Kanya
    half = first + second
    return half + half[::-1]   # Tula..Meena mirror: Tula=Kanya, ..., Meena=Mesha
def asus_between(table, a, b):
    """asus for tropical longitude to go from a to b (b ahead)."""
    total, x = 0.0, a
    dist = (b - a) % 360
    while dist > 1e-9:
        s = int(x // 30) % 12
        step = min(30 - x % 30, dist)
        total += table[s] * step / 30
        x = (x + step) % 360; dist -= step
    return total
def run(palabha, sidereal, ayan_mode, anchor_shift, show=False):
    table = rising_table(palabha); err = []
    for d, s in book.items():
        want = [mins(x) for x in s.split()]
        rise = surya.sunrise(d)
        ay = surya.ayanamsha(rise) if ayan_mode == "ss" else ayan_mode
        sun = surya.norm(surya.true_sun(rise) + ay)
        rise_min = (rise - surya.local_julian_day(d, 0)) * 1440 + anchor_shift
        got = []
        for k in range(12):
            b = surya.norm((9 + k) * 30 + ay)  # sidereal makara.. boundaries, tropical
            a = asus_between(table, sun, b)
            got.append(rise_min + a / 15 * (0.99727 if sidereal else 1.0))
        err += [g - w for g, w in zip(got, want)]
        if show: print(d, " ".join(f"{g-w:+.1f}" for g, w in zip(got, want)))
    return (sum(e*e for e in err)/len(err))**.5, sum(err)/len(err)
res = []
for p, sid, ay, sh in itertools.product([6.0, 6.18, 6.3, 6.5], [True, False], ["ss", 23.0, 24.0], [0]):
    res.append((*run(p, sid, ay, sh), p, sid, ay))
for r in sorted(res)[:6]: print(r)
b = sorted(res)[0]; run(b[2], b[3], b[4], 0, True)

print("--- spherical oblique ascension anchored at sunrise")
def oa(lam, obl, lat):
    l = math.radians(lam); e = math.radians(obl)
    ra = math.degrees(math.atan2(math.cos(e)*math.sin(l), math.cos(l))) % 360
    dec = math.asin(math.sin(e)*math.sin(l))
    return (ra - math.degrees(math.asin(math.tan(math.radians(lat))*math.tan(dec)))) % 360
def run2(obl, lat, ayan_mode, sidereal, show=False):
    err = []
    for d, s in book.items():
        want = [mins(x) for x in s.split()]
        rise = surya.sunrise(d)
        ay = surya.ayanamsha(rise) if ayan_mode == "ss" else ayan_mode
        sun = surya.norm(surya.true_sun(rise) + ay)
        rise_min = (rise - surya.local_julian_day(d, 0)) * 1440
        got = [rise_min + ((oa(surya.norm((9+k)*30 + ay), obl, lat) - oa(sun, obl, lat)) % 360) * 4 * (0.99727 if sidereal else 1)
               for k in range(12)]
        err += [g - w for g, w in zip(got, want)]
        if show: print(d, " ".join(f"{g-w:+.1f}" for g, w in zip(got, want)))
    return (sum(e*e for e in err)/len(err))**.5, sum(err)/len(err)
res = []
for obl, lat, ay, sid in itertools.product([24.0, 23.44], [27.7, 27.5, 27.9], ["ss", 23.0, 23.5, 24.0], [True, False]):
    res.append((*run2(obl, lat, ay, sid), obl, lat, ay, sid))
for r in sorted(res)[:6]: print(r)
b = sorted(res)[0]; run2(*b[2:], show=True)
print("--- fine")
res = []
for ay in [23.8, 23.9, 24.0, 24.1, 24.2, 24.3]:
    for obl in [23.436, 23.5]:
        res.append((*run2(obl, 27.7, ay, True), obl, ay))
for r in sorted(res)[:5]: print(r)
import swisseph as swe
swe.set_sid_mode(swe.SIDM_LAHIRI)
print("lahiri 2027-01-08", swe.get_ayanamsa_ut(swe.julday(2027,1,8,0)))
