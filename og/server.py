"""Render link-preview (Open Graph) images for illegal-in-nepal.org pages.

GET /<path>.png fetches SITE/<path>.html, reads its og:title and
og:description, and draws them onto a 1200×630 card. Cards are cached on
disk by path; clear CACHE_DIRECTORY to redraw them.
"""

import hashlib
import io
import os
import re
import threading
import urllib.error
import urllib.request
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SITE = os.environ.get("OG_SITE", "https://illegal-in-nepal.org")
CACHE = Path(os.environ.get("CACHE_DIRECTORY", "/tmp/og-cache"))
FONTS = Path(__file__).with_name("fonts")
PORT = int(os.environ.get("OG_PORT", "8090"))

WIDTH, HEIGHT, MARGIN = 1200, 630, 80
BG, INK, MUTE, ACCENT = "#fff1dc", "#2c1810", "#8a6456", "#b03a22"
SECTIONS = {"shabdakosh": "शब्दकोश", "blog": "ब्लग"}
PATH = re.compile(r"^/[^?#]*\.png$")
EMOJI = re.compile("[\u2600-\u27bf\ufe0f\U0001f000-\U0001faff]")


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size, layout_engine=ImageFont.Layout.RAQM)


SERIF = "TiroDevanagariHindi-Regular.ttf"
HAND = "Kalam-Bold.ttf"


class Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta, self.title, self._in_title = {}, "", False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property", "").startswith("og:"):
            self.meta[attrs["property"]] = attrs.get("content", "")
        self._in_title = tag == "title"

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        self._in_title = False


def page_meta(path):
    url = SITE + path[: -len(".png")] + ".html"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "og-image"}), timeout=10) as r:
        parser = Meta()
        parser.feed(r.read().decode("utf-8", "replace"))
    title = parser.meta.get("og:title") or parser.title.strip()
    # The card fonts have no emoji.
    clean = lambda s: re.sub(r" ([,.;:!?।])", r"\1", " ".join(EMOJI.sub("", s).split()))
    return clean(title), clean(parser.meta.get("og:description", "")), "og:title" in parser.meta


def wrap(draw, text, face, width, max_lines):
    lines = []
    for word in text.split():
        if lines and draw.textlength(f"{lines[-1]} {word}", font=face) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + "…", font=face) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "…"
    return lines


def render(path, title, description):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    width = WIDTH - 2 * MARGIN
    draw.rectangle([0, 0, WIDTH, 14], fill=ACCENT)

    size = 120
    while size > 56 and draw.textlength(title, font=font(SERIF, size)) > width:
        size -= 4
    title_face = font(SERIF, size)
    title_lines = wrap(draw, title, title_face, width, 2)
    y = MARGIN
    for line in title_lines:
        draw.text((MARGIN, y), line, font=title_face, fill=INK)
        y += int(size * 1.3)

    body = font(SERIF, 44)
    y += 20
    for line in wrap(draw, description, body, width, max((HEIGHT - 140 - y) // 62, 0)):
        draw.text((MARGIN, y), line, font=body, fill=INK)
        y += 62

    section = SECTIONS.get(path.strip("/").split("/")[0], "")
    footer = "illegal-in-nepal.org" + (f"  ·  {section}" if section else "")
    draw.line([MARGIN, HEIGHT - 120, WIDTH - MARGIN, HEIGHT - 120], fill=MUTE, width=2)
    draw.text((MARGIN, HEIGHT - 100), footer, font=font(HAND, 40), fill=ACCENT)

    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not PATH.match(self.path) or ".." in self.path:
            return self.send_error(404)
        # Images are kept until the cache directory is cleared.
        cached = CACHE / (hashlib.sha256(self.path.encode()).hexdigest() + ".png")
        keep = True
        if cached.exists():
            png = cached.read_bytes()
        else:
            try:
                title, description, tagged = page_meta(self.path)
            except urllib.error.HTTPError as e:
                return self.send_error(404 if e.code == 404 else 502)
            except (urllib.error.URLError, TimeoutError):
                return self.send_error(502)
            png = render(self.path, title, description)
            # Untagged pages are drawn from <title> alone; don't keep those.
            keep = tagged
            if keep:
                CACHE.mkdir(parents=True, exist_ok=True)
                partial = cached.with_suffix(f".{os.getpid()}.{threading.get_ident()}")
                partial.write_bytes(png)
                partial.replace(cached)

        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(png)))
        self.send_header("Cache-Control", "public, max-age=604800" if keep else "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(png)

    do_HEAD = do_GET


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
