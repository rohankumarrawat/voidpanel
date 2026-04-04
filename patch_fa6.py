#!/usr/bin/env python3
import os
import glob

fa4_line = '<link rel="stylesheet" href="/static/assets/vendor/font-awesome/css/font-awesome.min.css">'
fa6_snippet = (
    fa4_line
    + "\n    <!-- Font Awesome 6 -->\n"
    + '    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer">'
)

patched = 0
skipped = 0
for path in glob.glob("/Users/rohan/Downloads/voidpanel-main/templates/**/*.html", recursive=True):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()

    if fa4_line not in content:
        continue
    if "font-awesome/6" in content:
        skipped += 1
        continue

    content = content.replace(fa4_line, fa6_snippet, 1)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"Patched: {path}")
    patched += 1

print(f"\nDone: {patched} patched, {skipped} already had FA6.")
