OUTPUT_HTML = /tmp/README.html

docs:
	cat top.css > $(OUTPUT_HTML)
	pandoc -f markdown_github-hard_line_breaks -t html header.md --template=template.html >> $(OUTPUT_HTML)
	pandoc -f markdown_github-hard_line_breaks -t html releases.md --template=template.html >> $(OUTPUT_HTML)
	pandoc -f markdown_github-hard_line_breaks -t html body.md --template=template.html --table-of-contents >> $(OUTPUT_HTML)
	python docs.py
