"""rows.py OUT YEAR PAGE:TOP[:H[:LEFT]] ... -> stacked full-width row crops"""
import os, subprocess, sys

out, year, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
parts = []
for i, spec in enumerate(specs):
    page, top, *rest = spec.split(":")
    h = int(rest[0]) if rest else 110
    left = int(rest[1]) if len(rest) > 1 else 0
    img = f"h{year}/i-{int(page):03d}.jpg"
    if not os.path.exists(img):
        img = f"r{year}/p-{int(page):02d}.png"
    part = str(__import__("pathlib").Path(__file__).resolve().parent / f"_part{i}.png")
    subprocess.run(["magick", img, "-crop", f"{int(rest[2]) if len(rest) > 2 else 2000}x{h}+{left}+{max(0, int(top) - h // 2)}", "+repage",
                    "-bordercolor", "red", "-border", "2", part], check=True)
    parts.append(part)
subprocess.run(["magick", *parts, "-append", out], check=True)
