import sys
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from datetime import date
def deg(s): a, b, c, d = map(int, s.split(":")); return a * 30 + b + c / 60 + d / 3600
D = {28: ("0:13:37:48", "0:15:52:16", "11:1:4:31", "-1:32"), 29: ("0:14:35:59", "1:0:10:53", "11:1:1:21", "-1:41"),
     30: ("0:15:34:7", "1:14:25:9", "11:0:58:10", "-1:49")}
for d, (sun, moon, rahu, bel) in D.items():
    day = date(2025, 4, d); r = surya.sunrise(day)
    m, s = bel[1:].split(":"); b = -(int(m) * 60 + int(s))
    print(f"Apr {d}: sun {(surya.true_sun(r)-deg(sun))*3600:+5.1f}\" moon {(surya.true_moon(r)-deg(moon))*3600:+6.1f}\" "
          f"rahu {(surya.rahu(r)-deg(rahu))*3600:+5.1f}\" belantar {surya.equation_of_time(day)*60-b:+5.1f}s")
