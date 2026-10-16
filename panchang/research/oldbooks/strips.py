import csv, glob, os, re, subprocess, sys

KEY = re.compile(r"संक्रा|संक्रान्त|ऽर्क|र्क[:ः]")
SKIP = re.compile(r"संक्रामक|रोगे|व्यतीपाते|व्यतिपाते|संक्रान्तौ|संक्रान्तिको|संकान्ब्या|दिने|दिन,")

for path in sorted(glob.glob("tsv/*.tsv")):
    b = os.path.basename(path)[:-4]
    y, p = b.split("-", 1)
    img = f"h{y}/{p}.jpg"
    if not os.path.exists(img):
        img = f"r{y}/{p}.png"
    lines = {}
    with open(path) as f:
        for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if r["level"] != "5":
                continue
            k = (r["block_num"], r["par_num"], r["line_num"])
            lines.setdefault(k, []).append(r)
    n = 0
    for k, words in lines.items():
        text = " ".join(w["text"] for w in words)
        if not KEY.search(text) or SKIP.search(text):
            continue
        top = min(int(w["top"]) for w in words)
        bot = max(int(w["top"]) + int(w["height"]) for w in words)
        h = min(bot - top, 60)
        mid = (top + bot) // 2
        left = min(int(w["left"]) for w in words)
        right = max(int(w["left"]) + int(w["width"]) for w in words)
        out = f"strips/{y}-{p}-{n}.png"
        subprocess.run(["magick", img, "-crop", f"{right - left + 80}x{70}+{max(0, left - 40)}+{max(0, mid - 35)}",
                        "+repage", "-bordercolor", "red", "-border", "3", out], check=True)
        print(out, text)
        n += 1
