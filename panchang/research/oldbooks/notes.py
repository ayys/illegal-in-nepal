"""notes.py YEAR -> m{YEAR}-N.png: 1000x110 crops around every sankranti / sun-entry word"""
import csv, glob, os, re, subprocess, sys

KEY = re.compile(r"संक्रा|सङ्क्रा|संकरा|र्क|र्कः|र्क:")
SKIP = re.compile(r"संक्रामक|संक्रान्तौ|संक्रान्तिको|संक्रान्तिमा|सायना|दृश्या|दश्या|द्श्या|कर्को|अर्को")

year = sys.argv[1]
x0, x1 = (int(v) for v in sys.argv[2:4]) if len(sys.argv) > 3 else (None, None)
parts = []
for path in sorted(glob.glob(f"tsv/{year}-*.tsv")):
    p = os.path.basename(path)[len(year) + 1:-4]
    img = f"h{year}/{p}.jpg" if os.path.exists(f"h{year}/{p}.jpg") else f"r{year}/{p}.png"
    seen = []
    for r in csv.DictReader(open(path), delimiter="\t", quoting=csv.QUOTE_NONE):
        if r["level"] != "5" or not KEY.search(r["text"]) or SKIP.search(r["text"]):
            continue
        x, y = int(r["left"]), int(r["top"])
        if any(abs(y - sy) < 40 for sy in seen):
            continue
        seen.append(y)
        part = f"_n{len(parts)}.png"
        subprocess.run(["magick", img, "-crop", f"{x1 - x0}x130+{x0}+{max(0, y - 55)}" if x0 is not None else f"1000x100+{max(0, x - 550)}+{max(0, y - 40)}", "+repage",
                        "-bordercolor", "red", "-border", "2", part], check=True)
        parts.append(part)
        print(len(parts) - 1, p, x, y, r["text"])
for k in range(0, len(parts), 7):
    subprocess.run(["magick", *parts[k:k + 7], "-append", f"w{year}-{k // 7}.png"], check=True)
