#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "aiofiles",
#   "tqdm",
# ]
# ///


import os
import re
import json
import asyncio
import unicodedata
import aiofiles
from tqdm import tqdm


OUTPUT_DIR = "output"
INDEX_FILENAME = "index.html"
TEMPLATE_FILENAME = "template.html"
DATA_FILENAME = "shabdakosh.json"
SEARCH_DATA_FILENAME = "search-data.js"
SEARCH_WORKER_FILENAME = "search-worker.js"
FUSE_CDN = "https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/+esm"
MAX_CONCURRENT_FILES = 1000  # Limit concurrent file operations


async def load_template(filepath):
    """Loads the HTML template file content."""
    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        return await f.read()


async def load_data(filepath):
    """Loads the JSON data from a file."""
    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content)


def slugify(word):
    """Converts a word into a filesystem-safe slug."""
    normalized = unicodedata.normalize("NFKC", word.strip())
    normalized = normalized.replace(" ", "-").replace("/", "-")
    normalized = re.sub(r"[^\w\-\u0900-\u097F]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "entry"


def get_filename(word):
    """Creates a URL-safe filename for the word."""
    return f"{slugify(word)}.html"


def generate_definitions_html(definitions):
    """
    Generates the HTML block for all definition senses, including grammar/etymology,
    structured to fit the new template.
    """
    html_content = ""
    sense_content = ""

    if definitions:
        def_block = definitions[0]

        grammar = def_block.get("grammar", "N/A")
        etymology = def_block.get("etymology", "N/A")
        senses = def_block.get("senses", [])

        grammar_tag = (
            f'<span class="gram-tag">[{grammar}]</span>' if grammar != "N/A" else ""
        )

        source_p = (
            f'<p class="entry-source"><strong>मूल स्रोत:</strong> {etymology}</p>\n'
            if etymology != "N/A"
            else ""
        )

        main_def_p = ""
        blockquote_content = ""

        if senses:
            main_def_p = "\n".join(
                [f'<p class="main-definition">{sense}</p>' for sense in senses]
            )

    return {
        "grammar_tag": grammar_tag,
        "source_p": source_p,
        "main_def_p": main_def_p,
        "blockquote_content": "",
    }


def build_entry_metadata(word, definitions, filename):
    """Creates search metadata for a word entry."""
    primary_block = definitions[0] if definitions else {}
    grammar = primary_block.get("grammar", "")
    senses = primary_block.get("senses", []) or []
    preview = senses[0] if senses else ""

    return {
        "word": word,
        "slug": filename,
        "grammar": grammar,
        "preview": preview,
    }


async def generate_single_word_page(word, filename, definitions, template, semaphore):
    """Generates a single word page file."""
    async with semaphore:
        parts = generate_definitions_html(definitions)

        # Use single-pass replacement with dict for efficiency
        replacements = {
            "{{ word }}": word,
            "{{ grammar_tag }}": parts["grammar_tag"],
            "{{ source_p }}": parts["source_p"],
            "{{ main_def_p }}": parts["main_def_p"],
            "{{ blockquote_content }}": parts["blockquote_content"],
            "{{ page_title }}": f"परिभाषा: {word}",
        }

        page_content = template
        for placeholder, value in replacements.items():
            page_content = page_content.replace(placeholder, value)

        output_path = os.path.join(OUTPUT_DIR, filename)

        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(page_content)

        return (word, filename)


async def generate_word_pages(words_data, template):
    """Generates the static HTML file for each word concurrently."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FILES)
    tasks = []
    metadata = []

    # Create all tasks upfront
    for word_obj in words_data:
        words = [w for w in word_obj["word"].split("/") if w]
        for word in words:
            filename = get_filename(word)
            metadata.append(
                build_entry_metadata(word, word_obj["definitions"], filename)
            )
            task = asyncio.create_task(
                generate_single_word_page(
                    word, filename, word_obj["definitions"], template, semaphore
                )
            )
            tasks.append(task)

    # Process all tasks concurrently with progress bar
    generated_links = []
    total_tasks = len(tasks)

    with tqdm(total=total_tasks, desc="Generating pages", unit="page") as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            generated_links.append(result)
            pbar.update(1)

    return generated_links, metadata


async def write_search_data(metadata):
    """Writes search metadata into an ES module."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    search_path = os.path.join(OUTPUT_DIR, SEARCH_DATA_FILENAME)
    js_payload = json.dumps(metadata, ensure_ascii=False)
    content = f"export const WORDS = {js_payload};\n"

    async with aiofiles.open(search_path, "w", encoding="utf-8") as f:
        await f.write(content)

    return search_path


async def write_search_worker():
    """Writes the web worker that performs Fuse.js searches off the main thread."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    worker_path = os.path.join(OUTPUT_DIR, SEARCH_WORKER_FILENAME)
    worker_content = (
        f"""
import Fuse from "{FUSE_CDN}";
import {{ WORDS }} from "./{SEARCH_DATA_FILENAME}";

const fuse = new Fuse(WORDS, {{
    keys: [
        {{ name: "word", weight: 0.7 }},
        {{ name: "preview", weight: 0.25 }},
        {{ name: "grammar", weight: 0.05 }}
    ],
    minMatchCharLength: 1,
    threshold: 0.3,
    ignoreLocation: true,
    includeScore: true
}});

self.onmessage = (event) => {{
    const data = event.data || {{}};
    const id = data.id ?? 0;
    const query = (data.query || "").trim();

    if (!query) {{
        self.postMessage({{ id, results: [] }});
        return;
    }}

    const matches = fuse.search(query, {{ limit: 20 }}).map((match) => match.item);
    self.postMessage({{ id, results: matches }});
}};
""".strip()
        + "\n"
    )

    async with aiofiles.open(worker_path, "w", encoding="utf-8") as f:
        await f.write(worker_content)

    return worker_path


async def generate_index_page(links_list):
    """Generates a static index page linking to all word pages."""

    index_content = f"""
<!DOCTYPE html>
<html lang="ne">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>शब्दकोष अनुक्रमणिका (Dictionary Index)</title>
    <style>
        :root {{
            color-scheme: light dark;
            font-family: 'Noto Sans Devanagari', 'Poppins', sans-serif;
        }}

        body {{
            margin: 0;
            background: #f5f7fb;
            min-height: 100vh;
            color: #111827;
        }}

        .hero {{
            max-width: 900px;
            margin: 0 auto;
            padding: clamp(2rem, 4vw, 4rem);
        }}

        h1 {{
            text-align: center;
            font-size: clamp(2.5rem, 6vw, 3.5rem);
            margin-bottom: 1rem;
            color: #0f172a;
        }}

        .search-box {{
            display: flex;
            align-items: center;
            gap: 1rem;
            background: #ffffff;
            padding: 0.75rem 1.25rem;
            border-radius: 999px;
            box-shadow: 0 20px 40px rgb(15 23 42 / 10%);
        }}

        .search-box input {{
            flex: 1;
            font-size: 1.1rem;
            border: none;
            outline: none;
            background: transparent;
        }}

        .results {{
            margin-top: 2rem;
            display: grid;
            gap: 0.75rem;
        }}

        .result-item {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            padding: 1rem 1.25rem;
            border-radius: 0.85rem;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            text-decoration: none;
            color: inherit;
            transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
        }}

        .result-item:hover {{
            transform: translateY(-2px);
            border-color: #0ea5e9;
            box-shadow: 0 10px 25px rgb(14 165 233 / 20%);
        }}

        .result-word {{
            font-size: 1.4rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .result-grammar {{
            font-size: 0.95rem;
            color: #0369a1;
            background: #e0f2fe;
            padding: 0.1rem 0.6rem;
            border-radius: 999px;
        }}

        .result-preview {{
            color: #475467;
            font-size: 0.95rem;
            line-height: 1.4;
        }}

        .fallback {{
            margin-top: 3rem;
        }}

        .word-list {{
            column-count: 3;
            list-style: none;
            padding: 0;
            margin: 1.5rem 0 0;
        }}

        .word-list a {{
            color: #0f62fe;
            text-decoration: none;
        }}

        @media (max-width: 900px) {{
            .word-list {{ column-count: 2; }}
        }}
        @media (max-width: 600px) {{
            .word-list {{ column-count: 1; }}
            .search-box {{ border-radius: 1.5rem; flex-direction: column; align-items: stretch; }}
        }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>नेपाली बृहत शब्दकोश</h1>
        <div class="search-box">
            <input id="search-input" type="search" placeholder="शब्द छान्नुहोस्…" aria-label="शब्द खोज्नुहोस्">
        </div>
        <div id="search-results" class="results" aria-live="polite"></div>
        <section class="fallback" aria-live="polite">
            <noscript>
                <p>यो खोज प्रयोग गर्न JavaScript आवश्यक छ। कृपया ब्राउज़र सेटिङमा सक्षम गर्नुहोस्।</p>
            </noscript>
        </section>
    </div>
    <script type="module">
        const input = document.getElementById("search-input");
        const resultsContainer = document.getElementById("search-results");
        const worker = new Worker("./{SEARCH_WORKER_FILENAME}", {{ type: "module" }});
        let requestId = 0;

        const renderResults = (items) => {{
            if (!items.length) {{
                resultsContainer.innerHTML = "<p>कुनै परिणाम भेटिएन।</p>";
                return;
            }}

            const markup = items.map((item) => `
                <a class="result-item" href="./${{item.slug}}">
                    <span class="result-word">
                        ${{item.word}}
                        ${{item.grammar ? `<span class="result-grammar">${{item.grammar}}</span>` : ""}}
                    </span>
                    ${{item.preview ? `<span class="result-preview">${{item.preview}}</span>` : ""}}
                </a>
            `).join("");

            resultsContainer.innerHTML = markup;
        }};

        worker.addEventListener("message", (event) => {{
            const {{ id, results }} = event.data || {{}};
            if (id !== requestId) {{
                return;
            }}
            renderResults(results);
        }});

        const performSearch = (value) => {{
            const query = value.trim();
            resultsContainer.innerHTML = query ? "<p>खोज्दै...</p>" : "";
            const currentRequest = ++requestId;
            worker.postMessage({{ id: currentRequest, query }});
        }};

        input.addEventListener("input", (event) => performSearch(event.target.value));

        if (window.matchMedia("(pointer: fine)").matches) {{
            input.focus();
        }}
    </script>
</body>
</html>
"""

    index_path = os.path.join(OUTPUT_DIR, INDEX_FILENAME)

    async with aiofiles.open(index_path, "w", encoding="utf-8") as f:
        await f.write(index_content)
    return index_path


async def main():
    """Main execution function, loading template and data from files."""

    try:
        template_task = load_template(TEMPLATE_FILENAME)
        data_task = load_data(DATA_FILENAME)
        template, words_data = await asyncio.gather(template_task, data_task)
    except FileNotFoundError as e:
        if TEMPLATE_FILENAME in str(e):
            print(
                f"Error: Template file '{TEMPLATE_FILENAME}' not found. Please create it."
            )
        elif DATA_FILENAME in str(e):
            print(
                f"Error: Data file '{DATA_FILENAME}' not found. Please create it and ensure it's valid JSON."
            )
        else:
            print(f"Error: File not found: {e}")
        return
    except json.JSONDecodeError:
        print(
            f"Error: Failed to decode JSON from '{DATA_FILENAME}'. Check file structure."
        )
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    links, metadata = await generate_word_pages(words_data, template)
    print(f"Successfully generated {len(links)} word pages.")

    await write_search_data(metadata)
    await write_search_worker()

    index_path = await generate_index_page(links)
    print(f"Generated Index: {index_path}")


if __name__ == "__main__":
    asyncio.run(main())
