# Project guidance

## Product intent

keowee.club is an opinionated local guide, not a generic tourism directory.
Preserve its concise, knowledgeable, lightly playful voice and its handmade
visual identity. Favor useful local specificity over broad marketing copy.

## Architecture

Keep the site dependency-free and statically deployable unless a task clearly
requires an architectural change. The current Python renderer is the build
system for spot content; do not introduce a JavaScript framework incidentally.

`data/spots.json` is the source of truth for spots. After changing it or
`scripts/render_spots.py`, run:

```sh
python3 scripts/render_spots.py .
python3 scripts/validate_site.py
```

Commit the resulting generated HTML. Never hand-edit content inside generated
marker pairs in `index.html`, `eat-and-drink/index.html`, or `map/index.html`.

Shared navigation, brand tokens, sheet behavior, metadata, and analytics appear
on multiple pages. When changing one of these, audit every page rather than
assuming it is centralized.

## Verification

For every change:

1. Run `python3 scripts/validate_site.py`.
2. Run `python3 scripts/render_spots.py .` and confirm `git diff --check` passes.
3. Inspect the intended diff and ensure generated sections changed only when
   expected.
4. For visual changes, test approximately 390px and 1440px viewport widths.
5. For map or sheet changes, test keyboard operation, Escape-to-close, focus
   restoration, and a `/map/#spot-id` deep link.

Live lake and weather requests must fail gracefully. Avoid making the main page
content or navigation dependent on a third-party response.

## Branch and deployment model

`main` is production. `preview` is published at `/preview/`. The deployment
workflow checks out and publishes both branches on every push, so changes to
the workflow must continue to handle both intentionally.

Do not merge, overwrite, or discard work on `preview` without first comparing it
to `main` and confirming the desired disposition.
