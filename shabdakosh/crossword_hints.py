"""Ask a local model for a short crossword clue and an extra hint per crossword word.

Talks to an OpenAI-compatible server (llama.cpp's llama-server), e.g.

    llama-server -m gemma-3-4b-it-Q4_K_M.gguf -c 8192 -np 4 --port 8080

Appends raw model output to crossword_hints.jsonl and skips words already there, so it can
be stopped and resumed. crossword_lib.usable_text decides at build time what gets used.

    python3 crossword_hints.py --sample 50      # a fixed random sample, to judge quality
    python3 crossword_hints.py                  # everything not done yet
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from crossword_lib import HINTS_PATH, build_lexicon, load_hints
from wotd_lib import load_dictionary

SCHEMA = {
    "type": "object",
    "properties": {"clue": {"type": "string"}, "hint": {"type": "string"}},
    "required": ["clue", "hint"],
}
SYSTEM = """You write clues for a Nepali crossword. You are given a Nepali word and its dictionary definition.
Reply with JSON: {"clue": ..., "hint": ...}, both in natural Nepali (Devanagari), never in English.
- "clue": a short crossword clue, 1 to 5 words: a synonym or a crisp description, the way a Nepali newspaper crossword would put it.
- "hint": one short extra sentence for a stuck solver: where it is found, what it is used for, or a common phrase it appears in. Do not repeat the clue.
Never write the answer word, its root, or any inflected form of it in the clue or the hint."""
EXAMPLE_IN = "शब्द: किताब\nपरिभाषा: पढ्नका लागि छापिएका पानाहरूको बाँधिएको सङ्ग्रह; पुस्तक।"
EXAMPLE_OUT = json.dumps({"clue": "पढ्ने पुस्तक", "hint": "पुस्तकालयमा यस्ता धेरै हुन्छन्।"}, ensure_ascii=False)


def full_sense(entry: dict) -> str:
    for block in entry.get("definitions") or []:
        for sense in block.get("senses") or []:
            if str(sense).strip():
                return str(sense).strip()
    return ""


def ask(server: str, word: str, definition: str) -> dict:
    body = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": EXAMPLE_IN},
            {"role": "assistant", "content": EXAMPLE_OUT},
            {"role": "user", "content": f"शब्द: {word}\nपरिभाषा: {definition}"},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
        "response_format": {"type": "json_schema", "json_schema": {"name": "clue", "schema": SCHEMA}},
    }
    req = urllib.request.Request(
        server.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as res:
        reply = json.loads(res.read())
    return json.loads(reply["choices"][0]["message"]["content"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:8080")
    parser.add_argument("--model", default="gemma-3-4b-it-Q4_K_M", help="recorded with each row")
    parser.add_argument("--dictionary", default="shabdakosh.json.gz")
    parser.add_argument("--sample", type=int, help="only a fixed random sample of this many words")
    parser.add_argument("--parallel", type=int, default=4, help="match llama-server -np")
    args = parser.parse_args()

    data = load_dictionary(Path(args.dictionary))
    senses = {}
    for entry in data:
        senses.setdefault((entry.get("word") or "").strip(), full_sense(entry))
    words = [row[0] for row in build_lexicon(data)]
    if args.sample:
        words = random.Random(0).sample(words, args.sample)

    done = load_hints(HINTS_PATH)
    todo = [w for w in words if w not in done]
    print(f"{len(words) - len(todo)} done, {len(todo)} to go", flush=True)

    lock = threading.Lock()
    start = time.monotonic()
    count = 0

    with HINTS_PATH.open("a", encoding="utf-8") as out:

        def work(word: str) -> None:
            nonlocal count
            try:
                reply = ask(args.server, word, senses.get(word, ""))
            except Exception as err:  # keep going; the word is retried on the next run
                print(f"{word}: {err}", file=sys.stderr, flush=True)
                return
            row = {"word": word, "clue": reply.get("clue", ""), "hint": reply.get("hint", ""), "model": args.model}
            with lock:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                count += 1
                if count % 10 == 0 or count == len(todo):
                    rate = (time.monotonic() - start) / count
                    left = (len(todo) - count) * rate / 3600
                    print(f"{count}/{len(todo)}  {rate:.1f}s/word  ~{left:.1f}h left", flush=True)

        with ThreadPoolExecutor(args.parallel) as pool:
            list(pool.map(work, todo))


if __name__ == "__main__":
    main()
