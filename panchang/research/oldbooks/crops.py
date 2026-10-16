"""crops.py YEAR SIGN... -> read/{YEAR}-{SIGN}.png plus the prediction to check against.

Finds the page that holds each sankranti (PDF page = our page number, since
the old books also print one paksha per page), and cuts the right half of it
(day numbers, Gregorian dates and the notes column) in two halves, enlarged.
The prediction is the plain SS sankranti in ghati:pala after the sunrise of
the day it falls in; the book's note reads e.g. "मकरेऽर्कः १३।३१".
"""
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import panchanga  # noqa: E402
import surya  # noqa: E402

NAMES = "mesha vrisha mithuna karka simha kanya tula vrischika dhanu makara kumbha mina".split()

year = int(sys.argv[1])
signs = [int(s) for s in sys.argv[2:]] or list(range(12))
pages = panchanga.year(year)
start = panchanga._gregorian_jd(year - 57, 4, 1)
found = {(e + 1) % 12: jd for e, jd in surya.crossings(surya.true_sun, 30, start, start + 370)[:12]}
(HERE / "read").mkdir(exist_ok=True)
for sign in signs:
    jd = found[sign]
    day = surya.from_julian_day(jd).date()
    if jd < surya.sunrise(day):
        day -= timedelta(days=1)
    pala = (jd - surya.sunrise(day)) * 3600
    page = next((p["page"] for p in pages if p["rows"][0]["date"] <= day.isoformat() <= p["rows"][-1]["date"]),
                2 if day.isoformat() < pages[0]["rows"][0]["date"] else pages[-1]["page"])
    images = sorted((HERE / f"h{year}").glob(f"i-{page - 1:03d}.*"))
    out = HERE / "read" / f"{year}-{sign}.png"
    if images:
        w, h = (int(v) for v in subprocess.run(["magick", "identify", "-format", "%w %h", str(images[0])],
                                               capture_output=True, text=True).stdout.split())
        x0, x1 = int(w * 0.30), int(w * 0.85)
        top = HERE / "read" / f"_{year}-{sign}-top.png"
        bottom = HERE / "read" / f"_{year}-{sign}-bottom.png"
        subprocess.run(["magick", str(images[0]), "-crop", f"{x1 - x0}x{h // 2 + 40}+{x0}+0", "+repage",
                        "-resize", "150%", str(top)], check=True)
        subprocess.run(["magick", str(images[0]), "-crop", f"{x1 - x0}x{h // 2 + 40}+{x0}+{h // 2 - 40}", "+repage",
                        "-resize", "150%", str(bottom)], check=True)
        subprocess.run(["magick", str(top), str(bottom), "-append", str(out)], check=True)
        top.unlink()
        bottom.unlink()
    print(f"{year} {sign:2d} {NAMES[sign]:9s} day {day} (gregorian day-of-month {day.day}) "
          f"page {page} predicted {int(pala // 60)}:{int(pala % 60):02d} -> {out.name if images else 'NO IMAGE'}")
