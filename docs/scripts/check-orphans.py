"""Fail if a file of the docs is neither in the nav nor linked from a page that is.

Files under a path of `exclude_docs` (zensical.toml) are not built, so they
are skipped. Copied from the ENAC-IT4R wiki. A regex on the Markdown link
forms the docs use ([x](path), [x](<path>), src="path"), not a parser.
Run from docs/ by `make docs` and by the Dockerfile:
python3 scripts/check-orphans.py
"""

import os
import pathlib
import re
import sys
import tomllib
import unicodedata
import urllib.parse

LINK = re.compile(r'\]\(<([^>]+)>|\]\(([^)<\s]+)|(?:src|href)=["\']([^"\']+)')

config = tomllib.loads(pathlib.Path("zensical.toml").read_text())["project"]
docs = pathlib.Path(config["docs_dir"])
excluded = [
    line.strip().strip("/")
    for line in config.get("exclude_docs", "").splitlines()
    if line.strip()
]


def nfc(path):
    # macOS stores file names decomposed (NFD); links are composed (NFC).
    return unicodedata.normalize("NFC", os.path.normpath(path))


def is_excluded(path):
    return any(path == e or path.startswith(e + "/") for e in excluded)


def nav_files(node):
    if isinstance(node, str):
        return [node]
    items = node.values() if isinstance(node, dict) else node
    return [f for item in items for f in nav_files(item)]


files = {
    nfc(p.relative_to(docs))
    for p in docs.rglob("*")
    if p.is_file() and not p.name.startswith(".")
}
files = {f for f in files if not is_excluded(f)}
seen = set()
todo = [nfc(f) for f in nav_files(config["nav"])]
while todo:
    page = todo.pop()
    if page in seen or page not in files:
        continue
    seen.add(page)
    if not page.endswith(".md"):
        continue
    for groups in LINK.findall((docs / page).read_text()):
        ref = urllib.parse.unquote(next(g for g in groups if g)).split("#")[0]
        if ref and "://" not in ref and not ref.startswith("mailto:"):
            todo.append(nfc(os.path.join(os.path.dirname(page), ref)))

orphans = sorted(files - seen)
for f in orphans:
    print(f"{docs / f} is neither in the nav nor linked from a page that is")
print(f"{len(files)} files, {len(orphans)} orphans")
sys.exit(1 if orphans else 0)
