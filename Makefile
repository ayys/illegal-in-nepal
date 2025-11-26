build:
	make -C shabdakosh build
	rm -r site/shabdakosh || true
	cp -R shabdakosh/output site/shabdakosh



serve:
	python -m http.server -d site 8080
