# OCR of the books' स्पष्ट ग्रह tables (superseded findings: see ../NOTES.md)

The स्पष्ट ग्रह table prints every planet for every day. The book PDFs have
no text layer, so `batch.py` renders each page at 400 dpi and `cells.py`
OCRs the table cell by cell (tesseract, Devanagari digits). `align.py`
finds each row's date from the Moon column, and `resid.py` drops cells that
jump more than 3′ from their neighbours' median. `clean.json` holds the
result: 450–520 days per planet for Mars, Jupiter, Venus and Saturn, and
about 200 for Mercury (too fast for the filter).

Findings (book − Swiss Ephemeris, Lahiri, at Kathmandu sunrise):

- Errors change slowly over months: Mars −22′ to +49′, Jupiter −15′ to
  +21′, Saturn −1′ to −18′, Venus up to ±40′, and more near inferior
  conjunction. They are not Surya Siddhanta (off by 1–8°).
- Fitting corrected Keplerian elements (each planet plus Earth) leaves
  5–23′ rms and gives implausible corrections (Jupiter L +1.7°, Venus ϖ
  −29°), so the book does not use a smooth orbit theory.
- The book's daily motion is piecewise smooth, with breaks every 10–11 days
  whose phase differs from planet to planet. They don't fall on fixed गते,
  tithis, or 10° steps of the Sun. Quadratic interpolation between the breaks
  reproduces the in-between days to a median of about 20–30″.
- Mars turns retrograde in the book on 2027-01-15/16 (rail: "वक्री मङ्गल",
  माघ 1 28:22), going from +3′/d straight to −12′/d. The real station is
  about 2027-01-10/11.

So the book's planets look like values computed on anchor days, possibly
from tables with a fixed station date, then interpolated by hand. The
anchor days and their source are still unknown.
