.PHONY: clean word-of-the-day crossword test

word-of-the-day: shabdakosh.json
	uv run word_of_the_day.py --dry-run

crossword: output/crossword.json.gz
	cp आजको-वर्गपहेली.html crossword.js wotd.js output/

output/crossword.json.gz: shabdakosh.json.gz crossword_lib.py wotd_lib.py $(wildcard crossword_hints.jsonl)
	python3 crossword_lib.py shabdakosh.json.gz output

test: output/crossword.json.gz
	python3 -m unittest test_crossword_lib
	node crossword.test.js


shabdakosh.json: shabdakosh.json.gz
	gunzip -k shabdakosh.json.gz

build: shabdakosh.json generator.py template.html आजको-शब्द.html banner.html wotd.js wotd_lib.py आजको-वर्गपहेली.html crossword.js crossword_lib.py crossword_hints.jsonl
	uv run generator.py
	touch build

serve:
	python -m http.server -d output 8080

clean:
	rm -r output shabdakosh.json build

