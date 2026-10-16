import numpy as np
# sign: offset ghati (book - ours), 2032/2033 books
d = {0:-0.58,1:-2.48,2:-2.06,3:-2.95,5:-1.27,6:-0.95,7:0.30,8:0.47,9:1.10,10:0.07,11:-0.20}
s = np.array(list(d)); y = np.array(list(d.values()))
L = np.radians(30*s)
for name, cols in [("1st", [np.ones_like(L), np.cos(L), np.sin(L)]),
                   ("1st+2nd", [np.ones_like(L), np.cos(L), np.sin(L), np.cos(2*L), np.sin(2*L)])]:
    A = np.array(cols).T
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ c
    amp = np.hypot(c[1], c[2]); ph = np.degrees(np.arctan2(c[2], c[1])) % 360
    print(name, np.round(c, 2), f"amp {amp:.2f} peak {ph:.0f}", "resid", np.round(r, 2), "rms", round(float(np.sqrt((r**2).mean())), 2))
