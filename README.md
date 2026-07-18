# keowee.club

The unofficial guide to Lake Keowee and Lake Jocassee: local food and drink,
places to get on the water, nearby sights, and live lake conditions.

The production site is published at [keowee.club](https://keowee.club/).

## Project shape

This is a dependency-free static site hosted on GitHub Pages.

- `index.html` — homepage and featured spots
- `eat-and-drink/index.html` — full dining guide
- `map/index.html` — Leaflet map of places in the guide
- `lake-level/index.html` — live Keowee and Jocassee readings
- `data/spots.json` — canonical spot content and coordinates
- `scripts/render_spots.py` — renders spot cards, client-side data, and schema
- `brand/` — source and exported brand artwork

Spot-related sections inside the HTML files are generated. Edit
`data/spots.json`, then regenerate the pages; do not hand-edit content between
`<!-- spots:* -->`, `<!-- spots-data:* -->`, or `<!-- spots-schema:* -->`
markers.

## Local development

The site has no package installation or build step.

```sh
python3 scripts/render_spots.py .
python3 scripts/validate_site.py
python3 -m http.server 8000
```

Open <http://localhost:8000>. Before committing a data or renderer change,
confirm that rendering is deterministic:

```sh
python3 scripts/render_spots.py .
git diff --check
git diff --exit-code
```

The final command should be clean when generated pages were already committed.

## Publishing

The GitHub Pages workflow publishes:

- `main` at the site root
- `preview` at `/preview/`

A push to either branch rebuilds and republishes both. Pull requests run the
validation workflow, which checks the data model, HTML structure, and whether
the committed generated output is current.

## External services

- Duke Energy-derived lake-level API
- National Weather Service observations
- Leaflet with CARTO/OpenStreetMap tiles
- Buttondown newsletter signup
- Cloudflare Web Analytics and Umami

Live data is an enhancement: pages should retain useful static fallback copy
when an external service is unavailable.
