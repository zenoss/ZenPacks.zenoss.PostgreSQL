#! /usr/bin/env python

import re
rx_comments = re.compile(r'/\*.*?\*/\n', re.DOTALL)
rx_blanks = re.compile(r'\n\n\n')

try:

    with open('/tmp/README.html', 'r') as file:
        html = file.read()

    # Add class to images
    html = re.sub('<img src=', '<img class="gallery" src=', html)
    html = re.sub('screenshots/', '/sites/default/files/zenpack/MySQL Monitor/', html)
    with open('/tmp/README.html', 'w') as file:
        file.write(html)

except Exception as ex:
    print "Error filtering html"
