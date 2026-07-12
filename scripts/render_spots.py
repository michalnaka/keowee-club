#!/usr/bin/env python3
"""Render the guide from data/spots.json into TWO pages:

  index.html               — featured spots only (curated homepage row) + "See all" link
  eat-and-drink/index.html — every visible spot, with town + category filter chips

Usage: python3 scripts/render_spots.py [repo-root]

Both files must contain marker pairs:
  <!-- spots:<section-id>:start --> ... <!-- spots:<section-id>:end -->
  <!-- spots-data:start --> ... <!-- spots-data:end -->
  <!-- spots-schema:start --> ... <!-- spots-schema:end -->
Everything between a pair is regenerated; edit data/spots.json, not the HTML.
Sections/spots with "hidden": true render nowhere. Spots with "featured": true
appear on the homepage (all visible spots appear on the guide page).
"""
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
data = json.loads((root / "data" / "spots.json").read_text())

TINTS = ["t1", "t2", "t3", "t4", "t5", "t6"]
TOWN_TINT = {"Seneca": "t1", "Salem": "t2", "Pendleton": "t3", "Hwy 11": "t4", "Walhalla": "t5", "Sunset": "t6"}
GUIDE_URL = "/eat-and-drink/"
FILTER_MIN = int(os.environ.get("FILTER_MIN", "6"))


def tint_for(value, semantic=None, offset=0):
    if semantic and value in semantic:
        return semantic[value]
    return TINTS[(sum(ord(c) for c in value) + offset) % len(TINTS)]


def town_class(s):
    return tint_for(s.get("town", ""), TOWN_TINT)


def cat_class(s):
    # Category pills are outlined (towns are filled) so the two dimensions
    # stay distinguishable even when hues repeat.
    return "tag-cat " + tint_for(s.get("category", ""), offset=3)


def pills(s):
    out = ['<div class="tags">']
    if s.get("town"):
        out.append(f'<span class="tag {town_class(s)}">{html.escape(s["town"])}</span>')
    if s.get("category"):
        out.append(f'<span class="tag {cat_class(s)}">{html.escape(s["category"])}</span>')
    out.append("</div>")
    return "".join(out)


def card(spot_id, s, num, rich=False):
    lines = [
        f'    <article class="card" data-spot="{spot_id}" data-town="{html.escape(s.get("town", ""))}" data-category="{html.escape(s.get("category", ""))}" tabindex="0" role="button" aria-haspopup="dialog" aria-label="More about {html.escape(html.unescape(s["name"]))}">',
        f'      <div class="card-art art-{s["art"]}" aria-hidden="true"><span class="card-num">{num:02d}</span><span class="card-emoji">{s["emoji"]}</span></div>',
        '      <div class="card-body">',
        f'        {pills(s)}',
        f'        <h3>{s["name"]}</h3>',
        f'        <p>{s["blurb"]}</p>',
    ]
    if rich:
        if s.get("tip"):
            lines.append(f'        <p class="tip"><b>Pro tip:</b> {s["tip"]}</p>')
        if s.get("badges"):
            lines.append(f'        <p class="badges">{" · ".join(s["badges"])}</p>')
    lines += [
        '        <span class="more" aria-hidden="true">Details <i>→</i></span>',
        "      </div>",
        "    </article>",
    ]
    return "\n".join(lines)


def chips_row(label, dim, values):
    out = [f'  <div class="filters" role="group" aria-label="Filter by {label.lower()}">']
    out.append(f'    <span class="filter-label">{label}</span>')
    out.append(f'    <button class="chip is-active" data-dim="{dim}" data-value="">All</button>')
    for v in values:
        out.append(f'    <button class="chip" data-dim="{dim}" data-value="{html.escape(v)}">{html.escape(v)}</button>')
    out.append("  </div>")
    return "\n".join(out)


def maps_url(s):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(s["maps"])


def island_entry(s):
    return {
        "name": s["name"],
        "emoji": s["emoji"],
        "art": s["art"],
        "town": s.get("town", ""),
        "townClass": town_class(s),
        "category": s.get("category", ""),
        "catClass": cat_class(s),
        "blurb": s["blurb"],
        "tip": s.get("tip"),
        "badges": s.get("badges") or [],
        "website": s.get("website"),
        "maps": maps_url(s),
        "lat": s.get("lat"),
        "lng": s.get("lng"),
    }


def replace_between(text, start, end, block):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker pair not found: {start}")
    return pattern.sub(lambda _: f"{start}\n{block}\n{end}" if block else f"{start}{end}", text)


def plain(s):
    return html.unescape(re.sub("<[^>]+>", "", s))


def schema_block(graph):
    return '<script type="application/ld+json">\n' + json.dumps(graph, indent=2, ensure_ascii=False) + "\n</script>"


def item_list(spots, list_id, name):
    items = []
    for pos, s in enumerate(spots, start=1):
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
    return {"@type": "ItemList", "@id": list_id, "name": name, "numberOfItems": len(items), "itemListElement": items}


WEBSITE_NODE = {
    "@type": "WebSite",
    "@id": "https://keowee.club/#website",
    "url": "https://keowee.club/",
    "name": "keowee.club",
    "alternateName": "The Unofficial Guide to Lake Keowee & Lake Jocassee",
    "description": "The unofficial guide to Lake Keowee and Lake Jocassee, South Carolina — where locals eat and drink, live lake levels, and a map of every spot worth docking at.",
    "inLanguage": "en-US",
}


def render_page(path, pick, rich, with_filters, see_all_total=None, schema_graph=None, nosnippet=False):
    page = path.read_text()
    island = {}
    for sec in data["sections"]:
        start, end = f"<!-- spots:{sec['id']}:start -->", f"<!-- spots:{sec['id']}:end -->"
        has_markers = start in page
        if sec.get("hidden"):
            if has_markers:
                page = replace_between(page, start, end, "")
            continue
        chosen = [(i, s) for i, s in enumerate(sec["spots"]) if not s.get("hidden") and pick(s)]
        # island entries exist even on pages without card sections (e.g. the map)
        for i, s in chosen:
            island[f"{sec['id']}-{i}"] = island_entry(s)
        if not has_markers:
            continue
        if not chosen:
            page = replace_between(page, start, end, "")
            continue
        n = len(chosen)
        shown_count = see_all_total if see_all_total is not None else n
        out = [f'<section class="section" id="{sec["id"]}"{" data-nosnippet" if nosnippet else ""}>']
        out.append(
            f'  <div class="section-head"><h2>{sec["title"]}</h2><span class="count">{shown_count:02d} spots</span></div>'
        )
        out.append(f'  <p class="section-sub">{sec["sub"]}</p>')
        if with_filters and n >= FILTER_MIN:
            towns, cats = [], []
            for _, s in chosen:
                t, c = s.get("town"), s.get("category")
                if t and t not in towns:
                    towns.append(t)
                if c and c not in cats:
                    cats.append(c)
            if len(towns) > 1:
                out.append(chips_row("Town", "town", towns))
            if len(cats) > 1:
                out.append(chips_row("Vibe", "category", cats))
        out.append('  <div class="cards">')
        for num, (i, s) in enumerate(chosen, start=1):
            out.append(card(f"{sec['id']}-{i}", s, num, rich=rich))
        out.append("  </div>")
        if see_all_total is not None and see_all_total > n:
            out.append(f'  <a class="see-all" href="{GUIDE_URL}">See all {see_all_total} spots <i>→</i></a>')
        out.append("</section>")
        page = replace_between(page, start, end, "\n".join(out))

    island_block = (
        '<script type="application/json" id="spotData">'
        + json.dumps(island, ensure_ascii=False).replace("</", "<\\/")
        + "</script>"
    )
    page = replace_between(page, "<!-- spots-data:start -->", "<!-- spots-data:end -->", island_block)
    if schema_graph is not None:
        page = replace_between(page, "<!-- spots-schema:start -->", "<!-- spots-schema:end -->", schema_block(schema_graph))
    path.write_text(page)
    return len(island)


visible_spots = [
    s for sec in data["sections"] if not sec.get("hidden")
    for s in sec["spots"] if not s.get("hidden")
]

n_home = render_page(
    root / "index.html",
    pick=lambda s: s.get("featured"),
    rich=False,
    with_filters=False,
    nosnippet=True,
    see_all_total=len(visible_spots),
    schema_graph={"@context": "https://schema.org", "@graph": [WEBSITE_NODE]},
)

n_guide = render_page(
    root / "eat-and-drink" / "index.html",
    pick=lambda s: True,
    rich=True,
    with_filters=True,
    schema_graph={
        "@context": "https://schema.org",
        "@graph": [
            WEBSITE_NODE,
            item_list(
                visible_spots,
                "https://keowee.club/eat-and-drink/#guide",
                "Where to Eat & Drink near Lake Keowee",
            ),
        ],
    },
)

n_map = render_page(
    root / "map" / "index.html",
    pick=lambda s: True,
    rich=False,
    with_filters=False,
    schema_graph=None,
)

print(f"rendered homepage ({n_home} featured) + guide page ({n_guide} spots) + map ({n_map} pins)")
