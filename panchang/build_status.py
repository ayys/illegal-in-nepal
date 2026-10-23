#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["nepali-datetime", "nepali"]
# ///
"""Build panchang/status.html — a visual report of generator state vs the 2083 book."""

from __future__ import annotations

import io
import sys
import unittest
from datetime import date
from pathlib import Path

import panchanga
import surya
import test_panchanga as book
import test_editorial
import test_ketaki
import test_rail
import test_surya

OUT = Path(__file__).resolve().parent / "status.html"
PDF = Path(__file__).resolve().parent / "output" / "panchang-2083.pdf"
JSON_OUT = Path(__file__).resolve().parent / "output" / "panchang-2083.json"


def limb_accuracy(rows: dict) -> dict:
    hist: dict[str, int] = {}
    exact = total = mismatches = 0
    for day, ends in book.BOOK.items():
        row = rows[day]
        for limb, value in zip(("tithi", "nakshatra", "yoga"), ends):
            got = book.computed(row[limb]["ends"])
            want = book.expected(value)
            if len(got) != len(want):
                mismatches += 1
                continue
            for g, w in zip(got, want):
                total += 1
                d = g - w
                hist[str(d)] = hist.get(str(d), 0) + 1
                if d == 0:
                    exact += 1
    return {"exact": exact, "total": total, "mismatches": mismatches, "hist": hist}


def sun_accuracy(rows: dict) -> dict:
    exact = within1 = 0
    total = 0
    for day, (sr, ss) in book.SUN.items():
        row = rows[day]
        for clock, want in ((row["sunrise_clock"], sr), (row["sunset_clock"], ss)):
            got = clock[0] * 60 + clock[1]
            total += 1
            diff = abs(got - book.minutes(want))
            if diff == 0:
                exact += 1
            if diff <= 1:
                within1 += 1
    return {"exact": exact, "within1": within1, "total": total}


def dinamana_accuracy(rows: dict) -> dict:
    exact = within2 = 0
    for offset, pala in enumerate(book.DINAMANA):
        day = date(2027, 1, 8 + offset)
        ghati, got = rows[day.isoformat()]["dinamana"]
        assert ghati == 26
        diff = abs(got - pala)
        if diff == 0:
            exact += 1
        if diff <= 2:
            within2 += 1
    return {"exact": exact, "within2": within2, "total": len(book.DINAMANA)}


FORTNIGHTS = [
    ("2082 वैशाख शुक्ल", lambda d: d.year == 2025, book.BOOK_2082),
    ("2082 माघ कृष्ण", lambda d: d.year == 2026, book.BOOK_2082),
    ("2083 वैशाख", lambda d: d.month in (4, 5), book.BOOK),
    ("2083 कार्तिक", lambda d: d.month in (10, 11), book.BOOK),
    ("2083 पौष/माघ", lambda d: d.year == 2027, book.BOOK),
]
APOGEE_SHIFTS = [x / 100 for x in range(-180, -159, 2)]


def apogee_fits() -> list[dict]:
    """Best MOON_APOGEE_CORRECTION per transcribed fortnight."""
    saved = surya.MOON_APOGEE_CORRECTION
    out = []
    try:
        for label, keep, source in FORTNIGHTS:
            items = [(d, v) for d, v in source.items() if keep(d)]
            scores = {}
            for shift in APOGEE_SHIFTS:
                surya.MOON_APOGEE_CORRECTION = shift
                exact = total = 0
                for day, ends in items:
                    row = panchanga.day_row(day, 0, 1)
                    for limb, value in zip(("tithi", "nakshatra", "yoga"), ends):
                        got, want = book.computed(row[limb]["ends"]), book.expected(value)
                        if len(got) == len(want):
                            total += len(want)
                            exact += sum(g == w for g, w in zip(got, want))
                scores[shift] = (exact, total)
            best = max(scores, key=lambda s: scores[s][0])
            out.append({"label": label, "best": best, "scores": scores})
    finally:
        surya.MOON_APOGEE_CORRECTION = saved
    return out


def rahu_residuals() -> list[tuple[str, float, float]]:
    """(date, residual at local sunrise, residual at Ujjain mean sunrise) in arcseconds."""
    def deg(arc: str) -> float:
        sign, d, m, s = map(int, arc.split(":"))
        return sign * 30 + d + m / 60 + s / 3600

    out = []
    for table in (book.SPASHTA_2082, book.SPASHTA):
        for day, (_, _, rahu, _) in table.items():
            want = deg(rahu)
            at = lambda jd: ((surya.rahu(jd) - want + 180) % 360 - 180) * 3600
            out.append((day.isoformat(), at(surya.sunrise(day)), at(surya.ujjain_mean_sunrise(day))))
    return out


def table_comparison() -> list[dict]:
    """Computed month starts vs the BS lookup tables in nepali-datetime and py-nepali."""
    import nepali_datetime
    from nepali.date_converter import converter

    tables = {
        "nepali-datetime": lambda y, m: nepali_datetime.date(y, m, 1).to_datetime_date(),
        "py-nepali": lambda y, m: date(*converter.nepali_to_english(y, m, 1)),
    }
    spans = [("nepali-datetime", 1975, 2083), ("py-nepali", 2000, 2083),
             ("nepali-datetime", 2084, 2100), ("py-nepali", 2084, 2099)]
    starts = {y: panchanga.month_starts(y)[:12] for y in range(1975, 2101)}
    confirmed = {(int(r["bs_year"]), int(r["month"])): date.fromisoformat(r["first_day"])
                 for r in book.read_csv("month_starts.csv")}
    out = []
    for name, lo, hi in spans:
        misses = []
        total = known = 0
        for y in range(lo, hi + 1):
            for m in range(1, 13):
                total += 1
                want = tables[name](y, m)
                got = starts[y][m - 1]
                if got != want:
                    table_wrong = confirmed.get((y, m)) == got
                    known += table_wrong
                    misses.append(f"{y}/{m}: {got:%m-%d} vs {want:%m-%d}" + (" ✓" if table_wrong else ""))
        out.append({"table": name, "span": f"{lo}–{hi}", "match": total - len(misses),
                    "total": total, "known": known, "misses": misses})
    return out


def run_tests() -> tuple[bool, str, int]:
    buf = io.StringIO()
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.loadTestsFromModule(test_surya), loader.loadTestsFromModule(book),
                                  loader.loadTestsFromModule(test_editorial),
                                  loader.loadTestsFromModule(test_ketaki),
                                  loader.loadTestsFromModule(test_rail)])
    result = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
    return result.wasSuccessful(), buf.getvalue(), result.testsRun


def components() -> list[dict]:
    return [
        {"area": "Year layout (26 pages, 365 days)", "status": "ok", "note": "Matches FORMAT-2083-A structure"},
        {"area": "Solar month starts (sankranti date rule)", "status": "ok", "note": "1304/1308 vs nepali-datetime 1975–2083 (1993/4 is its error; 1977/7, 1989/8, 2018/9 open); nishitha day, Karka/Makara rule, per-era offsets read from books, geometric sunrise before 2064"},
        {"area": "Adhik maas naming", "status": "ok", "note": "Adhik Jyeshtha pages 5–6"},
        {"area": "Page headers (month, NS, Gregorian, ayana, ritu)", "status": "ok", "note": "7 pages regression-tested"},
        {"area": "Tithi / nakshatra / yoga end times", "status": "ok", "note": "±1 min on calibrated fortnights"},
        {"area": "Stacked endings & अहोरात्र", "status": "ok", "note": "Double endings in one civil day"},
        {"area": "Karana column", "status": "ok", "note": "First-half karanas before next sunrise"},
        {"area": "Anandadi yoga", "status": "ok", "note": "15/15 on Paush page 21"},
        {"area": "Moon sign change times", "status": "ok", "note": "Checked on Jan 8–21"},
        {"area": "Sunrise / sunset (printed clock)", "status": "ok", "note": "Ceil rise, floor set; Lahiri frame"},
        {"area": "Sun / Moon / Rahu at sunrise", "status": "ok", "note": "Arc-second to sub-arcminute"},
        {"area": "Belantar (equation of time)", "status": "ok", "note": "±2 s at noon"},
        {"area": "Lagna start table", "status": "ok", "note": "±1 min (Jan fortnight)"},
        {"area": "Sun pada rail (nakshatra / rashi entries)", "status": "ok", "note": "5 events on page 21"},
        {"area": "Dinamana (day length)", "status": "warn", "note": "Within 2 pala; rule not exact"},
        {"area": "Ghati-pala for tithi ends", "status": "warn", "note": "Mostly exact; 1 pala drift on some rows"},
        {"area": "Mars – Saturn spashta", "status": "ok", "note": "ketaki.py: median 1–16″ over 1841 book values (2082, 2083)"},
        {"area": "Planet rail: entries, stations, राशि प्रवेश", "status": "ok", "note": "179 rail lines (pp2-27) found on their गते; 18/22 boxes exact"},
        {"area": "Heliacal rising/setting (उदयास्त)", "status": "warn", "note": "Classic arcs: 7/17 book events to the hour, 10 off by days"},
        {"area": "Kundali chart", "status": "fail", "note": "Placeholder box"},
        {"area": "Festival / vrat notes column", "status": "fail", "note": "Editorial; optional JSON config"},
        {"area": "Samvatsara, papakshani, papamsha", "status": "ok", "note": "editorial.py; papakshani 50/51 pages, papamsha Mars 81/82, Saturn 32/33"},
        {"area": "PDF typography vs InDesign book", "status": "warn", "note": "Layout approximates; not pixel-identical"},
        {"area": "Other BS years", "status": "ok", "note": "2082 book: limb ends ±1 min, Sun/Moon/Rahu/belantar in tolerance with 2083 constants"},
    ]


def constants_sections() -> list[tuple[str, list[tuple[str, str, str]]]]:
    """(section title, rows of name, value, role)."""
    return [
        ("Place & time", [
            ("NST", "UTC+5:45", "Civil timezone for all clock times"),
            ("LATITUDE", "27.7° N", "Kathmandu — rise/set, lagna"),
            ("LONGITUDE", "85.3167° E", "LMT→NST: (86.25 − lon) × 4 min"),
            ("UJJAIN_LONGITUDE", "75.7682° E", "Kali epoch Julian day"),
        ]),
        ("Surya Siddhanta epoch & rates", [
            ("MAHAYUGA_DAYS", f"{surya.MAHAYUGA_DAYS:,}", "Days per mahayuga"),
            ("sun revolutions / mahayuga", f"{surya.MAHAYUGA_REVOLUTIONS['sun']:,}", "Mean Sun"),
            ("moon revolutions / mahayuga", f"{surya.MAHAYUGA_REVOLUTIONS['moon']:,}", "Mean Moon"),
            ("moon_apogee rev / mahayuga", f"{surya.MAHAYUGA_REVOLUTIONS['moon_apogee']:,}", "Mean Moon apogee"),
            ("CREATION_TO_KALI_DAYS", "1,955,880,000 × (mahayuga days / 4,320,000)", "Ahargana from creation"),
            ("KALI_JD", f"{surya.KALI_JD:.6f}", "Kali midnight at Ujjain"),
            ("KALI_MOON_APOGEE", "90°", "Moon apogee at Kali; other mean longitudes 0°"),
            ("SUN_APOGEE_AT_KALI", f"{surya.SUN_APOGEE_AT_KALI:.2f}°", "From 387 rev/kalpa; drifts with time"),
            ("SUN_APOGEE_KALPA_REVOLUTIONS", "387", "Sun apogee motion per kalpa"),
        ]),
        ("Manda (true Sun & Moon)", [
            ("RADIUS", "3438", "SS jyā table"),
            ("SINES", "24 SS values, 3°45′ steps", "Linear interpolation in _jya()"),
            ("Sun manda circumference", "14° → 13°40′", "Even/odd at kendra; eq. subtracted"),
            ("Moon manda circumference", "32° → 31°40′", "Even/odd at kendra"),
        ]),
        ("Fitted to 2082 + 2083 books", [
            ("MOON_APOGEE_CORRECTION", "−1.7°", "Added to mean Moon apogee — tithi/nak times; constant Apr 2025–Jan 2027"),
            ("RAHU_OFFSET", "−50.4″", "After Lahiri, Rahu taken at Ujjain mean sunrise (fixed daily moment)"),
            ("(not in surya.py)", "ceil sunrise / floor sunset", "Printed clock minutes"),
        ]),
        ("Lahiri / Ketaki frame", [
            ("Lahiri ayanamsha", "23.857092° + (5029.0966·T + 1.11113·T²)/3600", "T = Julian centuries from J2000"),
            ("Applied to", "true SS Sun (+ shift)", "Rise, set, lagna, belantar, Rahu — not Moon limbs"),
            ("Obliquity", "23.439291° − 0.0130042·T", "Declination, oblique ascension"),
            ("HORIZON", "−34′ (−34/60°)", "Disc centre + refraction only"),
            ("SIDEREAL_DAY", "0.99726957", "Lagna advance rate after sunrise"),
            ("Rahu mean node", "125.04452 − 1934.136261·T + …", "At Ujjain 6:00 LMT, then − Lahiri + RAHU_OFFSET"),
            ("Not used for book match", "SS trepidation (600/yuga), 24° obl., −0.83° horizon", "Earlier experiments"),
        ]),
        ("Display & rounding", [
            ("Ghati/pala from sunrise", "(jd − sunrise) × 1440 × 2.5", "1 ghati = 24 min ⇒ 2.5 pala/min"),
            ("दिनमान", "floor(2 × half_day × 2.5) palas", "Half-day from same rise geometry"),
        ]),
        ("Panchāṅga divisions (panchanga.py)", [
            ("TITHI_WIDTH", "12°", "30 tithis per cycle"),
            ("KARANA_WIDTH", "6°", "First-half karanas before next sunrise"),
            ("NAKSHATRA_WIDTH", "360/27°", "27 nakshatras"),
            ("PADA_WIDTH", "360/108°", "Sun rail (nakshatra quarters)"),
            ("SIGN_WIDTH", "30°", "Rashi, sankranti, lagna signs"),
            ("ABHIJIT", "276°40′ – 280°53′20″", "28-nakshatra Anandadi index 21"),
            ("ANANDADI_START", "[4,8,12,16,20,24,0]", "By weekday Mon=0 … Sun=6"),
        ]),
        ("Calendar / header", [
            ("BS → Gregorian anchor", "bs_year − 57", "Month boundaries from solar sankranti"),
            ("Shaka", "bs_year − 135 (+1 after Chaitra NM)", "From computed new moon"),
            ("Nepal Samvat", "bs_year − 937 (+1 after Kartik NM)", "From computed new moon"),
            ("Uttarayana signs", "{9,10,11,0,1,2}", "Makar through Mithun"),
            ("Solar month start", "Nishitha to nishitha", "Karka: sunrise; Makara: sunset"),
            ("SANKRANTI_ERAS", "−2.9 to +1.1 ghati", "Per-era, per-sign sankranti offset; 0 from 2070"),
        ]),
        ("PDF layout (render.py)", [
            ("PAGE_WIDTH × HEIGHT", "1007.01 × 555.591 pt", "From InDesign export"),
            ("Column widths", "Measured pt values", "Typography only, not astronomy"),
        ]),
        ("editorial.py", [
            ("samvatsara", "Jovian, SS mean Jupiter", "Current at शुक्ल चैत्र; no repeats, क्षय skipped"),
            ("papakshani, papamsha", "Per page", "Malefics, सप्तशलाका and corner vedha; navamshas"),
        ]),
        ("Config only (generate.py JSON)", [
            ("notes", "Per day", "Editorial"),
        ]),
    ]


def constants_html() -> str:
    parts = [
        '<p class="const-intro">Defined mainly in <code>surya.py</code> and '
        '<code>panchanga.py</code>. Fitted values are checked against the 2082 and 2083 books.</p>',
    ]
    for title, rows in constants_sections():
        trs = "".join(
            f"<tr><td><code>{name}</code></td><td>{val}</td><td>{role}</td></tr>"
            for name, val, role in rows
        )
        fitted = "Fitted" in title
        cls = " const-fitted" if fitted else ""
        parts.append(
            f'<details class="const-group{cls}"{" open" if fitted else ""}><summary>{title}</summary>'
            f'<table class="const"><tr><th>Name</th><th>Value</th><th>Role</th></tr>{trs}</table></details>'
        )
    return "".join(parts)


def page_timeline(pages: list[dict]) -> list[dict]:
    out = []
    for p in pages:
        h = p["header"]
        r = p["rows"]
        out.append({
            "page": p["page"],
            "days": len(r),
            "first": r[0]["date"],
            "last": r[-1]["date"],
            "header": f"{h['lunar_month']}{h['paksha']} · NS {h['nepal_samvat']} · {h['gregorian']}",
        })
    return out


def html_report(data: dict) -> str:
    def bar(pct: float, color: str) -> str:
        return f'<div class="bar"><i style="width:{pct:.1f}%;background:{color}"></i></div>'

    def badge(status: str) -> str:
        labels = {"ok": "Works", "warn": "Approximate", "fail": "Missing"}
        return f'<span class="badge {status}">{labels[status]}</span>'

    rows_html = "".join(
        f"<tr><td>{c['area']}</td><td>{badge(c['status'])}</td><td>{c['note']}</td></tr>"
        for c in data["components"]
    )
    timeline = "".join(
        f"<tr><td>{p['page']}</td><td>{p['days']}</td><td>{p['first']}</td><td>{p['last']}</td>"
        f"<td>{p['header']}</td></tr>"
        for p in data["timeline"]
    )
    hist = data["limb"]["hist"]
    hist_bars = "".join(
        f"<div class='hist-row'><span>{k} min</span>{bar(v / data['limb']['total'] * 100, '#333')}<span>{v}</span></div>"
        for k, v in sorted(hist.items(), key=lambda x: int(x[0]))
    )

    apogee_head = "".join(f"<th>{s:+.2f}</th>" for s in APOGEE_SHIFTS)
    apogee_rows = "".join(
        f"<tr><td>{f['label']}</td>"
        + "".join(
            f"<td{' class=best' if s == f['best'] else ''}>{e}/{n}</td>" for s, (e, n) in f["scores"].items()
        )
        + f"<td><b>{f['best']:+.2f}°</b></td></tr>"
        for f in data["apogee"]
    )
    rahu_rows = "".join(
        f"<tr><td>{d}</td><td>{a:+.1f}″</td><td>{b:+.1f}″</td></tr>" for d, a, b in data["rahu"]
    )

    table_rows = "".join(
        f"<tr><td>{t['table']}</td><td>BS {t['span']}</td><td>{t['match']}/{t['total']}</td>"
        f"<td>{t['match'] / t['total'] * 100:.1f}%</td>"
        f"<td>{t['known']}/{len(t['misses'])}</td>"
        f"<td style='font-size:.78rem'>{', '.join(t['misses'][:20])}{' …' if len(t['misses']) > 20 else ''}</td></tr>"
        for t in data["tables"]
    )

    tests_ok = "PASS" if data["tests_pass"] else "FAIL"
    test_class = "ok" if data["tests_pass"] else "fail"
    const_block = constants_html()

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panchang 2083 — generator status</title>
<style>
  :root {{
    --bg: #f4f1ea; --ink: #1a1a1a; --muted: #5c5c5c; --card: #fff;
    --ok: #2d6a4f; --warn: #bc6c25; --fail: #9b2226; --line: #ddd;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font: 15px/1.45 system-ui, sans-serif; background: var(--bg); color: var(--ink); }}
  header {{ background: #111; color: #fff; padding: 1.5rem 2rem; }}
  header h1 {{ margin: 0 0 .25rem; font-size: 1.5rem; }}
  header p {{ margin: 0; color: #ccc; max-width: 70ch; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 1.5rem; display: grid; gap: 1.25rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 1rem 1.1rem; }}
  .card h2 {{ margin: 0 0 .75rem; font-size: 1rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }}
  .metric {{ font-size: 2rem; font-weight: 700; line-height: 1.1; }}
  .metric small {{ display: block; font-size: .85rem; font-weight: 500; color: var(--muted); margin-top: .35rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
  th, td {{ border-bottom: 1px solid var(--line); padding: .45rem .35rem; text-align: left; vertical-align: top; }}
  th {{ color: var(--muted); font-weight: 600; }}
  .badge {{ display: inline-block; padding: .15rem .45rem; border-radius: 4px; font-size: .75rem; font-weight: 700; }}
  .badge.ok {{ background: #d8f3dc; color: var(--ok); }}
  .badge.warn {{ background: #ffe8cc; color: var(--warn); }}
  .badge.fail {{ background: #ffdad6; color: var(--fail); }}
  .bar {{ height: 8px; background: #eee; border-radius: 4px; overflow: hidden; flex: 1; }}
  .bar i {{ display: block; height: 100%; }}
  .hist-row {{ display: flex; align-items: center; gap: .5rem; margin: .35rem 0; }}
  .hist-row span:first-child {{ width: 3.5rem; font-size: .8rem; color: var(--muted); }}
  .hist-row span:last-child {{ width: 2rem; text-align: right; font-size: .8rem; }}
  pre {{ background: #f8f8f8; border: 1px solid var(--line); padding: .75rem; overflow: auto; font-size: .78rem; max-height: 280px; }}
  code {{ font-family: ui-monospace, monospace; font-size: .88em; }}
  .pipeline {{ display: flex; flex-wrap: wrap; gap: .5rem; align-items: stretch; }}
  .pipe {{ flex: 1 1 140px; background: #fafafa; border: 1px dashed var(--line); padding: .6rem; border-radius: 6px; }}
  .pipe b {{ display: block; margin-bottom: .25rem; }}
  .tests {{ font-weight: 700; color: var(--{test_class}); }}
  a {{ color: #005fcc; }}
  .const-intro {{ margin: 0 0 1rem; color: var(--muted); font-size: .92rem; }}
  .const-group {{ margin-top: 1.1rem; }}
  details.card > summary {{ cursor: pointer; font-size: 1rem; text-transform: uppercase; letter-spacing: .04em;
    color: var(--muted); font-weight: 600; margin: -.2rem 0; padding: .2rem 0; }}
  details.card[open] > summary {{ margin-bottom: .75rem; }}
  .const-group > summary {{ cursor: pointer; font-size: .95rem; font-weight: 700; padding: .25rem 0; }}
  .const-group.const-fitted > summary {{ color: var(--warn); }}
  .const-group[open] > summary {{ margin-bottom: .45rem; }}
  .toolbar {{ display: flex; gap: .5rem; justify-content: flex-end; }}
  .toolbar button {{ font: inherit; font-size: .85rem; padding: .3rem .7rem; border: 1px solid var(--line);
    background: var(--card); border-radius: 6px; cursor: pointer; }}
  table.const {{ font-size: .86rem; }}
  table.const code {{ font-size: .82rem; }}
  table.const td:nth-child(2) {{ font-family: ui-monospace, monospace; font-size: .82rem; white-space: nowrap; }}
  table.scan {{ font-size: .8rem; }}
  table.scan td.best {{ background: #d8f3dc; font-weight: 700; }}
</style>
</head>
<body>
<header>
  <h1>राष्ट्रिय पञ्चाङ्ग generator — status dashboard</h1>
  <p>Reverse-engineered from FORMAT-2083-A, cross-checked against the 2082 book. Compares computed output
     to transcribed book values (2083 वैशाख, कार्तिक, पौष/माघ; 2082 वैशाख, माघ). Regenerate with <code>./build_status.py</code> in <code>panchang/</code>.</p>
</header>
<main>
  <div class="toolbar">
    <button onclick="document.querySelectorAll('details').forEach(d => d.open = true)">Expand all</button>
    <button onclick="document.querySelectorAll('details').forEach(d => d.open = false)">Collapse all</button>
  </div>
  <details class="card" open>
    <summary>Summary</summary>
  <section class="grid">
    <div class="card"><h2>Tests</h2><div class="metric tests">{tests_ok}<small>{data['test_count']} unittest methods</small></div></div>
    <div class="card"><h2>Year</h2><div class="metric">{data['pages']}<small>fortnight pages · {data['days']} civil days</small></div></div>
    <div class="card"><h2>Limb ends</h2><div class="metric">{data['limb']['exact']}/{data['limb']['total']}<small>exact minute match (calibration set)</small></div></div>
    <div class="card"><h2>Sun times</h2><div class="metric">{data['sun']['exact']}/{data['sun']['total']}<small>printed sunrise/sunset exact</small></div></div>
    <div class="card"><h2>Dinamana</h2><div class="metric">{data['dinamana']['within2']}/{data['dinamana']['total']}<small>within 2 pala (Jan 8–22)</small></div></div>
  </section>
  </details>

  <details class="card" open>
    <summary>Computation pipeline</summary>
    <div class="pipeline">
      <div class="pipe"><b>Surya Siddhanta</b>Sun & Moon longitudes, tithi/nak/yoga/karana boundaries, Moon apogee −1.7°</div>
      <div class="pipe"><b>Lahiri frame</b>Sunrise, sunset, lagna, belantar, Rahu; modern obliquity; refraction at disc centre</div>
      <div class="pipe"><b>Ketaki</b>Mars–Saturn spashta (ketaki.py); graha udaya/asta and kundali still placeholders</div>
      <div class="pipe"><b>Editorial JSON</b>Festival notes — optional config</div>
    </div>
  </details>

  <details class="card" open>
    <summary>Accuracy &amp; outputs</summary>
  <section class="grid">
    <div class="card">
      <h2>Limb error histogram</h2>
      {hist_bars}
      <p style="font-size:.85rem;color:var(--muted);margin:.75rem 0 0">Count mismatches (stacked days): {data['limb']['mismatches']}</p>
    </div>
    <div class="card">
      <h2>Outputs</h2>
      <ul style="margin:0;padding-left:1.2rem">
        <li><code>generate.py 2083</code> → JSON + PDF (1007×556 pt)</li>
        <li>PDF sample: <code>{PDF}</code> {'exists' if data['pdf_exists'] else '(not generated here)'}</li>
        <li>JSON sample: <code>{JSON_OUT}</code> {'exists' if data['json_exists'] else '(not generated here)'}</li>
      </ul>
    </div>
  </section>
  </details>

  <details class="card" open>
    <summary>Cross-year check (2082 book)</summary>
    <p>Exact-minute tithi/nakshatra/yoga matches per fortnight for each Moon apogee correction.
       Best values span −1.74° to −1.70° with no trend from Apr 2025 to Jan 2027, so −1.7° is a constant.</p>
    <table class="scan"><tr><th>Fortnight</th>{apogee_head}<th>Best</th></tr>{apogee_rows}</table>
    <p style="margin-top:1rem">Rahu residual (computed − book). At local sunrise it swings with the season;
       at a fixed daily moment (Ujjain mean sunrise) it stays within a few arcseconds across both books.</p>
    <table class="scan"><tr><th>Date</th><th>At local sunrise</th><th>At Ujjain mean sunrise (used)</th></tr>{rahu_rows}</table>
  </details>

  <details class="card" open>
    <summary>Month starts vs published BS tables</summary>
    <p>First day of every solar month from <code>panchanga.month_starts</code> against the lookup tables in
       <code>nepali-datetime</code> and <code>py-nepali</code>. Rule, as printed in the books: the day runs from one
       night's midpoint (30 ghati + half the दिनमान after sunrise) to the next, a tie going to the earlier day;
       a Karka sankranti before sunrise counts for the day before and a Makara sankranti after sunset for the day
       after. Each era's sankrantis sit slightly off ours (<code>SANKRANTI_ERAS</code>): measured from the
       2031–2083 books (for 2024–2040, a separate value per sign), fitted to the tables before 2024.
       After 2083 the two libraries disagree with each other; the computed dates match py-nepali throughout.
       A ✓ marks a miss where a book or Drik Panchang confirms the computed date, i.e. the table is wrong
       (sources in <code>data/month_starts.csv</code>; see <code>docs/VERIFICATION.md</code>). The one open case is
       2093/10, a Makara sankranti about 1 pala after sunset, where Drik sides with nepali-datetime.</p>
    <table class="scan"><tr><th>Table</th><th>Years</th><th>Match</th><th></th><th>Table wrong</th><th>Misses (computed vs table)</th></tr>{table_rows}</table>
  </details>

  <details class="card" open>
    <summary>Constants reference</summary>
    {const_block}
  </details>

  <details class="card" open>
    <summary>Component matrix</summary>
    <table>
      <tr><th>Component</th><th>Status</th><th>Notes</th></tr>
      {rows_html}
    </table>
  </details>

  <details class="card">
    <summary>2083 page timeline (computed)</summary>
    <table>
      <tr><th>Book p.</th><th>Rows</th><th>First day</th><th>Last day</th><th>Header</th></tr>
      {timeline}
    </table>
  </details>

  <details class="card">
    <summary>Test log</summary>
    <pre>{data['test_log']}</pre>
  </details>
</main>
</body>
</html>"""


def main() -> None:
    pages = panchanga.year(2083)
    rows = {date.fromisoformat(r["date"]): r for p in pages for r in p["rows"]}
    ok, log, ntests = run_tests()
    data = {
        "pages": len(pages),
        "days": len(rows),
        "limb": limb_accuracy(rows),
        "sun": sun_accuracy(rows),
        "dinamana": dinamana_accuracy({d.isoformat(): r for d, r in rows.items()}),
        "components": components(),
        "apogee": apogee_fits(),
        "rahu": rahu_residuals(),
        "tables": table_comparison(),
        "timeline": page_timeline(pages),
        "tests_pass": ok,
        "test_count": ntests,
        "test_log": log.replace("<", "&lt;").replace(">", "&gt;"),
        "pdf_exists": PDF.is_file(),
        "json_exists": JSON_OUT.is_file(),
    }
    OUT.write_text(html_report(data), encoding="utf-8")
    print(OUT)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
