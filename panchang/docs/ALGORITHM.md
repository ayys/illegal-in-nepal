# How the राष्ट्रिय पञ्चाङ्ग is computed

This is a step-by-step description of everything `surya.py` and
`panchanga.py` do, written so that you can build your own implementation
from it without reading the Python. Every step was checked against the
printed books (see [SOURCES.md](SOURCES.md)). Where a value was *fitted*
rather than taken from a textbook, the evidence is in
[CALIBRATION.md](CALIBRATION.md). How well the result matches is in
[VERIFICATION.md](VERIFICATION.md).

A worked example for one day (sunrise on 8 January 2027 = पौष २४, 2083,
2083 book page 21) runs through the whole document. If your implementation
gives the same intermediate numbers, it will give the same book.

## Contents

1. [Units and conventions](#1-units-and-conventions)
2. [Time scale](#2-time-scale)
3. [Mean motions (Surya Siddhanta)](#3-mean-motions-surya-siddhanta)
4. [True Sun and Moon: the manda correction](#4-true-sun-and-moon-the-manda-correction)
5. [The Lahiri frame: sunrise, sunset, दिनमान, बेलान्तर](#5-the-lahiri-frame-sunrise-sunset-दिनमान-बेलान्तर)
6. [Finding end times](#6-finding-end-times)
7. [Day-row columns](#7-day-row-columns)
8. [Lagna table](#8-lagna-table)
9. [स्पष्ट ग्रह: Sun, Moon, Rahu, Mars to Saturn](#9-स्पष्ट-ग्रह-sun-moon-rahu-mars-to-saturn)
10. [Solar months (BS month starts)](#10-solar-months-bs-month-starts)
11. [Lunar months and adhik masa](#11-lunar-months-and-adhik-masa)
12. [Page layout and headers](#12-page-layout-and-headers)
13. [What is not computed](#13-what-is-not-computed)

---

## 1. Units and conventions

| Unit | Value |
|---|---|
| 1 day | 60 ghati (घटी) |
| 1 ghati | 60 pala (पला) = 24 minutes |
| 1 pala | 24 seconds; 2.5 pala per minute |
| Time zone | Nepal Standard Time, UTC+5:45 |
| Place | Kathmandu, 27.7° N, 85.3167° E |

- **Civil day.** A row of the book is the day from one sunrise at Kathmandu
  to the next. Everything "on" a day is what is current at its sunrise, plus
  whatever ends before the next sunrise.
- **घटी।पला.** End times are printed as ghati and pala *after that day's
  sunrise*: `palas = round((jd_end − jd_sunrise) × 1440 × 2.5)`.
- **Clock times.** They are printed as hours and minutes after the civil
  date's midnight (NST). Times after midnight continue past 24, so 27:31 is
  3:31 the next morning. End times are rounded to the nearest minute;
  sunrise is rounded *up* and sunset *down*.
- **Longitudes.** The Surya Siddhanta (SS) gives *sidereal* longitudes
  directly. The book prints them as `sign।degree।minute।second`, signs
  counted from Mesha = 0, so 8।22।59।25 is 8 × 30 + 22°59′25″ = 262.99°.
- **Indexing.** Code indices start at 0: tithi 0 is शुक्ल प्रतिपदा, sign 0
  is Mesha, nakshatra 0 is Ashvini, BS month 0 is बैशाख. Data files use
  1-based BS months.

## 2. Time scale

Everything is computed in Julian days (JD), counted in UT with no ΔT. The SS
counts civil days, and the books fit with plain UT.

- `JD = 2440587.5 + unix_seconds / 86400`
- **Kali epoch.** This is midnight at Ujjain beginning 18 February 3102 BCE
  (proleptic Julian). Greenwich midnight of that date is JD 588465.5, and
  Ujjain lies 75.7682° east, so `KALI_JD = 588465.5 − 75.7682 / 360`.
- **Ahargana.** The day count since the Kali epoch is `JD − KALI_JD`. It is
  fractional; we never round it to whole days.

> Example: sunrise on 2027-01-08 is JD 2461413.550235 (06:57:20 NST), so
> the ahargana is 1,872,948.26070.

## 3. Mean motions (Surya Siddhanta)

The SS (chapter 1) gives the number of civil days in a mahayuga (4,320,000
years) and how many revolutions each body completes in that time:

| Body | Revolutions per mahayuga |
|---|---|
| Civil days | 1,577,917,828 |
| Sun | 4,320,000 |
| Moon | 57,753,336 |
| Moon's apogee | 488,203 |

The mean longitude is the fractional part of
`ahargana × revolutions / days`, times 360°. At the Kali epoch every mean
longitude is 0°, except the apogees:

- **Moon's apogee.** It is 90° at Kali.
- **Sun's apogee.** It moves only 387 revolutions per kalpa (1000
  mahayugas), so it has to be counted from creation. 1,955,880,000 solar
  years passed from creation to Kali, each `1,577,917,828 / 4,320,000` days
  long. Multiply by `387 / (1000 × 1,577,917,828)`, keep the fraction, and
  you get 77.13° at Kali. Use exact rational arithmetic: the integer part is
  about 757,000 revolutions, and a double cannot keep the fraction to
  arc-seconds. The apogee then advances at the same kalpa rate; it is
  77.295° in 2027.

**Calibration.** The Moon's apogee needs a fixed **−1.7°** added to the
textbook value. This is the only change to the SS Moon; see
[CALIBRATION.md](CALIBRATION.md#1-moons-apogee-17).

> Example (2027-01-08 sunrise):
> mean Sun 262.77766°, Sun's apogee 77.29537°;
> mean Moon 265.83522°, Moon's apogee 264.42824°, corrected 262.72824°.

## 4. True Sun and Moon: the manda correction

**The sine table.** The SS (chapter 2) tabulates 24 sines at 3°45′ steps on
a radius of 3438 (the number of arc-minutes in a radian):

```
225 449 671 890 1105 1315 1520 1719 1910 2093 2267 2431
2585 2728 2859 2978 3084 3177 3256 3321 3372 3409 3431 3438
```

- `jya(x)` interpolates linearly in this table, with the usual quadrant
  symmetry.
- `inverse_jya` interpolates the other way.
- Use the table, not `sin`. It differs from 3438·sin by up to 1.7 units,
  which is enough to move printed minutes.

**Manda (equation of centre).** For a body with mean longitude `M` and
apogee `A`:

```
anomaly   = M − A
s         = jya(anomaly)
c         = even − (even − odd) × |s| / 3438        # epicycle circumference, degrees
true      = M − inverse_jya(c / 360 × s)
```

The epicycle circumference shrinks from `even` at the apsides to `odd` at
quadrature:

| Body | even | odd | Largest correction |
|---|---|---|---|
| Sun | 14° | 13°40′ | 2.175° |
| Moon | 32° | 31°40′ | 5.05° |

That is the whole model: one manda step, no śīghra, no bīja. From the true
Sun (S) and Moon (M):

| Quantity | Angle | Division |
|---|---|---|
| Tithi | elongation M − S | 12° |
| Karana | elongation M − S | 6° |
| Nakshatra | Moon M | 13°20′ |
| Yoga | M + S | 13°20′ |
| Moon's sign | Moon M | 30° |
| Sankranti | Sun S | 30° |
| Sun's pada | Sun S | 3°20′ |

> Example: true Sun 262.99007° (book: 8।22।59।25 = 262.99028°);
> true Moon 265.55920° (book: 8।25।33।40 = 265.56111°);
> elongation 2.569°, so tithi 1 (शुक्ल प्रतिपदा);
> M + S = 168.549°, so yoga 12 (व्याघात).

## 5. The Lahiri frame: sunrise, sunset, दिनमान, बेलान्तर

Sunrise needs the Sun's *tropical* position. The book (the "Ketaki side")
gets it by adding the Lahiri ayanamsha to the SS true Sun, and then uses
modern spherical astronomy:

```
T          = (JD − 2451545.0) / 36525
lahiri     = 23.857092 + (5029.0966 T + 1.11113 T²) / 3600      # degrees
obliquity  = 23.439291 − 0.0130042 T
λ          = true_sun + lahiri                                   # tropical
RA         = atan2(cos ε sin λ, cos λ)
δ          = asin(sin ε sin λ)
```

**Equation of time (बेलान्तर).** It is the mean Sun made tropical with the
*same* Lahiri shift, minus the true Sun's right ascension, at 4 minutes of
time per degree:

```
EoT (minutes, mean → apparent) = −wrap(mean_sun + lahiri − RA) × 4
```

The book prints it at local noon in minutes and seconds with a sign.

**Half day-arc.** For a horizon `h₀ = −34′` (refraction only; the centre of
the disc, no semidiameter, no dip). The books before BS 2064 use
`h₀ = 0`, no refraction; only the month-start rule needs that
(`panchanga.book_horizon`, section 10.2):

```
cos H = (sin h₀ − sin φ sin δ) / (cos φ cos δ)
half_day (minutes) = H (degrees) × 4
```

**Sunrise and sunset.**

```
apparent noon (minutes after NST midnight) = 720 + EoT + (86.25 − 85.3167) × 4
sunrise = noon − half_day,   sunset = noon + half_day
```

Iterate this six times, each time evaluating δ and EoT at the current
estimate of the event, starting from 06:00 or 18:00.

**दिनमान.** It is `2 × half_day` at the moment of sunrise, converted to pala
and truncated. Note that this is *not* sunset − sunrise; the two differ by
up to about 15 seconds, because δ changes between sunrise and sunset.

**Printed clock.** Sunrise is rounded up to the minute and sunset rounded
down.

> Example: Lahiri 24.23456°, ε 23.43578°. Sunrise 06:57:20 → printed 6:58;
> sunset 17:23:44 → 17:23. दिनमान 626.05 min = 26 ghati 5 pala (book 26।05).
> EoT +6.725 min = +6:43 (book +6:44).

## 6. Finding end times

Every end time is the moment a monotonically increasing angle crosses a
multiple of its division width. `surya.crossings(angle, width, start, end)`
does this by Newton's method on the wrapped angle. It starts from the
current value, steps to the next multiple using the angle's rate (from a
central difference of ±0.001 day), and iterates until it is within 1e-9°.

- It returns `(index_ending, jd)` pairs. The index is the division that
  ends, so 0 for शुक्ल प्रतिपदा, Ashvini or Mesha.
- For a day row, search from that day's sunrise to the next sunrise.
- There are usually one or zero ends per day, and sometimes two (a क्षय
  tithi). The book stacks two ends in one cell. With no end, it prints
  अहोरात्र.

## 7. Day-row columns

The columns run left to right, as on 2083 book page 21.

| Column | What it is |
|---|---|
| गते | Day of the BS month, 1-based |
| वा. | Weekday, सो. … आ. |
| ति. घ.प. बजे | Tithi current at sunrise, its end in घटी।पला and clock time |
| न. … | Nakshatra (Moon, 27 × 13°20′) and its end |
| योग … | Yoga (Sun + Moon, 27 × 13°20′) and its end |
| क. … | Karana (see below) and its end |
| योगाः | आनन्दादि yoga |
| च.रा. | Moon's sign at sunrise, and the time it changes |
| दिमा. | दिनमान in घटी।पला |
| सू.उ. / सू.अ. | Sunrise and sunset clock |

**Tithi number.** The printed number is `index mod 15 + 1`, except that
अमावस्या (index 29) is printed as 30. Indices 0–14 are शुक्ल and 15–29
कृष्ण.

**Karana.** There are 60 half-tithis per lunation, numbered 0–59 from the
new moon.

- Fixed karanas: 0 is किंस्तुघ्न; 57, 58 and 59 are शकुनि, चतुष्पद and नाग.
- Halves 1–56 cycle through बव, बालव, कौलव, तैतिल, गर, वणिज, विष्टि. विष्टि is
  printed भ. (भद्रा).
- The book's column only lists the karanas that end on the **first half of a
  tithi** (even half-tithi index ending), with their end times. The second
  half ends with the tithi itself.

**आनन्दादि.** This is a cycle of 28 yogas (आनन्द, काल, धुम्र, …, प्रवर्द्ध). It
uses the 28-nakshatra count, where अभिजित् is inserted as number 21 (0-based)
between उत्तराषाढा and श्रवण, covering 276°40′ to 280°53′20″ of the Moon's
longitude. Each weekday starts the count at a fixed nakshatra:

| आ. | सो. | मं. | बु. | बि. | शु. | श. |
|---|---|---|---|---|---|---|
| अश्विनी | मृगशिरा | आश्लेषा | हस्त | अनुराधा | उत्तराषाढा | शतभिषा |

The yoga is `(nakshatra28(Moon at sunrise) − start) mod 28`.

**The ग्रहचार rail.** Clock times (NST, past 24 for the small hours) of:

- the Sun entering each nakshatra pada (3°20′), with the sign when the
  pada starts one, अभिजित at pada 83 (उत्तराषाढा 4), and leaving अभिजित
  ("अभिजितत्याग सूर्य");
- Mars, Jupiter, Saturn and Rahu entering each pada (Rahu with Ketu's);
- Mercury and Venus entering each nakshatra and sign, and अभिजित्;
- वक्री and मार्गी, shaded at the foot.

Nakshatras are printed in full, the paired ones shortened (पू.फा.) and पुष्य
as तिष्य. A planet re-entering a division in वक्री motion gets पुनः
("२ पुनःपू.फा. १ मा मंगल"). The Sun's moments are exact; the planets' are
linear between the स्पष्ट ग्रह of consecutive sunrises, as one reads the
daily table. A station is the turning point by the tables themselves
(`ketaki.station`): where a केन्द्र crosses a 10° row and the motion flips;
flips a few days apart around one station are printed once, as the net
turn. Heliacal rising and setting (उदय/अस्त) are not computed yet.

**राशि प्रवेश.** The page's sign entries, planet by planet (सू मं बु बृ शु श
रा), as "गते, planet, sign number": "१सू.२, २८मं.१, ३१बु.२, ३०शु.३".

> Example, 2027-01-08 (book values in brackets):
>
> | Column | Ours | Book |
> |---|---|---|
> | Tithi | 1 ends 51।24, 27:31 | 27:31 |
> | Nakshatra | पू.षा. ends 9:10 | 9:10 |
> | Yoga | व्या. ends 15:45 | 15:45 |
> | Karana | किं. ends 14:27 | किं. 14:27 |
> | आनन्दादि | प्रवर्द्ध (शुक्रवार; Moon in पूर्वाषाढा, index 19 → (19 − 20) mod 28 = 27) | प्रवर्द्ध |
> | Moon's sign | धनु until 15:49 | 15:49 |

## 8. Lagna table

At sunrise the rising point is the Sun's own position. After that the
ascendant advances through each sign's **oblique ascension** at the
sidereal rate (one turn per 0.99726957 days):

```
OA(λ) = RA(λ) − asin(tan φ · tan δ(λ))         # φ = 27.7°, tropical λ
start of sign k = sunrise + ((OA(30k + lahiri) − OA(sun_tropical)) mod 360) / 360 × sidereal_day
```

Sort the twelve starts by time. The book lists them from the first sign
that begins after sunrise to the last before the next sunrise.

> Example: मकर 7:24, कुम्भ 9:07, मीन 10:36, … धनु 29:16, all within a minute
> of 2083 book page 21.

## 9. स्पष्ट ग्रह: Sun, Moon, Rahu, Mars to Saturn

| Body | How |
|---|---|
| Sun | SS true Sun at Kathmandu sunrise |
| Moon | SS true Moon at Kathmandu sunrise |
| Rahu | Modern mean node (Meeus, ch. 22), minus Lahiri, plus −50.4″, at Ujjain mean sunrise |

The modern mean node is
`125.04452 − 1934.136261 T + 0.0020708 T² + T³/450000`. Ujjain mean
sunrise is 06:00 local mean time at Ujjain, which is 06:41:56 NST. Why that
moment and that offset: [CALIBRATION.md](CALIBRATION.md#2-rahu-504-at-ujjain-mean-sunrise).

> Example: Rahu 9।28।13।11 (book 9।28।13।09).

### Mars to Saturn: the Ketaki tables

The committee requires the planets to be computed by the केतकी ग्रहगणितम्
(V. B. Ketkar, 1898), and `ketaki.py` follows it. It is a karana: an epoch,
mean motions, and 10° tables read by linear interpolation. Its longitudes
are sidereal in the Lahiri frame already. All at Kathmandu sunrise without
refraction (`ketaki.sunrise`, 2.7-2.8 minutes after the printed sunrise):

1. **Mean longitude.** The क्षेपक at Shaka 1800 elapsed (1878-04-03, 06:00
   Ujjain mean time), plus the ध्रुवक for each whole 6940-day चक्र, plus the
   per-day formula for the days left in the current चक्र. Mars: `10A/19`
   degrees `− 10A/73` minutes for A days. The planets' are heliocentric, the
   Sun's geocentric.
2. **कर्ष (Jupiter and Saturn only).** The 918-year great inequality: with
   b the भुज of `(Shaka − 1481) mod 918 × 2/153` signs, in degrees,
   `f = (b/9)(20 − b/9)` minutes; Jupiter `+f/5`, Saturn `−f/2`, signs
   reversed past 180°.
3. **मन्दफल.** मन्दकेन्द्र = mean − apogee; the table value (in असु, 0.1°)
   is subtracted for 0-180° and added beyond. The result is the
   heliocentric (मन्दस्पष्ट) planet.
4. **शीघ्रफल.** शीघ्र केन्द्र = heliocentric planet − Ketaki's true Sun; the
   table value (असु) is added for 0-180° and subtracted beyond for Mercury
   and Venus, the other way for Mars, Jupiter and Saturn. Mercury and Venus
   apply it to the Sun, the others to the planet. Mars scales it by
   `शीघ्रकर्ण / (r + शीघ्रकर्ण − 152)`, where `शीघ्रकर्ण = 252 − table` and
   `r = 152 + 14 cos(मन्दकेन्द्र + मन्दफल/2)`; Mercury by `r / 39`, with r
   read from Ketaki's distance table (47 … 31).
5. **The Sun of step 4** is Ketaki's Sun at the day's mean sunrise (06:00
   Kathmandu mean time), with its मन्दफल row read from perigee.

Points 4-5 and the choice of r are the books' conventions, found from
their tables: [CALIBRATION.md](CALIBRATION.md#5-ketaki-planets).

> Example, 8 January 2027 (2083 p21). Mars: 7 चक्र and 5756 days after the
> epoch, mean 3।13।3।36, apogee 4।12।22।53, मन्दकेन्द्र 330.7°, मन्दफल
> +4.70°, heliocentric 3।17।45।29; Sun 8।23।14।36, शीघ्र केन्द्र 204.5°;
> geocentric 4।16।26।31 (book 4।16।26।41). Mercury 8।27।14।46 (book …47),
> Jupiter 4।1।59।25 (…27), Venus 7।7।9।43 (…35), Saturn 11।14।16।50 (…50).

Because the tables are interpolated linearly, a planet's daily motion
changes abruptly each time a केन्द्र crosses a 10° row. That is why the
book's Mars "turns retrograde" overnight on 2027-01-15/16 (from +3′ a day
to −12′), five days after the real planet: the शीघ्र केन्द्र crosses 200°.
For moments other than sunrise, `ketaki.longitude` interpolates between
the sunrises, as a reader of the daily table would.

## 10. Solar months (BS month starts)

A BS month (बैशाख, जेठ, …) starts on the civil day its sankranti belongs to.
The sankranti is the moment the SS true Sun enters the month's sign:
बैशाख = Mesha, जेठ = Vrisha, and so on. Two things decide the date.

### 10.1 Which sankranti moment

The book did not always print the plain SS sankranti. Each era of the
calendar committee has a per-sign offset in ghati, added to our SS moment
before deciding the day (`SANKRANTI_ERAS` in `panchanga.py`):

| From BS | Offset (ghati) | Where it comes from |
|---|---|---|
| 1975 | per sign: −0.77 −0.97 −0.55 −0.10 −0.02 −0.40 −0.66 −0.79 −0.51 −0.13 −0.06 −0.35 | 1986 and 1987 books |
| 2005 | per sign: −0.67 −0.80 −0.40 −0.82 +0.58 +0.44 −0.12 −0.43 +0.02 +0.22 +0.12 −0.24 | 2016 book |
| 2017 | per sign: −0.46 −2.36 −1.94 −2.82 −1.84 −1.14 −0.84 +0.40 +0.61 +1.22 +0.19 −0.09 | 2028 and 2031–2044 books |
| 2045 | `SHAPE_2045` − 0.43 | 2045–2059 books |
| 2060 | `SHAPE_2045`: −0.01 −0.15 +0.04 +0.10 +0.04 +0.19 +0.01 −0.04 −0.01 −0.11 −0.07 0 | 2060–2062 books |
| 2063 | Mesha −0.06, Mina −0.03, else 0 | 2063–2076 books |

Each era lasts until the next. Years before 1975 use the 1975 era, and
generating them prints a warning. The offsets are measured from the
sunrise each book counts from (section 10.2). Evidence:
[CALIBRATION.md](CALIBRATION.md#3-sankranti-eras).

### 10.2 Which day a moment belongs to

The books print sankrantis in ghati after a sunrise, and assign the month
by the **night midpoint** (निशीथ) rule:

1. Find the civil (sunrise-to-sunrise) day that contains the shifted
   sankranti.
2. **Karka** (Sun entering Cancer, साउन): the month starts on that civil
   day. A Karka sankranti before sunrise therefore counts for the day
   before.
3. **Makara** (Sun entering Capricorn, माघ): if it falls after that day's
   sunset (ghati after sunrise > दिनमान), the month starts the next day.
   Otherwise it starts that day.
4. **All other signs**: the boundary is the following night's midpoint,
   30 ghati + दिनमान/2 after sunrise. At or before it, the month starts that
   day; after it, the next day. A tie goes to the earlier day.

Sunrise and दिनमान here are the book's own: geometric (`h₀ = 0`) for
books before BS 2064, refracted (`h₀ = −34′`) from 2064
(`panchanga.book_horizon`). The night midpoint is the same moment either
way, since it is apparent noon plus 30 ghati, but the book's ghati are
counted from its sunrise, and the Karka and Makara rules use that sunrise
and sunset directly.

```
h   = book_horizon(bs_year)                 # 0 before 2064, −34′ from 2064
day = civil_day_containing(jd, h)           # jd already shifted by the era
x   = jd − sunrise(day, h)                  # in days
dm  = day_length(day, h) / 1440             # दिनमान in days
if sign == KARKA:  return day
limit = dm if sign == MAKARA else 0.5 + dm / 2
return day if x <= limit else day + 1
```

Book examples (rows in `data/month_starts.csv`):

| Month | Sankranti | Book page | Result |
|---|---|---|---|
| 2035 माघ | Makara 26:56 after sunrise, दिनमान 26:05 | 2035 book p21 | after sunset, so the next day |
| 2051 साउन | Karka 59:35, just before the next sunrise | 2051 book p8 | stays on that day |
| 2066 चैत | Mina 44:52, exactly the night midpoint | 2066 book p25 | tie, so that day |
| 2062 कात्तिक | Tula 44:58 against a midpoint of 44:19 | 2062 book p15 | the next day |

### 10.3 The year

`month_starts(y)` returns 13 dates, बैशाख 1 of `y` through बैशाख 1 of `y+1`.
The last one uses the next year's era. Month lengths come out as 29–32 days
and year lengths as 365 or 366.

## 11. Lunar months and adhik masa

Lunar months are **amanta** (new moon to new moon). New moons are
crossings of elongation through 0°.

- **Naming.** A lunation is named for the sign after the one the Sun is in
  at its start. A lunation that starts with the Sun in Mina contains the
  Mesha sankranti and is चैत्र.
- **Adhik.** If the Sun is in the same sign at both new moons, the lunation
  has no sankranti. It is **adhik** and takes the following month's name.
- **Shuddha.** The month after an adhik one is called शुद्ध.

> 2083 has an adhik ज्येष्ठ (2083 book pages 5–6).

## 12. Page layout and headers

**Pages.** A new page starts whenever the paksha at sunrise changes (tithi
index < 15 is शुक्ल). Pages are numbered from 2, as page 1 is the cover.
2083 has 26 pages and 365 days.

**Header fields.**

- **Lunar month name.**
  - शुक्ल pages are named for their own amanta month.
  - कृष्ण pages are named for the *following* month (purnimanta style),
    unless the page itself is in an adhik month.
  - The prefix अधिक or शुद्ध is added as above.
- **Shaka year.** `BS − 135`, plus 1 once the page's first sunrise is past
  the start of शुक्ल चैत्र (the first non-adhik चैत्र new moon after बैशाख 1).
- **Nepal Sambat.**
  - The year is `BS − 937`, plus 1 after the start of शुक्ल कार्तिक.
  - Months run चौला … चिल्ला, with अनला for an adhik month. The suffix is
    थ्वः for शुक्ल and गा for कृष्ण.
- **Gregorian span.**
  - One month: "जनवरी 2027".
  - Two months in the same year: "जनवरी + फेब्रुअरी 2027".
  - Across a year end: "डिसेम्बर 2026 + जनवरी 2027".
- **Ayana and ritu.**
  - The Sun's sidereal sign at each sunrise gives the ayana: Makara through
    Mithuna is उत्तरायण, the rest दक्षिणायन.
  - It also gives the ritu: two signs per ritu, starting with वसन्त for
    Mina and Mesha.
  - When a value changes within the page, both are printed, in order.

## 13. What is not computed

- **Festival and vrat notes.** These are editorial. `generate.py --config`
  takes them from JSON. Samvatsara, पापर्क्षाणि and पापांश are computed in
  `editorial.py`; see [EDITORIAL.md](EDITORIAL.md).
- **Planets.** Heliacal rising and setting (उदयास्त) and the kundali chart
  are not computed yet; the स्पष्ट ग्रह, the rail's entries and stations,
  and the राशि प्रवेश box are. The kundali is a placeholder in the PDF.
