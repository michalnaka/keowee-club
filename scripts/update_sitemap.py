#!/usr/bin/env python3
"""Regenerate sitemap.xml with lastmod dates from git history.

Each page's lastmod = the commit date of the last change to its file
(or, for rendered pages, its data sources). Run after shipping page
changes; /contact/ is intentionally excluded (noindex).
"""
import os, subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# url path -> files whose newest commit drives lastmod
PAGES = [
    ("/", ["index.html", "data/spots.json"]),
    ("/eat-and-drink/", ["eat-and-drink/index.html", "data/spots.json"]),
    ("/map/", ["map/index.html", "data/spots.json"]),
    ("/lake-level/", ["lake-level/index.html"]),
    ("/guides/lake-keowee-first-timer/", ["guides/lake-keowee-first-timer/index.html", "assets/guide.css"]),
    ("/depth/", ["depth/index.html", "depth/meta.json"]),
    ("/boat-ramps/", ["boat-ramps/index.html"]),
    ("/weekend/", ["weekend/index.html", "data/weekend.json"]),
    ("/swim/", ["swim/index.html"]),
    ("/facts/", ["facts/index.html"]),
]
FREQ = {"/weekend/": "weekly", "/lake-level/": "daily"}

def last_commit_date(paths):
    dates = []
    for p in paths:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", p],
                             cwd=REPO, capture_output=True, text=True).stdout.strip()
        if out:
            dates.append(out)
    return max(dates) if dates else None

lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for path, files in PAGES:
    d = last_commit_date(files)
    entry = f'  <url><loc>https://keowee.club{path}</loc>'
    if d:
        entry += f'<lastmod>{d}</lastmod>'
    if path in FREQ:
        entry += f'<changefreq>{FREQ[path]}</changefreq>'
    entry += '</url>'
    lines.append(entry)
    print(f'{path} -> {d}')
lines.append('</urlset>')
open(os.path.join(REPO, "sitemap.xml"), "w").write("\n".join(lines) + "\n")
print("sitemap.xml written")
