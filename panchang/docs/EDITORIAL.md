# Samvatsara, पापर्क्षाणि and पापांश

Three fields that were taken from `--config` follow fixed rules and are now
computed by `editorial.py`. This page says what each one is in the book, the
rule, the evidence and how well it matches. Tests: `test_editorial.py`.

Book pages are PDF pages (page 1 is the cover). The 2082 and 2083 books are
the national books listed in [SOURCES.md](SOURCES.md). "Older books" are
the scans in <https://archive.org/details/2081_20240828>. Some of these come
from other publishers, for example the 2076 book is हिमाल पञ्चाङ्ग.

| Field | Where it is printed | Computed? | Match |
|---|---|---|---|
| Samvatsara | Header strip, every page: "रौद्रनामसंवत्सरः" | Yes | 20/20 years, every header page of 2082 and 2083 |
| पापर्क्षाणि | End of the header strip: "पापर्क्षाणि- अश्वि.भ.म.पूफा.उफा.ह.स्वा." | Yes | 50/51 pages (2082 and 2083) |
| पापांश | Box under the kundali: "सू.१, ४सू.२, मं.६, २मं.७, शं.७, ४शं.८, रा.१०के.४" | Yes | Sun 123/124 entries, Rahu/Ketu 29/29, Mars 81/82, Saturn 32/33; whole box on 24 pages |

Nothing in these three fields is editorial. Mars and Saturn come from the
Ketaki tables, as in the book (see [Mars and Saturn](#mars-and-saturn)).

## 1. Samvatsara

**What it is.** The year's name in the 60-year cycle प्रभव … क्षय. The book
uses the Jovian (बार्हस्पत्य) samvatsara of the Surya Siddhanta, not a fixed
count from the Shaka year. The 2078 and 2079 prefaces say so
("षष्ट्यब्दानां मध्ये बार्हस्पत्यमानेन …").

**Rule.**

1. Jovian years. Count mean-Jupiter signs since the Kali epoch (SS:
   364,220 revolutions per mahayuga, so one sign is 361.03 days). The
   samvatsara is that count mod 60, counted from विजय (SS 1.55). This is
   `jovian_samvatsara(jd)`.
2. Year name. A Shaka year takes the Jovian year that is current at its
   start, शुक्ल चैत्र प्रतिपदा (the new moon). It keeps that name until the
   next शुक्ल चैत्र, even though the Jovian year turns over mid-year. Pages
   before शुक्ल चैत्र show the outgoing name, and pages from it on show the
   incoming one. In the 2083 book that is रौद्र on pp2-26 and दुर्मति on p27.
   In the 2082 book it is सिद्धार्थि on pp2-24 and रौद्र on pp25-26. The
   header's own `shaka` is the argument to `samvatsara(shaka)`.
3. क्षय (expunged year). The Jovian year starts about 4.4 days earlier each
   year. When it crosses शुक्ल चैत्र, about once in 85 years, one Jovian
   year starts and ends inside a single lunar year. It is never current at
   a शुक्ल चैत्र, so its name is skipped. The last one was आनन्द (Shaka
   1943, BS 2078). The 2078 preface (p17) has "प्रमादीनामसंवत्सरो गतः अपर
   आनन्दनाम संवत्सरस्य क्षयत्वात् राक्षसनाम संवत्सरः प्राप्तः". The one
   before it was विरोधी, Shaka 1859.
4. No repeats. The opposite can also happen: a 354-day lunar year can sit
   wholly inside a 361-day Jovian year. Shaka 1944 and 1945 both start in
   नल (1 Apr 2022, 22 Mar 2023), and पिङ्गल starts on 24 Mar 2023. The
   2079 book prints नल on pp11-33 and पिङ्गल from शुक्ल चैत्र on p34. So a
   year never reuses the previous year's name.

**Checks.**

- The Jovian clock is the plain SS mean Jupiter, with no बीज correction.
  The 2079 preface (p5) gives नल's elapsed part at the Mesha sankranti as
  "मेषार्कात्प्राग्भुक्त मासादयः ०।१६।५५।१२" (in Jovian days of 1/360 year). We
  get 16 d 54 g.
- The 2078 preface (p17) gives राक्षस "०।१२।४२।०", and we get 12 d 40 g.
- Older books also print a day note "सौरात् X नामसंवत्सरप्रवेशः ghati।pala".
  It agrees with our Jovian start to within a day in 2062 (p7) and 2073
  (p3). In 2076-2079 it falls about 4 days later. The 2082 and 2083 books
  print no such note.

**Readings** (`SAMVATSARAS` in the tests): BS 2025, 2032, 2035, 2041, 2051,
2058, 2062, 2063, 2066, 2067, 2073, 2076, 2077, 2078, 2079, 2082 and 2083,
covering Shaka 1890 to 1949. All 20 names match.

Two simpler rules each get some of these wrong:

- Naming a year by the Jovian year at the Mesha sankranti gets 1941 and
  1942 wrong. It also never makes आनन्द क्षय, which the 2078 preface says
  happened.
- Naming a year by the Jovian year at शुक्ल चैत्र without the no-repeat
  rule gives नल twice (1944 and 1945).

## 2. पापर्क्षाणि ("sinful nakshatras", header)

**What it is.** A list of the Moon's nakshatras during the fortnight that
are afflicted by a malefic. They appear in the order the Moon passes them,
so each page continues where the previous one stopped. The malefics are
the Sun, Mars, Saturn, Rahu and Ketu. The Moon, Mercury, Jupiter and Venus
never count. A Moon nakshatra is afflicted if, while the Moon is in it,
a malefic is in one of these places:

- **Occupation.** The same nakshatra. Printed as the abbreviation (अश्वि,
  भ, कृ … पूफा, उफा … अभि, श्र, ध, श, पूभा, उभा, रे).
- **सप्तशलाका vedha.** The nakshatra at the other end of the same line of
  the सप्तशलाका chakra. Also printed as the abbreviation. The 28
  nakshatras, from कृत्तिका at the top left, sit at the ends of 7 vertical
  and 7 horizontal lines, which gives these pairs:
  - कृ-श्र, रो-अभि, मृ-उषा, आ-पूषा, पुन-मू, ति-ज्ये, अश्ले-अनु
  - भ-म, अश्वि-पूफा, रे-उफा, उभा-ह, पूभा-चि, श-स्वा, ध-वि
- **Corner vedha.** The chakra's four corner nakshatras each pierce the
  far corner: कृ-वि, भ-अनु, अश्ले-ध, म-श्र. These are printed as the
  nakshatra's number in the 27 list instead of its abbreviation, for
  example "९" for आश्लेषा and "२२" for श्रवण. That is why both "अश्ले.९"
  and "९.अश्ले" occur: the nakshatra is afflicted both ways. The order
  of the pair varies in print.

**Abhijit.** अभिजित् (276°40′ to 280°53′20″) is a Moon nakshatra only.

- A Moon in that range is both अभिजित् and उत्तराषाढा/श्रवण. 2083 p6 prints
  "अभि" because the Sun in रोहिणी pierces it. 2082 p21 prints "उषा" for a
  Moon at 277°, with the Sun and Mars in उत्तराषाढा.
- Planets are placed in the 27 list. 2083 p22 prints "१०" (मघा, pierced
  from श्रवण) while the Sun is at 280.0-280.4°.

**How the three kinds were found.**

- Occupation and सप्तशलाका vedha explain every abbreviation on every page
  of both books, using the stretch of time when the Moon is in the
  nakshatra. For example, on 2083 p3 Sun अश्वि/भ, Ketu म, Sun→पूफा,
  Mars→उफा, Mars and Saturn→ह, and Rahu→स्वा give exactly "अश्वि.भ.म.पूफा.उफा.ह.स्वा".
- The numbers had no planet in the same nakshatra or in सप्तशलाका vedha.
  Each of them has a malefic exactly at the far corner:
  - "२२" (श्रवण) appears whenever Mars or Ketu is in मघा (2083 pp4-24). It
    is absent on p21 and p26, when neither is there.
  - "९" (आश्लेषा) appears when Rahu is in धनिष्ठा (2083 pp10-25).
  - "२३" (धनिष्ठा) appears when Ketu or Mars is in आश्लेषा (2083 pp15-26,
    and 2082 pp9-10 with the Sun there).
  - "२" (भरणी) appears with the Sun or Mars in अनुराधा (2082 pp15-17).
  - "१६" (विशाखा) appears with the Sun or Mars in कृत्तिका (2082 pp3-4,
    2083 p7).

**Match.** 50 of 51 pages are exact, ignoring the order of a name and a
number for the same nakshatra.

- 2082 p4: we add २३. Mars is in आश्लेषा in both the book's table and ours,
  so the book seems to have left it out.

## 3. पापांश (box under the kundali)

**What it is.** The navamsha of each malefic, written as the navamsha's sign
number (मेष = 1). Each nakshatra pada is one navamsha, so the value is
`floor(longitude / 3°20′) mod 12 + 1`. For example, अश्विनी 2 is वृष (2),
and उत्तरभाद्रपदा 3 is तुला (7).

**Format.** Each malefic's value at the page's first sunrise is printed,
then "gate + label + new value" for every change:

- सू. Sun, मं. Mars, शं. Saturn. Rahu and Ketu share one entry, "रा.१०के.४",
  because Ketu is always 6 navamshas on.
- Example, 2083 p2: "सू.१, ४सू.२, मं.६, २मं.७, शं.७, ४शं.८, रा.१०के.४".

**Rules.**

- A change is dated by the civil (sunrise-to-sunrise) day it happens in.
  This matches the ग्रहचार box: "१० रेवती १ मा मंगल २७:२१" is printed as
  "१०मं.९".
- Changes on the first day are printed, for example 2083 p6 "सू.२,
  १८सू.३", where the page starts on gate 18.
- The exception is a page that starts on the sankranti day (gate 1). There
  the Sun starts in the new sign: 2083 p2 is "सू.१" although the Sun
  enters मेष at 12:04 on gate 1.
- Retrograde motion is printed the same way, for example "२८शं.९" and
  "२मं.५".

**Match** (2083 pp2-26 except 5 and 8, plus 2082 pp2, 20 and 21):

- Sun, all entries. The one miss is "१सू.१" on 2083 p27, which is
  बैशाख 1 of the next year, after our page ends.
- Rahu/Ketu, all entries.
- Mars 81 of 82 entries, Saturn 32 of 33.
- Whole box exact on 24 pages: 2083 pp2-4, 6, 7, 9-12, 14-25, and 2082
  pp2, 20 and 21. The rest differ in the two entries above or the Sun's
  2083 p27 entry.

## Mars and Saturn

Both come from `ketaki.longitude`, the Ketaki tables the book's स्पष्ट ग्रह
column is computed from (ketaki.py, docs/ALGORITHM.md section 9), read
linearly between sunrises. With them:

- पापर्क्षाणि: every page but one (2082 p4, where the book leaves out "२३").
  Before, with JPL elements, 2082 p10 also differed, because the book's Mars
  ran 0.5° ahead of the real planet.
- पापांश: Mars 81 of 82 entries, Saturn 32 of 33, the whole box on 24
  pages. The two misses (2083 p13 "२७मं.३", p26 "२४शं.११") are dated a day
  or more before the book's own Mars and Saturn reach the navamsha.
