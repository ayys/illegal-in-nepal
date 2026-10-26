import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import app_db

DATA = Path(__file__).with_name("shabdakosh.json")


def tables(path: Path) -> dict:
    db = sqlite3.connect(path)
    out = {t: sorted(db.execute(f"SELECT * FROM {t}")) for t in ("entries", "search", "wotd")}
    out["meta"] = dict(db.execute("SELECT key, value FROM meta"))
    db.close()
    return out


class AppDictionaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))[:1500]
        cls.dir = Path(tempfile.mkdtemp())

    def build(self, data, version):
        path = self.dir / f"{version}.sqlite"
        app_db.full(data, version, path)
        return path

    def test_entries_hold_linked_senses(self):
        db = sqlite3.connect(self.build(self.data, "dictionary-a"))
        word, grammar, body = db.execute("SELECT word, grammar, body FROM entries LIMIT 1").fetchone()
        blocks = json.loads(body)
        self.assertTrue(word)
        self.assertEqual(blocks[0][0], grammar)
        self.assertTrue(all(len(run) in (1, 2) for sense in blocks[0][1] for run in sense))
        bodies = (json.loads(b) for (b,) in db.execute("SELECT body FROM entries"))
        self.assertTrue(any(len(run) == 2 for blocks in bodies for _, senses in blocks for sense in senses
                            for run in sense), "some sense links to another entry")

    def test_update_turns_old_into_new(self):
        old = self.build(self.data, "dictionary-2026.01.01.0000-old")
        changed = copy.deepcopy(self.data)
        changed[10]["definitions"][0]["senses"] = ["नयाँ अर्थ।"]
        removed = changed.pop(20)
        changed.append({"word": "परीक्षणशब्द", "definitions": [{"grammar": "ना.", "senses": ["जाँच।"]}]})
        new = self.build(changed, "dictionary-2026.01.02.0000-new")

        update = self.dir / "update.sqlite"
        app_db.update(old, new, update)
        upd = sqlite3.connect(update)
        slugs = {r[0] for r in upd.execute("SELECT slug FROM entries")}
        self.assertIn("परीक्षणशब्द", slugs)
        self.assertLess(len(slugs), 10, "only what changed")
        self.assertIn((removed["word"].split("/")[0].strip(),), list(upd.execute("SELECT slug FROM removed")))
        upd.close()

        app_db.apply(old, update)
        self.assertEqual(tables(old), tables(new))

    def test_splice_keeps_shared_ends(self):
        self.assertEqual(app_db.splice([1, 2, 3], [1, 2, 3]), ([], ""))
        self.assertEqual(app_db.splice([1, 2, 3], [1, 9, 2, 3]), ([9], "2:2"))
        self.assertEqual(app_db.splice([1, 2, 3], [1, 3]), ([], "2:3"))
        self.assertEqual(app_db.splice([1, 2, 2], [1, 2, 2, 2]), ([2], "4:4"))
        self.assertEqual(app_db.splice([], [5]), ([5], "1:1"))

    def test_update_skips_unchanged_lists(self):
        a = self.build(self.data, "dictionary-a")
        edited = copy.deepcopy(self.data)
        edited[5]["definitions"][0]["senses"] = ["बदलिएको अर्थ।"]
        b = self.build(edited, "dictionary-b")
        update = self.dir / "update-lists.sqlite"
        app_db.update(a, b, update)
        meta = dict(sqlite3.connect(update).execute("SELECT key, value FROM meta"))
        self.assertEqual((meta["search"], meta["wotd"]), ("", ""))
        app_db.apply(a, update)
        self.assertEqual(tables(a), tables(b))


if __name__ == "__main__":
    unittest.main()
