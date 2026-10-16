import sys; sys.path.insert(0,'/Users/ayys/git/illegal-in-nepal/panchang')
import surya
from datetime import date, timedelta
def g(x): x*=60; return f"{int(x)}:{round(x%1*60):02d}"
d0 = date.fromisoformat(sys.argv[1]); n = int(sys.argv[2])
for k in range(n):
    d = d0 + timedelta(days=k); sr = surya.sunrise(d); nx = surya.sunrise(d + timedelta(days=1))
    t = [(i + 1, g(jd - sr)) for i, jd in surya.crossings(surya.elongation, 12, sr, nx)]
    s = [(i + 1, g(jd - sr)) for i, jd in surya.crossings(surya.true_moon, 360/27, sr, nx)]
    print(d, f"sunrise {surya.from_julian_day(sr):%H:%M} dm {g(surya.day_length(d)/1440)}", "tithi", t, "nak", s)
