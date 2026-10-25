#!/usr/bin/env python3
"""Check that the tests pin every rule and constant: break each one on
purpose, in a scratch copy of this directory, and run the suite.

Each mutation is an exact edit (`old` must occur once in `file`) that changes
one convention found from the books: a constant, a rounding, a table entry, a
rule for which day or page something lands on. A mutation the suite still
passes is a rule no test checks. Run after changing the model or the tests:

    python3 mutation_check.py              # all, 8 at a time (~3 min)
    python3 mutation_check.py sunrise      # only those whose name contains it

It exits 1 if any mutation survives. Survivors listed in EXPECTED_SURVIVORS
(with the reason) are reported but don't fail the run.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Tests against the books and the texts. The snapshots (test_snapshot) are
# tried only on what these miss, and reported apart.
TESTS = ["test_surya", "test_panchanga", "test_editorial", "test_ketaki", "test_rail", "test_render"]
SNAPSHOT = ["test_snapshot"]

# (name, file, old, new)
MUTATIONS = [
    # ---- surya.py: the Sun and Moon ---------------------------------------
    ("moon apogee -1.70", "surya.py", "MOON_APOGEE_CORRECTION = -1.71", "MOON_APOGEE_CORRECTION = -1.70"),
    ("moon apogee -1.72", "surya.py", "MOON_APOGEE_CORRECTION = -1.71", "MOON_APOGEE_CORRECTION = -1.72"),
    ("sine shrunk like the SS table", "surya.py",
     "sine = math.sin(math.radians(mean_longitude - apogee))",
     "sine = 0.9996 * math.sin(math.radians(mean_longitude - apogee))"),
    ("sun epicycle constant", "surya.py", "_manda(mean_sun(jd), sun_apogee(jd), 14, 13 + 40 / 60)",
     "_manda(mean_sun(jd), sun_apogee(jd), 14, 14)"),
    ("moon epicycle constant", "surya.py", "32, 31 + 40 / 60)", "32, 32)"),
    ("kali moon apogee", "surya.py", "KALI_MOON_APOGEE = 90.0", "KALI_MOON_APOGEE = 90.01"),
    ("sun apogee revolutions", "surya.py", "SUN_APOGEE_KALPA_REVOLUTIONS = 387", "SUN_APOGEE_KALPA_REVOLUTIONS = 388"),
    ("lahiri epoch value", "surya.py", "return 23.857092 + ", "return 23.858092 + "),
    ("lahiri rate", "surya.py", "(5029.0966 * t", "(5028.0966 * t"),
    ("obliquity", "surya.py", "return 23.439291 - ", "return 23.449291 - "),
    ("ghati origin EoT at 6:00", "surya.py", "noon = 12 * 60 + _equation_of_time(local_julian_day(day, 12))",
     "noon = 12 * 60 + _equation_of_time(local_julian_day(day, 6))"),
    ("ghati origin from rounded dinamana", "surya.py", "- _dinamana_pala(day) / 2.5 / 2 / 1440", "- dinamana(day) / 2.5 / 2 / 1440"),
    # ---- surya.py: sunrise, दिनमान, बेलान्तर, lagna, Rahu ----------------------
    ("horizon -33'", "surya.py", "HORIZON = -34 / 60", "HORIZON = -33 / 60"),
    ("horizon -35'", "surya.py", "HORIZON = -34 / 60", "HORIZON = -35 / 60"),
    ("latitude", "surya.py", "LATITUDE = 27.7", "LATITUDE = 27.6"),
    ("longitude", "surya.py", "LONGITUDE = 85.3167", "LONGITUDE = 85.25"),
    ("NST meridian", "surya.py", "noon = 12 * 60 + _equation_of_time(jd) + (86.25 - LONGITUDE) * 4",
     "noon = 12 * 60 + _equation_of_time(jd) + (86.0 - LONGITUDE) * 4"),
    ("dinamana shift 21'", "surya.py", "DINAMANA_SHIFT = 22 / 60", "DINAMANA_SHIFT = 21 / 60"),
    ("dinamana shift 0", "surya.py", "DINAMANA_SHIFT = 22 / 60", "DINAMANA_SHIFT = 0"),
    ("dinamana horizon -31'", "surya.py", "DINAMANA_HORIZON = -30 / 60", "DINAMANA_HORIZON = -31 / 60"),
    ("dinamana at sunrise", "surya.py",
     "jd = local_julian_day(day, 6 + NST.utcoffset(None).total_seconds() / 3600 - LONGITUDE / 15)",
     "jd = sunrise(day)"),
    ("dinamana truncated", "surya.py", "return round(_dinamana_pala(day))", "return int(_dinamana_pala(day))"),
    ("rahu offset", "ketaki.py", "RAHU_OFFSET = 16.2 / 3600", "RAHU_OFFSET = 15.2 / 3600"),
    ("rahu epoch", "ketaki.py", "RAHU_AT_EPOCH = _arc(9, 27, 37)", "RAHU_AT_EPOCH = _arc(9, 27, 38)"),
    ("rahu per cycle", "ketaki.py", "RAHU_PER_CYCLE = _arc(11, 22, 13, 58)", "RAHU_PER_CYCLE = _arc(11, 22, 13, 59)"),
    ("rahu daily motion", "ketaki.py", "(days / 19 + days / 46 / 60)", "(days / 19 + days / 47 / 60)"),
    ("rahu at true sunrise", "ketaki.py", "    return rahu(mean_sunrise(sunrise(day)))", "    return rahu(sunrise(day))"),
    ("rahu rail from printed sunrise", "panchanga.py",
     "start, end = ketaki.sunrise(day), ketaki.sunrise(day + timedelta(days=1))\n                jd = start",
     "start, end = surya.sunrise(day), surya.sunrise(day + timedelta(days=1))\n                jd = start"),
    ("ujjain longitude", "surya.py", "UJJAIN_LONGITUDE = 75.7682", "UJJAIN_LONGITUDE = 75.5"),
    ("sidereal day", "surya.py", "SIDEREAL_DAY = 0.99726957", "SIDEREAL_DAY = 0.9973"),
    ("lagna without ascensional difference", "surya.py",
     "return norm(_right_ascension(longitude, eps) - math.degrees(ascensional))",
     "return norm(_right_ascension(longitude, eps))"),
    ("belantar sign", "surya.py", "return -((norm(mean_sun(jd) + shift - right_ascension) + 180) % 360 - 180) * 4",
     "return ((norm(mean_sun(jd) + shift - right_ascension) + 180) % 360 - 180) * 4"),
    # ---- panchanga.py: day rows ---------------------------------------------
    ("ghati from sunrise", "panchanga.py", "palas = round((jd - surya.ghati_origin(day)) * 1440 * 2.5)",
     "palas = round((jd - surya.sunrise(day)) * 1440 * 2.5)"),
    ("NS vachhala", "panchanga.py", '"चौला", "वछला",', '"चौला", "बछला",'),
    ("NS gunla", "panchanga.py", '"दिल्ला", "गुंला", "ञँला",', '"दिल्ला", "गुँला", "ञँला",'),
    ("NS nyanla", "panchanga.py", '"दिल्ला", "गुंला", "ञँला",', '"दिल्ला", "गुंला", "ञला",'),
    ("sunrise rounded", "panchanga.py", '"sunrise_clock": _clock(rise, day, math.ceil)',
     '"sunrise_clock": _clock(rise, day, round)'),
    ("sunset rounded", "panchanga.py", '"sunset_clock": _clock(set_, day, math.floor)',
     '"sunset_clock": _clock(set_, day, round)'),
    ("pala truncated", "panchanga.py", "palas = round((jd - surya.ghati_origin(day)) * 1440 * 2.5)",
     "palas = math.floor((jd - surya.ghati_origin(day)) * 1440 * 2.5)"),
    ("clock truncated", "panchanga.py", "def _clock(jd: float, day: date, rounding=round)",
     "def _clock(jd: float, day: date, rounding=math.floor)"),
    ("amavasya numbered 15", "panchanga.py", 'if tithi["index"] != 29 else 30', 'if tithi["index"] != 29 else 15'),
    ("paksha split", "panchanga.py", 'tithi["paksha"] = "शुक्ल" if tithi["index"] < 15 else "कृष्ण"',
     'tithi["paksha"] = "शुक्ल" if tithi["index"] < 14 else "कृष्ण"'),
    ("karana second halves", "panchanga.py", "if half % 2 == 0\n", "if half % 2 == 1\n"),
    ("fixed karanas swapped", "panchanga.py", '57: ("शकुनि", "श."), 58: ("चतुष्पद", "च.")',
     '57: ("चतुष्पद", "च."), 58: ("शकुनि", "श.")'),
    ("bhadra abbreviation", "panchanga.py", '("विष्टि", "भ.")', '("विष्टि", "वि.")'),
    ("movable karana offset", "panchanga.py", "MOVABLE_KARANAS[(half - 1) % 7]", "MOVABLE_KARANAS[half % 7]"),
    ("anandadi sunday start", "panchanga.py", "ANANDADI_START = [4, 8, 12, 16, 20, 24, 0]",
     "ANANDADI_START = [4, 8, 12, 16, 20, 24, 1]"),
    ("anandadi without abhijit", "panchanga.py", "return index if index <= 20 else index + 1\n\n\ndef anandadi",
     "return index\n\n\ndef anandadi"),
    ("abhijit start", "panchanga.py", "ABHIJIT = (276 + 40 / 60,", "ABHIJIT = (276 + 30 / 60,"),
    ("abhijit end", "panchanga.py", "280 + 53 / 60 + 20 / 3600)", "280 + 50 / 60)"),
    ("nakshatra abbreviation", "panchanga.py", '("पुष्य", "ति.")', '("पुष्य", "पु.")'),
    ("yoga name", "panchanga.py", '("व्याघात", "व्या.")', '("व्याघात", "व्य.")'),
    ("weekday order", "panchanga.py", 'WEEKDAYS = ["सो.", "मं.", "बु.", "बि.", "शु.", "श.", "आ."]',
     'WEEKDAYS = ["आ.", "सो.", "मं.", "बु.", "बि.", "शु.", "श."]'),
    ("sun pada sign entry", "panchanga.py", "if pada % 9 == 0:", "if pada % 9 == 1:"),
    ("abhijit pada", "panchanga.py", "ABHIJIT_PADA = 83", "ABHIJIT_PADA = 82"),
    ("abhijit leaving not printed", "panchanga.py", "if surya.true_sun(rise) < ABHIJIT[1] <= surya.true_sun(next_rise):",
     "if False:"),
    ("rail name tishya", "panchanga.py", '"पुनर्वसु", "तिष्य",', '"पुनर्वसु", "पुष्य",'),
    ("rail name hasta", "panchanga.py", '"उ.फा.", "हस्ता",', '"उ.फा.", "हस्त",'),
    ("rahu at sunrise in spashta", "panchanga.py", '"rahu": arc(ketaki.rahu_of_day(day)),',
     '"rahu": arc(ketaki.rahu(rise)),'),
    ("planets at refracted sunrise in spashta", "panchanga.py",
     "**{body: arc(ketaki.at_sunrise(body, day)) for body in ketaki.PLANETS},",
     "**{body: arc(ketaki.geocentric(body, rise)) for body in ketaki.PLANETS},"),
    # ---- panchanga.py: the rail, stations, heliacal, boxes -------------------
    ("rail timed linearly", "panchanga.py", "jd = _refine(body, x, rise + ahead / abs(step) * (after - rise), rise, after)",
     "jd = rise + ahead / abs(step) * (after - rise)"),
    ("rail day from geometric sunrise", "panchanga.py",
     "rise, after = surya.sunrise(day), surya.sunrise(day + timedelta(days=1))\n    events = []",
     "rise, after = ketaki.sunrise(day), ketaki.sunrise(day + timedelta(days=1))\n    events = []"),
    ("no punah", "panchanga.py", 'again=step < 0 and body != "rahu"', "again=False"),
    ("mercury padas instead of nakshatras", "panchanga.py", 'if body in ("mercury", "venus"):\n        return sorted',
     'if body in ("venus",):\n        return sorted'),
    ("station flips not collapsed", "panchanga.py", "if turns and i - turns[-1][-1] <= 5:", "if turns and i - turns[-1][-1] <= 0:"),
    ("station at first flip", "panchanga.py", "            i = group[-1]\n", "            i = group[0]\n"),
    ("heliacal mercury 13", "panchanga.py", '"mercury": (14, 12)', '"mercury": (13, 12)'),
    ("heliacal mercury retro 13", "panchanga.py", '"mercury": (14, 12)', '"mercury": (14, 13)'),
    ("heliacal saturn 14", "panchanga.py", '"saturn": (15, 15)', '"saturn": (14, 14)'),
    ("heliacal mars 16", "panchanga.py", '"mars": (17, 17)', '"mars": (16, 16)'),
    ("heliacal jupiter 12", "panchanga.py", '"jupiter": (11, 11)', '"jupiter": (12, 12)'),
    ("heliacal venus 9", "panchanga.py", '"venus": (10, 8)', '"venus": (9, 8)'),
    ("heliacal venus retro 9", "panchanga.py", '"venus": (10, 8)', '"venus": (10, 9)'),
    ("heliacal at opposition", "panchanga.py", "        if e0 * e1 <= 0:\n", "        if e0 * e1 <= 0 and abs(e0) + abs(e1) < 90:\n"),
    ("august spelling", "panchanga.py", '"जुलाई", "अगस्त",', '"जुलाई", "अगस्ट",'),
    ("heliacal udaya/asta swapped", "panchanga.py", 'heliacal="उदय" if f1 > f0 else "अस्त"', 'heliacal="अस्त" if f1 > f0 else "उदय"'),
    ("rashi pravesh order", "panchanga.py", 'RAIL_ORDER = ["sun", "mars", "mercury", "jupiter", "venus", "saturn", "rahu"]',
     'RAIL_ORDER = ["sun", "mercury", "mars", "jupiter", "venus", "saturn", "rahu"]'),
    ("status visible threshold", "panchanga.py",
     "visible = abs((a - sun + 180) % 360 - 180) > HELIACAL_ARCS[body][0 if direct else 1]",
     "visible = abs((a - sun + 180) % 360 - 180) > HELIACAL_ARCS[body][0 if direct else 1] + 3"),
    ("status direct from the Sun", "panchanga.py", "direct = (b - a + 180) % 360 - 180 >= 0",
     "direct = (b - a + 180) % 360 - 180 > 0.1"),
    ("kundali at panchami", "panchanga.py", 'r["tithi"]["index"] % 15 + 1 >= 6', 'r["tithi"]["index"] % 15 + 1 >= 5'),
    ("kundali at saptami", "panchanga.py", 'r["tithi"]["index"] % 15 + 1 >= 6', 'r["tithi"]["index"] % 15 + 1 >= 7'),
    ("kundali ketu with rahu", "panchanga.py", 'int(surya.norm(rahu + 180) // SIGN_WIDTH)', "int(rahu // SIGN_WIDTH)"),
    # ---- panchanga.py: months and headers ------------------------------------
    ("era 1975 mesha", "panchanga.py", "(1975, (-0.713,", "(1975, (-0.663,"),
    ("era 1975 mina", "panchanga.py", "-0.129, -0.063, -0.316)),", "-0.129, -0.063, -0.296)),"),
    ("era 2005 karka", "panchanga.py", "(2005, (-0.613, -0.790, -0.386, -0.826,", "(2005, (-0.613, -0.790, -0.386, -0.776,"),
    ("era 2017 vrishabha", "panchanga.py", "(2017, (-0.403, -2.350,", "(2017, (-0.403, -2.300,"),
    ("era 2045 offset", "panchanga.py", "(2045, tuple(s - 0.43 for s in SHAPE_2045)),", "(2045, tuple(s - 0.38 for s in SHAPE_2045)),"),
    ("era 2045 shape", "panchanga.py", "SHAPE_2045 = (0.047,", "SHAPE_2045 = (0.097,"),
    ("era 2063 not plain", "panchanga.py", "(2063, (0,) * 12),", "(2063, (0.05,) * 12),"),
    ("era boundary 2063", "panchanga.py", "    (2063, (0,) * 12),", "    (2064, (0,) * 12),"),
    ("era boundary 2045", "panchanga.py", "    (2045, tuple(", "    (2046, tuple("),
    ("refraction from 2063", "panchanga.py", "REFRACTION_FROM = 2064", "REFRACTION_FROM = 2063"),
    ("refraction from 2065", "panchanga.py", "REFRACTION_FROM = 2064", "REFRACTION_FROM = 2065"),
    ("no karka rule", "panchanga.py", "    if sign == KARKA:\n        return day\n", ""),
    ("no makara rule", "panchanga.py", "boundary = dinamana if sign == MAKARA else 0.5 + dinamana / 2",
     "boundary = 0.5 + dinamana / 2"),
    ("night midpoint tie to later day", "panchanga.py", "return day if jd - rise <= boundary else", "return day if jd - rise < boundary else"),
    ("midnight instead of night midpoint", "panchanga.py", "boundary = dinamana if sign == MAKARA else 0.5 + dinamana / 2",
     "boundary = dinamana if sign == MAKARA else (surya.local_julian_day(day + timedelta(days=1), 0) - rise)"),
    ("no adhik months", "panchanga.py", "result.append(Lunation(begin, finish, (first + 1) % 12, first == last))",
     "result.append(Lunation(begin, finish, (first + 1) % 12, False))"),
    ("krishna named amanta", "panchanga.py", "        named = months[position + 1]\n", "        named = lunation\n"),
    ("no shuddha", "panchanga.py", '"shuddha" if position and months[position - 1].adhik else None)', "None)"),
    ("shaka offset", "panchanga.py", "shaka = bs_year - 135 +", "shaka = bs_year - 134 +"),
    ("nepal sambat offset", "panchanga.py", '"nepal_samvat": bs_year - 937 +', '"nepal_samvat": bs_year - 936 +'),
    ("nepal sambat new year", "panchanga.py", "KARTIK = 7", "KARTIK = 6"),
    ("nepal sambat month suffix", "panchanga.py", '("थ्वः" if shukla else "गा")', '("गा" if shukla else "थ्वः")'),
    ("ritu offset", "panchanga.py", "ritus = [RITUS[((s + 1) % 12) // 2] for s in signs]", "ritus = [RITUS[(s % 12) // 2] for s in signs]"),
    ("ayana signs", "panchanga.py", "UTTARAYANA_SIGNS = {9, 10, 11, 0, 1, 2}", "UTTARAYANA_SIGNS = {10, 11, 0, 1, 2, 3}"),
    ("gregorian span joiner", "panchanga.py", 'f"{GREGORIAN_MONTHS[first.month - 1]} + {GREGORIAN_MONTHS[last.month - 1]} {last.year}"',
     'f"{GREGORIAN_MONTHS[first.month - 1]}-{GREGORIAN_MONTHS[last.month - 1]} {last.year}"'),
    ("pages by month", "panchanga.py", 'same = (row["tithi"]["index"] < 15) == (current[-1]["tithi"]["index"] < 15)',
     'same = row["bs_month"] == current[-1]["bs_month"]'),
    ("status on first page only", "panchanga.py", "for page in (result[0], result[-1]):", "for page in (result[0],):"),
    # ---- ketaki.py ------------------------------------------------------------
    ("sun equation 115.0", "ketaki.py", "SUN_EQUATION = (115.2, 1.2)", "SUN_EQUATION = (115.0, 1.2)"),
    ("sun equation no e2", "ketaki.py", "SUN_EQUATION = (115.2, 1.2)", "SUN_EQUATION = (115.2, 0.0)"),
    ("sun equation e2 sign", "ketaki.py", "SUN_EQUATION = (115.2, 1.2)", "SUN_EQUATION = (115.2, -1.2)"),
    ("sun at true sunrise", "ketaki.py", "    return _sun(mean_sunrise(jd))", "    return _sun(jd)"),
    ("planets at refracted sunrise", "ketaki.py", "return surya.sunrise(day, surya.GEOMETRIC)", "return surya.sunrise(day)"),
    ("mercury manda 30 = 97", "ketaki.py", '"mercury": [0, 32, 65, 96,', '"mercury": [0, 32, 65, 97,'),
    ("mars manda entry", "ketaki.py", '"mars": [0, 17, 33, 48, 63, 76,', '"mars": [0, 17, 33, 48, 63, 77,'),
    ("jupiter manda entry", "ketaki.py", '"jupiter": [0, 9, 18, 26, 34, 41,', '"jupiter": [0, 9, 18, 26, 34, 42,'),
    ("venus manda entry", "ketaki.py", '"venus": [0, 1, 3, 4, 5, 6,', '"venus": [0, 1, 3, 4, 5, 7,'),
    ("saturn manda entry", "ketaki.py", '"saturn": [0, 10, 21, 30, 39, 47,', '"saturn": [0, 10, 21, 30, 39, 48,'),
    ("mars shighra entry", "ketaki.py", "333, 361, 385, 402, 410,", "333, 361, 385, 402, 411,"),
    ("mercury shighra entry", "ketaki.py", "197, 212, 222, 227, 226,", "197, 212, 222, 226, 226,"),
    ("jupiter shighra entry", "ketaki.py", "104, 109, 111, 109, 104, 95,", "104, 109, 112, 109, 104, 95,"),
    ("venus shighra 140 = 463", "ketaki.py", "445, 460, 462, 441,", "445, 460, 463, 441,"),
    ("saturn shighra entry", "ketaki.py", "54, 58, 60, 60, 58, 55,", "54, 58, 60, 61, 58, 55,"),
    ("mars karnanka entry", "ketaki.py", "MARS_KARNANKA = [0, 1, 3, 8, 16, 22,", "MARS_KARNANKA = [0, 1, 3, 8, 16, 23,"),
    ("mercury distance entry", "ketaki.py", "MERCURY_DISTANCE = [47, 47, 46, 46, 45, 45, 44,", "MERCURY_DISTANCE = [47, 47, 46, 46, 45, 45, 45,"),
    ("mercury mean distance", "ketaki.py", '"mercury": 39}', '"mercury": 38}'),
    ("mars eccentricity", "ketaki.py", "MARS_ECCENTRIC = 14", "MARS_ECCENTRIC = 13"),
    ("mars distance without half phala", "ketaki.py", "math.cos(math.radians(k + phala / 2))", "math.cos(math.radians(k))"),
    ("karsha formula", "ketaki.py", "f = (b / 9) * (20 - b / 9)", "f = (b / 9) * (21 - b / 9)"),
    ("mars mean motion", "ketaki.py", '"mars": 10 / 19 - 10 / (73 * 60),', '"mars": 10 / 19 - 10 / (74 * 60),'),
    ("mercury epoch", "ketaki.py", '"mercury": _arc(1, 22, 30),', '"mercury": _arc(1, 22, 31),'),
    ("venus apogee motion", "ketaki.py", '"venus": -28.5,', '"venus": 28.5,'),
    ("table longitude without shift", "ketaki.py",
     "return _shighra(body, jd + rise - printed, _sun(mean_sunrise(rise) + jd - printed))",
     "return _shighra(body, jd, _sun(mean_sunrise(rise) + jd - printed))"),
    ("station sampling coarse", "ketaki.py", "    step = 5 / 1440\n", "    step = 120 / 1440\n"),
    # ---- editorial.py ---------------------------------------------------------
    ("samvatsara vijaya", "editorial.py", "VIJAYA = 26", "VIJAYA = 27"),
    ("jupiter revolutions", "editorial.py", "JUPITER_REVOLUTIONS = 364_220", "JUPITER_REVOLUTIONS = 364_226"),
    ("samvatsara may repeat", "editorial.py", "index = (index + 1) % 60 if current == index else current", "index = current"),
    ("saptashalaka pair", "editorial.py", '("ति", "ज्ये"),', '("ति", "मू"),'),
    ("corner pair dropped", "editorial.py", 'CORNERS = _pairs(("कृ", "वि"), ("भ", "अनु"), ("अश्ले", "ध"), ("म", "श्र"))',
     'CORNERS = _pairs(("कृ", "वि"), ("भ", "अनु"), ("अश्ले", "ध"))'),
    ("papakshani one end only", "editorial.py", "        for jd in (a, b):\n", "        for jd in (a,):\n"),
    ("planet abhijit counted", "editorial.py", "    index = int(longitude // panchanga.NAKSHATRA_WIDTH)\n    return index if index <= 20 else index + 1",
     "    return panchanga.nakshatra28(longitude)"),
    ("papamsha first-day rule", "editorial.py", "if i == 0 and gates[0] == 1:", "if False:"),
    ("papamsha rahu at sunrise", "editorial.py", "    rahu = ketaki.rahu_of_day(day)\n    found[\"rahu\"]",
     "    rahu = ketaki.rahu(surya.sunrise(day))\n    found[\"rahu\"]"),
    ("papamsha mars linear", "editorial.py",
     'found["mars"], found["saturn"] = ketaki.at_sunrise("mars", day), ketaki.at_sunrise("saturn", day)',
     'found["mars"], found["saturn"] = ketaki.longitude("mars", surya.sunrise(day)), ketaki.longitude("saturn", surya.sunrise(day))'),
    ("navamsha from 0", "editorial.py", "return int(longitude // NAVAMSHA_WIDTH) % 12 + 1", "return int(longitude // NAVAMSHA_WIDTH) % 12 + 2"),
    ("papakshani number order", "editorial.py", "return panchanga_digits(index28 + 1 - (index28 > 21))",
     "return panchanga_digits(index28 + 1)"),
    # ---- render.py ------------------------------------------------------------
    ("no pitri paksha", "render.py", '{"कृष्ण": " (पितृ) ", "शुक्ल": " (दुर्गा) "}', '{"कृष्ण": "", "शुक्ल": " (दुर्गा) "}'),
    ("no durga paksha", "render.py", '{"कृष्ण": " (पितृ) ", "शुक्ल": " (दुर्गा) "}', '{"कृष्ण": " (पितृ) ", "शुक्ल": ""}'),
    ("comma after paksha", "render.py", '{named}पक्षः "', '{named}पक्षः, "'),
    ("two-ayana form without visarga", "render.py", 'parts = [f"{a}ं {r}ः" for', 'parts = [f"{a}ं {r}" for'),
    ("rail punah text", "render.py", 'again = "पुनः" if entry.get("again") else ""', 'again = ""'),
    ("rail abhijit out text", "render.py", 'where = "अभिजितत्याग"', 'where = "अभिजितमा"'),
    ("rashi pravesh sign from 0", "render.py", "{deva(e['sign'] + 1)}", "{deva(e['sign'])}"),
    ("rashi pravesh ketu dropped", "render.py", "text += f\"के.{deva(e['ketu_sign'] + 1)}\"", "pass"),
    ("status box letters", "render.py", "{'मा' if s['direct'] else 'व'}", "{'व' if s['direct'] else 'मा'}"),
    ("kundali houses clockwise", "render.py", "sign = (chart[\"lagna\"] + house) % 12", "sign = (chart[\"lagna\"] - house) % 12"),
    ("belantar text sign", "render.py", 'sign = "+" if seconds >= 0 else "-"', 'sign = "-" if seconds >= 0 else "+"'),
    ("dinamana text", "render.py", "dinamana = deva(f\"{row['dinamana'][0]}।{row['dinamana'][1]}\")",
     "dinamana = deva(f\"{row['dinamana'][0]}:{row['dinamana'][1]}\")"),
    ("ghati separator", "render.py", "return deva(f\"{ending['ghati']}।{ending['pala']}\")", "return deva(f\"{ending['ghati']}:{ending['pala']}\")"),
    ("ahoratra text", "render.py", 'return f"<td>{escape(label)}</td><td>अहोरात्र</td><td>अहोरात्र</td>"',
     'return f"<td>{escape(label)}</td><td></td><td></td>"'),
    ("ritu suffix", "render.py", '"शरद्": "शरदृतुः"', '"शरद्": "शरद्र्तुः"'),
    ("heliacal rail text", "render.py", 'text = f\'{deva(gate)} {RAIL_NAMES[e["body"]].replace("मंगल", "मङ्गल")} {e["side"]}मा {e["heliacal"]}\'',
     'text = f\'{deva(gate)} {RAIL_NAMES[e["body"]]} {e["side"]}मा {e["heliacal"]}\''),
    ("station rail text", "render.py", 'text = f\'{deva(gate)} {e["station"]} {STATION_NAMES[e["body"]]}\'',
     'text = f\'{deva(gate)} {STATION_NAMES[e["body"]]} {e["station"]}\''),
]

# Mutations no test can catch, with the reason. Keep this short.
EXPECTED_SURVIVORS: dict[str, str] = {
    "night midpoint tie to later day": "`<=` and `<` differ only when a sankranti lands on the night midpoint "
                                        "to the last bit; the 2066 चैत tie is exact in pala, not in floats",
    "heliacal rail text": "no Mars उदय/अस्त falls in 2082 or 2083; मङ्गल follows the station lines (p21)",
}


def run(mutation: tuple[str, str, str, str]) -> tuple[str, list[str]]:
    name, file, old, new = mutation
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "panchang"
        shutil.copytree(HERE, root, ignore=shutil.ignore_patterns("output", "research", "__pycache__", ".*", "*.html"))
        path = root / file
        text = path.read_text()
        count = text.count(old)
        if count != 1:
            return name, [f"BAD MUTATION: `old` found {count} times"]
        path.write_text(text.replace(old, new))
        for tests, tag in ((TESTS, ""), (SNAPSHOT, "SNAPSHOT ONLY: ")):
            result = subprocess.run([sys.executable, "-m", "unittest", *tests], cwd=root,
                                    capture_output=True, text=True, timeout=900)
            if result.returncode:
                failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+)", result.stderr, re.M)))
                return name, [tag + ", ".join(failed or ["(non-zero exit)"])]
        return name, []


def main() -> int:
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    chosen = [m for m in MUTATIONS if pattern in m[0]]
    names = [m[0] for m in MUTATIONS]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        print("duplicate names:", duplicates)
        return 1
    survivors, bad, snapshot_only = [], [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, failed in pool.map(run, chosen):
            if failed and failed[0].startswith("BAD MUTATION"):
                bad.append(name)
                print(f"  ?? {name}: {failed[0]}")
            elif failed and failed[0].startswith("SNAPSHOT ONLY"):
                snapshot_only.append(name)
                print(f"  ~~ {name}: {failed[0]}")
            elif failed:
                print(f"  ok {name}: caught by {failed[0][:120]}")
            else:
                survivors.append(name)
                print(f"  !! {name}: SURVIVED" + (f" (expected: {EXPECTED_SURVIVORS[name]})" if name in EXPECTED_SURVIVORS else ""))
    unexpected = [s for s in survivors if s not in EXPECTED_SURVIVORS]
    print(f"\n{len(chosen)} mutations: {len(chosen) - len(survivors) - len(bad) - len(snapshot_only)} caught by the "
          f"book tests, {len(snapshot_only)} only by a snapshot, {len(survivors)} survived "
          f"({len(unexpected)} unexpected), {len(bad)} malformed")
    return 1 if unexpected or bad else 0


if __name__ == "__main__":
    sys.exit(main())
