#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "tweepy>=4.14",
# ]
# ///
"""Post today's Nepali dictionary word to X, with a link to its शब्दकोश page.

Required env (GitHub Actions secrets) when not using --dry-run:
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import quote

from wotd_lib import (
    flatten_entries,
    load_dictionary,
    nepal_today,
    pick_for_day,
)

SITE = os.environ.get("SITE_BASE", "https://illegal-in-nepal.org")
URL_WEIGHT = 23
TWEET_LIMIT = 280


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 1:
        return "…"[:limit]
    return text[: limit - 1].rstrip() + "…"


def compose_tweet(word: str, sense: str, url: str) -> str:
    header = f"आजको शब्द: {word}"
    overhead = len(header) + 2 + 1 + URL_WEIGHT
    room = TWEET_LIMIT - overhead
    if room < 0:
        header = truncate(header, TWEET_LIMIT - URL_WEIGHT - 1)
        return f"{header}\n{url}"
    body = truncate(sense, room)
    if body:
        return f"{header}\n\n{body}\n{url}"
    return f"{header}\n{url}"


def post_tweet(text: str) -> str:
    import tweepy

    missing = [
        name
        for name in (
            "X_API_KEY",
            "X_API_SECRET",
            "X_ACCESS_TOKEN",
            "X_ACCESS_TOKEN_SECRET",
        )
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit(
            "Missing env: "
            + ", ".join(missing)
            + ". Add them as GitHub Actions secrets, or pass --dry-run."
        )

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    response = client.create_tweet(text=text)
    return response.data["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Post शब्दकोश word of the day to X")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date", help="YYYY-MM-DD in Nepal time (default: today)")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    data_path = here / "shabdakosh.json"
    if not data_path.exists():
        data_path = here / "shabdakosh.json.gz"
    if not data_path.exists():
        raise SystemExit(f"No dictionary at {here / 'shabdakosh.json.gz'}")

    day = args.date or nepal_today()
    entries = flatten_entries(load_dictionary(data_path))
    if not entries:
        raise SystemExit("Dictionary has no usable entries")

    picked = pick_for_day(entries, day)
    url = f"{SITE}/shabdakosh/{quote(picked['slug'])}.html"
    text = compose_tweet(picked["word"], picked["sense"], url)

    print(f"day={day} word={picked['word']} slug={picked['slug']}")
    print("--- tweet ---")
    print(text)
    print("-------------")

    if args.dry_run:
        return

    tweet_id = post_tweet(text)
    print(f"posted https://x.com/i/web/status/{tweet_id}")


if __name__ == "__main__":
    main()
