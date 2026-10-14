"""Pick dictionary words that make good crossword answers."""

from __future__ import annotations

import gzip
import json
import re
import sys
import unicodedata
from pathlib import Path

from wotd_lib import load_dictionary, slugify

LEXICON_FILENAME = "crossword.json.gz"
HINTS_PATH = Path(__file__).resolve().parent / "crossword_hints.jsonl"
MAX_SHORT_CLUE_LEN = 40
MAX_HINT_LEN = 120

MIN_AKSHARS = 3
# Keep in sync with SIZE in crossword.js.
MAX_AKSHARS = 7
MIN_CLUE_LEN = 3
MAX_CLUE_LEN = 90
CLUE_GRAMMAR = {"ना.", "वि."}

# One cell: an independent vowel, or a consonant with an optional vowel sign,
# then an optional chandrabindu / anusvara / visarga. Keep in sync with crossword.js.
AKSHAR = re.compile(
    r"(?:[\u0905-\u0914]|[\u0915-\u0939][\u093e-\u094c]?)[\u0901-\u0903]?"
)
INVISIBLE = re.compile(r"[\u200b-\u200d\ufeff]")
NUMBERING = re.compile(r"^[०-९0-9]+[.\)]\s*")
SURNAME = re.compile(r"(?:^|\s)थर$")
LATIN = re.compile(r"[A-Za-z]")


def akshars(word: str) -> list[str] | None:
    """Split into crossword cells, or None if the word has anything else (e.g. a conjunct)."""
    cells = AKSHAR.findall(word)
    return cells if "".join(cells) == word else None


def is_crosswordy_word(word: str) -> bool:
    cells = akshars(unicodedata.normalize("NFC", word))
    return cells is not None and MIN_AKSHARS <= len(cells) <= MAX_AKSHARS


def clue_for(entry: dict) -> str | None:
    """First clause of the first sense, if it's a usable noun/adjective gloss."""
    word = entry.get("word") or ""
    for block in entry.get("definitions") or []:
        for sense in block.get("senses") or []:
            text = INVISIBLE.sub("", str(sense)).strip()
            text = NUMBERING.sub("", text).strip()
            if not text:
                continue
            if (block.get("grammar") or "").strip() not in CLUE_GRAMMAR:
                return None
            clue = re.split(r"[;।]", text, maxsplit=1)[0].strip()
            if clue.startswith("हे.") or word in clue or SURNAME.search(clue):
                return None
            if not MIN_CLUE_LEN <= len(clue) <= MAX_CLUE_LEN:
                return None
            return clue
    return None


def usable_text(word: str, text: str, max_len: int) -> str | None:
    """Model-written clue/hint text, cleaned, or None if it is empty, not Nepali, or gives the answer away."""
    text = INVISIBLE.sub("", unicodedata.normalize("NFC", str(text or "")))
    text = re.sub(r"\s+", " ", text).strip().rstrip("।.").strip()
    if not text or len(text) > max_len or LATIN.search(text):
        return None
    cells = akshars(word) or []
    giveaways = [word] + (["".join(cells[:-1])] if len(cells) >= 3 else [])
    if any(g in text for g in giveaways):
        return None
    return text


def load_hints(path: Path) -> dict[str, dict]:
    """word -> {"clue", "hint"} from a JSON-lines file; later lines win."""
    hints: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                hints[row["word"]] = row
    return hints


def build_lexicon(data: list, hints: dict[str, dict] | None = None) -> list[list[str]]:
    """[word, clue, hint] rows, one per word, sorted by word. A crosswordy word is its own slug.

    With hints, only words that have a usable written clue are kept.
    """
    seen: dict[str, list[str]] = {}
    for entry in data:
        word = unicodedata.normalize("NFC", (entry.get("word") or "").strip())
        if word in seen or not is_crosswordy_word(word) or slugify(word) != word:
            continue
        clue = clue_for(entry)
        if not clue:
            continue
        if not hints:
            seen[word] = [word, clue, ""]
            continue
        written = hints.get(word) or {}
        short = usable_text(word, written.get("clue"), MAX_SHORT_CLUE_LEN)
        if short:
            seen[word] = [word, short, usable_text(word, written.get("hint"), MAX_HINT_LEN) or ""]
    return [seen[w] for w in sorted(seen)]


def write_lexicon(data: list, out_dir: Path) -> Path:
    rows = build_lexicon(data, load_hints(HINTS_PATH))
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / LEXICON_FILENAME
    path.write_bytes(gzip.compress(payload, compresslevel=9))
    print(f"Wrote crossword lexicon ({len(rows)} words)")
    return path


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "shabdakosh.json.gz")
    write_lexicon(load_dictionary(src), Path(sys.argv[2] if len(sys.argv) > 2 else "output"))
