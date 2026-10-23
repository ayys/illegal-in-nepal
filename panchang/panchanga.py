"""Day rows and page headers for one year of the राष्ट्रिय पञ्चाङ्ग, as plain data.

year(bs_year) returns one dict per printed page (one paksha each). Every page
has a header (lunar month, paksha, Shaka, Nepal Sambat, ayana, ritu) and one
row per civil day, whose fields follow the book's columns left to right:
tithi, nakshatra, yoga, karana, आनन्दादि, Moon's sign, दिनमान, sunrise and
sunset, the Sun's nakshatra padas, lagna starts, स्पष्ट ग्रह (Mars to Saturn
from ketaki.py) and बेलान्तर.

A civil day runs from sunrise to the next sunrise at Kathmandu. Each limb
reports what is current at sunrise plus every end inside the day, in ghati
and pala after sunrise (1 ghati = 24 min, 1 pala = 24 s) and as a clock time.

Column layout and abbreviations are from the 2083 book, page 21:
  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
See docs/ALGORITHM.md for every column in detail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import ketaki
import surya

# Degrees of the angle that measures each limb: tithi and karana of the
# elongation, nakshatra of the Moon, yoga of Sun + Moon, padas of the Sun.
TITHI_WIDTH = 12.0
KARANA_WIDTH = 6.0
NAKSHATRA_WIDTH = 360 / 27
PADA_WIDTH = 360 / 108
SIGN_WIDTH = 30.0
# The Sun's pada at which the book notes "अभिजित" (उत्तराषाढा pada 4).
ABHIJIT_PADA = 83

# (full name, the abbreviation printed in the day rows). पुष्य is printed
# as "ति." for its other name तिष्य.
NAKSHATRAS = [
    ("अश्विनी", "अश्वि."), ("भरणी", "भ."), ("कृत्तिका", "कृ."), ("रोहिणी", "रो."),
    ("मृगशिरा", "मृ."), ("आर्द्रा", "आ."), ("पुनर्वसु", "पुन."), ("पुष्य", "ति."),
    ("आश्लेषा", "अश्ले."), ("मघा", "म."), ("पूर्वफाल्गुनी", "पू.फा."),
    ("उत्तरफाल्गुनी", "उ.फा."), ("हस्त", "ह."), ("चित्रा", "चि."), ("स्वाती", "स्वा."),
    ("विशाखा", "वि."), ("अनुराधा", "अनु."), ("ज्येष्ठा", "ज्ये."), ("मूल", "मू."),
    ("पूर्वाषाढा", "पू.षा."), ("उत्तराषाढा", "उ.षा."), ("श्रवण", "श्र."),
    ("धनिष्ठा", "ध."), ("शतभिषा", "श."), ("पूर्वभाद्रपदा", "पू.भा."),
    ("उत्तरभाद्रपदा", "उ.भा."), ("रेवती", "रे."),
]
YOGAS = [
    ("विष्कुम्भ", "वि."), ("प्रीति", "प्री."), ("आयुष्मान्", "आ."), ("सौभाग्य", "सौ."),
    ("शोभन", "शो."), ("अतिगण्ड", "अ."), ("सुकर्मा", "सु."), ("धृति", "धृ."),
    ("शूल", "शू."), ("गण्ड", "गं."), ("वृद्धि", "वृ."), ("ध्रुव", "ध्रु."),
    ("व्याघात", "व्या."), ("हर्षण", "ह."), ("वज्र", "व."), ("सिद्धि", "सि."),
    ("व्यतीपात", "व्य."), ("वरीयान्", "व."), ("परिघ", "प."), ("शिव", "शि."),
    ("सिद्ध", "सि."), ("साध्य", "सा."), ("शुभ", "शु."), ("शुक्ल", "शु."),
    ("ब्रह्म", "ब्र."), ("ऐन्द्र", "ऐ."), ("वैधृति", "वै."),
]
# Half-tithis 1-56 cycle through the seven movable karanas; विष्टि is printed
# as "भ." (भद्रा). The four fixed ones fill half-tithis 0 and 57-59.
MOVABLE_KARANAS = [
    ("बव", "ब."), ("बालव", "बा."), ("कौलव", "कौ."), ("तैतिल", "तै."),
    ("गर", "ग."), ("वणिज", "व."), ("विष्टि", "भ."),
]
FIXED_KARANAS = {
    0: ("किंस्तुघ्न", "किं."), 57: ("शकुनि", "श."), 58: ("चतुष्पद", "च."), 59: ("नाग", "ना."),
}
# The 28 आनन्दादि yogas, from the weekday and the Moon's nakshatra counted
# with अभिजित् as the 22nd.
ANANDADI = [
    "आनन्द", "काल", "धुम्र", "धाता", "सौम्य", "ध्वाङ्क्ष", "ध्वज", "श्रीवत्स", "वज्र",
    "मुद्गर", "छत्र", "मित्र", "मानस", "पद्म", "लुम्ब", "उत्पात", "मृत्यु", "काण",
    "सिद्धि", "शुभ", "अमृत", "मुशल", "गद", "मातङ्ग", "राक्षस", "चर", "स्थिर", "प्रवर्द्ध",
]
# 28-nakshatra index (with अभिजित्) that starts the आनन्दादि cycle, Monday first.
ANANDADI_START = [4, 8, 12, 16, 20, 24, 0]
# अभिजित्'s span of the Moon's longitude for the 28-nakshatra count: the last
# quarter of उत्तराषाढा plus the first 1/15 of श्रवण.
ABHIJIT = (276 + 40 / 60, 280 + 53 / 60 + 20 / 3600)

SIGNS = [
    "मेष", "वृष", "मिथुन", "कर्कट", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुम्भ", "मीन",
]
# Monday first, to match date.weekday().
WEEKDAYS = ["सो.", "मं.", "बु.", "बि.", "शु.", "श.", "आ."]
BS_MONTHS = [
    "बैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज",
    "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत",
]
# Amanta months (new moon to new moon), named by the sign the Sun enters
# during them: a lunation with the Mina→Mesha sankranti is चैत्र.
LUNAR_MONTHS = [
    "चैत्र", "वैशाख", "ज्येष्ठ", "आषाढ", "श्रावण", "भाद्र",
    "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन",
]
NEPAL_SAMBAT_MONTHS = [
    "चौला", "बछला", "तछला", "दिल्ला", "गुँला", "ञला",
    "कौला", "कछला", "थिंल्ला", "पोहेला", "सिल्ला", "चिल्ला",
]
NEPAL_SAMBAT_LEAP_MONTH = "अनला"
# Nepal Sambat's year turns at the start of शुक्ल कार्तिक.
KARTIK = 7
GREGORIAN_MONTHS = [
    "जनवरी", "फेब्रुअरी", "मार्च", "अप्रिल", "मे", "जुन",
    "जुलाई", "अगस्ट", "सेप्टेम्बर", "अक्टोबर", "नोभेम्बर", "डिसेम्बर",
]
# Two solar months per ritu, starting with वसन्त for Mina and Mesha.
RITUS = ["वसन्त", "ग्रीष्म", "वर्षा", "शरद्", "हेमन्त", "शिशिर"]
UTTARAYANA_SIGNS = {9, 10, 11, 0, 1, 2}


@dataclass(frozen=True)
class Lunation:
    """One amanta month: new moon to new moon, as Julian days.

    `month` indexes LUNAR_MONTHS. A lunation with no sankranti in it is adhik
    and takes the name of the month that follows it.
    """
    start: float
    end: float
    month: int
    adhik: bool


def karana(half: int) -> tuple[str, str]:
    """Karana for half-tithi `half` (0-59, counted from the new moon)."""
    return FIXED_KARANAS.get(half) or MOVABLE_KARANAS[(half - 1) % 7]


def nakshatra28(moon: float) -> int:
    """Index in the 28-nakshatra list, where अभिजित् is 21 and श्रवण onward
    move up by one."""
    if ABHIJIT[0] <= moon < ABHIJIT[1]:
        return 21
    index = int(moon // NAKSHATRA_WIDTH)
    return index if index <= 20 else index + 1


def anandadi(day: date, moon: float) -> str:
    """Counted from the weekday's starting nakshatra to the Moon's at sunrise.
    Checked against the आनन्दादि column, 2083 book p21."""
    return ANANDADI[(nakshatra28(moon) - ANANDADI_START[day.weekday()]) % 28]


def sun_sign(jd: float) -> int:
    return int(surya.true_sun(jd) // SIGN_WIDTH)


def _local_midnight(day: date) -> float:
    return surya.local_julian_day(day, 0)


def arc(longitude: float) -> list[int]:
    """[sign, degree, minute, second], the book's ८।२२।५९।२५ form."""
    seconds = round(longitude * 3600) % (360 * 3600)
    return [seconds // 108000, seconds // 3600 % 30, seconds // 60 % 60, seconds % 60]


def _clock(jd: float, day: date, rounding=round) -> list[int]:
    """Hours and minutes after the civil day's midnight; past 24 means the next morning.

    The book prints sunrise rounded up and sunset rounded down.
    """
    minutes = rounding((jd - _local_midnight(day)) * 1440)
    return [minutes // 60, minutes % 60]


def _ending(index: int, name: tuple[str, str] | None, jd: float, rise: float, day: date) -> dict:
    """An end time in the book's two forms: घटी।पला after sunrise (2.5 pala a
    minute, rounded to the nearest pala) and a clock time."""
    palas = round((jd - rise) * 1440 * 2.5)
    ending = {
        "index": index,
        "at": surya.from_julian_day(jd).isoformat(timespec="seconds"),
        "ghati": palas // 60,
        "pala": palas % 60,
        "clock": _clock(jd, day),
    }
    if name:
        ending["name"], ending["abbr"] = name
    return ending


def _limb(angle, width, names, day, rise, next_rise):
    """What `angle` is in at sunrise, and every division that ends before the
    next sunrise. Usually one end; none or two also happen."""
    found = surya.crossings(angle, width, rise, next_rise)
    start = int(angle(rise) // width)
    return {
        "index": start,
        **({"name": names[start][0], "abbr": names[start][1]} if names else {}),
        "ends": [_ending(i, names[i] if names else None, jd, rise, day) for i, jd in found],
    }


def day_row(day: date, bs_month: int, gate: int) -> dict:
    """Every column of one day. `gate` is the day of the BS month (गते)."""
    rise = surya.sunrise(day)
    next_rise = surya.sunrise(day + timedelta(days=1))
    set_ = surya.sunset(day)

    tithi = _limb(surya.elongation, TITHI_WIDTH, None, day, rise, next_rise)
    # 1-15 in each paksha, except that अमावस्या is printed as 30.
    tithi["number"] = tithi["index"] % 15 + 1 if tithi["index"] != 29 else 30
    tithi["paksha"] = "शुक्ल" if tithi["index"] < 15 else "कृष्ण"

    # The karana column lists the karanas that end on the first half of a
    # tithi; the second half ends with the tithi itself.
    halves = [
        (half, jd)
        for half, jd in surya.crossings(surya.elongation, KARANA_WIDTH, rise, next_rise)
        if half % 2 == 0
    ]
    karanas = {
        "ends": [_ending(h, karana(h), jd, rise, day) for h, jd in halves],
    }
    if halves:
        karanas["name"], karanas["abbr"] = karana(halves[0][0])

    moon = surya.true_moon(rise)
    sign_changes = surya.crossings(surya.true_moon, SIGN_WIDTH, rise, next_rise)
    # दिनमान in pala, truncated.
    day_length = math.floor(surya.day_length(day) * 2.5)
    sun_padas = []
    # The Sun enters a new nakshatra pada every ~3.3 days; the book prints the
    # moment, and the sign when the pada starts one.
    for index, jd in surya.crossings(surya.true_sun, PADA_WIDTH, rise, next_rise):
        pada = (index + 1) % 108
        entry = _ending(pada, None, jd, rise, day)
        entry["nakshatra"] = NAKSHATRAS[pada // 4][1]
        entry["pada"] = pada % 4 + 1
        if pada % 9 == 0:
            entry["enters"] = SIGNS[pada // 9]
        elif pada == ABHIJIT_PADA:
            entry["enters"] = "अभिजित"
        sun_padas.append(entry)

    return {
        "date": day.isoformat(),
        "bs_month": bs_month,
        "bs_month_name": BS_MONTHS[bs_month],
        "gate": gate,
        "weekday": WEEKDAYS[day.weekday()],
        "tithi": tithi,
        "nakshatra": _limb(surya.true_moon, NAKSHATRA_WIDTH, NAKSHATRAS, day, rise, next_rise),
        "yoga": _limb(surya.yoga_angle, NAKSHATRA_WIDTH, YOGAS, day, rise, next_rise),
        "karana": karanas,
        "anandadi": anandadi(day, moon),
        "moon_sign": {
            "index": int(moon // SIGN_WIDTH),
            "name": SIGNS[int(moon // SIGN_WIDTH)],
            "ends": [_ending(i, (SIGNS[i], SIGNS[i]), jd, rise, day) for i, jd in sign_changes],
        },
        "dinamana": [day_length // 60, day_length % 60],
        "sunrise": surya.from_julian_day(rise).isoformat(timespec="seconds"),
        "sunset": surya.from_julian_day(set_).isoformat(timespec="seconds"),
        "sunrise_clock": _clock(rise, day, math.ceil),
        "sunset_clock": _clock(set_, day, math.floor),
        "sun_sign": sun_sign(rise),
        "sun_padas": sun_padas,
        "lagna": [
            {"sign": sign, "name": SIGNS[sign], "clock": _clock(jd, day)}
            for sign, jd in surya.lagna_starts(day)
        ],
        "spashta": {
            "sun": arc(surya.true_sun(rise)),
            "moon": arc(moon),
            # Mars to Saturn by the Ketaki tables, at the same sunrise.
            **{body: arc(ketaki.geocentric(body, rise)) for body in ketaki.PLANETS},
            # Not at Kathmandu sunrise; see surya.RAHU_OFFSET.
            "rahu": arc(surya.rahu(surya.ujjain_mean_sunrise(day))),
        },
        # In seconds; the book prints मि।से with a sign.
        "belantar": round(surya.equation_of_time(day) * 60),
    }


# ---- Solar months -------------------------------------------------------
#
# A BS month starts on the day its sankranti (the Sun's entry into the next
# sign) belongs to. Two things decide it: where the book's sankranti is, and
# which civil day a moment belongs to. Both are described in
# docs/ALGORITHM.md ("Month starts") and docs/CALIBRATION.md; every book
# reading is in data/book_sankrantis.csv and every disputed month in
# data/month_starts.csv.

KARKA, MAKARA = 3, 9
# Earliest year checked against published BS month tables.
VERIFIED_FROM = 1975


def _wave(base: float, swing: float = 0.0, peak: float = 0.0) -> tuple[float, ...]:
    """Twelve per-sign offsets: base + swing·cos(30·sign − peak)."""
    return tuple(base + swing * math.cos(math.radians(30 * sign - peak)) for sign in range(12))


# The 2045-2062 books share one per-sign shape, fitted to all their readings;
# the 2045-2059 books print it 0.43 ghati earlier.
SHAPE_2045 = (-0.01, -0.15, 0.04, 0.10, 0.04, 0.19, 0.01, -0.04, -0.01, -0.11, -0.07, 0.00)

# Where each era's printed sankrantis sit relative to ours, in ghati after the
# book's own sunrise (see book_horizon), per sign from Mesha. Each era applies
# from its year until the next one. Every era is read from books: 1975 from
# the 1986 and 1987 books (EAP1485-1-3-127, EAP1485-1-6-123; the 1986 book
# prints तुला as "४।" with no pala, so तुला is the 1987 book's alone), 2016 from
# the 2016 book (EAP1485-1-3-45),
# 2028 from the 2028 and 2031-2044 books, the rest from the books of their
# years. The boundaries from 2045 on are bracketed by books of consecutive
# years (2044/2045, 2059/2060, 2062/2063); the two earlier ones fall in the
# unread years 1987-2015 and 2017-2027 and are placed by the published month
# tables. Book readings, with page numbers and sources, are in
# data/book_sankrantis.csv; most books are at
#   https://archive.org/download/2081_20240828/{year}.pdf
# From 2063 the printed sankrantis are plain SS to within about a pala,
# except Mesha and Mina, which every book from 2063 to 2076 prints 3-4 and
# about 2 pala early (2066 book p25: मीनेऽर्कः 44।52, exactly on the night
# midpoint, so चैत starts 2010-03-14).
SANKRANTI_ERAS = [
    (1975, (-0.77, -0.97, -0.55, -0.10, -0.02, -0.40, -0.66, -0.79, -0.51, -0.13, -0.06, -0.35)),
    (2005, (-0.67, -0.80, -0.40, -0.82, 0.58, 0.44, -0.12, -0.43, 0.02, 0.22, 0.12, -0.24)),
    (2017, (-0.46, -2.36, -1.94, -2.82, -1.84, -1.14, -0.84, 0.40, 0.61, 1.22, 0.19, -0.09)),
    (2045, tuple(s - 0.43 for s in SHAPE_2045)),
    (2060, SHAPE_2045),
    (2063, (-0.06, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -0.03)),
]


# Books before 2064 count their ghati from the Sun's centre on the horizon,
# with no refraction: their दिनमान matches surya.GEOMETRIC to about a pala in
# every season (2062 book p5 33।23 on 2005-05-14, p21 26।3 on 2006-01-14; 2063
# book p21 26।17 on 2007-01-20), and the pre-2058 books run about 3 pala
# longer still (2035 book p21 26।5 on 1979-01-14). From the 2064 book
# (p21 26।3 on 2008-01-08) they use surya.HORIZON.
REFRACTION_FROM = 2064


def book_horizon(bs_year: int) -> float:
    """Altitude of the sunrise the year's book counts from."""
    return surya.HORIZON if bs_year >= REFRACTION_FROM else surya.GEOMETRIC


def _sankranti_shift(bs_year: int, sign: int) -> float:
    """Days to add to our sankranti into `sign`. Years before the first era
    use the first era."""
    eras = [era for era in SANKRANTI_ERAS if era[0] <= bs_year] or SANKRANTI_ERAS[:1]
    return eras[-1][1][sign] / 60


def _month_start(bs_year: int, sign: int, jd: float) -> date:
    """Day a sankranti belongs to. The day runs from one night's midpoint
    (30 ghati plus half the dinamana after sunrise) to the next, a tie going
    to the earlier day; a Karka sankranti before sunrise counts for the day
    before, a Makara one after sunset for the day after.

    Examples from the books, all in data/month_starts.csv: 2035 माघ (2035 book
    p21) and 2082 माघ (2082 book p20) are Makara sankrantis after sunset, so
    the month starts the next day; 2051 साउन (2051 book p8) is a Karka one at
    59:35, just before the next sunrise, so it still starts the month on the
    day it falls in; 2066 चैत (2066 book p25) lands exactly on the night
    midpoint and goes to the earlier day.
    """
    horizon = book_horizon(bs_year)
    jd += _sankranti_shift(bs_year, sign)
    day = surya.from_julian_day(jd).date()
    # From here `day` is the sunrise-to-sunrise day holding `jd`.
    rise = surya.sunrise(day, horizon)
    if jd < rise:
        day -= timedelta(days=1)
        rise = surya.sunrise(day, horizon)
    if sign == KARKA:
        return day
    dinamana = surya.day_length(day, horizon) / 1440
    boundary = dinamana if sign == MAKARA else 0.5 + dinamana / 2
    return day if jd - rise <= boundary else day + timedelta(days=1)


def month_starts(bs_year: int) -> list[date]:
    """First day of each solar month, from the sankranti that opens it.

    Thirteen dates: बैशाख 1 through चैत 1, then बैशाख 1 of the next year, so
    month lengths are differences of consecutive entries. The Mesha sankranti
    that closes the year is shifted with the next year's era.
    """
    gregorian = bs_year - 57
    start = _gregorian_jd(gregorian, 4, 1)
    end = _gregorian_jd(gregorian + 1, 4, 30)
    crossings = surya.crossings(surya.true_sun, SIGN_WIDTH, start, end)[:13]
    return [
        _month_start(bs_year + (k == 12), (ended + 1) % 12, jd)
        for k, (ended, jd) in enumerate(crossings)
    ]


def lunations(start: float, end: float) -> list[Lunation]:
    """Amanta months between `start` and `end`, named by sankranti.

    A lunation is named for the sign after the one the Sun is in at its
    start. When the Sun is in the same sign at both ends there was no
    sankranti, and the month is adhik.
    """
    new_moons = [jd for _, jd in surya.crossings(surya.elongation, 360, start, end)]
    result = []
    for begin, finish in zip(new_moons, new_moons[1:]):
        first, last = sun_sign(begin), sun_sign(finish)
        result.append(Lunation(begin, finish, (first + 1) % 12, first == last))
    return result


def _gregorian_span(first: date, last: date) -> str:
    if (first.year, first.month) == (last.year, last.month):
        return f"{GREGORIAN_MONTHS[first.month - 1]} {first.year}"
    if first.year == last.year:
        return f"{GREGORIAN_MONTHS[first.month - 1]} + {GREGORIAN_MONTHS[last.month - 1]} {last.year}"
    return (
        f"{GREGORIAN_MONTHS[first.month - 1]} {first.year} + "
        f"{GREGORIAN_MONTHS[last.month - 1]} {last.year}"
    )


def _joined(values: list[str]) -> list[str]:
    return [v for i, v in enumerate(values) if i == 0 or v != values[i - 1]]


def _jd(iso: str) -> float:
    return surya.julian_day(datetime.fromisoformat(iso))


def header(rows: list[dict], months: list[Lunation], new_years: dict, bs_year: int,
           config: dict) -> dict:
    """The strip above a fortnight's rows.

    शुक्ल pages are named for their own amanta month. कृष्ण pages are named
    purnimanta-style, for the month that follows, unless they are themselves
    in an adhik month. The month after an adhik one is शुद्ध. Samvatsara,
    पापर्क्षाणि and पापांश come from editorial.py (docs/EDITORIAL.md); a value
    in `config` overrides the computed one.
    """
    import editorial  # here, not at the top: editorial imports panchanga
    first_rise = _jd(rows[0]["sunrise"])
    position = next(i for i, l in enumerate(months) if l.start <= first_rise < l.end)
    lunation = months[position]
    shukla = rows[0]["tithi"]["index"] < 15

    if shukla:
        named = lunation
        kind = "adhik" if lunation.adhik else (
            "shuddha" if position and months[position - 1].adhik else None)
    elif lunation.adhik:
        named, kind = lunation, "adhik"
    else:
        named = months[position + 1]
        kind = "shuddha" if named.adhik else None
    prefix = {"adhik": "अधिक ", "shuddha": "शुद्ध ", None: ""}[kind]
    paksha = "शुक्ल" if shukla else "कृष्ण"

    ns_month = NEPAL_SAMBAT_LEAP_MONTH if lunation.adhik else NEPAL_SAMBAT_MONTHS[lunation.month]

    first, last = date.fromisoformat(rows[0]["date"]), date.fromisoformat(rows[-1]["date"])
    signs = [row["sun_sign"] for row in rows]
    ayanas = ["उत्तरायण" if s in UTTARAYANA_SIGNS else "दक्षिणायन" for s in signs]
    ritus = [RITUS[((s + 1) % 12) // 2] for s in signs]
    # Shaka turns at शुक्ल चैत्र 1, Nepal Sambat at शुक्ल कार्तिक 1.
    shaka = bs_year - 135 + (first_rise >= new_years["shaka"])
    return {
        "shaka": shaka,
        "vikram_samvat": bs_year,
        "lunar_month": f"{prefix}{LUNAR_MONTHS[named.month]}",
        "lunar_month_kind": kind,
        "paksha": paksha,
        "nepal_samvat": bs_year - 937 + (first_rise >= new_years["nepal_samvat"]),
        "nepal_samvat_month": ns_month + ("थ्वः" if shukla else "गा"),
        "gregorian": _gregorian_span(first, last),
        "ayana": _joined(ayanas),
        "ritu": _joined(ritus),
        "ayana_ritu": _joined([[a, r] for a, r in zip(ayanas, ritus)]),
        "samvatsara": config.get("samvatsara") or editorial.samvatsara(shaka),
        "papakshani": (config.get("papakshani", {}).get(first.isoformat())
                       or editorial.papakshani(rows)),
        # {body: [(गते it changes on, or None at the start; navamsha 1-12)]}
        "papamsha": editorial.papamsha(rows),
    }


def _gregorian_jd(year: int, month: int, day: int) -> float:
    return surya.local_julian_day(date(year, month, day), 0)


def year(bs_year: int, config: dict | None = None) -> list[dict]:
    """Every fortnight page of a Bikram Sambat year.

    Days run from बैशाख 1 to the last of चैत. A new page starts whenever the
    paksha changes at sunrise, and pages are numbered from 2 because page 1
    of the book is the cover.
    """
    config = config or {}
    starts = month_starts(bs_year)
    # Generous bounds: every lunar month touching the BS year, plus margin.
    months = lunations(_gregorian_jd(bs_year - 57, 2, 1), _gregorian_jd(bs_year - 56, 6, 1))
    year_start = _gregorian_jd(starts[0].year, starts[0].month, starts[0].day)
    new_years = {
        "nepal_samvat": next(
            l.start for l in months if l.month == KARTIK and not l.adhik and l.start > year_start),
        "shaka": next(
            l.start for l in months if l.month == 0 and not l.adhik and l.start > year_start),
    }

    rows = []
    for month, (begin, end) in enumerate(zip(starts, starts[1:])):
        for gate in range((end - begin).days):
            rows.append(day_row(begin + timedelta(days=gate), month, gate + 1))

    pages, current = [], [rows[0]]
    for row in rows[1:]:
        same = (row["tithi"]["index"] < 15) == (current[-1]["tithi"]["index"] < 15)
        if same:
            current.append(row)
        else:
            pages.append(current)
            current = [row]
    pages.append(current)

    return [
        {"page": i + 2, "header": header(page, months, new_years, bs_year, config), "rows": page}
        for i, page in enumerate(pages)
    ]
