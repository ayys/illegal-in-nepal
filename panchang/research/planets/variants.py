import sys, statistics
from datetime import date
sys.path.insert(0, "../.."); import surya, ketaki
from vsbook import clean, diff
def stats(b, cap=900):
    res = []
    for d, v in clean[b].items():
        r = diff(v, ketaki.geocentric(b, surya.sunrise(date.fromisoformat(d)), rounded=False, short=False))
        if abs(r) < cap: res.append(r)
    res.sort(key=abs); n = len(res)
    return f"{abs(res[n//2]):4.0f}″/{abs(res[int(n*.9)]):4.0f}″"
def run(label):
    print(f"{label:28s}", "  ".join(f"{b} {stats(b)}" for b in ketaki.ORDER))
