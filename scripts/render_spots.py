#!/usr/bin/env python3
"""Render the guide sections and structured data in index.html from data/spots.json.

Usage: python3 scripts/render_spots.py [repo-root]

index.html must contain marker pairs:
  <!-- spots:<section-id>:start --> ... <!-- spots:<section-id>:end -->
  <!-- spots-schema:start --> ... <!-- spots-schema:end -->
Everything between a pair is regenerated; edit data/spots.json, not the HTML.
"""
import html
import json
import pathlib
import re
import sys
import urllib.parse

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
data = json.loads((root / "data" / "spots.json").read_text())
index = root / "index.html"
page = index.read_text()


def card(s):
    out = ['    <article class="card">']
    out.append(f'      <div class="card-art art-{s["art"]}" aria-hidden="true">{s["emoji"]}</div>')
    out.append('      <div class="card-body">')
    out.append(f'        <span class="tag">{s["tag"]}</span>')
    out.append(f'        <h3>{s["name"]}</h3>')
    out.append(f'        <p>{s["blurb"]}</p>')
    if s.get("tip"):
        out.append(f'        <p class="tip"><b>Pro tip:</b> {s["tip"]}</p>')
    if s.get("badges"):
        out.append(f'        <p class="badges">{" · ".join(s["badges"])}</p>')
    links = []
    if s.get("website"):
        links.append(f'<a href="{s["website"]}" target="_blank" rel="noopener">Website</a>')
    query = urllib.parse.quote(s["maps"])
    links.append(
        f'<a href="https://www.google.com/maps/search/?api=1&amp;query={query}" target="_blank" rel="noopener">Directions</a>'
    )
    out.append(f'        <div class="card-links">{"".join(links)}</div>')
    out.append("      </div>")
    out.append("    </article>")
    return "\n".join(out)


def replace_between(text, start, end, block):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker pair not found: {start}")
    return pattern.sub(lambda _: f"{start}\n{block}\n{end}", text)


total = 0
for sec in data["sections"]:
    n = len(sec["spots"])
    total += n
    out = [f'<section class="section" id="{sec["id"]}">']
    out.append(
        f'  <div class="section-head"><h2>{sec["title"]}</h2><span class="count">{n:02d} spots</span></div>'
    )
    out.append(f'  <p class="section-sub">{sec["sub"]}</p>')
    out.append('  <div class="cards">')
    out.extend(card(s) for s in sec["spots"])
    out.append("  </div>")
    out.append("</section>")
    page = replace_between(page, f"<!-- spots:{sec['id']}:start -->", f"<!-- spots:{sec['id']}:end -->", "\n".join(out))

# Structured data: WebSite + ItemList of every spot
def plain(s):
    return html.unescape(re.sub("<[^>]+>", "", s))

items, pos = [], 0
for sec in data["sections"]:
    for s in sec["spots"]:
        pos += 1
        item = {
            "@type": s.get("schema", "LocalBusiness"),
            "name": plain(s["name"]),
            "description": plain(s["blurb"]),
        }
        addr = {"@type": "PostalAddress", "addressRegion": s.get("region", "SC")}
        if s.get("locality"):
            addr["addressLocality"] = s["locality"]
        item["address"] = addr
        if s.get("website"):
            item["url"] = s["website"]
        items.append({"@type": "ListItem", "position": pos, "item": item})

graph = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "WebSite",
            "@id": "https://keowee.club/#website",
            "url": "https://keowee.club/",
            "name": "keowee.club",
            "alternateName": "The Unofficial Guide to Lake Keowee",
            "description": "Where to eat, drink, swim, and wander around Lake Keowee, Seneca & Salem, South Carolina.",
            "inLanguage": "en-US",
        },
        {
            "@type": "ItemList",
            "@id": "https://keowee.club/#guide",
            "name": "Lake Keowee Guide: Where to Eat, Drink, and Play",
            "numberOfItems": total,
            "itemListElement": items,
        },
    ],
}
schema_block = (
    '<script type="application/ld+json">\n' + json.dumps(graph, indent=2, ensure_ascii=False) + "\n</script>"
)
page = replace_between(page, "<!-- spots-schema:start -->", "<!-- spots-schema:end -->", schema_block)

index.write_text(page)
print(f"rendered {total} spots into {index}")
