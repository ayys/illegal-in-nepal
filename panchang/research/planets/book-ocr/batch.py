import sys, json, subprocess, os
from cells import page
book, pdf, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
out = {}
for p in range(first, last + 1):
    png = f"{book}-{p:02d}.png"
    if not os.path.exists(png):
        subprocess.run(["pdftoppm", "-r", "400", "-f", str(p), "-l", str(p), "-png", "-singlefile", pdf, png[:-4]], check=True)
    try:
        out[p] = page(png)
    except Exception as e:
        out[p] = f"error {e}"
    print(p, flush=True)
    json.dump(out, open(f"ocr-{book}.json", "w"), ensure_ascii=False, indent=0)
