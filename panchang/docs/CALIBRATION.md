# Calibration: the fitted constants and their evidence

Almost everything in the generator is textbook Surya Siddhanta (SS) plus
textbook spherical astronomy. A few things are not. They were measured from
the printed books, and this page shows how, so that you can check them or
re-fit them.

| Constant | Where | Value | Fitted from |
|---|---|---|---|
| `MOON_APOGEE_CORRECTION` | `surya.py` | −1.71° | Tithi, nakshatra and yoga end times in 5 fortnights of the 2082 and 2083 books |
| `RAHU_OFFSET` and the Ujjain-sunrise moment | `surya.py` | −50.4″ | राहु in the स्पष्ट ग्रह tables of the 2082 and 2083 books |
| `SANKRANTI_ERAS` | `panchanga.py` | per era | Sankranti ghati in the 1986–2076 books |
| `REFRACTION_FROM` | `panchanga.py` | BS 2064 | दिनमान printed in the 2058–2066 books |
| `DINAMANA_SHIFT`, `DINAMANA_HORIZON` | `surya.py` | 22′, −30′ | The दिनमान column of the 2083 book, April to January (section 6) |
| How the books apply Ketaki | `ketaki.py` | five conventions, `SUN_EQUATION` 115.2′, 1.2′ | Mars–Saturn in the 2082 and 2083 स्पष्ट ग्रह tables (section 5) |

All figures below come from running the code in this directory. Regenerate
them with `build_status.py` (constants 1 and 2) or the snippets given.

## 1. Moon's apogee: −1.71°

**Symptom.** With the textbook SS Moon, the printed end times of tithi,
nakshatra and yoga are consistently off by several minutes, in a way that
depends on the Moon's anomaly. A shift of the apogee is the one-parameter
change that removes it.

**Method.** For each transcribed fortnight, scan the correction from −1.76°
to −1.66° in 0.01° steps. Count the ends that match the printed minute
exactly (`build_status.apogee_fits()`):

| Fortnight (book page) | −1.74 | −1.73 | −1.72 | **−1.71** | −1.70 | −1.69 | −1.68 | Best |
|---|---|---|---|---|---|---|---|---|
| 2082 वैशाख शुक्ल (2082 p3) | 34/44 | 36/44 | 40/44 | **44/44** | 42/44 | 40/44 | 36/44 | −1.71 |
| 2082 माघ कृष्ण (2082 p20) | 42/45 | 43/45 | 44/45 | **45/45** | 41/45 | 38/45 | 34/45 | −1.71 |
| 2083 वैशाख (2083 pp2–3) | 43/51 | 46/51 | 49/51 | **50/51** | 48/51 | 46/51 | 43/51 | −1.71 |
| 2083 कार्तिक (2083 p16) | 38/45 | 41/45 | 43/45 | **44/45** | 42/45 | 40/45 | 39/45 | −1.71 |
| 2083 पौष/माघ (2083 p21) | 32/43 | 34/43 | 40/43 | **43/43** | 42/43 | 38/43 | 37/43 | −1.71 |

**Reading.** Every fortnight from April 2025 to January 2027 picks −1.71°
on its own, so it is a constant. Two ends of 228 miss, each by 4 seconds
past a half-minute.

**Exact sines.** Until the sine question was settled (section 7), the
fortnights scattered from −1.74° to −1.70° and only 191 ends matched: the
SS's interpolated sine table leaves a 9″·sin(anomaly) error in the Moon,
which no apogee shift can absorb.

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
| 1986 (p9) | 1929-07-16 | 33।57 | −16.2 | −2.2 |
| 1986 (p21) | 1930-01-14 | 26।1 | −14.8 | −0.7 |
| 1987 (p14) | 1930-07-11 | 34।7 | −15.5 | −1.4 |
| 1987 (p26) | 1931-01-14 | 26।4 | −11.3 | +2.8 |
| 2016 (p12) | 1959-07-20 | 33।50 | −15.5 | −1.5 |
| 2016 (p25) | 1960-01-20 | 26।13 | −15.9 | −2.0 |
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
`test_book_horizon` checks the 2062–2066 rows.

The same column says which *place* a book was computed for, because the
seasonal swing of the day length grows with latitude. The 1986, 1987 and
2016 books, which the 1975 and 2005 eras are read from, fit Kathmandu with
a geometric horizon to within 3 pala on the days above; at 29.1° N they would be 12–22 pala
off (short in July, long in January). The 2016 book's July page drifts
from −6 to −1.5 pala over 1959-07-07 to 07-20; it is still far from any
other latitude. The 1995 almanac fails this check (see
[SOURCES.md](SOURCES.md#older-books-elsewhere)), so check the दिनमान of
any new book, in July and in January, before using its sankrantis.

This matters because a geometric sunrise is about 7 pala later than a
refracted one. Measuring a pre-2064 book's ghati from the refracted
sunrise puts its sankranti 7 pala too early. Before this was found, it
showed up as a spurious −0.12-ghati era for 2063 and a wrong जेठ for 2062.

(`research/oldbooks/read/dinamana.csv` is a first pass at this column for
35 books. Its values for books after 2051 are wrong, as the pages above
show; don't use it.)

### 3.2 Reading the sankrantis

Every reading is in
[`data/book_sankrantis.csv`](../data/book_sankrantis.csv), 198 rows, with
the book, the PDF page and the source URL. The raw offset is the book's
moment minus our unshifted SS moment, both measured from the book's own
sunrise, in ghati (sign 0 = Mesha):

| Book | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1986 | −0.76 | −0.93 | −0.55 | −0.10 | −0.04 | −0.34 | | −0.83 | −0.52 | −0.13 | −0.01 | −0.34 |
| 1987 | −0.78 | −1.00 | −0.56 | −0.10 | −0.00 | −0.46 | −0.66 | −0.75 | −0.50 | −0.12 | −0.11 | −0.37 |
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

These offsets were measured against the SS Sun computed with the SS's
interpolated sine table. The generator now uses exact sines (section 7),
which moves each sankranti by a fixed amount per sign, in ghati: Mesha
−0.057, Vrishabha −0.010, Mithuna −0.014, Karka +0.006, Simha +0.036,
Kanya +0.026, Tula +0.027, Vrischika +0.035, Dhanu +0.016, Makara −0.001,
Kumbha +0.003, Mina −0.034. The era tuples in `panchanga.py` have this
added, to three decimals, so every month start from 1970 to 2100 is the same
as before.

The 1986, 1987 and 2016 books are from the British Library's Endangered
Archives Programme (EAP1485-1-3-127, EAP1485-1-6-123 and EAP1485-1-3-45). The
1986 book prints its तुला sankranti as "४।" with no pala (p15), so that sign
is left out; the 2028 one is the
archive.org item `nepali-patro-2028`. See [SOURCES.md](SOURCES.md).

What the readings show:

- **1986–1987 and 2016.** Each has its own per-sign pattern; the 1986 and
  1987 books agree to within 4 pala in every sign. With no books in between,
  1986–1987 and 2016 get separate eras.
- **2028–2044.** One per-sign table, repeated book to book to within
  2 pala (2028 sits 2 pala later than the rest): Karka −2.82,
  Makara +1.22.
- **2045–2059.** The 2060–2062 shape minus 0.43 ghati (fitted, −0.431).
- **2060–2062.** A small per-sign shape, mean 0, up to ±0.19.
- **2063 on.** Plain SS with exact sines, to within about a pala (rms
  0.83 pala over 53 readings). The Mesha (−0.06) and Mina (−0.03) that
  "lean early" in the table above are the table-sine error itself.

### 3.3 The eras

| From BS | Offset | Read from | Boundary set by |
|---|---|---|---|
| 1975 | 1986–1987 table | 1986 and 1987 books | first verified year |
| 2005 | 2016 table | 2016 book | month tables (any of 2005–2016 fits equally) |
| 2017 | 2028–2044 table | 2028, 2031–2044 books | month tables (any of 2017–2027 fits equally) |
| 2045 | shape − 0.43 | 2045–2059 books | 2044 and 2045 books |
| 2060 | shape | 2060–2062 books | 2059 and 2060 books |
| 2063 | none | 2063–2076 books | 2062 and 2063 books |

The two pre-2045 boundaries fall in years with no book read (1988–2015,
2017–2027). They are placed where the published month tables are best
matched. Every split in the ranges shown leaves the same 3 misses in
1975–2044 against `nepali-datetime`:

| Month | Ours | Tables | Margin |
|---|---|---|---|
| 1977/7 | 1920-10-17 | 1920-10-16 (nepali-datetime only) | 3 pala past the night midpoint |
| 1989/8 | 1932-11-16 | 1932-11-15 (nepali-datetime only) | 12 pala past it |
| 2018/9 | 1961-12-16 | 1961-12-15 (both tables) | 54 pala past it |

2018/9 is the clear one: only the 1975 era's table puts it on the 15th, so the
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

## 5. Ketaki planets

**Problem.** The books print Mars to Saturn to the arc-second. They are
neither the Surya Siddhanta (off by 1–8°) nor a modern ephemeris (off by
5–50′, with odd jumps in the daily motion). The committee's notices name
the केतकी ग्रहगणितम्, and implemented as written it lands within about a
minute. Five conventions take it the rest of the way. Four are discrete
choices; the fifth, the Sun's equation, has two fitted coefficients, which
come out as Kepler's terms for the Earth's eccentricity. Each was found
with the others fixed.

**Data.** `data/book_planets.csv`: 1841 values from both books, 69 read by
hand (all five planets on 2083 p21, Mercury on 2082 pp6-8 and 12), the rest OCR
cells two independent passes read identically (research/planets/book-ocr/).

**The conventions**, with the 90th-percentile error before and after:

| Convention | Alternative | Before → after |
|---|---|---|
| Planets at Kathmandu sunrise without refraction (2.7 min after the printed one) | the refracted sunrise | Mercury 90% 43″ → 37″; every planet improves (half an hour either way is far worse) |
| Ketaki's Sun for the शीघ्र step at mean sunrise (06:00 Kathmandu mean time) | at true sunrise | Mars 131″ → 69″, Jupiter 42″ → 23″ |
| The Sun's मन्दफल as `115.2′ sin k + 1.2′ sin 2k` | the table as printed; the table read from perigee | 90%: Mars 54″ / 12″ → 1.7″, Venus 191″ / 37″ → 5.8″, Mercury 146″ / 37″ → 4.5″ |
| Saturn without the two optional short-period terms (p159) | with them | Saturn 4.6′ → 6″ median |
| Mercury's distance from the table of verses 11-13; Mars's from the cosine of verse 8, unrounded | the cosine for both; the table for both | Mercury 229″ → 17″ median; Mars 63″ → 5″ median |

The Sun's equation is the surprising one. Ketaki tabulates it in whole
कला at 10° steps (p95). For a while the best fit was that table read
backwards from perigee, which flips its e² asymmetry (±1-2′ at 45° and
135°) and cut every planet's error several times over. It was still a
table: Mercury and Venus kept a −13″ to −18″·sin k residual, the signature
of an amplitude error. Fitting `A sin k + B sin 2k` directly gives
A = 115.2′, B = +1.2′: Kepler's 2e and 5e²/4 for e = 0.01676, the Earth's
eccentricity around 1900, with the e² term of the reversed reading. The
books' software evidently evaluates the curve, not the table. Ketaki's own
worked example uses the table as printed.

| Sun's equation | Mercury | Venus | Mars | Jupiter | Saturn |
|---|---|---|---|---|---|
| table as printed (median / 90%) | 84 / 146″ | 65 / 191″ | 27 / 54″ | 11 / 22″ | 7 / 12″ |
| table read from perigee | 15 / 37″ | 11 / 37″ | 5 / 12″ | 2 / 4″ | 0.8 / 2.9″ |
| `115.2′ sin k + 1.2′ sin 2k` | **1.8 / 4.5″** | **1.4 / 5.8″** | **0.9 / 1.7″** | **0.3 / 0.6″** | **0.2 / 0.5″** |
| exact Kepler, e = 0.01676 | 3.0 / 9.5″ | 2.3 / 4.6″ | 1.3 / 1.9″ | 0.3 / 0.8″ | 0.2 / 0.5″ |

**Mercury's table.** With the Sun right, every Mercury value more than 30″
off had its मन्दकेन्द्र within 10° of 30° or 330°, at any शीघ्र केन्द्र: the
signature of one wrong entry. The 30° entry is 96, not 97. The commentary
lists 96 (p157), and the verse's word is ऽङ्गनिधयः (अङ्ग 6, निधि 9), which
had been read as ऽग्निनिधयः. With 96, Mercury values more than 30″ off go
from 28 to 0. This also explains the "up to 3′ at the July 2025 station".

Mercury's distance was found from the book's own irregular daily motion
(2082 p7: steps of 1°09′52″ four days running, then 57′46″, 46′20″, 41′55″,
45′02″, 55′46″, …). The distance each day's value implies rises in exact
steps of 0.409 or 0.818 a day and sits flat at 45.00, 46.00 and 46.97: the
whole-number table, interpolated.

**Result** (`test_ketaki.py`, book − ours, arc-seconds):

| Planet | median | 90% | hand-read |
|---|---|---|---|
| Saturn | 0.2 | 0.5 | ≤1 |
| Jupiter | 0.3 | 0.6 | ≤1 |
| Mars | 0.9 | 1.7 | ≤2 |
| Venus | 1.4 | 5.8 | ≤1 |
| Mercury | 1.8 | 4.5 | ≤4 (49 values, including the July 2025 station) |

The books print whole arc-seconds, so most of this is rounding. Two
"misses" were the data: a hand-read ३४ taken for ३८ (2025-07-22) and an OCR
७ taken for १ (2025-09-10), both now corrected in `book_planets.csv`.

The tables are Ketkar's verses decoded (भूतसंख्या, digits right to left).
Where the commentary's digit list or a low-resolution reading differed, the
verse decided: Venus शीघ्रफल 140° is "द्विषट्सागराः" 462, Mercury's मन्दफल row
is 0, 32, 65, 97, 125, 153, 178, 199, 217, 229, 236, 236, 228, 211, 185, 149,
105, 54, 0. The full investigation is in research/planets/NOTES.md.

## 6. दिनमान

**Symptom.** The दिनमान column is not twice our sunrise half-day arc. Read
on 79 rows of the 2083 book (pp2, 5, 8, 11, 14, 21), book minus that runs
+0.4 pala in April, −0.7 in May, −2 in July, −3.2 in August to October and
−1 in January, with a scatter of 1.1 pala about the mean.

**Decomposition.** Written as a declination error plus a constant, the
residual is −1.6 pala (a horizon) and +8.9′·cos λ, with no semi-annual
term. A declination error of that form is the tropical Sun sitting
Δλ = 8.9′ / sin ε ≈ 22′ further along.

**Fit.** `surya.dinamana`: the SS true Sun at 06:00 Kathmandu mean time,
plus Lahiri plus 22′, horizon −30′, rounded to the pala. All 79 exact
(mean error +0.02 pala, scatter 0.30, which is the rounding).

| Variant | Exact (of 79) |
|---|---|
| 2 × sunrise half-day, −34′, truncated (before) | 21 |
| Modern (Meeus) Sun, best horizon | 50 |
| Ketaki's स्पष्ट रवि at mean sunrise, best horizon | 52 |
| SS + 22′ at sunrise, −30′, rounded | 71 |
| SS + 22′ at 06:00 Kathmandu mean time, −30′, rounded | **79** |

**Not shared.** The sunrise and sunset columns keep the plain frame. With
the shift they get 145 of 186 minutes instead of 154 (93 days, the same 5
pages plus `SUN`). The बेलान्तर keeps it too: with the shift it is 5 s off
the book, without it under 1 s. Where the 22′ comes from is open. The
month-start rule still uses `2 × half_day` with each book's horizon, since
the eras were read against it.

## 7. Exact sines

The SS tabulates 24 sines and reads between them linearly. That shrinks the
equation of centre by up to 0.05% (h²/8 for 3.75° steps), which is 4″ of
Sun and 9″ of Moon. Three independent sets of book data reject the table:

| Data | Table | Exact |
|---|---|---|
| The Sun's pada and sign entries, 2083 pp2, 11, 17, 25 (16) | 3 to the minute | **16** |
| Tithi, nakshatra and yoga ends, 2082 and 2083 (228; apogee refitted) | 191 | **226** |
| Sun at sunrise, स्पष्ट ग्रह (30 days) | rms 1.7″, worst 3.7″ | **rms 0.9″, worst 1.8″** |

The 2063–2076 sankrantis agree (section 3.2). `surya._manda` uses
`math.sin` and `math.asin`.
