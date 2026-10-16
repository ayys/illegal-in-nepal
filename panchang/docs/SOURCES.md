# Sources

Every value the code is checked against comes from one of the sources below.
Each test dict and data row records the page it came from.

## The national panchang books (राष्ट्रिय पञ्चाङ्ग)

These are published by the Nepal Panchang Nirnayak Bikas Samiti (नेपाल
पञ्चाङ्ग निर्णायक विकास समिति).

### 2083 (FORMAT-2083-A): the main reference

- **URL:** <https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf>
- **Page numbering:** PDF page = book page. Page 1 is the cover, and
  fortnights start on page 2.

| Book page | Fortnight | What was read | Test data (`test_panchanga.py`) |
|---|---|---|---|
| 2–3 | वैशाख शुक्ल and कृष्ण (Apr 14 – May 1, 2026) | Tithi, nakshatra and yoga ends; karana; sunrise and sunset; Sun and Moon spashta | `BOOK`, `KARANAS`, `SUN`, `SUN_MOON`, `HEADERS` |
| 2, 4–7, 20 | वैशाख, शुद्ध/अधिक ज्येष्ठ, पौष | Page headers: lunar month (with अधिक/शुद्ध), paksha, Nepal Sambat, Gregorian span, ritu | `HEADERS` |
| 16 | कार्तिक कृष्ण (Oct 27 – Nov 9, 2026) | Limb ends; Sun and Moon spashta | `BOOK`, `SUN_MOON` |
| 20 | पौष कृष्ण | Sunrise and sunset | `SUN` |
| 21 | पौष शुक्ल (Jan 8 – 22, 2027) | Every column: limb ends, karana, आनन्दादि, दिनमान, sunrise and sunset, lagna table, स्पष्ट ग्रह (Sun, Moon, Rahu), बेलान्तर, the Sun's pada rail | `BOOK`, `KARANAS`, `ANANDADI`, `DINAMANA`, `SUN`, `LAGNA`, `SPASHTA`, `SUN_PADAS`, `SUN_MOON` |

The page layout in `render.py` (1007.01 × 555.591 pt, column widths) was
measured from this PDF.

### 2082 (npnbs_2082): cross-year check

- **URL:** <https://giwmscdnone.gov.np/media/pages/files/npnbs_2082_ussfian.pdf>
- **Page numbering:** the same as 2083.

| Book page | Fortnight | What was read | Test data |
|---|---|---|---|
| 3 | वैशाख शुक्ल (Apr 2025) | Limb ends; स्पष्ट ग्रह | `BOOK_2082`, `SPASHTA_2082` |
| 20 | माघ कृष्ण (Jan 2026) | Limb ends; स्पष्ट ग्रह; Makara sankranti after sunset (2082 माघ starts Jan 15) | `BOOK_2082`, `SPASHTA_2082`, `data/month_starts.csv` |

The 2082 book was not used to fit anything except `MOON_APOGEE_CORRECTION`
and `RAHU_OFFSET`, which it shares with 2083 (see
[CALIBRATION.md](CALIBRATION.md)).

### Older books: the archive.org "Nepali patro collection"

- **Item:** <https://archive.org/details/2081_20240828>
- **Download pattern:** `https://archive.org/download/2081_20240828/{year}.pdf`
- **Format:** scans, one image per PDF page. In
  [`data/`](../data/) files, `pdf_page` is the 1-based PDF page.

Books read so far, and what was read from them:

| BS | Read for | Rows |
|---|---|---|
| 2031, 2032, 2033, 2035 | Sankranti ghati and pala for most signs | `data/book_sankrantis.csv` (26 rows) |
| 2035 | ज्येष्ठ start (p4); माघ start, Makara after sunset (p21) | `data/month_starts.csv` |
| 2046 | Kumbha sankranti, फागुन start (p21) | both CSVs |
| 2051 | 9 sankrantis; साउन start, Karka before the next sunrise (p8) | both CSVs |
| 2062 | 11 sankrantis; जेठ start (p5); कात्तिक start (p15) | both CSVs |
| 2066 | Mina sankranti exactly at the night midpoint, चैत start (p25) | both CSVs |
| 2073 | Kumbha sankranti, फागुन start (p24) | both CSVs |
| 2076 | 9 sankrantis, including 2077 Mesha; पुस start (p20) | both CSVs |

Other books in the item:

- **Unreadable:** 2016, 2020, 2022, 2025, 2028 and 2029 are in the item, but
  the scans are too low-resolution to read pala. Better copies of 2016 and
  2028 are listed below.
- **Read for sankrantis:** 2031–2033, 2035, 2038–2046, 2051, 2058–2063,
  2065–2073 and 2076. 2064 prints clock times only, but its दिनमान column
  fixes its sunrise convention.
- **Not yet read:** 2036, 2037, 2047–2050, 2052–2057, 2074, 2075 and
  2077–2079. None of them sits at an era boundary any more; the open
  boundaries are in 1987–2015 and 2017–2027, which this item doesn't cover
  readably.

### Older books elsewhere

| Book | Where | Used for |
|---|---|---|
| 1986 | British Library Endangered Archives Programme, <https://eap.bl.uk/archive-file/EAP1485-1-3-127> | the 1975 era (12 sankrantis) |
| 2016 | <https://eap.bl.uk/archive-file/EAP1485-1-3-45> | the 2005 era (12 sankrantis) |
| 2028 | <https://archive.org/details/nepali-patro-2028> | the 2017 era, with the 2031–2044 books (12 sankrantis) |

The EAP1485 project holds more Nepali almanacs of this period. A readable
book from 2017–2027 (especially 2018) or 1987–2015 would replace the two
boundaries that are still set by the month tables.

**How to read a book.** Render a page at 300 dpi and OCR it:

```
pdftoppm -r 300 -f N -l N book.pdf page
tesseract page.ppm out -l nep
```

OCR of these scans is noisy. Use it only to *find* the page, by searching
the text for संक्रान्ति. Then read the ghati and pala from the image itself.
The value counts from the sunrise of the row it is printed in, so each row
of `book_sankrantis.csv` stores it with `sunrise_day`, the Gregorian date of
that row.

## Online calendars (checked by hand)

| Site | URL pattern | Used for |
|---|---|---|
| Drik Panchang | `https://www.drikpanchang.com/nepali/calendar/nepali-patro.html?solar-date=01/MM/YYYY` | 1993 साउन; the 64 future months where the two libraries disagree |
| nepali-calendar.com | `https://nepali-calendar.com/{BS year}/{month name}` (BS 1969 on) | 1993 साउन (e.g. <https://nepali-calendar.com/1993/Shrawan>) |

Every date taken from them is a row in `data/month_starts.csv`, with the
URL in the `source` column.

## BS lookup tables (Python libraries)

These are hand-maintained tables of month lengths. They are compared
against in `build_status.py`, not used by the generator.

| Library | PyPI | Range compared |
|---|---|---|
| nepali-datetime | <https://pypi.org/project/nepali-datetime/> | BS 1975–2100 |
| py-nepali | <https://pypi.org/project/nepali/> | BS 2000–2099 |

## Astronomy references

- **Surya Siddhanta.** Chapter 1 (mean motions, epoch) and chapter 2 (sine
  table, manda correction). The standard English translation is Burgess
  (1860), which is in the public domain.
- **Lahiri ayanamsha.** 23°51′25.53″ at J2000 with IAU 1976 precession, as
  in the Swiss Ephemeris (`SE_SIDM_LAHIRI`).
- **Mean lunar node and obliquity.** Meeus, *Astronomical Algorithms*,
  2nd ed., chapter 22.
