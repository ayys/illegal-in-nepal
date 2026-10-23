"""Fit a constant shift to each planet's SS mean longitude (Mars, Jupiter,
Saturn) or शीघ्रोच्च (Mercury, Venus), optionally also its apogee, and report
the residuals. A good fit to arcseconds means "SS + bija"."""
import sys
from datetime import date
sys.path.insert(0, "../..")
import surya
import ss_planets as ss
from epoch import deg, diff, sun_moment
from swiss2083 import BOOK as BOOK_2083

ORDER = ss.ORDER


def shifted(jd, body, d_mean, d_apogee=0.0):
    saved_mean, saved_ap = ss.mean_body, ss.apogee
    ss.mean_body = lambda j, b: saved_mean(j, b) + (d_mean if b == body else 0)
    ss.apogee = lambda j, b: saved_ap(j, b) + (d_apogee if b == body else 0)
    try:
        return ss.true_planet(jd, body)
    finally:
        ss.mean_body, ss.apogee = saved_mean, saved_ap


def residuals(samples, body, d_mean, d_ap=0.0):
    return [diff(want, shifted(jd, body, d_mean, d_ap)) for jd, want in samples]


def rms(values):
    return (sum(v * v for v in values) / len(values)) ** 0.5


def fit(samples, body, with_apogee=False):
    best = None
    aps = [x / 2 for x in range(-40, 41)] if with_apogee else [0.0]
    for d_ap in aps:
        d, width = 0.0, 10.0
        for _ in range(6):  # grid, then zoom in
            grid = [d + width * (k / 20 - 1) for k in range(41)]
            d = min(grid, key=lambda x: rms(residuals(samples, body, x, d_ap)))
            width /= 10
        res = residuals(samples, body, d, d_ap)
        if best is None or rms(res) < rms(best[2]):
            best = (d, d_ap, res)
    return best


def book_samples(book, moment):
    out = {b: [] for b in ORDER}
    for day, row in book.items():
        jd = moment(day, row)
        for b in ORDER:
            if b in row:
                out[b].append((jd, deg(row[b])))
    return out


if __name__ == "__main__":
    from epoch import READINGS as HIMAL_2076
    nat = {d: dict(zip(ORDER, r)) for d, r in BOOK_2083.items()}
    sets = [
        ("2083 national, at sunrise", book_samples(nat, lambda d, r: surya.sunrise(d))),
        ("2076 Himal, at the Sun's moment", book_samples(HIMAL_2076, lambda d, r: sun_moment(d, r["sun"]))),
    ]
    for label, samples in sets:
        print(label)
        for b in ORDER:
            if not samples[b]:
                continue
            d, _, res = fit(samples[b], b)
            d2, ap2, res2 = fit(samples[b], b, with_apogee=True)
            print(f"  {b:8s} mean {d * 60:+8.2f}′ rms {rms(res) * 60:6.1f}″ | mean {d2 * 60:+8.2f}′ apogee {ap2:+6.2f}° rms {rms(res2) * 60:6.1f}″"
                  f"  resid″ {' '.join(f'{x * 60:+.0f}' for x in res)}")
