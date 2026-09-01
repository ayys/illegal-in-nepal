build:
	make -C shabdakosh build
	rm -r site/shabdakosh || true
	cp -R shabdakosh/output site/shabdakosh
	emacs -Q --batch -l org/publish.el

blog:
	emacs -Q --batch -l org/publish.el

serve:
	python -m http.server -d site 8080
