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
import gzip
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


def find_root_word(word):
    """
    Strips common Nepali suffixes to find the root word.
    Returns the root word if a suffix is found, otherwise returns the original word.
    """
    # Common Nepali suffixes (case endings, plural markers, etc.)
    suffixes = [
        'हरू',      # plural marker
        'ले',       # instrumental/ergative case
        'को',       # genitive case
        'लाई',      # dative/accusative case
        'मा',       # locative case
        'बाट',      # ablative case
        'सम्म',     # terminative case
        'सँग',      # comitative case
        'बिना',     # without
        'का',       # genitive (alternative)
        'देखि',     # from
        'तिर',      # towards
    ]
    
    # Try removing suffixes (longest first)
    for suffix in sorted(suffixes, key=len, reverse=True):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            root = word[:-len(suffix)]
            if len(root) >= 3:  # Ensure root is meaningful
                return root
    
    return word


def link_words_in_text(text, word_to_filename, current_word=None):
    """
    Links words in text to their definition pages if they exist in the dictionary.
    Improved word extraction and root word detection for Nepali.
    """
    if not text or not word_to_filename:
        import html
        return html.escape(text) if text else text
    
    import html
    import re
    escaped_text = html.escape(text)
    
    # Extract all potential Nepali words from the text
    # Match sequences of Devanagari characters (3+ chars)
    nepali_word_pattern = r'[\u0900-\u097F]{3,}'
    all_matches = list(re.finditer(nepali_word_pattern, escaped_text))
    
    # Build mapping of words to link
    # Format: (word_in_text, start_pos, end_pos) -> (filename, word_to_display)
    words_to_link = {}
    known_suffixes = ['को', 'ले', 'लाई', 'मा', 'बाट', 'सम्म', 'सँग', 'का', 'देखि', 'तिर', 'हरू', 'बिना']
    
    # Punctuation characters to strip (both Nepali and common punctuation)
    punctuation_chars = '।॥.,;:!?()[]{}"\'—–\u0964\u0965'
    
    for match in all_matches:
        full_word = match.group(0)
        start_pos = match.start()
        end_pos = match.end()
        
        # Clean word: strip all punctuation from both ends
        # Use strip() to remove leading and trailing punctuation
        cleaned_word = full_word.strip(punctuation_chars)
        
        # Also remove any punctuation that might be embedded (though rare)
        # This handles cases where punctuation got included in the match
        cleaned_word = re.sub(r'[' + re.escape(punctuation_chars) + r']+', '', cleaned_word)
        
        # Skip if word became too short after cleaning or is the current word
        if len(cleaned_word) < 3 or cleaned_word == current_word:
            continue
        
        # Adjust positions if we stripped leading punctuation
        # Calculate how much was stripped from the start
        stripped_from_start = len(full_word) - len(full_word.lstrip(punctuation_chars))
        adjusted_start = start_pos + stripped_from_start
        adjusted_end = adjusted_start + len(cleaned_word)
        
        # Strategy 1: Check exact match
        if cleaned_word in word_to_filename:
            key = (cleaned_word, adjusted_start, adjusted_end)
            words_to_link[key] = (word_to_filename[cleaned_word], cleaned_word, False)  # Not a root link
            continue
        
        # Strategy 2: Check root form (stripping suffixes using find_root_word)
        root = find_root_word(cleaned_word)
        if root != cleaned_word and root in word_to_filename:
            # Link the root part only
            root_start = adjusted_start
            root_end = adjusted_start + len(root)
            key = (root, root_start, root_end)
            if key not in words_to_link:
                words_to_link[key] = (word_to_filename[root], root, True)  # Mark as root link
            continue
        
        # Strategy 3: For compound words like "कामको", explicitly check known suffixes
        # This is more aggressive and handles cases where find_root_word might miss something
        if len(cleaned_word) > 4:
            found_prefix = False
            for suffix in known_suffixes:
                if cleaned_word.endswith(suffix):
                    prefix_word = cleaned_word[:-len(suffix)]
                    if len(prefix_word) >= 3 and prefix_word in word_to_filename:
                        # Link only the prefix part
                        prefix_start = adjusted_start
                        prefix_end = adjusted_start + len(prefix_word)
                        key = (prefix_word, prefix_start, prefix_end)
                        if key not in words_to_link:
                            words_to_link[key] = (word_to_filename[prefix_word], prefix_word, True)  # Mark as root link
                        found_prefix = True
                        break  # Found a valid prefix, stop checking other suffixes
            if found_prefix:
                continue
    
    if not words_to_link:
        return escaped_text
    
    # Convert to list and sort by start position (process earlier words first)
    # Then by length (longest first) to match phrases before individual words
    word_list = [(word, start, end, filename, display_word, is_root_link) 
                 for ((word, start, end), (filename, display_word, is_root_link)) in words_to_link.items()]
    word_list.sort(key=lambda x: (x[1], -len(x[0])))  # Sort by position, then by length (desc)
    
    linked_text = escaped_text
    linked_positions = []
    
    # Process words in reverse order of position (end to start) to avoid index shifting issues
    word_list.reverse()
    
    for word, start_pos, end_pos, filename, display_word, is_root_link in word_list:
        # Verify the word still matches at this position (text hasn't been modified)
        if linked_text[start_pos:end_pos] != word:
            # Try to find the word near this position
            search_start = max(0, start_pos - 10)
            search_end = min(len(linked_text), end_pos + 10)
            pos = linked_text.find(word, search_start, search_end)
            if pos == -1:
                continue
            start_pos = pos
            end_pos = pos + len(word)
        
        # Skip if inside HTML tag
        text_before = linked_text[:start_pos]
        last_open = text_before.rfind('<')
        last_close = text_before.rfind('>')
        if last_open > last_close:
            continue
        
        # Word boundary check (including Nepali punctuation)
        before_char = linked_text[start_pos - 1] if start_pos > 0 else ' '
        after_char = linked_text[end_pos] if end_pos < len(linked_text) else ' '
        
        # Include Nepali punctuation and common separators
        boundary_chars = ' \n\t.,;:!?()[]{}"\'—–\u0964\u0965'
        
        # Check before character
        if start_pos > 0 and before_char not in boundary_chars:
            continue
        
        # Check after character
        if end_pos < len(linked_text):
            if is_root_link:
                # For root links (like "काम" from "कामको"), allow known suffixes after the word
                # Check if it's a boundary char OR if the following text starts with a known suffix
                if after_char not in boundary_chars:
                    # Check if the text after starts with any known suffix
                    text_after = linked_text[end_pos:]
                    starts_with_suffix = any(text_after.startswith(suffix) for suffix in known_suffixes)
                    if not starts_with_suffix:
                        continue
            else:
                # For regular words, require a boundary character
                if after_char not in boundary_chars:
                    continue
        
        # Check overlap with existing links
        if any(start_pos >= ls and start_pos < le or end_pos > ls and end_pos <= le 
               for ls, le in linked_positions):
            continue
        
        # Create link - use the word as found in text
        link_html = f'<a href="./{filename}" style="color: #0f62fe; text-decoration: underline;">{word}</a>'
        linked_text = linked_text[:start_pos] + link_html + linked_text[end_pos:]
        linked_positions.append((start_pos, start_pos + len(link_html)))
    
    return linked_text


def generate_definitions_html(definitions, word_to_filename=None, current_word=None):
    """
    Generates the HTML block for all definition senses, including grammar/etymology,
    structured to fit the new template. Handles multiple definition blocks.
    Automatically links words in definitions to their pages if they exist.
    """
    if not definitions:
        return {
            "grammar_tag": "",
            "source_p": "",
            "main_def_p": "",
            "blockquote_content": "",
        }

    # Collect all grammar tags for the header
    grammar_tags = []
    source_parts = []
    definition_blocks = []

    for idx, def_block in enumerate(definitions):
        grammar = def_block.get("grammar", "N/A")
        etymology = def_block.get("etymology", "N/A")
        senses = def_block.get("senses", [])

        # Collect unique grammar tags
        if grammar != "N/A" and grammar not in grammar_tags:
            grammar_tags.append(grammar)

        # Build definition block HTML
        def_html_parts = []
        
        # Add grammar tag for this definition block
        if grammar != "N/A":
            def_html_parts.append(
                f'<div style="margin-top: {"1.5rem" if idx > 0 else "0"}; margin-bottom: 0.5rem;">'
                f'<span class="gram-tag">[{grammar}]</span>'
                f'</div>'
            )

        # Add senses with word linking
        if senses:
            for sense in senses:
                # Link words in the sense text if word mapping is available
                linked_sense = link_words_in_text(sense, word_to_filename, current_word) if word_to_filename else sense
                def_html_parts.append(f'<p class="main-definition">{linked_sense}</p>')

        if def_html_parts:
            definition_blocks.append("\n".join(def_html_parts))

    # Grammar tag removed from header - shown in definition blocks instead
    grammar_tag = ""

    # Etymology removed from display
    source_p = ""

    # Combine all definition blocks
    main_def_p = "\n".join(definition_blocks)

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


async def generate_single_word_page(word, filename, definitions, template, semaphore, word_to_filename=None):
    """Generates a single word page file."""
    async with semaphore:
        parts = generate_definitions_html(definitions, word_to_filename, current_word=word)

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
    
    # Build word-to-filename mapping for linking (build once, reuse for all pages)
    word_to_filename = {}
    for word_obj in words_data:
        words = [w.strip() for w in word_obj["word"].split("/") if w.strip()]
        for word in words:
            if word and len(word) >= 3:  # Include words 3+ chars (e.g., काम, दौड, भेउ)
                filename = get_filename(word)
                word_to_filename[word] = filename

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
                    word, filename, word_obj["definitions"], template, semaphore, word_to_filename
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
    """Writes search metadata into an ES module and creates a gzipped version."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    search_path = os.path.join(OUTPUT_DIR, SEARCH_DATA_FILENAME)
    js_payload = json.dumps(metadata, ensure_ascii=False)
    content = f"export const WORDS = {js_payload};\n"

    # Write uncompressed version
    async with aiofiles.open(search_path, "w", encoding="utf-8") as f:
        await f.write(content)

    # Write gzipped version
    gz_path = f"{search_path}.gz"
    async with aiofiles.open(gz_path, "wb") as f:
        compressed = gzip.compress(content.encode("utf-8"))
        await f.write(compressed)

    return search_path


async def write_search_worker():
    """Writes the web worker that performs Fuse.js searches off the main thread."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    worker_path = os.path.join(OUTPUT_DIR, SEARCH_WORKER_FILENAME)
    worker_content = (
        f"""
import Fuse from "{FUSE_CDN}";
import pako from "https://cdn.jsdelivr.net/npm/pako@2.1.0/+esm";

let fuse = null;
let wordsLoaded = false;

const loadWords = async () => {{
    if (wordsLoaded) return;
    
    // Try to load gzipped version first (much smaller ~4MB vs ~27MB)
    let WORDS;
    try {{
        const gzResponse = await fetch("./{SEARCH_DATA_FILENAME}.gz");
        if (gzResponse.ok) {{
            const arrayBuffer = await gzResponse.arrayBuffer();
            const uint8Array = new Uint8Array(arrayBuffer);
            
            // Try native DecompressionStream first (modern browsers)
            if (typeof DecompressionStream !== 'undefined') {{
                try {{
                    console.log("Using native DecompressionStream API");
                    const blob = new Blob([uint8Array]);
                    const stream = blob.stream().pipeThrough(new DecompressionStream("gzip"));
                    const decompressed = await new Response(stream).text();
                    // Create a blob URL and import it as a module
                    const blobUrl = new Blob([decompressed], {{ type: "application/javascript" }});
                    const url = URL.createObjectURL(blobUrl);
                    const module = await import(url);
                    WORDS = module.WORDS;
                    URL.revokeObjectURL(url);
                }} catch (streamError) {{
                    console.warn("DecompressionStream failed:", streamError);
                    throw new Error("DecompressionStream failed: " + streamError.message);
                }}
            }} else {{
                // Fallback to pako for older browsers (iOS Safari < 16.4, etc.)
                console.log("Using pako.js polyfill for gzip decompression");
                const decompressed = pako.ungzip(uint8Array, {{ to: 'string' }});
                const blob = new Blob([decompressed], {{ type: "application/javascript" }});
                const url = URL.createObjectURL(blob);
                const module = await import(url);
                WORDS = module.WORDS;
                URL.revokeObjectURL(url);
            }}
        }} else {{
            throw new Error("Gzip version not available");
        }}
    }} catch (e) {{
        console.warn("Gzip loading failed, falling back to uncompressed:", e);
        // Final fallback to uncompressed version
        const module = await import("./{SEARCH_DATA_FILENAME}");
        WORDS = module.WORDS;
    }}
    
    fuse = new Fuse(WORDS, {{
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
    
    wordsLoaded = true;
}};

self.onmessage = async (event) => {{
    const data = event.data || {{}};
    const id = data.id ?? 0;
    const query = (data.query || "").trim();

    if (!query) {{
        self.postMessage({{ id, results: [] }});
        return;
    }}

    // Lazy load words data only when first search is performed
    await loadWords();
    
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
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04);
            border: 1px solid #e5e7eb;
            transition: box-shadow 150ms ease, border-color 150ms ease;
        }}

        .search-box:focus-within {{
            box-shadow: 0 4px 12px rgba(14, 165, 233, 0.15), 0 2px 4px rgba(0, 0, 0, 0.06);
            border-color: #0ea5e9;
        }}

        .search-box input {{
            flex: 1;
            font-size: 1.1rem;
            border: none;
            outline: none;
            background: transparent;
            color: #111827;
        }}

        .search-box input::placeholder {{
            color: #9ca3af;
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
            color: #111827;
            transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease, background-color 120ms ease;
        }}

        .result-item:hover {{
            transform: translateY(-2px);
            border-color: #0ea5e9;
            box-shadow: 0 8px 16px rgba(14, 165, 233, 0.12), 0 2px 4px rgba(0, 0, 0, 0.06);
            background: #f8fafc;
        }}

        .result-word {{
            font-size: 1.4rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #0f172a;
        }}

        .result-grammar {{
            font-size: 0.9rem;
            color: #0369a1;
            background: #e0f2fe;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            font-weight: 500;
            white-space: nowrap;
        }}

        .result-preview {{
            color: #64748b;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-top: 0.25rem;
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
        @media (prefers-color-scheme: dark) {{
            body {{
                background: #0f172a;
                color: #e2e8f0;
            }}
            
            h1 {{
                color: #f1f5f9;
            }}
            
            .search-box {{
                background: #1e293b;
                border-color: #334155;
            }}
            
            .search-box input {{
                color: #f1f5f9;
            }}
            
            .search-box input::placeholder {{
                color: #64748b;
            }}
            
            .result-item {{
                background: #1e293b;
                border-color: #334155;
                color: #e2e8f0;
            }}
            
            .result-item:hover {{
                background: #334155;
                border-color: #0ea5e9;
            }}
            
            .result-word {{
                color: #f1f5f9;
            }}
            
            .result-preview {{
                color: #94a3b8;
            }}
        }}

        @media (max-width: 600px) {{
            .word-list {{ column-count: 1; }}
            .search-box {{ 
                border-radius: 1.5rem; 
                flex-direction: column; 
                align-items: stretch; 
                padding: 0.5rem 1rem;
            }}
            .search-box input {{
                font-size: 16px; /* Prevents zoom on iOS */
            }}
            .result-item {{
                padding: 0.75rem 1rem;
            }}
            .result-word {{
                font-size: 1.2rem;
            }}
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
        let worker = null;
        let workerReady = false;
        let requestId = 0;
        let pendingQuery = null;

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

        const initWorker = async () => {{
            if (workerReady) return;
            
            try {{
                resultsContainer.innerHTML = "<p>खोज प्रणाली लोड हुँदैछ...</p>";
                worker = new Worker("./{SEARCH_WORKER_FILENAME}", {{ type: "module" }});
                
                worker.addEventListener("message", (event) => {{
                    const {{ id, results }} = event.data || {{}};
                    if (id !== requestId) {{
                        return;
                    }}
                    workerReady = true;
                    renderResults(results);
                    
                    // Process pending query if any
                    if (pendingQuery !== null) {{
                        const query = pendingQuery;
                        pendingQuery = null;
                        performSearch(query);
                    }}
                }});
                
                // Trigger worker initialization by sending empty message
                worker.postMessage({{ id: 0, query: "" }});
            }} catch (error) {{
                resultsContainer.innerHTML = "<p>खोज प्रणाली लोड गर्न असफल। कृपया पृष्ठ पुनः लोड गर्नुहोस्।</p>";
                console.error("Worker initialization failed:", error);
            }}
        }};

        const performSearch = async (value) => {{
            const query = value.trim();
            
            if (!query) {{
                resultsContainer.innerHTML = "";
                return;
            }}
            
            // Initialize worker if not ready
            if (!workerReady) {{
                if (!worker) {{
                    await initWorker();
                }}
                // Store query to process after worker is ready
                if (!workerReady) {{
                    pendingQuery = query;
                    resultsContainer.innerHTML = "<p>खोज प्रणाली लोड हुँदैछ...</p>";
                    return;
                }}
            }}
            
            resultsContainer.innerHTML = "<p>खोज्दै...</p>";
            const currentRequest = ++requestId;
            worker.postMessage({{ id: currentRequest, query }});
        }};

        // Lazy load worker only when user starts typing
        let inputTimeout;
        input.addEventListener("input", (event) => {{
            const query = event.target.value.trim();
            
            // Clear previous timeout
            clearTimeout(inputTimeout);
            
            if (query) {{
                // Small delay to avoid loading on every keystroke
                inputTimeout = setTimeout(() => performSearch(query), 100);
            }} else {{
                resultsContainer.innerHTML = "";
            }}
        }});

        // Also initialize on focus (user might want to search)
        input.addEventListener("focus", () => {{
            if (!worker && !workerReady) {{
                initWorker();
            }}
        }});

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
