"""Ketaki against the स्पष्ट ग्रह tables of the 2082 and 2083 books (OCR in book-ocr/clean.json)."""
import json, statistics, sys
from datetime import date
sys.path.insert(0, "../..")
import surya
import ketaki

clean = json.load(open("book-ocr/ketaki_clean.json"))
def diff(a, b): return ((a - b + 180) % 360 - 180) * 3600   # arcsec
def report(label, moment, **kw):
    print(label)
    for b in ketaki.ORDER:
        res = []
        for d, v in clean[b].items():
            jd = moment(date.fromisoformat(d))
            res.append(diff(v, ketaki.geocentric(b, jd, **kw)))
        res.sort(key=abs)
        n = len(res)
        print(f"  {b:8s} n={n:3d} median|Δ| {abs(res[n//2]):7.0f}″  90% {abs(res[int(n*.9)]):7.0f}″  mean {statistics.mean(res):+7.0f}″")
if __name__ == "__main__":
    report("Kathmandu sunrise", lambda d: surya.sunrise(d))
    report("Ujjain mean sunrise", surya.ujjain_mean_sunrise)
