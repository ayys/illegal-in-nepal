"""Samvatsara, पापर्क्षाणि and पापांश: the header and side-box fields that look
editorial but follow fixed rules.

**Samvatsara.** The name in the header ("रौद्रनामसंवत्सरः") is the Jovian
(बार्हस्पत्य) samvatsara of the Surya Siddhanta: the count of mean-Jupiter
signs since the Kali epoch, taken modulo 60 and started from विजय (SS 1.55).
The book names a Shaka year by the samvatsara current at its start, शुक्ल
चैत्र प्रतिपदा, and keeps that name until the next शुक्ल चैत्र although the
Jovian year (361 days) turns over mid-year, about 4.4 days earlier every
year. Near a turnover at शुक्ल चैत्र, roughly every 85 years, one name is
skipped (क्षय: आनन्द, Shaka 1943 = BS 2078) and a name is never used twice.

**पापर्क्षाणि** ("sinful nakshatras", the end of the header strip). The Moon's
nakshatras during the fortnight, in the order the Moon passes them, that are
occupied by a malefic (Sun, Mars, Saturn, Rahu, Ketu) or are in vedha with
one in the सप्तशलाका chakra, at the time the Moon is there. A second kind of
vedha, between the four corner nakshatras of the chakra and the far corners
(कृत्तिका-विशाखा, भरणी-अनुराधा, आश्लेषा-धनिष्ठा, मघा-श्रवण), is printed as
the nakshatra's number instead of its name ("अश्ले.९", "२२.ध").

**पापांश** (box under the kundali). The navamsha (1-12, Mesha = 1) of each
malefic at the page's first sunrise, then "gate + new navamsha" each time one
changes: "सू.१, ४सू.२, मं.६, २मं.७, शं.७, ४शं.८, रा.१०के.४".

The Sun is the SS Sun and Rahu the book's mean node (surya.py); Mars and
Saturn are the Ketaki tables (ketaki.py), the book's own स्पष्ट ग्रह.

Reference values (PDF page = book page):
  2083  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
  2082  https://giwmscdnone.gov.np/media/pages/files/npnbs_2082_ussfian.pdf
  older https://archive.org/download/2081_20240828/{year}.pdf
See docs/EDITORIAL.md for the evidence, page by page.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import panchanga
import ketaki
import surya

# ---- Samvatsara ---------------------------------------------------------

# The 60 names from प्रभव, spelled as they are printed before "नामसंवत्सरः".
# Attested in the books: सिद्धार्थि, रौद्र, दुर्मति (2082/2083), नल, पिङ्गल
# (2079), राक्षस (2078), परिधावी, प्रमादी, आनन्द (2076), सौम्य, साधारण (2073),
# विकारी (2063), शोभन (2067), विलम्बी (2062, printed विलम्ब), जय, मन्मथ (2058),
# सर्वजित् (2051), ईश्वर (2041), प्रजापति (2035), विभव (2032).
SAMVATSARAS = [
    "प्रभव", "विभव", "शुक्ल", "प्रमोद", "प्रजापति", "अङ्गिरा",
    "श्रीमुख", "भाव", "युवा", "धाता", "ईश्वर", "बहुधान्य",
    "प्रमाथी", "विक्रम", "वृष", "चित्रभानु", "सुभानु", "तारण",
    "पार्थिव", "व्यय", "सर्वजित्", "सर्वधारी", "विरोधी", "विकृति",
    "खर", "नन्दन", "विजय", "जय", "मन्मथ", "दुर्मुख",
    "हेमलम्बी", "विलम्बी", "विकारी", "शार्वरी", "प्लव", "शुभकृत्",
    "शोभन", "क्रोधी", "विश्वावसु", "पराभव", "प्लवङ्ग", "कीलक",
    "सौम्य", "साधारण", "विरोधकृत्", "परिधावी", "प्रमादी", "आनन्द",
    "राक्षस", "नल", "पिङ्गल", "कालयुक्त", "सिद्धार्थि", "रौद्र",
    "दुर्मति", "दुन्दुभि", "रुधिरोद्गारी", "रक्ताक्ष", "क्रोधन", "क्षय",
]
# SS chapter 1: Jupiter's revolutions in a mahayuga.
JUPITER_REVOLUTIONS = 364_220
# SS 1.55: count the elapsed Jupiter signs and start from विजय (the 27th).
VIJAYA = 26


def jovian_signs(jd: float) -> float:
    """Mean-Jupiter signs elapsed since the Kali epoch (SS mean motion)."""
    return (jd - surya.KALI_JD) * JUPITER_REVOLUTIONS / surya.MAHAYUGA_DAYS * 12


def jovian_samvatsara(jd: float) -> int:
    """Index into SAMVATSARAS of the Jovian year current at `jd`."""
    return (math.floor(jovian_signs(jd)) + VIJAYA) % 60


def jovian_starts(start: float, end: float) -> list[tuple[int, float]]:
    """Every (index, jd) at which a Jovian year begins in [start, end).

    The prefaces of the 2078 and 2079 books give the time from these to the
    Mesha sankranti to the ghati ("मेषार्कात् प्राग्भुक्त मासादयः ०।१६।५५।१२").
    Older books also print a day note "सौरात् X नामसंवत्सरप्रवेशः", which
    falls within a day of these in 2062 (p7) and 2073 (p3) but about 4 days
    later in 2076-2079; the 2082 and 2083 books print none.
    """
    sign_days = surya.MAHAYUGA_DAYS / JUPITER_REVOLUTIONS / 12
    found = []
    n = math.floor(jovian_signs(start)) + 1
    while (jd := surya.KALI_JD + n * sign_days) < end:
        found.append(((n + VIJAYA) % 60, jd))
        n += 1
    return found


def shaka_new_year(shaka: int) -> float:
    """Julian day of शुक्ल चैत्र प्रतिपदा (the new moon) that begins Shaka
    `shaka`: the first non-adhik चैत्र of Gregorian year shaka + 78, as in
    panchanga.year's Shaka turnover."""
    year = shaka + 78
    start = surya.local_julian_day(date(year, 2, 1), 0)
    end = surya.local_julian_day(date(year, 6, 1), 0)
    return next(l.start for l in panchanga.lunations(start, end) if l.month == 0 and not l.adhik)


def samvatsara_index(shaka: int) -> int:
    """Index into SAMVATSARAS of Shaka year `shaka`.

    The Jovian year current at शुक्ल चैत्र प्रतिपदा, except that a year never
    repeats the previous year's name. A 354-day lunar year can fall wholly
    inside a 361-day Jovian year: Shaka 1944 and 1945 both start in नल
    (1 Apr 2022, 22 Mar 2023; पिङ्गल starts 24 Mar 2023), and the 2079 book
    prints नल for 1944 and पिङ्गल from शुक्ल चैत्र 1945 (pp11-33, p34). The
    other way round, a Jovian year that starts and ends inside one lunar
    year is never current at a शुक्ल चैत्र and is skipped (क्षय): आनन्द,
    between प्रमादी (1942) and राक्षस (1943), as the 2078 book's preface says.
    """
    # Repeats are rare and isolated; a few years of history settle them.
    index = jovian_samvatsara(shaka_new_year(shaka - 4))
    for year in range(shaka - 3, shaka + 1):
        current = jovian_samvatsara(shaka_new_year(year))
        index = (index + 1) % 60 if current == index else current
    return index


def samvatsara(shaka: int) -> str:
    """Name of Shaka year `shaka`, as printed before "नामसंवत्सरः".

    Pages before शुक्ल चैत्र carry the outgoing name and pages from it on the
    incoming one (2083 book: रौद्र on pp2-26, दुर्मति on p27), so the header's
    own Shaka year is the right argument.
    """
    return SAMVATSARAS[samvatsara_index(shaka)]


def kshaya_samvatsaras(first: int, last: int) -> list[tuple[int, str]]:
    """(Shaka year, name) for every name skipped between Shaka `first` and
    `last`."""
    skipped = []
    previous = samvatsara_index(first)
    for shaka in range(first + 1, last + 1):
        current = samvatsara_index(shaka)
        for gap in range(1, (current - previous) % 60):
            skipped.append((shaka, SAMVATSARAS[(previous + gap) % 60]))
        previous = current
    return skipped


# ---- Mars and Saturn ------------------------------------------------------
#
# From the Ketaki tables, as in the स्पष्ट ग्रह column (ketaki.py), so the
# malefics' nakshatras and navamshas are the book's own.


def planet(body: str, jd: float) -> float:
    """Sidereal longitude of "mars" or "saturn" by the Ketaki tables."""
    return ketaki.longitude(body, jd)


# ---- The malefics -------------------------------------------------------

# पापग्रह in the order the पापांश box prints them. Ketu is Rahu + 180°.
MALEFICS = ["sun", "mars", "saturn", "rahu", "ketu"]


def malefics(jd: float) -> dict[str, float]:
    """Sidereal longitudes of the five malefics."""
    rahu = ketaki.rahu(jd)
    return {
        "sun": surya.true_sun(jd),
        "mars": planet("mars", jd),
        "saturn": planet("saturn", jd),
        "rahu": rahu,
        "ketu": surya.norm(rahu + 180),
    }


# ---- पापर्क्षाणि ------------------------------------------------------------

# The header's abbreviations, in the 28-nakshatra order (अभिजित् is 21).
ABBREVIATIONS = [
    "अश्वि", "भ", "कृ", "रो", "मृ", "आ", "पुन", "ति", "अश्ले", "म", "पूफा", "उफा",
    "ह", "चि", "स्वा", "वि", "अनु", "ज्ये", "मू", "पूषा", "उषा", "अभि", "श्र", "ध",
    "श", "पूभा", "उभा", "रे",
]


def _pairs(*lines: tuple[str, str]) -> dict[int, int]:
    pairs = {}
    for a, b in lines:
        i, j = ABBREVIATIONS.index(a), ABBREVIATIONS.index(b)
        pairs[i], pairs[j] = j, i
    return pairs


# सप्तशलाका chakra: seven vertical and seven horizontal lines, the 28
# nakshatras round the ends from कृत्तिका at the top left. Two nakshatras on
# one line pierce each other. Every pair here is printed in the 2082 and 2083
# books, e.g. पुष्य-ज्येष्ठा (2082 p2, Mars in पुष्य), रोहिणी-अभिजित् (2083 p6,
# Sun in रोहिणी), शतभिषा-स्वाती (2083 p3, Rahu in शतभिषा).
SAPTASHALAKA = _pairs(
    ("कृ", "श्र"), ("रो", "अभि"), ("मृ", "उषा"), ("आ", "पूषा"), ("पुन", "मू"),
    ("ति", "ज्ये"), ("अश्ले", "अनु"),
    ("भ", "म"), ("अश्वि", "पूफा"), ("रे", "उफा"), ("उभा", "ह"), ("पूभा", "चि"),
    ("श", "स्वा"), ("ध", "वि"),
)
# The far-corner vedha, printed as numbers. Fitted from both books: श्रवण (22)
# exactly when Mars or Ketu is in मघा (2083 pp4-24, not p21 or p26 when
# neither is), आश्लेषा (9) when Rahu is in धनिष्ठा (2083 pp10-25),
# धनिष्ठा (23) when Ketu or Mars is in आश्लेषा (2083 pp15-26), भरणी (2)
# with the Sun or Mars in अनुराधा (2082 pp15-17), विशाखा (16) with the Sun
# or Mars in कृत्तिका (2082 pp3-4, 2083 p7).
CORNERS = _pairs(("कृ", "वि"), ("भ", "अनु"), ("अश्ले", "ध"), ("म", "श्र"))


def _number(index28: int) -> str:
    """The nakshatra's number in the 27 list, in Devanagari digits."""
    return panchanga_digits(index28 + 1 - (index28 > 21))


def panchanga_digits(n: int) -> str:
    return "".join("०१२३४५६७८९"[int(c)] for c in str(n))


def _crossing_times(angle, width: float, start: float, end: float) -> list[float]:
    return [jd for _, jd in surya.crossings(angle, width, start, end)]


def moon_spans(start: float, end: float) -> list[tuple[int, float, float]]:
    """(28-nakshatra index, from, to) for the Moon between two moments.

    The Moon's nakshatras are the 27 of the day rows, plus अभिजित् while it
    is between 276°40' and 280°53'20", overlapping the end of उत्तराषाढा and
    the start of श्रवण. Both identities count: 2083 p6 prints अभि (the Sun in
    रोहिणी pierces it), 2082 p21 prints उषा for a Moon at 277° (the Sun and
    Mars are in उत्तराषाढा) and no अभि."""
    cuts = _crossing_times(surya.true_moon, panchanga.NAKSHATRA_WIDTH, start, end)
    bounds = [start] + cuts + [end]
    spans = [
        (_nakshatra_of_planet(surya.true_moon((a + b) / 2)), a, b)
        for a, b in zip(bounds, bounds[1:]) if b > a
    ]
    low, high = panchanga.ABHIJIT
    abhijit = panchanga.nakshatra28(low)
    enter = _crossing_times(lambda jd: surya.norm(surya.true_moon(jd) - low), 360, start, end)
    leave = _crossing_times(lambda jd: surya.norm(surya.true_moon(jd) - high), 360, start, end)
    if low <= surya.true_moon(start) < high:
        enter = [start] + enter
    for a in enter:
        spans.append((abhijit, a, min([jd for jd in leave if jd > a] + [end])))
    # By start time; अभिजित् starts inside उत्तराषाढा and before श्रवण.
    return sorted(spans, key=lambda s: (s[1], s[0] == abhijit))


def _nakshatra_of_planet(longitude: float) -> int:
    """28-list index of the nakshatra a planet is in, counted in the 27 list:
    अभिजित् is only a Moon nakshatra. 2083 p22 prints "१०" (मघा pierced
    from श्रवण) while the Sun goes from 279.4° to 280.4°: into श्रवण by the
    27 list, still inside अभिजित् by the 28."""
    index = int(longitude // panchanga.NAKSHATRA_WIDTH)
    return index if index <= 20 else index + 1


def papa_nakshatras(start: float, end: float) -> list[dict]:
    """The पापर्क्षाणि of the stretch from `start` to `end`, in the order the
    Moon passes them. Each entry is the Moon's nakshatra and why it counts:
    `named` for occupation or सप्तशलाका vedha, `numbered` for the corner
    vedha. The malefics are checked at both ends of the Moon's stay, since
    the Sun can change nakshatra while the Moon is in one."""
    found = []
    for index, a, b in moon_spans(start, end):
        named = numbered = False
        for jd in (a, b):
            for longitude in malefics(jd).values():
                where = _nakshatra_of_planet(longitude)
                named |= where == index or SAPTASHALAKA.get(where) == index
                numbered |= CORNERS.get(where) == index
        if named or numbered:
            found.append({"index": index, "named": named, "numbered": numbered})
    return found


def papakshani_tokens(found: list[dict]) -> list[str]:
    tokens = []
    for entry in found:
        if entry["named"]:
            tokens.append(ABBREVIATIONS[entry["index"]])
        if entry["numbered"]:
            tokens.append(_number(entry["index"]))
    return tokens


def page_span(rows: list[dict]) -> tuple[float, float]:
    """First sunrise of a page to the sunrise after its last day."""
    first = date.fromisoformat(rows[0]["date"])
    last = date.fromisoformat(rows[-1]["date"])
    return surya.sunrise(first), surya.sunrise(last + timedelta(days=1))


def papakshani(rows: list[dict]) -> str:
    """The header text after "पापर्क्षाणि-" for one page's day rows."""
    return ".".join(papakshani_tokens(papa_nakshatras(*page_span(rows)))) + "."


# ---- पापांश -----------------------------------------------------------------

NAVAMSHA_WIDTH = 360 / 108
PAPAMSHA_LABELS = {"sun": "सू.", "mars": "मं.", "saturn": "शं.", "rahu": "रा.", "ketu": "के."}


def navamsha(longitude: float) -> int:
    """1-12, the sign of the navamsha (Mesha = 1). Each nakshatra pada is a
    navamsha, so this is the pada count mod 12: अश्विनी 2 is वृष (2)."""
    return int(longitude // NAVAMSHA_WIDTH) % 12 + 1


def _malefics_at_sunrise(day: date) -> dict[str, float]:
    found = malefics(surya.sunrise(day))
    # Mars and Saturn as the day's स्पष्ट ग्रह (ketaki.at_sunrise), and the
    # book's राहु is Ketaki's at 06:00 Kathmandu mean time (ketaki.rahu_of_day).
    found["mars"], found["saturn"] = ketaki.at_sunrise("mars", day), ketaki.at_sunrise("saturn", day)
    rahu = ketaki.rahu_of_day(day)
    found["rahu"], found["ketu"] = rahu, surya.norm(rahu + 180)
    return found


def papamsha(rows: list[dict]) -> dict[str, list[tuple[int | None, int]]]:
    """Per malefic, [(None, navamsha at the start), (gate, new navamsha), ...].

    A change is dated by the civil day it happens in: the navamsha differs
    between that day's sunrise and the next. The start is the navamsha at
    the first sunrise, and a change on the first day is printed too (2083
    p6 "सू.२, १८सू.३", p14 "सू.१२, ११सू.१", the pages starting on gates 18
    and 11). The exception is a page that starts on a month's first day,
    the sankranti day: the box starts in the new sign (2083 p2: the Sun
    enters मेष at 12:04 on gate 1 and the box starts "सू.१")."""
    days = [date.fromisoformat(r["date"]) for r in rows]
    gates = [r["gate"] for r in rows]
    values = [_malefics_at_sunrise(d) for d in days + [days[-1] + timedelta(days=1)]]
    result = {}
    for body in MALEFICS:
        series = [navamsha(v[body]) for v in values]
        entries = [(None, series[0])]
        for i in range(len(rows)):
            if series[i + 1] != series[i]:
                if i == 0 and gates[0] == 1:
                    entries = [(None, series[1])]
                else:
                    entries.append((gates[i], series[i + 1]))
        result[body] = entries
    return result


def papamsha_text(found: dict[str, list[tuple[int | None, int]]]) -> str:
    """The box as printed: "सू.१, ४सू.२, मं.६, २मं.७, शं.७, ४शं.८, रा.१०के.४".
    Rahu and Ketu always move together and share one entry."""
    def entry(gate, label, value):
        return f"{panchanga_digits(gate) if gate else ''}{label}{panchanga_digits(value)}"

    parts = []
    for body in ("sun", "mars", "saturn"):
        parts += [entry(g, PAPAMSHA_LABELS[body], v) for g, v in found[body]]
    for (g, rahu), (_, ketu) in zip(found["rahu"], found["ketu"]):
        parts.append(entry(g, "रा.", rahu) + f"के.{panchanga_digits(ketu)}")
    return ", ".join(parts)
