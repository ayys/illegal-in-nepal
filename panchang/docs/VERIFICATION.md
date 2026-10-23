# Verification: how well it matches, and where the references are wrong

All numbers are from `build_status.py` (which writes `status.html`) and the
two test files. Re-run them after any change.

```
python3 -m unittest test_surya test_panchanga test_editorial test_ketaki test_rail   # all tests
/path/to/venv/bin/python build_status.py          # needs nepali-datetime and nepali
```

## Day rows against the 2083 book

| What | Match | Data |
|---|---|---|
| Tithi, nakshatra and yoga ends (5 fortnights) | 116/139 to the exact minute, 139/139 within 1 minute | `BOOK` (2083 pp2–3, 16, 21) |
| Number of ends per day (stacked ends, अहोरात्र) | 0 count mismatches | the same |
| Sunrise and sunset clock | 61/66 exact, 66/66 within 1 minute | `SUN` (2083 pp2, 20, 21) |
| दिनमान | 7/15 exact, 15/15 within 2 pala | `DINAMANA` (2083 p21) |
| Karana names and ends | all | `KARANAS` (2083 pp2, 21) |
| आनन्दादि | 15/15 | `ANANDADI` (2083 p21) |
| Lagna starts | all within 1 minute | `LAGNA` (2083 p21) |
| Sun, Moon, Rahu spashta | Sun within 4″, Rahu within 3″, Moon within 15″ (p21) | `SPASHTA`, `SUN_MOON` |
| Mars to Saturn spashta (2082 and 2083, 1841 values) | median 1″ Saturn, 2″ Jupiter, 5″ Mars, 11″ Venus, 16″ Mercury; 90% within 3, 5, 15, 45, 41″ | `data/book_planets.csv`, `test_ketaki.py` |
| Rail planet lines (84 on 11 pages) | every line found, same गते; 78 within 20 minutes, the rest within the planet's few-arc-second error (Mars at its station: 2½ h); stations within a day | `data/book_rail.csv`, `test_rail.py` |
| राशि प्रवेश box (17 pages) | 14 exact; the other 3 are where the book's box disagrees with its own rail | `test_rail.py` |
| बेलान्तर | within 2 seconds | `SPASHTA` |
| Page count and layout | 26 pages, 365 days, headers on 6 pages | `HEADERS` |

The 2082 book (pp3, 20) matches to the same tolerances with the same
constants.

The minute-level misses are consistent with rounding in the book's own
worksheets. No constant was found that removes them without breaking
others.

## Month starts against the published BS tables

`panchanga.month_starts` gives the first day of every month. Here is how it
compares with the lookup tables in two Python libraries:

| Table | BS years | Match |
|---|---|---|
| nepali-datetime | 1975–2083 | 1304/1308 |
| py-nepali | 2000–2083 | 1006/1008 |
| py-nepali | 2084–2099 | 192/192 |
| nepali-datetime | 2084–2100 | 139/204 |

Two of the disagreements up to 2083 (1993 साउन, 2062 जेठ) were checked
against a book or an independent calendar, and the library is wrong. The
other three (1977/7, 1989/8 and 2018/9) fall in years with no book read;
the eras there come from the nearest books (1986–1987, 2016, 2028), so these are
the model's open cases, listed in
[CALIBRATION.md](CALIBRATION.md#33-the-eras).

## Known errors in the reference tables

Each case below is a row in [`data/month_starts.csv`](../data/month_starts.csv),
and `test_documented_month_starts` checks it.

| Month | Table says | Correct | Evidence |
|---|---|---|---|
| 1993 साउन | nepali-datetime: Jul 16, 1936 | **Jul 15, 1936** | Drik Panchang ([1993 calendar](https://www.drikpanchang.com/nepali/calendar/nepali-patro.html?solar-date=01/04/1993)) and [nepali-calendar.com/1993/Shrawan](https://nepali-calendar.com/1993/Shrawan) |
| 2062 जेठ | py-nepali: May 14, 2005 | **May 15, 2005** | The 2062 book prints वृषेऽर्कः 46।44 on the May 14 row with दिनमान 33।23, so its night midpoint is 46।41½ and the sankranti goes to the next day (archive.org 2062.pdf, PDF page 5) |
| 2084–2100, 65 months | nepali-datetime | as py-nepali | Drik Panchang agrees with py-nepali (and us) in 64 of the 65; see 2093 माघ below |

The future part of the nepali-datetime table (2084 on) disagrees with
py-nepali in 65 months, nearly all by one day. Drik Panchang was checked for
every one of them. It sides with py-nepali, and with this code, in all but
one.

## The one open case: 2093 माघ

- **Who says what.** Drik Panchang puts 2093 माघ 1 on January 14, 2037.
  py-nepali and this code put it on January 15.
- **Why it is close.** The Makara sankranti falls about 1 pala (24 s) after
  sunset. By the Makara rule the month starts the next day.
- **What would flip it.** Any difference in sunrise, sunset or the Sun's
  position larger than that would.

It is a knife edge; the date depends on which model you trust to 24
seconds. It stays at January 15 because:

- this code reproduces every printed book since 2070 to within 4 pala;
- py-nepali, an independent table, agrees.

## Before 1975

`VERIFIED_FROM = 1975`. Earlier years are generated with the 1975 era
offsets, and `generate.py` prints a warning. The day rule and the SS
positions are presumably the same, but nothing before 1975 has been
compared.

## What the tests cover

**`test_surya.py`** covers the astronomy primitives:

- the time scale and the Kali epoch;
- the sine table, its symmetry and its inverse;
- the mean and true motions, and the bounds of the equation of centre;
- the Lahiri rate;
- that sankrantis, tithis and new moons are found in the right numbers and
  order;
- sunrise order, seasonal day lengths, the range of the equation of time,
  and the lagna table.

**`test_panchanga.py`** has three groups:

- **Book values** (`BookTest`): every transcribed number from the 2082
  and 2083 books, as listed above.
- **Month starts** (`MonthStartTest`):
  - every sankranti reading in `data/book_sankrantis.csv`, within the
    tolerances in [CALIBRATION.md](CALIBRATION.md#33-tolerances-used-in-the-tests);
  - every documented month in `data/month_starts.csv`;
  - that each year's last date is the next year's first, for 1970–2099;
  - month and year lengths, and Mesha sankranti dates;
  - the era lookup;
  - the Karka, Makara and night-midpoint rules at their exact boundaries.
- **Structure** (`DayRowTest`, `YearLayoutTest`):
  - karana and 28-nakshatra numbering, the arc format, tithi numbering;
  - that ends fall inside their day and lagnas are in order;
  - that every day appears once, गते restarts each month, there is one
    paksha per page, and pages are numbered from 2.

**`test_ketaki.py`** covers Mars to Saturn:

- Ketaki's own worked example (Shaka 1815 चैत्र शुक्ल १५): mean longitudes
  to 1″, heliocentric longitudes to 20″, the कर्ष, the Shaka year;
- every hand-read value in `data/book_planets.csv`, per planet (Saturn 2″,
  Jupiter 6″, Mars and Venus 20″, Mercury 70″, 3′ on four days at its July
  2025 station);
- the OCR values as a whole: median and 90th percentile per planet;
- that `ketaki.longitude` equals the sunrise value at sunrise and is linear
  between sunrises.

**`test_editorial.py`** covers samvatsara, पापर्क्षाणि and पापांश; see
[EDITORIAL.md](EDITORIAL.md).
