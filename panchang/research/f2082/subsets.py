import sys
sys.path.insert(0, "/Users/ayys/git/illegal-in-nepal/panchang")
import surya, panchanga, test_panchanga as t
from datetime import date
from fit2082 import BOOK as B82, want

def score(book_items, shift):
    surya.MOON_APOGEE_CORRECTION = shift
    exact = n = 0; sq = 0.0
    for day, ends in book_items:
        row = panchanga.day_row(day, 0, 1)
        for limb, v in zip(("tithi", "nakshatra", "yoga"), ends):
            got = [h * 60 + m for h, m in (e["clock"] for e in row[limb]["ends"])]
            w = want(v)
            if len(got) != len(w): continue
            for g, x in zip(got, w):
                n += 1; exact += g == x; sq += (g - x) ** 2
    return exact, n

sets = {
    "2082 Jan (माघ कृष्ण)": [(date(2026, 1, d), v) for d, v in B82.items()],
    "2083 Apr (वैशाख)": [(d, v) for d, v in t.BOOK.items() if d.month in (4, 5)],
    "2083 Oct-Nov (कार्तिक)": [(d, v) for d, v in t.BOOK.items() if d.month in (10, 11)],
    "2083 Jan (पौष/माघ)": [(d, v) for d, v in t.BOOK.items() if d.year == 2027],
}
shifts = [x / 100 for x in range(-190, -149, 2)]
for name, items in sets.items():
    results = [(score(items, s), s) for s in shifts]
    best = max(results, key=lambda r: r[0][0])
    good = [s for (e, n), s in results if e >= best[0][0] - 2]
    print(f"{name:26} best {best[1]:+.2f} ({best[0][0]}/{best[0][1]}), near-best {min(good):+.2f}..{max(good):+.2f}")
