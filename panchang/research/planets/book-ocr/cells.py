"""Cut the स्पष्ट ग्रह table of one rendered page into cells and OCR each."""
import sys, subprocess, tempfile, os, json, numpy as np
from PIL import Image
DIG = "०१२३४५६७८९"
def groups(ix, gap=3):
    out = []
    for i in ix:
        if out and i - out[-1][-1] <= gap: out[-1].append(i)
        else: out.append([i])
    return [(g[0], g[-1]) for g in out]
def ocr(img):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
    r = subprocess.run(["tesseract", f.name, "-", "-l", "hin", "--psm", "7",
                        "-c", f"tessedit_char_whitelist={DIG}:+-"], capture_output=True, text=True)
    os.unlink(f.name)
    return r.stdout.strip().translate(str.maketrans(DIG, "0123456789"))
def page(path):
    g = Image.open(path).convert("L"); im = np.array(g) < 128; H, W = im.shape
    y0, y1, x0, x1 = int(H*0.565), int(H*0.99), int(W*0.42), int(W*0.87)
    sub = im[y0:y1, x0:x1]
    cl = [(a+x0, b+x0) for a, b in groups(np.where(sub.mean(axis=0) > 0.5)[0])]
    # rows: horizontal lines across the planet columns only
    left, right = cl[0][1], cl[-3][0]
    band = im[y0:y1, left:right]
    rl = [(a+y0, b+y0) for a, b in groups(np.where(band.mean(axis=1) > 0.5)[0])]
    out = []
    for (ra, rb), (rc, rd) in zip(rl, rl[1:]):
        if rc - rb < 30: continue
        cells = []
        for (ca, cb), (cc, cd) in zip(cl, cl[1:]):
            crop = g.crop((cb+3, rb+3, cc-2, rc-2))
            crop = crop.resize((crop.width*2, crop.height*2))
            cells.append(ocr(crop))
        out.append(cells)
    return out
if __name__ == "__main__":
    for row in page(sys.argv[1]): print(row)
