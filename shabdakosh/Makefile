build: shabdakosh.json.gz generator.py template.html
	gunzip -k shabdakosh.json.gz
	uv run generator.py
	touch build


clean:
	rm -r output shabdakosh.json build
