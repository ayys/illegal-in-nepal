# Calibration: the fitted constants and their evidence

Almost everything in the generator is textbook Surya Siddhanta (SS) plus
textbook spherical astronomy. Three things are not. They were measured from
the printed books, and this page shows how, so that you can check them or
re-fit them.

| Constant | Where | Value | Fitted from |
|---|---|---|---|
| `MOON_APOGEE_CORRECTION` | `surya.py` | −1.7° | Tithi, nakshatra and yoga end times in 5 fortnights of the 2082 and 2083 books |
| `RAHU_OFFSET` and the Ujjain-sunrise moment | `surya.py` | −50.4″ | राहु in the स्पष्ट ग्रह tables of the 2082 and 2083 books |
| `SANKRANTI_ERAS` | `panchanga.py` | per era | Sankranti ghati in the 1986–2076 books |
| `REFRACTION_FROM` | `panchanga.py` | BS 2064 | दिनमान printed in the 2058–2066 books |

All figures below come from running the code in this directory. Regenerate
them with `build_status.py` (constants 1 and 2) or the snippets given.

## 1. Moon's apogee: −1.7°

**Symptom.** With the textbook SS Moon, the printed end times of tithi,
nakshatra and yoga are consistently off by several minutes, in a way that
depends on the Moon's anomaly. A shift of the apogee is the one-parameter
change that removes it.

**Method.** For each transcribed fortnight, scan the correction from −1.80°
to −1.60° in 0.02° steps. Count the ends that match the printed minute
exactly (`build_status.apogee_fits()`):

| Fortnight (book page) | −1.80 | −1.74 | −1.72 | **−1.70** | −1.68 | −1.60 | Best |
|---|---|---|---|---|---|---|---|
| 2082 वैशाख शुक्ल (2082 p3) | 22/44 | 34/44 | 37/44 | **40/44** | 34/44 | 16/44 | −1.70 |
| 2082 माघ कृष्ण (2082 p20) | 23/45 | 38/45 | 38/45 | 35/45 | 30/45 | 9/45 | −1.74 |
| 2083 वैशाख (2083 pp2–3) | 21/51 | 40/51 | 44/51 | 40/51 | 40/51 | 25/51 | −1.72 |
| 2083 कार्तिक (2083 p16) | 16/45 | 31/45 | 36/45 | 39/45 | 39/45 | 17/45 | −1.70 |
| 2083 पौष/माघ (2083 p21) | 13/43 | 30/43 | 32/43 | 37/43 | 35/43 | 14/43 | −1.70 |

**Reading.** The best value sits between −1.74° and −1.70° in every
fortnight from April 2025 to January 2027, with no trend, so it is a
constant. Every remaining end is within one minute.

## 2. Rahu: −50.4″ at Ujjain mean sunrise

**Symptom.** At Kathmandu sunrise, the residual of the Lahiri mean node
against the book's राहु changes with the season: about −2.5″ to +8″ across
the year. A constant offset cannot remove a seasonal swing, so the moment
is wrong, not just the value.

**Fix.** Evaluate the node at a *fixed daily moment*, 06:00 local mean time
at Ujjain (the SS's day start, 06:41:56 NST). There the residual is flat,
and after an offset of −50.4″ it stays within ±2.5″ across all 14 tabulated
days in both books (`build_status.rahu_residuals()`):

| Evaluated at | Residual range (computed − book) |
|---|---|
| Kathmandu sunrise | −2.5″ … +8.0″ |
| Ujjain mean sunrise (used) | −2.4″ … +2.5″ |

The book prints whole arc-seconds, so ±2.5″ is close to its rounding.

**Data.** The स्पष्ट ग्रह tables are on 2082 book pp3 and 20 and 2083 book
p21; they are the `SPASHTA_2082` and `SPASHTA` dicts in `test_panchanga.py`.

## 3. Sankranti eras

**Problem.** The month a day belongs to depends on the sankranti moment to
within a few pala when the sankranti is near a boundary (sunrise, sunset or
the night midpoint). Older books evidently used slightly different Sun
positions: different editions of the SS tables, or rounding in the
committee's worksheets. The offset changes in steps between eras.

### 3.1 Which sunrise the books count from

A book prints each sankranti as ghati and pala after *its own* sunrise, so
before comparing anything you need to know which sunrise that is. The
दिनमान column answers it. Compared with `surya.day_length` at the two
horizons (`surya.HORIZON` = −34′, refraction only; `surya.GEOMETRIC` = 0°,
the Sun's centre on the horizon), book minus ours:

| Book (PDF page) | Day | Printed | vs −34′ | vs 0° |
|---|---|---|---|---|
| 2035 (p21) | 1979-01-14 | 26।5 | −10.8 | +3.2 |
| 2058 (p20) | 2002-01-13 | 26।3 | −11.5 | +2.5 |
| 2062 (p5) | 2005-05-14 | 33।23 | −13.9 | −0.1 |
| 2062 (p13) | 2005-09-13 | 30।43 | −12.6 | +0.2 |
| 2062 (p21) | 2006-01-14 | 26।3 | −13.7 | +0.4 |
| 2062 (p25) | 2006-03-14 | 29।32 | −12.6 | +0.2 |
| 2063 (p21) | 2007-01-20 | 26।17 | −13.2 | +0.7 |
| 2064 (p21) | 2008-01-08 | 26।3 | −1.6 | +12.6 |
| 2065 (p21) | 2009-01-05 | 26।0 | −1.2 | +13.0 |
| 2066 (p5) | 2009-05-14 | 33।36 | −0.9 | +12.8 |
| 2066 (p20) | 2009-12-22 | 25।50 | −1.2 | +13.1 |

So the books up to 2063 leave refraction out, in every season, and the
books from 2064 put it in. The older books (2035, 2058) run another
2–3 pala long, which is too small to matter for the day rule.
`panchanga.book_horizon` encodes this, `REFRACTION_FROM = 2064`, and
`test_book_horizon` checks the table above.

This matters because a geometric sunrise is about 7 pala later than a
refracted one. Measuring a pre-2064 book's ghati from the refracted
sunrise puts its sankranti 7 pala too early. Before this was found, it
showed up as a spurious −0.12-ghati era for 2063 and a wrong जेठ for 2062.

(`research/oldbooks/read/dinamana.csv` is a first pass at this column for
35 books. Its values for books after 2051 are wrong, as the pages above
show; don't use it.)

### 3.2 Reading the sankrantis

Every reading is in
[`data/book_sankrantis.csv`](../data/book_sankrantis.csv), 187 rows, with
the book, the PDF page and the source URL. The raw offset is the book's
moment minus our unshifted SS moment, both measured from the book's own
sunrise, in ghati (sign 0 = Mesha):

| Book | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1986 | −0.76 | −0.93 | −0.55 | −0.10 | −0.04 | −0.34 | −1.03 | −0.83 | −0.52 | −0.13 | −0.01 | −0.34 |
| 2016 | −0.67 | −0.80 | −0.40 | −0.82 | +0.58 | +0.44 | −0.12 | −0.43 | +0.02 | +0.22 | +0.12 | −0.24 |
| 2028 | −0.44 | −2.31 | −1.90 | −2.80 | −1.84 | −1.13 | −0.82 | +0.43 | +0.63 | +1.26 | +0.22 | −0.04 |
| 2033 | | −2.37 | −1.95 | −2.83 | | | −0.85 | +0.42 | +0.58 | +1.22 | +0.18 | −0.12 |
| 2041 | | −2.39 | −1.97 | −2.85 | | | | +0.40 | | +1.20 | | |
| 2044 | | −2.37 | −1.94 | −2.81 | | | | +0.40 | | +1.22 | | |
| 2045 | | | | −0.33 | | | | | | −0.54 | | |
| 2051 | −0.43 | −0.58 | −0.40 | −0.34 | | | −0.43 | −0.47 | −0.45 | | −0.52 | −0.43 |
| 2058 | −0.44 | −0.58 | | −0.33 | | | −0.42 | | | −0.54 | −0.49 | |
| 2059 | | | | −0.32 | | | | | | | | |
| 2060 | −0.03 | −0.16 | | +0.12 | | | +0.03 | | | −0.10 | −0.07 | |
| 2062 | −0.01 | −0.15 | +0.04 | +0.11 | +0.04 | +0.19 | +0.01 | | −0.01 | −0.11 | −0.06 | −0.01 |
| 2063 | −0.05 | +0.01 | | −0.00 | | | +0.02 | | | +0.00 | +0.01 | |
| 2065 | −0.05 | −0.01 | | −0.01 | | | +0.00 | | | −0.02 | −0.00 | |
| 2076 | −0.06 | −0.01 | | −0.02 | +0.01 | | +0.01 | +0.02 | | −0.02 | +0.01 | −0.03 |

(A selection; the 2031–2044, 2061 and 2066–2073 books repeat their
neighbours to within 2 pala. `research/oldbooks/` has the reading scripts.)

The 1986 and 2016 books are from the British Library's Endangered Archives
Programme (EAP1485-1-3-127 and EAP1485-1-3-45); the 2028 one is the
archive.org item `nepali-patro-2028`. See [SOURCES.md](SOURCES.md).

What the readings show:

- **1986 and 2016.** Each has its own per-sign pattern. With no books in
  between, each gets its own era.
- **2028–2044.** One per-sign table, repeated book to book to within
  2 pala (2028 sits 2 pala later than the rest): Karka −2.82,
  Makara +1.22.
- **2045–2059.** The 2060–2062 shape minus 0.43 ghati (fitted, −0.431).
- **2060–2062.** A small per-sign shape, mean 0, up to ±0.19.
- **2063 on.** Plain SS to within about a pala, except Mesha (−0.06) and
  Mina (−0.03), which lean early in every book from 2063 to 2076.

### 3.3 The eras

| From BS | Offset | Read from | Boundary set by |
|---|---|---|---|
| 1975 | 1986 table | 1986 book | first verified year |
| 2005 | 2016 table | 2016 book | month tables (any of 2005–2016 fits equally) |
| 2017 | 2028–2044 table | 2028, 2031–2044 books | month tables (any of 2017–2027 fits equally) |
| 2045 | shape − 0.43 | 2045–2059 books | 2044 and 2045 books |
| 2060 | shape | 2060–2062 books | 2059 and 2060 books |
| 2063 | Mesha −0.06, Mina −0.03 | 2063–2076 books | 2062 and 2063 books |

The two pre-2045 boundaries fall in years with no book read (1987–2015,
2017–2027). They are placed where the published month tables are best
matched. Every split in the ranges shown leaves the same 3 misses in
1975–2044 against `nepali-datetime`:

| Month | Ours | Tables | Margin |
|---|---|---|---|
| 1977/7 | 1920-10-17 | 1920-10-16 (nepali-datetime only) | 3 pala past the night midpoint |
| 1989/8 | 1932-11-16 | 1932-11-15 (nepali-datetime only) | 12 pala past it |
| 2018/9 | 1961-12-16 | 1961-12-15 (both tables) | 54 pala past it |

2018/9 is the clear one: only the 1986 table puts it on the 15th, so the
2018 book probably follows yet another convention. The 2017–2027 books
(not yet found in a readable copy) would settle it. The fitted curves the
model used before had none of these misses, but they were fitted to these
very tables; the eras now come from the books instead.

To reproduce the comparison (needs `nepali-datetime` and `nepali`):

```python
import panchanga, nepali_datetime
for y in range(1975, 2084):
    for m, start in enumerate(panchanga.month_starts(y)[:12], 1):
        if start != nepali_datetime.date(y, m, 1).to_datetime_date():
            print(y, m, start)
```

### 3.4 Tolerances used in the tests

`test_book_sankrantis` checks every CSV row against the model to 4 pala.
That covers each book's scatter about its era's values; the largest are the
2028 book's 2-pala lean against the other 2028–2044 books and the 2062
book against the 2060 shape.

## 4. Things tried and rejected

These were tried and made the match worse:

- the SS trepidation ayanamsha (600 oscillations per yuga);
- the SS obliquity of 24°;
- a −0.83° horizon (the standard upper-limb sunrise);
- modern ephemerides for Mars to Saturn.

The books use the Lahiri ayanamsha, the modern obliquity, and the disc
centre: with refraction only from 2064, without it before (section 3.1).
