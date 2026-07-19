#!/usr/bin/env python3
"""Render long-form guides from data/guides.json using the Python stdlib."""

from __future__ import annotations

import html
import json
import pathlib
import sys


ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SOURCE = ROOT / "data" / "guides.json"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def link(item: dict, class_name: str = "action") -> str:
    attrs = ' target="_blank" rel="noopener"' if item.get("external") else ""
    external_label = ' <span aria-hidden="true">↗</span>' if item.get("external") else ""
    return f'<a class="{class_name}" href="{esc(item["url"])}"{attrs}>{esc(item["label"])}{external_label}</a>'


def render_section(section: dict) -> str:
    out = [
        f'<section class="guide-section" id="{esc(section["id"])}">',
        f'  <p class="section-kicker">{esc(section["kicker"])}</p>',
        f'  <h2>{esc(section["heading"])}</h2>',
    ]
    paragraphs = section.get("paragraphs", [])
    if paragraphs:
        out.append('  <div class="prose">')
        out.extend(f"    <p>{esc(paragraph)}</p>" for paragraph in paragraphs)
        out.append("  </div>")

    cards = section.get("cards", [])
    if cards:
        out.append('  <div class="guide-cards">')
        for card in cards:
            out.extend(
                [
                    '    <article class="guide-card">',
                    f'      <h3>{esc(card["title"])}</h3>',
                    f'      <p>{esc(card["body"])}</p>',
                    "    </article>",
                ]
            )
        out.append("  </div>")

    places = section.get("places", [])
    if places:
        out.append('  <div class="place-grid">')
        for place in places:
            out.extend(
                [
                    '    <article class="place">',
                    f'      <p class="place-tag">{esc(place["tag"])}</p>',
                    f'      <h3>{esc(place["name"])}</h3>',
                    f'      <p>{esc(place["body"])}</p>',
                    f'      <a href="{esc(place["url"])}">Open on the map →</a>',
                    "    </article>",
                ]
            )
        out.append("  </div>")

    timeline = section.get("timeline", [])
    if timeline:
        out.append('  <div class="timeline">')
        for item in timeline:
            out.extend(
                [
                    '    <article class="timeline-item">',
                    f'      <p class="timeline-time">{esc(item["time"])}</p>',
                    "      <div>",
                    f'        <h3>{esc(item["title"])}</h3>',
                    f'        <p>{esc(item["body"])}</p>',
                    "      </div>",
                    "    </article>",
                ]
            )
        out.append("  </div>")

    bullets = section.get("bullets", [])
    if bullets:
        out.append('  <ul class="bullet-list">')
        out.extend(f"    <li>{esc(item)}</li>" for item in bullets)
        out.append("  </ul>")

    actions = section.get("actions", [])
    if actions:
        out.append('  <div class="actions">')
        out.extend(f"    {link(item)}" for item in actions)
        out.append("  </div>")

    if section.get("note"):
        out.append(f'  <aside class="note">{esc(section["note"])}</aside>')
    out.append("</section>")
    return "\n".join(out)


def schema_for(guide: dict) -> str:
    canonical = f'https://keowee.club/guides/{guide["slug"]}/'
    graph = [
        {
            "@type": "WebSite",
            "@id": "https://keowee.club/#website",
            "url": "https://keowee.club/",
            "name": "keowee.club",
            "alternateName": "The Unofficial Guide to Lake Keowee & Lake Jocassee",
            "inLanguage": "en-US",
        },
        {
            "@type": "Article",
            "@id": canonical + "#article",
            "headline": guide["title"],
            "description": guide["description"],
            "datePublished": guide["updated"],
            "dateModified": guide["updated"],
            "mainEntityOfPage": canonical,
            "author": {"@type": "Organization", "name": "keowee.club", "url": "https://keowee.club/"},
            "publisher": {"@type": "Organization", "name": "keowee.club", "url": "https://keowee.club/"},
            "image": "https://keowee.club/og.png",
            "inLanguage": "en-US",
            "about": ["Lake Keowee", "Boating", "Travel guide", "Oconee County", "Pickens County"],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://keowee.club/"},
                {"@type": "ListItem", "position": 2, "name": guide["title"], "item": canonical},
            ],
        },
        {
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
                }
                for item in guide["faq"]
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False).replace("</", "<\\/")


def render_guide(guide: dict) -> str:
    canonical = f'https://keowee.club/guides/{guide["slug"]}/'
    title_html = esc(guide["title"]).replace("Lake Keowee", "<em>Lake Keowee</em>")
    toc = "\n".join(
        f'          <li><a href="#{esc(section["id"])}">{esc(section["heading"])}</a></li>'
        for section in guide["sections"]
    )
    facts = "\n".join(
        "\n".join(
            [
                '        <div class="fact">',
                f'          <span class="fact-label">{esc(item["label"])}</span>',
                f'          <span class="fact-value">{esc(item["value"])}</span>',
                "        </div>",
            ]
        )
        for item in guide["quick_facts"]
    )
    sections = "\n\n".join(render_section(section) for section in guide["sections"])
    faq = "\n".join(
        "\n".join(
            [
                "      <details>",
                f'        <summary>{esc(item["question"])}</summary>',
                f'        <p>{esc(item["answer"])}</p>',
                "      </details>",
            ]
        )
        for item in guide["faq"]
    )
    sources = "\n".join(
        f'          <li><a href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["label"])}</a></li>'
        for item in guide["sources"]
    )
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(guide["seo_title"])}</title>
<meta name="description" content="{esc(guide["description"])}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#0A3A34">
<link rel="icon" type="image/png" sizes="512x512" href="/favicon.png?v=2">
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=2">
<meta property="og:type" content="article">
<meta property="og:site_name" content="keowee.club">
<meta property="og:title" content="{esc(guide["seo_title"].split(" | ")[0])}">
<meta property="og:description" content="{esc(guide["description"])}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://keowee.club/og.png">
<meta property="article:published_time" content="{esc(guide["updated"])}">
<meta property="article:modified_time" content="{esc(guide["updated"])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(guide["seo_title"].split(" | ")[0])}">
<meta name="twitter:description" content="{esc(guide["description"])}">
<meta name="twitter:image" content="https://keowee.club/og.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=Instrument+Sans:wght@400;500;600&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../assets/guide.css">
<script type="application/ld+json">
{schema_for(guide)}
</script>
</head>
<body>
<nav class="nav" aria-label="Main">
  <div class="nav-inner">
    <a class="wordmark" href="/" aria-label="Keowee Club home">
      <img class="pennant-logo" src="/brand/keoweeclub.svg" alt="Keowee Club" width="383" height="312">
    </a>
    <ul class="nav-links">
      <li><a href="/">Home</a></li>
      <li><a href="/eat-and-drink/">Eat &amp; Drink</a></li>
      <li><a href="/map/">Map</a></li>
      <li><a href="/lake-level/">Lake Level</a></li>
    </ul>
    <a class="nav-cta" href="/#dispatch">Get the Dispatch</a>
  </div>
</nav>

<header class="guide-hero">
  <div class="guide-hero-inner">
    <p class="breadcrumb"><a href="/">Keowee Club</a> &nbsp;→&nbsp; First-timer guide</p>
    <p class="eyebrow">{esc(guide["eyebrow"])}</p>
    <h1>{title_html}</h1>
    <p class="guide-dek">{esc(guide["dek"])}</p>
    <p class="guide-meta"><span>Updated {esc(guide["updated_display"])}</span><span>{esc(guide["reading_time"])}</span><span>Locally edited</span></p>
  </div>
</header>

<main>
  <div class="guide-shell">
    <aside class="toc" aria-label="Guide contents">
      <p class="toc-label">In this guide</p>
      <ol>
{toc}
      </ol>
      <a class="toc-cta" href="/map/">Open the lake map →</a>
    </aside>

    <article class="guide-content">
      <section class="quick-facts" aria-label="Lake Keowee quick facts">
{facts}
      </section>

{sections}
    </article>
  </div>

  <section class="faq" id="faq">
    <div class="faq-inner">
      <p class="section-kicker">Good questions</p>
      <h2>First-timer FAQ</h2>
{faq}
      <div class="sources">
        <h3>Official sources and further reading</h3>
        <ul>
{sources}
        </ul>
      </div>
    </div>
  </section>

  <section class="dispatch" id="dispatch">
    <div class="dispatch-inner">
      <p class="eyebrow">One useful lake email</p>
      <h2>The Dock <em>Dispatch</em></h2>
      <p>Lake conditions, places worth going, and what is happening around Keowee and Jocassee. Free, local, and never daily.</p>
      <form action="https://buttondown.com/api/emails/embed-subscribe/keowee" method="post" target="bd-frame">
        <input type="email" name="email" placeholder="you@somewhere.com" aria-label="Email address" required>
        <input type="hidden" name="embed" value="1">
        <button type="submit">Sign me up</button>
      </form>
      <iframe name="bd-frame" title="Newsletter signup" style="display:none" aria-hidden="true"></iframe>
      <p class="fine">Unsubscribe whenever. We would rather be on the water too.</p>
    </div>
  </section>
</main>

<footer>
  <div class="foot-inner">
    <span>Independent. Local. Unofficial.</span>
    <span><a href="/map/">Map</a> &nbsp;·&nbsp; <a href="/lake-level/">Lake levels</a> &nbsp;·&nbsp; <a href="/eat-and-drink/">Eat &amp; Drink</a></span>
  </div>
</footer>
<!-- Cloudflare Web Analytics -->
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "6ffce0786eb54943b7422d812178fe84"}}'></script>
<!-- End Cloudflare Web Analytics -->
<script defer src="https://cloud.umami.is/script.js" data-website-id="293cc55f-258d-4388-953c-41b49d0dd6ca"></script>
</body>
</html>
'''


def main() -> int:
    data = json.loads(SOURCE.read_text())
    guides = data.get("guides", [])
    if not guides:
        raise SystemExit("guides.json: guides must be a non-empty list")
    seen: set[str] = set()
    for guide in guides:
        slug = guide["slug"]
        if slug in seen:
            raise SystemExit(f"guides.json: duplicate slug {slug!r}")
        seen.add(slug)
        destination = ROOT / "guides" / slug / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_guide(guide))
        print(f"rendered guide: /guides/{slug}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
