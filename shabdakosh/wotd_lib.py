"""Shared 'word of the day' picking — used by the X bot and the website."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NEPAL = ZoneInfo("Asia/Kathmandu")
MIN_WORD_LEN = 2


def slugify(word: str) -> str:
    normalized = unicodedata.normalize("NFKC", word.strip())
    normalized = normalized.replace(" ", "-").replace("/", "-")
    normalized = re.sub(r"[^\w\-\u0900-\u097F]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "entry"


def first_sense(entry: dict) -> str:
    for block in entry.get("definitions") or []:
        for sense in block.get("senses") or []:
            text = re.sub(r"^[०-९0-9]+[.\)]\s*", "", str(sense).strip())
            if text:
                return text
    return ""


def flatten_entries(data: list) -> list[dict]:
    out = []
    for entry in data:
        raw = entry.get("word") or ""
        sense = first_sense(entry)
        if not sense:
            continue
        for part in raw.split("/"):
            word = part.strip()
            if len(word) < MIN_WORD_LEN:
                continue
            out.append({"word": word, "sense": sense, "slug": slugify(word)})
    return out


def pick_for_day(entries: list[dict], day: str) -> dict:
    idx = int(hashlib.sha256(day.encode("utf-8")).hexdigest(), 16) % len(entries)
    return entries[idx]


def nepal_today() -> str:
    return datetime.now(NEPAL).date().isoformat()


def load_dictionary(path: Path) -> list:
    if path.suffix == ".gz":
        import gzip

        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    with path.open(encoding="utf-8") as f:
        return json.load(f)
