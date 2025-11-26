build:
	make -C shabdakosh build
	mv shabdakosh/output site/shabdakosh



serve:
	python -m http.server -d site 8080
