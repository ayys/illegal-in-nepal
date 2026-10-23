# Mars–Saturn: the national books use केतकी ग्रहगणितम्

The method now lives in `panchang/ketaki.py` (tested by `test_ketaki.py`,
documented in docs/ALGORITHM.md section 9 and docs/CALIBRATION.md section
5). `research/planets/ketaki.py` is the research copy with the variants
that were tested and rejected.

The committee's notices (research/npns/) say so: from 2083 planets must be
computed "केतकीय ग्रहगणितबाट", and in 2082 by "ज्योतिर्गणितम् तथा केतकी
ग्रहगणितम्". The text is V. B. Ketkar's karana of 1898, read from the 2001
Chaukhamba reprint with Datta Raj's commentary:
https://archive.org/details/KetakiGrahaGanitam (PDF page = book page + 6).

`ketaki.py` implements it. Against two years of the books' स्पष्ट ग्रह tables
(OCR cells two independent passes agree on, `book-ocr/agreed.json`), at
Kathmandu sunrise, book − Ketaki:

| Planet | median | 90% | page 21, hand-read |
|---|---|---|---|
| Saturn | 1″ | 3″ | 0″ |
| Jupiter | 2″ | 5″ | +2 … +4″ |
| Mars | 5″ | 15″ | +10 … +16″ |
| Venus | 11″ | 45″ | −8 … −17″ |
| Mercury | 17″ | 45″ | 25″ median over 43 hand-read days (`mercury/hand.csv`) |

The book prints whole arc-seconds, so Saturn and Jupiter are exact and the
other three within a fraction of an arc-minute.

## The procedure (ketaki.py has the page numbers)

1. **Mean longitudes**: क्षेपक at Shaka 1800 elapsed, चैत्र शुक्ल प्रतिपदा
   (1878-04-03), Ujjain mean sunrise; whole 6940-day चक्रs by ध्रुवक, the
   days inside the current चक्र by Ketaki's per-day formulas (p53-62, e.g.
   Mars 10A/19° − 10A/73′). With this the worked example's mean Mars,
   Mercury and Venus come out to the arc-second. The epoch Sun and Moon
   equal the Lahiri mean Sun and Moon to 0.01°: no ayanamsha step.
2. **Jupiter and Saturn**: the 918-year कर्ष by integer Shaka year. Not
   Saturn's two optional short terms (with them Saturn is 4.6′ off).
3. **मन्दफल**: 10° tables, linear interpolation.
4. **शीघ्र**: केन्द्र = heliocentric − Ketaki's true Sun; 10° tables, linear
   interpolation (exact triangles make Jupiter 77″, Saturn 76″). Mars: फल ×
   शीघ्रकर्ण / (r + शीघ्रकर्ण − 152), r = 152 + 14 cos(k + मन्दफल/2)
   unrounded (verse 8); Mercury: फल × r / 39 with r **interpolated in the
   whole-number distance table of verses 11-13** (p167: 47, 47, 46, 46, 45,
   45, 44, 43, 42, 40, 39, 38, 37, 35, 33, 32, 32, 31, 31). Using that table
   for Mars too makes Mars worse (5″ → 63″), though Ketaki's own Mars example
   takes its 158 from it.
5. **Time**: planets at true Kathmandu sunrise; **the Sun for step 4 at
   mean sunrise** (06:00 Kathmandu mean time). Sun at true sunrise: Mars's
   90% error is 131″; at mean sunrise 69″.
6. **The Sun's row read from the other end**: the books index the Sun's
   मन्दफल by the केन्द्र counted from perigee, i.e. Ketaki's p95 row
   reversed. A likely cause: Ketaki works with the Earth ("सूर्यः स्थिरः
   भूर्भ्रमति") and its रवि-उच्च 2:18:41 is the Earth's perihelion; read as
   the Earth's उच्च, the row runs backwards. It only flips the row's e²
   asymmetry (±1-2′ at 45° and 135°), but that was the whole "~2′ Sun
   offset": Mars 69″ → 15″, Venus 191″ → 45″, Jupiter 23″ → 5″, Saturn 12″ →
   3″ (90% figures). Ketaki's own example uses the row as printed.

## Tables: verse, not digits

Every row was checked against its verse (भूतसंख्या, digits right to left).
Two of my low-resolution readings were wrong, and the verse caught them:
Venus शीघ्रफल 140° is "द्विषट्सागराः" 462 (I had 463; this was the "Venus
drift"), and Mercury's मन्दफल row is 0, 32, 65, 97, 125, 153, 178, 199, 217,
229, 236, 236, 228, 211, 185, 149, 105, 54, 0.

## Why the book's planets looked strange

- **Breaks every 10–11 days**: each time the शीघ्र केन्द्र crosses a 10°
  table row, the slope of the interpolation changes (Jupiter 11.1 days,
  Saturn 10.5, Mars ~22).
- **The Mars "station" on 2027-01-15/16** (rail: वक्री मङ्गल माघ 1): the
  शीघ्र केन्द्र crosses the 200° row; Ketaki's daily motion goes +3.05,
  +0.14, −12.48′, the book's +3.07, +1.50, −12.42′.
- **Slow errors of tens of ′ against the real sky**: Ketaki's mean distances
  for Jupiter, Venus, Saturn and the Earth, and its 1878 elements.

## Mercury: the distance table

The book's Mercury moves irregularly (2082 p7, daily steps 2025-06-26 →
07-10: 1°16′46″, 1°09′52″ ×4, 57′46″, 46′20″, 41′55″, 45′02″, 55′46″, …).
Hand-reading pages 6-8 and solving for the distance each day's value implies
showed the cause: r rises in exact steps of 0.409 or 0.818 a day and sits
flat at 45.00, 46.00, 46.97 — a whole-number table at 10° of the मन्दकेन्द्र
(4.09°/day), linearly interpolated. That is the स्पष्ट मन्दकर्ण table of
verses 11-13. With it Mercury goes from 229″ to 17″ (median) on the agreed
OCR cells. What remains is a smooth ±30-50″ drift and up to ~3′ on a few
days at the July 2025 station (2025-07-21, 07-23), where a node crossing
falls a fraction of a day apart.

## Files

- `ketaki.py` — the method, with the national books' conventions as
  defaults; `python3 ketaki.py` checks it against Ketaki's worked example
  (Shaka 1815 चैत्र शुक्ल १५: mean longitudes exact, heliocentric within 12″;
  its Sun differs by 1′43″ because the example reads the Sun row as printed).
- `vsbook.py`, `variants.py`, `invert.py`, `bins.py`, `helioerr.py`,
  `sunerr.py`, `sunfit.py`, `ahargana.py` — the comparisons behind the notes.
- `mercury/hand.csv` — Mercury hand-read from 2082 pp6-8 (2025-06-12 →
  07-24); `mercury/compare.py` compares it with Ketaki day by day.
- `book-ocr/` — OCR of the books' tables. `agreed.json` keeps cells two OCR
  passes read identically; `ketaki_clean.json` keeps cells within 15′ of
  Ketaki; the earlier `clean.json` dropped days near breaks.
