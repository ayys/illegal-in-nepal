"""Add Open Graph tags to built pages.

usage: tags.py ROOT URL_PREFIX [FILE ...]

Each FILE (default: every .html under ROOT) is served at
URL_PREFIX/<path relative to ROOT>. A page's own <meta name="description">
wins over text pulled from its body.
"""

import html
import re
import sys
import urllib.parse
from pathlib import Path

SITE = "https://illegal-in-nepal.org"
IMAGES = "https://dic.illegal-in-nepal.org"
MAX_DESCRIPTION = 200
BEGIN, END = "    <!-- og -->\n", "    <!-- /og -->\n"

BLOCK = re.compile(re.escape(BEGIN) + ".*?" + re.escape(END), re.S)
TAG = re.compile(r"<[^>]+>")
NOSCRIPT = re.compile(r"<noscript>.*?</noscript>", re.S)
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
DESCRIPTION = re.compile(r'<meta name="description" content="([^"]*)"')
DEFINITION = re.compile(r'<p class="main-definition">(.*?)</p>', re.S)
PARAGRAPH = re.compile(r"<p[^>]*>(.*?)</p>", re.S)


def text(fragment):
    return " ".join(html.unescape(TAG.sub("", fragment)).split())


def shorten(s):
    if len(s) <= MAX_DESCRIPTION:
        return s
    return s[:MAX_DESCRIPTION].rsplit(" ", 1)[0] + "…"


def describe(head, body):
    if found := DESCRIPTION.search(head) or DEFINITION.search(body):
        return text(found.group(1))
    for p in PARAGRAPH.finditer(body):
        if len(t := text(p.group(1))) >= 40:
            return t
    return ""


def tags(url_path, head, body):
    # Dictionary entries are titled by the bare word in their <h1>.
    title = (DEFINITION.search(body) and H1.search(body)) or TITLE.search(head)
    name = text(title.group(1)) if title else ""
    description = shorten(describe(head, body))
    page_url = url_path.removesuffix("index.html")
    image = url_path.removesuffix(".html") + ".png"
    meta = [
        ("property", "og:type", "website"),
        ("property", "og:site_name", "illegal-in-nepal.org"),
        ("property", "og:title", name),
        ("property", "og:description", description),
        ("property", "og:url", SITE + urllib.parse.quote(page_url)),
        ("property", "og:image", IMAGES + urllib.parse.quote(image)),
        ("property", "og:image:width", "1200"),
        ("property", "og:image:height", "630"),
        ("name", "twitter:card", "summary_large_image"),
    ]
    if not DESCRIPTION.search(head):
        meta.append(("name", "description", description))
    lines = (f'    <meta {k}="{v}" content="{html.escape(c)}">\n' for k, v, c in meta)
    return BEGIN + "".join(lines) + END


def add_tags(root, prefix, path):
    page = BLOCK.sub("", path.read_text(encoding="utf-8", errors="surrogateescape"))
    end = page.find("</head>")
    if end < 0:
        return
    end = page.rfind("\n", 0, end) + 1
    url_path = prefix.rstrip("/") + "/" + path.relative_to(root).as_posix()
    block = tags(url_path, page[:end], NOSCRIPT.sub("", page[end:]))
    path.write_text(page[:end] + block + page[end:], encoding="utf-8", errors="surrogateescape")


def main(argv):
    root, prefix, *files = argv
    root = Path(root)
    for path in map(Path, files) if files else root.rglob("*.html"):
        add_tags(root, prefix, path)


if __name__ == "__main__":
    main(sys.argv[1:])
