"""The typeset text (render.py) against the 2083 and 2082 books as printed.

Every string here is transcribed from the page, not from our output:
  2083  https://giwmscdnone.gov.np/media/pages/files/FORMAT-2083-A_7f75xmb.pdf
  2082  https://giwmscdnone.gov.np/media/pages/files/npnbs_2082_ussfian.pdf
(PDF page = book page.)
"""

import re
import unittest

import panchanga
import render

DIGITS = "०१२३४५६७८९"

# Header strips as printed, up to पापर्क्षाणि (tested in test_editorial).
HEADERS = {
    (2083, 2): "श्रीशाके १९४८ वि.सं. २०८३ वैशाखकृष्णपक्षः ने.सं. ११४६ (चौलागा), ई.सं. अप्रिल २०२६, "
               "उत्तरायणं वसन्तर्तुः, रौद्रनामसंवत्सरः,",
    (2083, 3): "श्रीशाके १९४८ वि.सं. २०८३ वैशाखशुक्लपक्षः ने.सं. ११४६ (वछलाथ्व), ई.सं. अप्रिल + मे २०२६, "
               "उत्तरायणं वसन्तर्तुः, रौद्रनामसंवत्सरः,",
    (2083, 9): "श्रीशाके १९४८ वि.सं. २०८३ आषाढशुक्लपक्षः ने.सं. ११४६ (दिल्लाथ्व), ई.सं. जुलाई २०२६, "
               "उत्तरायणं ग्रीष्मः+ दक्षिणायनं वर्षर्तुः, रौद्रनामसंवत्सरः,",
    (2083, 11): "श्रीशाके १९४८ वि.सं. २०८३ श्रावणशुक्लपक्षः ने.सं. ११४६ (गुंलाथ्व), ई.सं. अगस्त २०२६, "
                "दक्षिणायनं वर्षर्तुः, रौद्रनामसंवत्सरः,",
    (2083, 14): "श्रीशाके १९४८ वि.सं. २०८३ आश्विनकृष्ण (पितृ) पक्षः ने.सं. ११४६ (ञँलागा), "
                "ई.सं. सेप्टेम्बर + अक्टोबर २०२६, दक्षिणायनं शरदृतुः, रौद्रनामसंवत्सरः,",
    (2083, 15): "श्रीशाके १९४८ वि.सं. २०८३ आश्विनशुक्ल (दुर्गा) पक्षः ने.सं. ११४६ (कौलाथ्व), "
                "ई.सं. अक्टोबर २०२६, दक्षिणायनं शरदृतुः, रौद्रनामसंवत्सरः,",
    (2083, 16): "श्रीशाके १९४८ वि.सं. २०८३ कार्तिककृष्णपक्षः ने.सं. ११४६ (कौलागा), "
                "ई.सं. अक्टोबर + नोभेम्बर २०२६, दक्षिणायनं शरदृतुः रौद्रनामसंवत्सरः",
    (2083, 17): "श्रीशाके १९४८ वि.सं. २०८३ कार्तिकशुक्लपक्षः ने.सं. ११४७ (कछलाथ्व), ई.सं. नोभेम्बर २०२६, "
                "दक्षिणायनं शरद + हेमन्तर्तुः, रौद्रनामसंवत्सरः,",
    (2083, 21): "श्रीशाके १९४८ वि.सं. २०८३ पौषशुक्लपक्षः ने.सं. ११४७ (पोहेलाथ्व), ई.सं. जनवरी २०२७, "
                "दक्षिणायनं हेमन्त + उत्तरायणं शिशिरर्तुः, रौद्रनामसंवत्सरः,",
    (2083, 26): "श्रीशाके १९४८ वि.सं. २०८३ चैत्रकृष्णपक्षः ने.सं. ११४७ (चिल्लागा), ई.सं. मार्च + अप्रिल २०२७, "
                "उत्तरायणं वसन्तर्तुः, रौद्रनामसंवत्सरः,",
    (2082, 8): "श्रीशाके १९४७ वि.सं. २०८२ श्रावणकृष्णपक्षः ने.सं. ११४५ (दिल्लागा), ई.सं. जुलाई २०२५, "
               "उत्तरायणं ग्रीष्मः + दक्षिणायनं वर्षर्तुः, सिद्धार्थिनामसंवत्सरः,",
    (2082, 12): "श्रीशाके १९४७ वि.सं. २०८२ आश्विनकृष्ण (पितृ) पक्षः ने.सं. ११४५ (ञँलागा), ई.सं. सेप्टेम्बर २०२५, "
                "दक्षिणायनं वर्षा + शरदृतुः, सिद्धार्थिनामसंवत्सरः,",
}
# The print is not consistent with itself, so the comparison ignores spaces,
# the commas on NO_COMMAS pages (2083 p16 has none before the samvatsara),
# and these variants:
# थ्व and थ्वः (pp3, 9, 17, 21 against pp5, 7), and a bare first ritu before
# "+" (p17 "शरद +", p21 "हेमन्त +", against p9 and 2082 p8 "ग्रीष्मः +").
VARIANTS = [("थ्वः", "थ्व"), ("शरद्+", "शरद+"), ("हेमन्तः+", "हेमन्त+")]
NO_COMMAS = {(2083, 16)}


def normal(text: str, commas: bool = True) -> str:
    text = re.sub(r"\s" if commas else r"[\s,]", "", text.split("पापर्क्षाणि")[0])
    for a, b in VARIANTS:
        text = text.replace(a, b)
    return text


# Day rows as printed, cell by cell: गते, वार, तिथि, घ.प., बजे, नक्षत्र, घ.प.,
# बजे, योग, घ.प., बजे, करण, घ.प., बजे, आनन्दादि, चन्द्रराशि, दिनमान, सूर्योदय,
# सूर्यास्त, date. Stacked cells are space-separated.
ROWS = {
    2: [
        "१|मं.|१२|३९।३३|२१:३२|श.|१९।४३|१३:३६|शु.|१९।२७|१३:२९|कौ.|१०।१२|९:४८|मृत्यु|कुम्भ|३१।५२|५:४३|१८:२७|१४",
        "२|बु.|१३|३७।२५|२०:४०|पू.भा.|१९।४१|१३:३४|ब्र.|१५।२१|११:५०|ग.|८।३९|९:९|पद्म|७:३७|३१।५६|५:४२|१८:२८|१५",
        "३|बि.|१४|३४।१३|१९:२२|उ.भा.|१८।३३|१३:६|ऐ.|१०।२३|९:५०|भ.|५।५८|८:४|छत्र|मीन|३१।५९|५:४१|१८:२८|१६",
        "४|शु.|३०|३०।५|१७:४२|रे.|१६।२८|१२:१५|वै.|४।३७ ५८।८|७:३० २८:५५|च.|२।१६ ५७।४२|६:३४ २८:४५|श्रीवत्स|१२:१५|३२।३|५:४०|१८:२९|१७",
    ],
    21: [
        "२४|शु.|१|५१।२३|२७:३१|पू.षा.|५।३१|९:१०|व्या.|२२।०|१५:४५|किं.|१८।४२|१४:२७|प्रवर्द्ध|१५:४९|२६।४|६:५८|१७:२३|८",
        "२५|श.|२|५६।२१|२९:३०|उ.षा.|११।५६|११:४४|ह.|२३।८|१६:१३|बा.|२३।५६|१६:३२|चर|मकर|२६।६|६:५८|१७:२४|९",
        "२६|आ.|३|अहोरात्र|अहोरात्र|श्र.|१७।४८|१४:५|व.|२३।४८|१६:२९|तै.|२८।३२|१८:२३|गद|२७:८|२६।७|६:५८|१७:२५|१०",
        "२७|सो.|३|०।३१|७:१०|ध.|२२।५०|१६:६|सि.|२३।४८|१६:२९|व.|३२।१३|१९:५१|शुभ|कुम्भ|२६।९|६:५८|१७:२६|११",
        "२८|मं.|४|३।३८|८:२५|श.|२६।४७|१७:४१|व्य.|२२।५६|१६:८|ब.|३४।४४|२०:५२|मृत्यु|कुम्भ|२६।११|६:५८|१७:२६|१२",
        "२९|बु.|५|५।३१|९:१०|पू.भा.|२९।३२|१८:४७|व.|२१।८|१५:२५|कौ.|३५।५९|२१:२१|पद्म|१२:३३|२६।१३|६:५८|१७:२७|१३",
        "३०|बि.|६|६।७|९:२५|उ.भा.|३१।१|१९:२२|प.|१८।१९|१४:१८|ग.|३५।५६|२१:२०|छत्र|मीन|२६।१५|६:५८|१७:२८|१४",
        "१|शु.|७|५।२६|९:८|रे.|३१।१८|१९:२९|शि.|१४।३२|१२:४७|भ.|३४।३७|२०:४९|श्रीवत्स|१९:२९|२६।१८|६:५८|१७:२९|१५",
        "२|श.|८|३।३२|८:२३|अश्वि.|३०।२७|१९:९|सि.|९।५०|१०:५४|बा.|३२।१०|१९:५०|सौम्य|मेष|२६।२०|६:५८|१७:३०|१६",
        "३|आ.|९|०।३३ ५६।२६|७:११ २९:३६|भ.|२८।३६|१८:२४|सा.|४।१७ ५७।५८|८:४० ३०:९|तै.|२८।४१|१८:२६|काल|२४:१०|२६।२२|६:५८|१७:३०|१७",
        "४|सो.|११|५१।५६|२७:४४|कृ.|२५।५५|१७:२०|शु.|५१।६|२७:२४|व.|२४।२२|१६:४२|स्थिर|वृष|२६।२५|६:५७|१७:३१|१८",
        "५|मं.|१२|४६।३९|२५:३७|रो.|२२।३५|१५:५९|ब्र.|४३।४५|२४:२७|ब.|१९।२१|१४:४२|मातङ्ग|२७:१४|२६।२७|६:५७|१७:३२|१९",
        "६|बु.|१३|४०।५८|२३:२०|मृ.|१८।४५|१४:२७|ऐ.|३६।४|२१:२३|कौ.|१३।५१|१२:३०|अमृत|मिथुन|२६।३०|६:५७|१७:३३|२०",
        "७|बि.|१४|३५।५|२०:५९|आ.|१४।३९|१२:४९|वै.|२८।१२|१८:१४|ग.|८।३|१०:१०|काण|२९:३३|२६।३२|६:५७|१७:३४|२१",
        "८|शु.|१५|२९।१३|१८:३८|पुन.|१०।२९|११:८|वि.|२०।१९|१५:४|भ.|२।८ ५६।२०|७:४८ २९:२९|लुम्ब|कर्कट|२६।३५|६:५७|१७:३५|२२",
    ],
}
# Rows from other pages, by (page, row): the two पुष्य ("ति.") rows the
# pages above lack.
OTHER_ROWS = {
    (3, 6): "११|शु.|८|४५।४९|२३:५३|ति.|४७।४०|२४:३७|धृ.|६।३१ ६०।०|८:९|भ.|१८।८|१२:४८|उत्पात|कर्कट|३२।३०|५:३३|१८:३३|२४",
    (22, 0): "९|श.|१|२३।३४|१६:२२|ति.|६।२८|९:३१|प्री.|१२।३६|११:५९|तै.|५०।५३|२७:१८|मित्र|कर्कट|२६।३८|६:५६|१७:३५|२३",
}
# Cells we print apart from the book, by (page, row, column), with the gap
# in pala or minutes: ghati ends at a rounding edge of surya.ghati_origin
# (p21 row 9's yoga is ours 57।59.5), and two sunrises the book rounds down
# (test_panchanga.SUN). MISPRINTS are not compared.
APART = {(2, 2, 3): 1, (2, 2, 12): 1, (21, 0, 9): 1, (21, 1, 12): 1, (21, 2, 12): 1, (21, 9, 9): 2,
         (21, 10, 17): 1, (21, 11, 17): 1, (21, 14, 12): 1, (3, 6, 17): 1, (22, 0, 6): 1, (22, 0, 17): 1}
MISPRINTS = {(21, 9, 3): "५६।२६ beside its own clock २९:३६ (५६।३५ after sunrise)",
             (3, 6, 9): "the book files the next yoga end, 1.6 min after our next sunrise, here as ६०।०"}

# The rail's special lines as printed.
# Up to the clock; the उदय/अस्त whose day we miss (test_rail.HELIACAL_OPEN)
# are left out.
SPECIAL_LINES = {
    3: ["१८ बुध पूर्वमा अस्त"],
    9: ["९ मार्गी बुध"],
    16: ["१३ बुध पश्चिममा अस्त"],
    21: ["१ वक्री मङ्गल"],
    22: ["११ अभिजितत्याग सूर्य १९:१२"],
    25: ["७ शनि पश्चिममा अस्त"],
}
# 2083 p20's kundali as printed: house (1 = top centre, anticlockwise), its
# sign number and the planets in it.
KUNDALI_P20 = {1: ("९", "सू. बु."), 2: ("१०", "रा."), 4: ("१२", "श."), 8: ("४", "के."),
               9: ("५", "मं. बृ."), 11: ("७", "शु.")}


def cells(row_html: str) -> list[str]:
    out = []
    for td in re.findall(r"<td[^>]*>(.*?)</td>", row_html):
        spans = re.findall(r'<span class="stack">(.*?)</span>', td)
        out.append(" ".join(spans) if spans else re.sub(r"<[^>]+>", "", td))
    return out


def numbers(text: str) -> list[int]:
    return [int("".join(str(DIGITS.index(c)) for c in n)) for n in re.findall(f"[{DIGITS}]+", text)]


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.years = {y: {p["page"]: p for p in panchanga.year(y)} for y in (2082, 2083)}
        cls.pages = cls.years[2083]

    def test_headers(self):
        for (year, page), printed in HEADERS.items():
            with self.subTest(year=year, page=page):
                commas = (year, page) not in NO_COMMAS
                ours = render.header_line(self.years[year][page]["header"])
                self.assertEqual(normal(ours, commas), normal(printed, commas))

    def test_day_rows(self):
        checks = []
        for page in {p for p, _ in OTHER_ROWS} | set(ROWS):
            ours = [cells(r) for r in re.findall(r"<tr>(.*?)</tr>", render.day_table(self.pages[page]["rows"], {}))[1:]]
            if page in ROWS:
                self.assertEqual(len(ours), len(ROWS[page]))
                checks += [(page, i, ours[i], line) for i, line in enumerate(ROWS[page])]
            checks += [(page, i, ours[i], line) for (p, i), line in OTHER_ROWS.items() if p == page]
        for page, i, got, line in checks:
            for j, cell in enumerate(line.split("|")):
                with self.subTest(page=page, row=i, column=j, printed=cell):
                    if (page, i, j) in MISPRINTS:
                        continue
                    if (page, i, j) in APART:
                        a, b = numbers(got[j]), numbers(cell)
                        self.assertEqual(len(a), len(b))
                        self.assertNotEqual(got[j], cell)
                        # घटी।पला or h:m pairs, compared in the smaller unit.
                        gaps = [abs((a[k] * 60 + a[k + 1]) - (b[k] * 60 + b[k + 1])) for k in range(0, len(a), 2)]
                        self.assertEqual(max(gaps), APART[page, i, j], f"{got[j]} vs {cell}")
                    else:
                        self.assertEqual(got[j], cell)

    def test_graha_row(self):
        # 2083 p21, पौष २४ (Jan 8, 2027): Mars to Saturn as printed.
        html = render.graha_table(self.pages[21]["rows"])
        first = cells(re.findall(r"<tr>(.*?)</tr>", html)[1])
        self.assertEqual(first[2:7], ["४:१६:२६:४१", "८:२७:१४:४७", "४:१:५९:२७", "७:७:९:३५", "११:१४:१६:५०"])
        self.assertEqual(first[-1], "२४")

    def test_belantar_text(self):
        # As printed in the स्पष्ट ग्रह tables (test_panchanga.SPASHTA_2082).
        self.assertEqual(render.belantar(-92), "-१:३२")
        self.assertEqual(render.belantar(404), "+६:४४")
        self.assertEqual(render.belantar(0), "+०:०")

    def test_special_rail_lines(self):
        for page, printed in SPECIAL_LINES.items():
            text = re.sub(r"<[^>]+>", "\n", render.rail(self.pages[page]["rows"]))
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in printed:
                with self.subTest(page=page, line=line):
                    self.assertTrue(any(l.startswith(line) for l in lines), lines)

    def test_kundali_houses(self):
        html = render.kundali_svg(self.pages[20]["header"]["kundali"])
        houses = re.findall(r'<div class="house" style="left:([\d.]+)pt;top:([\d.]+)pt">(.*?)</div>', html)
        self.assertEqual(len(houses), 12)
        for house, (sign, planets) in KUNDALI_P20.items():
            fx, fy = render.HOUSES[house - 1]
            text = next(t for x, y, t in houses if abs(float(x) - fx * 108) < 0.1 and abs(float(y) - fy * 84) < 0.1)
            with self.subTest(house=house):
                self.assertIn(planets, text)
                self.assertTrue(text.endswith(sign), text)

    def test_rashi_pravesh_with_ketu(self):
        # 2083 p18 prints "१९रा.१०के.४" (its Mercury entry is a day off; test_rail).
        self.assertIn("१९रा.१०के.४", render.rashi_pravesh(self.pages[18]["header"]["sign_entries"]))


if __name__ == "__main__":
    unittest.main()
