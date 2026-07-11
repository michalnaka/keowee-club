#!/usr/bin/env python3
"""Render the guide sections and structured data in index.html from data/spots.json.

Usage: python3 scripts/render_spots.py [repo-root]

index.html must contain marker pairs:
  <!-- spots:<section-id>:start --> ... <!-- spots:<section-id>:end -->
  <!-- spots-data:start --> ... <!-- spots-data:end -->
  <!-- spots-schema:start --> ... <!-- spots-schema:end -->
Everything between a pair is regenerated; edit data/spots.json, not the HTML.
Sections with "hidden": true render nothing (their spots stay in the data file).
Card faces are minimal; full details live in the JSON data island and open
in the detail sheet (see the inline script in index.html).
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


def card(spot_id, s, num):
    return "\n".join(
        [
            f'    <article class="card" data-spot="{spot_id}" tabindex="0" role="button" aria-haspopup="dialog" aria-label="More about {html.escape(html.unescape(s["name"]))}">',
            f'      <div class="card-art art-{s["art"]}" aria-hidden="true"><span class="card-num">{num:02d}</span><span class="card-emoji">{s["emoji"]}</span></div>',
            '      <div class="card-body">',
            f'        <span class="tag">{s["tag"]}</span>',
            f'        <h3>{s["name"]}</h3>',
            f'        <p>{s["blurb"]}</p>',
            '        <span class="more" aria-hidden="true">Details <i>→</i></span>',
            "      </div>",
            "    </article>",
        ]
    )


def replace_between(text, start, end, block):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker pair not found: {start}")
    return pattern.sub(lambda _: f"{start}\n{block}\n{end}" if block else f"{start}{end}", text)


def maps_url(s):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(s["maps"])


total = 0
island = {}
for sec in data["sections"]:
    start, end = f"<!-- spots:{sec['id']}:start -->", f"<!-- spots:{sec['id']}:end -->"
    if sec.get("hidden"):
        page = replace_between(page, start, end, "")
        continue
    visible = [(i, s) for i, s in enumerate(sec["spots"]) if not s.get("hidden")]
    n = len(visible)
    total += n
    out = [f'<section class="section" id="{sec["id"]}">']
    out.append(
        f'  <div class="section-head"><h2>{sec["title"]}</h2><span class="count">{n:02d} spots</span></div>'
    )
    out.append(f'  <p class="section-sub">{sec["sub"]}</p>')
    out.append('  <div class="cards">')
    for num, (i, s) in enumerate(visible, start=1):
        spot_id = f"{sec['id']}-{i}"
        out.append(card(spot_id, s, num))
        island[spot_id] = {
            "name": s["name"],
            "emoji": s["emoji"],
            "art": s["art"],
            "tag": s["tag"],
            "blurb": s["blurb"],
            "tip": s.get("tip"),
            "badges": s.get("badges") or [],
            "website": s.get("website"),
            "maps": maps_url(s),
        }
    out.append("  </div>")
    out.append("</section>")
    page = replace_between(page, start, end, "\n".join(out))

# Data island for the detail sheet
island_block = (
    '<script type="application/json" id="spotData">'
    + json.dumps(island, ensure_ascii=False).replace("</", "<\\/")
    + "</script>"
)
page = replace_between(page, "<!-- spots-data:start -->", "<!-- spots-data:end -->", island_block)


# Structured data: WebSite + ItemList of every visible spot
def plain(s):
    return html.unescape(re.sub("<[^>]+>", "", s))

items, pos = [], 0
for sec in data["sections"]:
    if sec.get("hidden"):
        continue
    for s in sec["spots"]:
        if s.get("hidden"):
            continue
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
            "name": "Lake Keowee Guide: Where to Eat and Drink",
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
print(f"rendered {total} visible spots into {index}")
