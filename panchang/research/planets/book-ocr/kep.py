"""Keplerian (unperturbed) geocentric longitudes from Standish's JPL elements
(1800-2050 table), made sidereal with Lahiri, against the 2083 book p21."""
import math, sys
sys.path.insert(0, "../..")
import surya

# a, e, I, L, long.peri, node  and rates per Julian century (J2000 ecliptic/equinox)
EL = {
 "mercury": ((0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
             (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081)),
 "venus":   ((0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
             (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418)),
 "earth":   ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
             (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
 "mars":    ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
             (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
 "jupiter": ((5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
             (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106)),
 "saturn":  ((9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
             (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794)),
}
ORDER = ["mars", "mercury", "jupiter", "venus", "saturn"]

def helio(body, t):
    a, e, i, L, w, O = (x + r * t for x, r in zip(*EL[body]))
    M = math.radians((L - w) % 360); E = M
    for _ in range(30): E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    xp, yp = a * (math.cos(E) - e), a * math.sqrt(1 - e * e) * math.sin(E)
    om, O, i = math.radians(w - O), math.radians(O), math.radians(i)
    co, so, cO, sO, ci, si = math.cos(om), math.sin(om), math.cos(O), math.sin(O), math.cos(i), math.sin(i)
    return ((co*cO - so*sO*ci) * xp + (-so*cO - co*sO*ci) * yp,
            (co*sO + so*cO*ci) * xp + (-so*sO + co*cO*ci) * yp,
            (so*si) * xp + (co*si) * yp)

def geo(body, jd, light=False):
    t = (jd - 2451545.0) / 36525
    ex, ey, _ = helio("earth", t)
    tau = 0.0
    for _ in range(3 if light else 1):
        px, py, _ = helio(body, t - tau / 36525)
        dist = math.hypot(px - ex, py - ey); tau = dist * 0.0057755
    lon = math.degrees(math.atan2(py - ey, px - ex))
    # J2000 ecliptic longitude -> sidereal: subtract Lahiri at J2000
    return (lon - 23.857092) % 360

