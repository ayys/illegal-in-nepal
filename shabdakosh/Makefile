.PHONY: clean word-of-the-day crossword test app-dictionary app-dictionary-local

word-of-the-day: shabdakosh.json
	uv run word_of_the_day.py --dry-run

crossword: output/crossword.json.gz
	cp आजको-वर्गपहेली.html crossword.js output/

output/crossword.json.gz: shabdakosh.json.gz crossword_lib.py wotd_lib.py
	python3 crossword_lib.py shabdakosh.json.gz output

test: output/crossword.json.gz
	python3 -m unittest test_crossword_lib
	node crossword.test.js
	uv run --with aiofiles --with tqdm python -m unittest test_app_db
	cd ../dic && cargo test


# The offline dictionary bundled into the iOS app: the newest release, so the
# updates that later releases carry apply on top of it.
APP_DICTIONARY = ../ios/Vikramashi/Dictionary/dictionary.sqlite
REPO = ayys/illegal-in-nepal

app-dictionary:
	mkdir -p $(dir $(APP_DICTIONARY))
	url=$$(curl -fsSL "https://api.github.com/repos/$(REPO)/releases?per_page=100" | python3 -c \
	  'import json, sys; r = sorted((x for x in json.load(sys.stdin) if x["tag_name"].startswith("dictionary-") and not x["draft"] and not x["prerelease"]), key=lambda x: x["tag_name"])[-1]; print(next(a["browser_download_url"] for a in r["assets"] if a["name"] == "dictionary-v1.sqlite.gz"))') && \
	curl -fsSL "$$url" | gunzip > $(APP_DICTIONARY) && \
	echo "Bundled $$url"

# A dictionary built here instead, for trying changes; it is older than any
# release, so the app replaces it with the newest whole dictionary.
app-dictionary-local: shabdakosh.json
	mkdir -p $(dir $(APP_DICTIONARY))
	uv run app_db.py full dictionary-0000.00.00.0000-local $(APP_DICTIONARY)

shabdakosh.json: shabdakosh.json.gz
	gunzip -k shabdakosh.json.gz

build: shabdakosh.json generator.py template.html आजको-शब्द.html wotd_lib.py आजको-वर्गपहेली.html crossword.js crossword_lib.py ../og/tags.py
	uv run generator.py
	python3 ../og/tags.py output /shabdakosh
	touch build

serve:
	python -m http.server -d output 8080

clean:
	rm -r output shabdakosh.json build

