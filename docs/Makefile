OUTPUT_HTML = /tmp/README.html

docs:
	cat top.css > $(OUTPUT_HTML)
	pandoc -f markdown_github -t html header.md --template=template.html >> $(OUTPUT_HTML)
	pandoc -f markdown_github -t html releases.md --template=template.html >> $(OUTPUT_HTML)
	pandoc -f markdown_github -t html body.md --template=template.html --table-of-contents >> $(OUTPUT_HTML)
	python docs.py
