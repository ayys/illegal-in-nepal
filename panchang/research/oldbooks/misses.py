import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta
from ours import rows, ghati, MONTHS
st = json.load(open(__import__("pathlib").Path(__file__).resolve().parent.parent / "bscmp/starts.json"))
for y in range(1975, 2084):
    for i, jd, day, g, dm in rows(y):
        if i > 11: continue
        want = date.fromisoformat(st[str(y)]["nd"][i])
        pn = st[str(y)].get("pn"); pn = pn[i] if pn else "-"
        nish = 0.5 + dm / 2
        rule = day if g < nish else day + timedelta(days=1)
        if i == 3: rule = day          # Karka: belongs to the sunrise-day
        if i == 9: rule = day if g < dm else day + timedelta(days=1)
        ours = panchanga.month_starts(y)[i]
        if rule != want or ours != want:
            print(y, MONTHS[i], f"{surya.from_julian_day(jd):%Y-%m-%d %H:%M}", "g", ghati(g), "nish", ghati(nish),
                  "margin", ghati(g - nish) if g >= nish else "-" + ghati(nish - g).strip(),
                  "table", want, "pn", pn, "nishitha-rule", "ok" if rule == want else "MISS", "current", "ok" if ours == want else "MISS")
