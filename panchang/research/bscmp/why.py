import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga
from datetime import date, timedelta
from collections import Counter
d = json.load(open("starts.json"))
misses = [(1993,4),(2024,4),(2035,2),(2035,10),(2046,11),(2051,4),(2062,2),(2066,12),(2073,11)]
def lengths(starts): return [(starts[i+1]-starts[i]).days for i in range(12)]
def table_starts(y, key):
    s = [date.fromisoformat(x) for x in d[str(y)][key]]
    nxt = date.fromisoformat(d[str(y+1)][key][0]) if d.get(str(y+1)) and d[str(y+1)][key] else None
    return s + [nxt]
all_lengths = Counter()
for y in range(1975, 2084):
    for i, L in enumerate(lengths(table_starts(y, "nd"))): all_lengths[(i+1, L)] += 1
for y, m in misses:
    key = "pn" if d[str(y)]["pn"] and y != 1993 else "nd"
    tb = table_starts(y, key); ours = panchanga.month_starts(y)
    i = m - 1
    lt, lo = lengths(tb), lengths(ours)
    t_day, o_day = tb[i], ours[i]
    rise = surya.sunrise(t_day); rise_o = surya.sunrise(o_day)
    tithi = lambda day: int(surya.elongation(surya.sunrise(day)) // 12) + 1
    print(f"BS {y}/{m:2} {panchanga.BS_MONTHS[i]:7} table {t_day} {t_day:%a} tithi {tithi(t_day):2} | ours {o_day} {o_day:%a} tithi {tithi(o_day):2}")
    print(f"     prev+this month lengths  table {lt[i-1]},{lt[i]}  ours {lo[i-1]},{lo[i]}   "
          f"how common in tables: prev {all_lengths[(m-1 if m>1 else 12, lt[i-1])]} vs {all_lengths[(m-1 if m>1 else 12, lo[i-1])]}, this {all_lengths[(m, lt[i])]} vs {all_lengths[(m, lo[i])]}")
