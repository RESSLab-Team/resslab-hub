"""Fail if the built docs site has a dead relative link or image.

Zensical --strict checks the links between pages. This also checks images
and other files, on the HTML it wrote. Copied from the ENAC-IT4R wiki.
Run from docs/ by `make docs` and by the Dockerfile:
python3 scripts/check-links.py site
"""

import html
import pathlib
import re
import sys
import urllib.parse

site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site")
bad = total = 0
for page in site.rglob("*.html"):
    for ref in re.findall(r'(?:href|src)="([^"#?]+)', page.read_text()):
        ref = html.unescape(ref)
        if ref.startswith(("http", "mailto:", "/", "javascript", "&", "data:")):
            continue
        total += 1
        target = (page.parent / urllib.parse.unquote(ref)).resolve()
        if not (target.exists() or (target / "index.html").exists()):
            bad += 1
            print(f"{page.relative_to(site)} -> {ref}")
print(f"{total} relative links, {bad} broken")
sys.exit(1 if bad else 0)
