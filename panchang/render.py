"""Typeset fortnight pages in the layout of the committee's book."""

from __future__ import annotations

from datetime import date
from html import escape

import editorial
import panchanga

PAGE_WIDTH = 1007.01
PAGE_HEIGHT = 555.591
DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
RITU_WITH_SUFFIX = {
    "वसन्त": "वसन्तर्तुः", "ग्रीष्म": "ग्रीष्मर्तुः", "वर्षा": "वर्षर्तुः",
    "शरद्": "शरदृतुः", "हेमन्त": "हेमन्तर्तुः", "शिशिर": "शिशिरर्तुः",
}
PLANETS = ["सूर्य", "चन्द्र", "मंगल", "बुध", "बृहस्पति", "शुक्र", "शनि", "राहु"]
COMPUTED_PLANETS = {"सूर्य": "sun", "चन्द्र": "moon", "मंगल": "mars", "बुध": "mercury",
                    "बृहस्पति": "jupiter", "शुक्र": "venus", "शनि": "saturn", "राहु": "rahu"}
DAY_COLUMNS = [
    ("गते", 16), ("वा.", 12), ("ति.", 12), ("घ.प.", 22), ("बजे सम्म", 23),
    ("न.", 17), ("घ.प.", 21), ("बजे सम्म", 22), ("योग", 13), ("घ.प.", 22),
    ("बजे सम्म", 24), ("क.", 13), ("घ.प.", 23), ("बजे सम्म", 25), ("योगाः", 28),
    ("च.रा. (ब.सं.)", 23), ("दिमा.", 22), ("सू.उ.", 17), ("सू.अ.", 22), ("ता.", 13),
]

CSS = f"""
@page {{ size: {PAGE_WIDTH}pt {PAGE_HEIGHT}pt; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "Mukta", "Noto Sans Devanagari", "Kohinoor Devanagari", sans-serif;
        color: #000; font-weight: 600; }}
.page {{ position: relative; width: {PAGE_WIDTH}pt; height: {PAGE_HEIGHT}pt;
         page-break-after: always; overflow: hidden; }}
.bar {{ position: absolute; background: #000; color: #fff; border-radius: 6pt 6pt 0 0;
        font-weight: 700; white-space: nowrap; overflow: hidden; }}
.header {{ left: 22pt; top: 4pt; width: 982pt; height: 20pt; font-size: 11.4pt;
           line-height: 20pt; padding: 0 8pt; }}
table {{ border-collapse: collapse; position: absolute; table-layout: fixed; }}
td, th {{ border: 0.6pt solid #000; padding: 0 1pt; text-align: center; white-space: nowrap;
          overflow: hidden; line-height: 1; }}
th {{ font-weight: 700; }}
.days {{ left: 22pt; top: 27pt; width: 867pt; font-size: 8pt; }}
.days th {{ font-size: 7pt; line-height: 7.5pt; height: 16pt; }}
.days td {{ line-height: 14.2pt; height: 14.6pt; }}
.days td.note {{ text-align: left; font-size: 7.2pt; padding-left: 3pt; }}
.stack {{ font-size: 5.6pt; line-height: 6.6pt; display: block; }}
.side {{ position: absolute; left: 22pt; font-size: 6.4pt; font-weight: 700; }}
.rail {{ left: 892pt; top: 27pt; width: 112pt; height: 250pt; font-size: 7.4pt; }}
.rail-box {{ position: absolute; left: 892pt; top: 27pt; width: 112pt; height: 250pt;
             border: 0.6pt solid #000; font-size: 7.4pt; }}
.rail-box .title {{ background: #000; color: #fff; text-align: center; padding: 1pt; }}
.rail-box div.line {{ border-bottom: 0.4pt solid #000; padding: 1.2pt 3pt; white-space: normal; }}
.rail-box div.special {{ background: #ddd; }}
.rail-box div.pending {{ color: #666; font-weight: 500; padding: 3pt; white-space: normal; }}
.title-text {{ position: absolute; font-size: 13pt; font-weight: 700; }}
.lagna {{ left: 22pt; top: 300pt; width: 330pt; font-size: 7pt; }}
.lagna th {{ background: #000; color: #fff; line-height: 11pt; }}
.lagna td {{ line-height: 11.4pt; }}
.graha {{ left: 358pt; top: 300pt; width: 460pt; font-size: 7pt; }}
.graha th {{ background: #ddd; line-height: 11pt; }}
.graha td {{ line-height: 11.4pt; }}
.graha td.pending {{ color: #888; }}
.box {{ position: absolute; border: 0.8pt solid #000; border-radius: 4pt; font-size: 8pt;
        padding: 2pt 5pt; }}
.chip {{ position: absolute; right: 4pt; bottom: 6pt; background: #ddd; border-radius: 4pt;
         font-size: 9pt; font-weight: 700; padding: 1pt 8pt; }}
.imprint {{ position: absolute; left: 22pt; bottom: 6pt; font-size: 6.5pt; color: #555;
            font-weight: 500; }}
"""


def deva(value) -> str:
    return str(value).translate(DIGITS)


def clock(hm) -> str:
    return deva(f"{hm[0]}:{hm[1]}")


def ghati(ending) -> str:
    return deva(f"{ending['ghati']}।{ending['pala']}")


def arc(value) -> str:
    return deva(":".join(str(v) for v in value))


def belantar(seconds: int) -> str:
    sign = "+" if seconds >= 0 else "-"
    mins, secs = divmod(abs(seconds), 60)
    return f"{sign}{deva(mins)}:{deva(secs)}"


def stacked(values: list[str]) -> str:
    if len(values) == 1:
        return escape(values[0])
    return "".join(f'<span class="stack">{escape(v)}</span>' for v in values)


def limb_cells(limb: dict, label: str) -> str:
    ends = limb["ends"]
    if not ends:
        return f"<td>{escape(label)}</td><td>अहोरात्र</td><td>अहोरात्र</td>"
    return (
        f"<td>{escape(label)}</td>"
        f"<td>{stacked([ghati(e) for e in ends])}</td>"
        f"<td>{stacked([clock(e['clock']) for e in ends])}</td>"
    )


def header_line(header: dict) -> str:
    pairs = header["ayana_ritu"]
    if len({a for a, _ in pairs}) == 1:
        ritus = [r for _, r in pairs]
        season = f"{pairs[0][0]}ं " + " + ".join(ritus[:-1] + [RITU_WITH_SUFFIX[ritus[-1]]])
    else:
        parts = [f"{a} {r}" for a, r in pairs[:-1]]
        parts.append(f"{pairs[-1][0]} {RITU_WITH_SUFFIX[pairs[-1][1]]}")
        season = " + ".join(parts)
    pieces = [
        f"श्रीशाके {deva(header['shaka'])} वि.सं. {deva(header['vikram_samvat'])} "
        f"{header['lunar_month']}{header['paksha']}पक्षः",
        f"ने.सं. {deva(header['nepal_samvat'])} ({header['nepal_samvat_month']})",
        f"ई.सं. {deva(header['gregorian'])}",
        season,
    ]
    if header.get("samvatsara"):
        pieces.append(f"{header['samvatsara']}नामसंवत्सरः")
    if header.get("papakshani"):
        pieces.append(f"पापर्क्षाणि- {deva(header['papakshani'])}")
    return ", ".join(pieces)


def day_table(rows: list[dict], notes: dict) -> str:
    head = "".join(
        f'<th style="width:{width}pt">{escape(name)}</th>' for name, width in DAY_COLUMNS)
    head += "<th>व्रतपर्व विवरण एवं मुद्रा (प्रामाणिक समयमा)</th>"
    body = []
    for row in rows:
        tithi = row["tithi"]
        karana = row["karana"]
        moon_sign = row["moon_sign"]
        sign_cell = (
            clock(moon_sign["ends"][0]["clock"]) if moon_sign["ends"] else moon_sign["name"])
        karana_cells = (
            limb_cells(karana, karana["abbr"]) if karana["ends"]
            else "<td></td><td>अहोरात्र</td><td>अहोरात्र</td>")
        dinamana = deva(f"{row['dinamana'][0]}।{row['dinamana'][1]}")
        body.append(
            "<tr>"
            f"<td>{deva(row['gate'])}</td><td>{row['weekday']}</td>"
            + limb_cells(tithi, deva(tithi["number"]))
            + limb_cells(row["nakshatra"], row["nakshatra"]["abbr"])
            + limb_cells(row["yoga"], row["yoga"]["abbr"])
            + karana_cells
            + f"<td>{row['anandadi']}</td><td>{sign_cell}</td><td>{dinamana}</td>"
            f"<td>{clock(row['sunrise_clock'])}</td><td>{clock(row['sunset_clock'])}</td>"
            f"<td>{deva(date.fromisoformat(row['date']).day)}</td>"
            f'<td class="note">{escape(notes.get(row["date"], ""))}</td>'
            "</tr>"
        )
    return f'<table class="days"><tr>{head}</tr>{"".join(body)}</table>'


STATION_NAMES = {"mars": "मङ्गल", "mercury": "बुध", "jupiter": "गुरु", "venus": "शुक्र", "saturn": "शनि"}
RAIL_NAMES = {"mars": "मंगल", "mercury": "बुध", "jupiter": "गुरु", "venus": "शुक्र", "saturn": "शनि"}
SHORT_NAMES = {"sun": "सू", "mars": "मं", "mercury": "बु", "jupiter": "बृ", "venus": "शु", "saturn": "श", "rahu": "रा"}


def rail_text(gate: int, entry: dict) -> str:
    """One ग्रहचार line, worded as the book words it (2083 pp2-21)."""
    again = "पुनः" if entry.get("again") else ""
    enters = entry.get("enters")
    if entry["body"] in ("mercury", "venus"):
        if entry.get("abhijit") == "out":
            where = "अभिजितत्याग"
        elif entry.get("abhijit") == "in":
            where = "अभिजितमा"
        elif entry.get("nakshatra") and enters:
            where = f"{again}{entry['nakshatra']} {enters}मा"
        elif entry.get("nakshatra"):
            where = f"{again}{entry['nakshatra']}मा"
        else:
            where = f"{again}{enters}मा"
        return f"{deva(gate)} {where} {RAIL_NAMES[entry['body']]} {clock(entry['clock'])}"
    where = f"{again}{entry['nakshatra']} {deva(entry['pada'])} {enters + 'मा' if enters else 'मा'}"
    if entry["body"] == "rahu":
        ketu = entry["ketu"]
        ketu_where = f"{ketu['enters']}मा" if ketu.get("enters") else "मा"
        return (f"{deva(gate)} {where} राहु {ketu['nakshatra']} {deva(ketu['pada'])} {ketu_where} केतु "
                f"{clock(entry['clock'])}")
    return f"{deva(gate)} {where} {RAIL_NAMES[entry['body']]} {clock(entry['clock'])}"


def rail(rows: list[dict]) -> str:
    lines = []
    for row in rows:
        for entry in row["sun_padas"]:
            if entry.get("leaves"):
                lines.append(f'<div class="line">{deva(row["gate"])} अभिजितत्याग सूर्य '
                             f'{clock(entry["clock"])}</div>')
                continue
            enters = entry.get("enters")
            where = f"{enters}मा" if enters else "मा"
            lines.append(
                f'<div class="line">{deva(row["gate"])} {entry["nakshatra"]} '
                f'{deva(entry["pada"])} {where} सूर्य {clock(entry["clock"])}</div>')
    planets = sorted(((panchanga.RAIL_ORDER.index(e["body"]), e["at"], row["gate"], e)
                      for row in rows for e in row["planet_events"] if "station" not in e), key=lambda x: x[:2])
    lines += [f'<div class="line">{rail_text(gate, e)}</div>' for _, _, gate, e in planets]
    # वक्री/मार्गी, shaded at the foot as in the book (2083 p18 "२० मार्गी शनि ६:४३").
    stations = sorted(((e["at"], row["gate"], e) for row in rows for e in row["planet_events"] if "station" in e),
                      key=lambda x: x[0])
    lines += [f'<div class="line special">{deva(gate)} {e["station"]} {STATION_NAMES[e["body"]]} '
              f'{clock(e["clock"])}</div>' for _, gate, e in stations]
    lines.append('<div class="pending">उदयास्त: गणना बाँकी</div>')
    return (
        '<div class="rail-box"><div class="title">गते ग्रहचार/उदयास्त (बजे)</div>'
        + "".join(lines) + "</div>")


def lagna_table(rows: list[dict]) -> str:
    groups: list[list[dict]] = []
    for row in rows:
        if groups and groups[-1][0]["sun_sign"] == row["sun_sign"]:
            groups[-1].append(row)
        else:
            groups.append([row])
    html = []
    for group in groups:
        first = group[0]["sun_sign"]
        order = [(first + k) % 12 for k in range(12)]
        html.append(
            "<tr><th>गते</th><th>वार</th>"
            + "".join(f"<th>{panchanga.SIGNS[s]}</th>" for s in order) + "</tr>")
        for row in group:
            starts = {l["sign"]: l["clock"] for l in row["lagna"]}
            html.append(
                f"<tr><td>{deva(row['gate'])}</td><td>{row['weekday']}</td>"
                + "".join(f"<td>{clock(starts[s])}</td>" for s in order) + "</tr>")
    return f'<table class="lagna">{"".join(html)}</table>'


def graha_table(rows: list[dict]) -> str:
    head = "".join(f"<th>{p}</th>" for p in PLANETS) + "<th>बेलान्तर</th><th>गते</th>"
    body = []
    for row in rows:
        cells = []
        for planet in PLANETS:
            key = COMPUTED_PLANETS.get(planet)
            if key:
                cells.append(f"<td>{arc(row['spashta'][key])}</td>")
            else:
                cells.append('<td class="pending">—</td>')
        body.append(
            "<tr>" + "".join(cells)
            + f"<td>{belantar(row['belantar'])}</td><td>{deva(row['gate'])}</td></tr>")
    return f'<table class="graha"><tr>{head}</tr>{"".join(body)}</table>'


def rashi_pravesh(entries: list[dict]) -> str:
    """"१सू.२, २८मं.१": गते, planet, sign entered (मेष = 1)."""
    out = []
    for e in entries:
        text = f"{deva(e['gate'])}{SHORT_NAMES[e['body']]}.{deva(e['sign'] + 1)}"
        if e["body"] == "rahu":
            text += f"के.{deva(e['ketu_sign'] + 1)}"
        out.append(text)
    return ", ".join(out)


def page_html(page: dict, notes: dict | None = None, papamsha: str = "") -> str:
    rows = page["rows"]
    notes = notes or {}
    entries = rashi_pravesh(page["header"]["sign_entries"])
    pravesh = (
        f'<div class="box" style="left:690pt;top:280pt">राशि प्रवेश: {entries}</div>'
        if entries else "")
    return (
        '<section class="page">'
        f'<div class="bar header">{escape(header_line(page["header"]))}</div>'
        + day_table(rows, notes)
        + rail(rows)
        + '<div class="title-text" style="left:60pt;top:281pt">'
          'दैनिक लग्न आरम्भ समयतालिका, घ.मि. (बजे) मा</div>'
        + lagna_table(rows)
        + '<div class="title-text" style="left:420pt;top:281pt">उदयकालिक सूर्यादि स्पष्ट ग्रह</div>'
        + pravesh
        + graha_table(rows)
        + '<div class="box" style="left:892pt;top:300pt;width:112pt;height:90pt">'
          '<b>कुण्डली</b><br>गणना बाँकी</div>'
        + f'<div class="box" style="left:892pt;top:396pt;width:112pt;height:120pt">'
          f'<b>पापांशाः</b><br>{escape(papamsha)}</div>'
        + '<div class="imprint">सूर्यसिद्धान्तबाट स्वचालित गणना — आधिकारिक प्रति होइन</div>'
        + f'<div class="chip">राष्ट्रिय-पञ्चाङ्गम् - {deva(page["page"])}</div>'
        + "</section>"
    )


def document(pages: list[dict], config: dict | None = None) -> str:
    config = config or {}
    notes = config.get("notes", {})
    papamsha = config.get("papamsha", {})
    body = "".join(
        page_html(p, notes, papamsha.get(str(p["page"]))
                  or editorial.papamsha_text(p["header"]["papamsha"]))
        for p in pages)
    return (
        '<!doctype html><html lang="ne"><head><meta charset="utf-8">'
        f"<style>{CSS}</style></head><body>{body}</body></html>")


def write_pdf(pages: list[dict], path: str, config: dict | None = None) -> None:
    from weasyprint import HTML

    HTML(string=document(pages, config)).write_pdf(path)
