import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import panchanga
import nepali_datetime as nd
from nepali.date_converter import converter as pn

out = {}
for y in range(1975, 2101):
    ours = panchanga.month_starts(y)[:12]
    a = [nd.date(y, m, 1).to_datetime_date() for m in range(1, 13)]
    try:
        b = [__import__("datetime").date(*pn.nepali_to_english(y, m, 1)) for m in range(1, 13)]
    except Exception:
        b = None
    out[y] = {"ours": [d.isoformat() for d in ours], "nd": [d.isoformat() for d in a],
              "pn": [d.isoformat() for d in b] if b else None}
json.dump(out, open("starts.json", "w"))
print("done")
