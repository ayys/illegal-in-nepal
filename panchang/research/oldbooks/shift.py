import sys, json
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya
from datetime import date, timedelta
from ours import rows
st = json.load(open(__import__("pathlib").Path(__file__).resolve().parent.parent / "bscmp/starts.json"))
GRID = [k / 100 for k in range(-200, 101)]          # shift in ghati

def start(i, g, day, dm, shift):
    g = g + shift / 60
    if g < 0: day, g = day - timedelta(days=1), g + 1   # crude: day lengths ~1
    if i == 3: return day                                # Karka: sunrise-day
    if i == 9: return day if g < dm else day + timedelta(days=1)
    return day if g <= 0.5 + dm / 2 else day + timedelta(days=1)

cache = {}
for y in range(1975, 2084):
    cache[y] = [(i, g, day, dm, date.fromisoformat(st[str(y)]["nd"][i])) for i, jd, day, g, dm in rows(y) if i < 12]
if __name__ == "__main__":
  for y in range(1975, 2084):
      ok = [s for s in GRID if all(start(i, g, d, dm, s) == w for i, g, d, dm, w in cache[y])]
      best = max(sum(start(i, g, d, dm, s) == w for i, g, d, dm, w in cache[y]) for s in GRID)
      rng = f"[{min(ok):+.2f}, {max(ok):+.2f}]" if ok else f"none (best {best}/12)"
      print(y, rng)
