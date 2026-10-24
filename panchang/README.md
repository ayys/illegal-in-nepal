# राष्ट्रिय पञ्चाङ्ग generator

This computes Nepal's national panchang, the yearly almanac published by the
Nepal Panchang Nirnayak Bikas Samiti, from first principles. The Sun and
Moon come from the Surya Siddhanta. Sunrise and everything else that needs
the equinox uses the Lahiri ("Ketaki") frame.

The output is JSON plus a PDF laid out like the printed book. It reproduces
the 2082 and 2083 books to the minute on most entries. Every BS month start
from 1975 to 2083 matches the published tables, except where the tables
themselves are wrong.

The astronomy and calendar code is small (`surya.py` and `panchanga.py`,
about 840 lines including comments, standard library only) and
written to be read. The docs explain every step in enough detail to write
your own implementation in another language.

## Quickstart

```sh
cd panchang
python3 -m unittest test_surya test_panchanga test_editorial test_ketaki test_rail   # ~15 s, no dependencies
./generate.py 2083 --no-pdf                       # JSON for every fortnight → output/
./generate.py 2083 --page 21                      # one fortnight, JSON + PDF (needs weasyprint)
./generate.py 2083 --config 2083.json             # with festival notes, or overrides
./build_status.py                                 # writes status.html (needs nepali-datetime, nepali)
```

`generate.py` and `build_status.py` are [uv](https://docs.astral.sh/uv/)
scripts, so `./generate.py` installs their dependencies on first run.
`python3 generate.py 2083 --no-pdf` also works with no dependencies at all.

As a library:

```python
import panchanga
pages = panchanga.year(2083)          # list of fortnight pages
pages[0]["header"]["lunar_month"]     # 'वैशाख'
pages[0]["rows"][0]["tithi"]          # {'index': ..., 'ends': [{'ghati': .., 'pala': .., 'clock': [h, m]}], ...}
panchanga.month_starts(2083)          # 13 dates: बैशाख 1 … चैत 1, बैशाख 1 of 2084
```

## Files

| File | What it does |
|---|---|
| `surya.py` | Astronomy: SS mean and true Sun and Moon, sunrise, sunset, दिनमान, equation of time, lagna, Rahu, and a generic "when does this angle cross a multiple of N" solver |
| `panchanga.py` | Calendar: day rows (tithi, nakshatra, yoga, karana, आनन्दादि, …), solar month starts (the sankranti day rule and eras), lunar months, adhik masa, page headers, the year layout |
| `ketaki.py` | Mars to Saturn by the केतकी ग्रहगणितम्, with the books' conventions |
| `editorial.py` | Samvatsara (Jovian, from SS mean Jupiter), पापर्क्षाणि and पापांश |
| `render.py` | HTML/PDF typesetting in the book's page layout |
| `generate.py` | Command line: year → JSON and PDF |
| `build_status.py` | Writes `status.html`, a dashboard comparing the output with the books and the BS tables |
| `test_surya.py` | Unit tests for the astronomy |
| `test_panchanga.py` | Book regression tests and calendar invariants |
| `test_editorial.py` | Samvatsara, पापर्क्षाणि and पापांश against the books |
| `test_ketaki.py` | Mars to Saturn against Ketaki's worked example and both books |
| `test_rail.py` | The ग्रहचार rail, the राशि प्रवेश and status boxes, and the kundali against the 2083 book |
| `data/book_planets.csv` | Mars to Saturn as printed, hand-read and OCR, with pages |
| `data/book_rail.csv` | The rail's planet lines as printed, 2083 pp2-9, 18, 21, 22 |
| `data/book_sankrantis.csv` | Sankranti moments read from old books, with PDF pages |
| `data/month_starts.csv` | Month starts that settle disagreements between references, with sources |
| `research/` | Working scripts and notes from reading the old books (`oldbooks/fetch_ocr.sh`, `oldbooks/crops.py`, `oldbooks/read/`); the PDFs and page images are git-ignored and re-downloadable |

## Documentation

| Doc | Read it for |
|---|---|
| [docs/ALGORITHM.md](docs/ALGORITHM.md) | Every column, step by step, with formulas and a worked example for one day |
| [docs/CALIBRATION.md](docs/CALIBRATION.md) | The fitted things (Moon apogee −1.71°, Rahu offset, sankranti eras, each book's sunrise convention, the दिनमान routine, exact sines) and the evidence for each |
| [docs/VERIFICATION.md](docs/VERIFICATION.md) | Match rates, the known errors in the reference tables, open cases |
| [docs/EDITORIAL.md](docs/EDITORIAL.md) | Samvatsara, पापर्क्षाणि and पापांश: what they are, the rules, the evidence |
| [docs/SOURCES.md](docs/SOURCES.md) | Every book and page used, with URLs |

## The model in one paragraph

- **Positions.** Mean longitudes come from the SS revolution numbers counted
  from the Kali epoch. One manda correction, with exact sines rather than
  the SS's 24-row table, gives the true Sun and Moon. The Moon's apogee is
  shifted by −1.71°.
- **Limbs.** Tithi, nakshatra, yoga and karana are 12°, 13°20′, 13°20′ and
  6° divisions of Moon − Sun, Moon, and Moon + Sun. Their ends are found by
  Newton's method and printed in ghati and pala after Kathmandu sunrise.
- **Sunrise.** The SS true Sun plus the Lahiri ayanamsha, with the modern
  obliquity and a −34′ horizon.
- **Month starts.** A BS month starts on the civil day its sankranti belongs
  to under the night-midpoint rule: Karka by sunrise, Makara by sunset. Each
  book era has a small offset on the sankranti.
- **Lunar months.** They are amanta and named by the sankranti they
  contain. One with no sankranti is adhik.
- **Mars to Saturn.** By the केतकी ग्रहगणितम्, as the committee requires: an
  1878 epoch, mean motions, and 10° tables read by linear interpolation,
  with five conventions read off the books' own tables. Median error 0.2″
  (Saturn) to 1.8″ (Mercury) over 1841 printed values.

## Data file formats

**`data/book_sankrantis.csv`:** one row per sankranti read from a book.

| Column | Meaning |
|---|---|
| `bs_year` | BS year the sankranti opens a month of (2077 for the Mesha printed at the end of the 2076 book) |
| `sign` | Sign being entered, 0 = Mesha |
| `sign_name` | For readability |
| `ghati`, `pala` | Time after sunrise of `sunrise_day`, as printed |
| `sunrise_day` | Gregorian date of the book row the sankranti is printed in |
| `book` | Which book (BS year) |
| `pdf_page` | 1-based page in the PDF (blank if not located) |
| `source` | PDF URL |

**`data/book_planets.csv`:** one row per Mars–Saturn value read from a
book's स्पष्ट ग्रह table.

| Column | Meaning |
|---|---|
| `date` | Gregorian date of the row (Kathmandu sunrise) |
| `body` | `mars`, `mercury`, `jupiter`, `venus` or `saturn` |
| `longitude` | As printed: sign, degree, minute, second |
| `source` | `hand` (read off the page) or `ocr` (two OCR passes agree) |
| `book`, `pdf_page` | Which book and page |

**`data/month_starts.csv`:** one row per month whose first day is settled
by a primary source.

| Column | Meaning |
|---|---|
| `bs_year`, `month` | BS year and month, 1 = बैशाख |
| `first_day` | Gregorian date of गते 1 |
| `source` | URL of the book or calendar, or the library tables that agree |
| `pdf_page` | Page in the book, when it is a book |
| `note` | Why: sankranti time against the boundary, or which table was wrong |

## Not computed

- **Festival and vrat notes.** These are editorial and come from the
  `--config` JSON. Samvatsara, पापर्क्षाणि and पापांश are computed
  (`editorial.py`, [docs/EDITORIAL.md](docs/EDITORIAL.md)); a value in the
  config overrides them.

See the component matrix in `status.html` for the full list.
