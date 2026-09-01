.PHONY: build blog serve

SHABDAKOSH_SRC = \
	shabdakosh/shabdakosh.json.gz \
	shabdakosh/generator.py \
	shabdakosh/template.html \
	shabdakosh/आजको-शब्द.html \
	shabdakosh/banner.html \
	shabdakosh/wotd.js \
	shabdakosh/wotd_lib.py

BLOG_SRC = org/publish.el $(wildcard org/*.org)

build: site/shabdakosh/.built site/blog/.built

blog:
	emacs -Q --batch -l org/publish.el
	mkdir -p site/blog
	touch site/blog/.built

site/blog/.built: $(BLOG_SRC)
	emacs -Q --batch -l org/publish.el
	mkdir -p site/blog
	touch site/blog/.built

site/shabdakosh/.built: shabdakosh/build $(SHABDAKOSH_SRC)
	rm -r site/shabdakosh || true
	cp -R shabdakosh/output site/shabdakosh
	touch site/shabdakosh/.built

shabdakosh/build: $(SHABDAKOSH_SRC)
	$(MAKE) -C shabdakosh build

serve:
	python -m http.server -d site 8080
