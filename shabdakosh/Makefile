.PHONY: clean word-of-the-day

word-of-the-day: shabdakosh.json
	uv run word_of_the_day.py --dry-run



shabdakosh.json: shabdakosh.json.gz
	gunzip -k shabdakosh.json.gz

build: shabdakosh.json generator.py template.html आजको-शब्द.html banner.html wotd.js wotd_lib.py
	uv run generator.py
	touch build

serve:
	python -m http.server -d output 8080

clean:
	rm -r output shabdakosh.json build

