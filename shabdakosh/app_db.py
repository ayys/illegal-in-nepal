#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "aiofiles",
#   "tqdm",
# ]
# ///
"""The iOS app's offline dictionary (ios/): one SQLite file holding what the
site's pages, search data, word-of-the-day list and crossword lexicon hold,
made by the same code (generator.py, wotd_lib.py, crossword_lib.py) so the app
agrees with the site.

  app_db.py full <version> <out.sqlite>          the whole dictionary
  app_db.py update <old.sqlite> <new.sqlite> <out.sqlite>
                                                 what changed from old to new

The app ships with a full dictionary and applies updates on top of it, one
release after another; .github/workflows/dictionary.yml publishes both.

Tables, SCHEMA 2 (the app refuses other schemas):
  meta(key, value)        schema, version, entries; in an update also base
                          (the version it applies to) and, for each list
                          (search, wotd, crossword), "from:to" if the update's
                          rows of it replace the old rows with ids from..to-1,
                          "" if unchanged
  entries(slug, word, grammar, preview, body)
                          one per page. grammar and preview are the search
                          data's; body is JSON [[grammar, [sense, ...]], ...]
                          with each sense a list of [text] or [text, slug],
                          slug "" when it is the text itself
  search(id, word, slug)  search-data.json.gz's rows, in order
  wotd(id, word, slug)    wotd.json.gz's rows, in order; the sense is the
                          entry's preview without its number
  crossword(id, word, clue)
                          crossword.json.gz's rows, in order
  removed(slug)           in an update only: entries to delete
"""

import html
import json
import re
import sqlite3
import sys
from pathlib import Path

import generator
from crossword_lib import build_lexicon
from wotd_lib import flatten_entries

SCHEMA = 2
LINK = re.compile(r'<a href="\./([^"]+?)\.html">(.*?)</a>')
TABLES = """
    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE entries(slug TEXT PRIMARY KEY, word TEXT NOT NULL, grammar TEXT NOT NULL,
                         preview TEXT NOT NULL, body TEXT NOT NULL) WITHOUT ROWID;
    CREATE TABLE search(id INTEGER PRIMARY KEY, word TEXT NOT NULL, slug TEXT NOT NULL);
    CREATE TABLE wotd(id INTEGER PRIMARY KEY, word TEXT NOT NULL, slug TEXT NOT NULL);
    CREATE TABLE crossword(id INTEGER PRIMARY KEY, word TEXT NOT NULL, clue TEXT NOT NULL);
"""
# Ordered lists an update splices, with their columns after id.
LISTS = {"search": ("word", "slug"), "wotd": ("word", "slug"), "crossword": ("word", "clue")}


def spans(linked: str) -> list[list[str]]:
    """generator.link_words_in_text's HTML as runs of text, links with a slug."""
    out: list[list[str]] = []
    at = 0
    for match in LINK.finditer(linked):
        if match.start() > at:
            out.append([html.unescape(linked[at : match.start()])])
        text, slug = html.unescape(match.group(2)), match.group(1)
        out.append([text, "" if slug == text else slug])
        at = match.end()
    if at < len(linked):
        out.append([html.unescape(linked[at:])])
    return out


def body(definitions: list, word_to_filename: dict, word: str) -> list:
    """The blocks generator.generate_definitions_html renders, as data."""
    blocks = []
    for block in definitions:
        grammar = block.get("grammar", "N/A")
        senses = [spans(generator.link_words_in_text(s, word_to_filename, word)) for s in block.get("senses") or []]
        if senses:
            blocks.append(["" if grammar == "N/A" else grammar, senses])
    return blocks


def full(words_data: list, version: str, out: Path) -> int:
    # The same map generator.generate_word_pages links with.
    word_to_filename = {}
    for word_obj in words_data:
        for word in (w.strip() for w in word_obj["word"].split("/")):
            if len(word) >= 3:
                word_to_filename[word] = generator.get_filename(word)

    entries = {}
    search = []
    for word_obj in words_data:
        for word in (w for w in word_obj["word"].split("/") if w):
            filename = generator.get_filename(word)
            slug = filename.removesuffix(".html")
            meta = generator.build_entry_metadata(word, word_obj["definitions"], filename)
            search.append((meta["word"], slug))
            # Like the site's files, a later entry with the same page wins.
            blocks = json.dumps(body(word_obj["definitions"], word_to_filename, word), ensure_ascii=False,
                                separators=(",", ":"))
            entries[slug] = (word, meta["grammar"] or "", meta["preview"] or "", blocks)

    db = create(out)
    db.executemany("INSERT INTO entries VALUES (?, ?, ?, ?, ?)", ((s, *row) for s, row in entries.items()))
    db.executemany("INSERT INTO search(word, slug) VALUES (?, ?)", search)
    db.executemany("INSERT INTO wotd(word, slug) VALUES (?, ?)",
                   ((e["word"], e["slug"]) for e in flatten_entries(words_data)))
    db.executemany("INSERT INTO crossword(word, clue) VALUES (?, ?)", build_lexicon(words_data))
    db.executemany("INSERT INTO meta VALUES (?, ?)",
                   [("schema", str(SCHEMA)), ("version", version), ("entries", str(len(entries)))])
    return finish(db, len(entries))


def update(old_path: Path, new_path: Path, out: Path) -> int:
    old, new = sqlite3.connect(old_path), sqlite3.connect(new_path)
    meta = lambda db: dict(db.execute("SELECT key, value FROM meta"))  # noqa: E731
    old_meta, new_meta = meta(old), meta(new)
    assert old_meta["schema"] == new_meta["schema"] == str(SCHEMA)

    rows = lambda db: {r[0]: r for r in db.execute("SELECT * FROM entries")}  # noqa: E731
    old_entries, new_entries = rows(old), rows(new)
    changed = [r for slug, r in new_entries.items() if old_entries.get(slug) != r]
    removed = [(slug,) for slug in old_entries if slug not in new_entries]
    db = create(out)
    db.execute("CREATE TABLE removed(slug TEXT PRIMARY KEY) WITHOUT ROWID")
    db.executemany("INSERT INTO entries VALUES (?, ?, ?, ?, ?)", changed)
    db.executemany("INSERT INTO removed VALUES (?)", removed)
    splices = {}
    for table, columns in LISTS.items():
        rows, splices[table] = splice(
            [r[1:] for r in old.execute(f"SELECT * FROM {table} ORDER BY id")],
            [r[1:] for r in new.execute(f"SELECT * FROM {table} ORDER BY id")],
        )
        db.executemany(f"INSERT INTO {table}({', '.join(columns)}) VALUES (?, ?)", rows)
    db.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("schema", str(SCHEMA)), ("version", new_meta["version"]), ("entries", new_meta["entries"]),
        ("base", old_meta["version"]), *splices.items(),
    ])
    print(f"{len(changed)} changed, {len(removed)} removed; "
          + ", ".join(f"{t} {s or 'same'}" for t, s in splices.items()))
    return finish(db, len(changed) + len(removed))


def splice(old: list, new: list) -> tuple[list, str]:
    """The rows that turn `old` into `new` in place of old's ids from..to-1,
    keeping what both start and end with; ([], "") if they're equal."""
    if old == new:
        return [], ""
    start = 0
    while start < min(len(old), len(new)) and old[start] == new[start]:
        start += 1
    end = 0
    while end < min(len(old), len(new)) - start and old[-1 - end] == new[-1 - end]:
        end += 1
    return new[start : len(new) - end], f"{start + 1}:{len(old) - end + 1}"


def apply(dictionary: Path, update_path: Path) -> None:
    """Applies an update in place: what the app does, for tests."""
    db = sqlite3.connect(dictionary)
    db.execute("ATTACH ? AS u", (str(update_path),))
    meta = dict(db.execute("SELECT key, value FROM u.meta"))
    assert meta["base"] == db.execute("SELECT value FROM meta WHERE key = 'version'").fetchone()[0]
    with db:
        db.execute("DELETE FROM entries WHERE slug IN (SELECT slug FROM u.removed)")
        db.execute("INSERT OR REPLACE INTO entries SELECT * FROM u.entries")
        for table, columns in LISTS.items():
            if meta[table]:
                start, end = map(int, meta[table].split(":"))
                cols = ", ".join(columns)
                db.execute(f"CREATE TEMP TABLE spliced(id INTEGER PRIMARY KEY, {cols})")
                db.execute(f"INSERT INTO spliced({cols}) SELECT {cols} FROM main.{table} WHERE id < ? ORDER BY id", (start,))
                db.execute(f"INSERT INTO spliced({cols}) SELECT {cols} FROM u.{table} ORDER BY id")
                db.execute(f"INSERT INTO spliced({cols}) SELECT {cols} FROM main.{table} WHERE id >= ? ORDER BY id", (end,))
                db.execute(f"DELETE FROM main.{table}")
                db.execute(f"INSERT INTO main.{table} SELECT * FROM spliced")
                db.execute("DROP TABLE spliced")
        db.execute("UPDATE meta SET value = ? WHERE key = 'version'", (meta["version"],))
        db.execute("UPDATE meta SET value = ? WHERE key = 'entries'", (meta["entries"],))
    db.close()


def create(out: Path) -> sqlite3.Connection:
    out.unlink(missing_ok=True)
    db = sqlite3.connect(out)
    db.executescript(TABLES)
    return db


def finish(db: sqlite3.Connection, count: int) -> int:
    db.commit()
    db.execute("VACUUM")
    db.close()
    return count


def main() -> None:
    match sys.argv[1:]:
        case ["full", version, out]:
            data = json.loads(Path(__file__).with_name(generator.DATA_FILENAME).read_text(encoding="utf-8"))
            print(f"Wrote {out}: {full(data, version, Path(out))} entries, version {version}")
        case ["update", old, new, out]:
            update(Path(old), Path(new), Path(out))
            print(f"Wrote {out}")
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main()
