.PHONY: clean



shabdakosh.json: shabdakosh.json.gz
	gunzip -k shabdakosh.json.gz

build: shabdakosh.json generator.py template.html
	uv run generator.py
	touch build

serve:
	python -m http.server -d output 8080

clean:
	rm -r output shabdakosh.json build

