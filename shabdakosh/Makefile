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
	tag=$$(gh release list --repo $(REPO) --limit 100 --json tagName,isDraft \
	  --jq '[.[] | select(.isDraft | not) | select(.tagName | startswith("dictionary-"))][0].tagName') && \
	gh release download "$$tag" --repo $(REPO) --pattern dictionary-v1.sqlite.gz --output - | gunzip > $(APP_DICTIONARY) && \
	echo "Bundled $$tag"

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

