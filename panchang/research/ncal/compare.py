import json, os, re, sys
from datetime import date, timedelta
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import panchanga

MONTHS = "Baishakh Jestha Ashadh Shrawan Bhadra Ashwin Kartik Mangsir Poush Magh Falgun Chaitra".split()
starts = json.load(open(__import__("pathlib").Path(__file__).resolve().parent.parent / "bscmp/starts.json"))


def site(y, m):
    path = f"pages/{y}-{MONTHS[m]}.html"
    if not os.path.exists(path):
        return None
    days = [int(d) for d in re.findall(r"<sub>(?:\s|&nbsp;)*(\d+)</sub>", open(path).read())]
    return days or None


def resolve(day, near):
    for k in range(-5, 6):
        d = near + timedelta(days=k)
        if d.day == day:
            return d


rows = []
for y in range(1969, 2101):
    ours = panchanga.month_starts(y)
    for m in range(12):
        days = site(y, m)
        if not days:
            continue
        sd = resolve(days[0], ours[m])
        nd = starts.get(str(y), {}).get("nd")
        pn = starts.get(str(y), {}).get("pn")
        rows.append(dict(y=y, m=m + 1, site=str(sd), length=len(days), ours=str(ours[m]),
                         ours_len=(ours[m + 1] - ours[m]).days,
                         nd=nd[m] if nd else None, pn=pn[m] if pn else None))
json.dump(rows, open("site.json", "w"))
years = sorted({r["y"] for r in rows})
print("years", years[0], "-", years[-1], "months", len(rows))
for key in ["ours", "nd", "pn"]:
    have = [r for r in rows if r[key]]
    bad = [r for r in have if r[key] != r["site"]]
    print(f"site vs {key}: {len(have) - len(bad)}/{len(have)} agree")
print("\nmonths where the site disagrees with ours:")
for r in rows:
    if r["site"] != r["ours"]:
        print(f"  {r['y']}/{r['m']:2}  site {r['site']}  ours {r['ours']}  nd {r['nd']}  pn {r['pn']}")
