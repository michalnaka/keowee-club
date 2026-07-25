#!/usr/bin/env python3
"""Prepare an assembled static-site directory for the /preview/ mount point."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PREVIEW_PREFIX = "/preview/"
ROBOTS_META = '<meta name="robots" content="noindex, nofollow">\n'
ROOT_RELATIVE_ATTRIBUTE = re.compile(
    r'(?P<prefix>\b(?:href|src|action)\s*=\s*["\'])(?P<path>/(?!/|preview(?:/|["\'])))',
    re.IGNORECASE,
)
CHARSET_META = re.compile(r'(<meta\s+charset=["\'][^"\']+["\']>\s*)', re.IGNORECASE)


def prepare_html(path: Path) -> int:
    text = path.read_text()

    if 'name="robots"' not in text.lower():
        text, insertions = CHARSET_META.subn(r"\1" + ROBOTS_META, text, count=1)
        if insertions != 1:
            raise ValueError(f"{path}: could not find a charset meta tag")

    text, replacements = ROOT_RELATIVE_ATTRIBUTE.subn(
        lambda match: f'{match.group("prefix")}{PREVIEW_PREFIX}',
        text,
    )

    leaked = ROOT_RELATIVE_ATTRIBUTE.search(text)
    if leaked:
        raise ValueError(f"{path}: root-relative URL escaped preview rebasing")

    path.write_text(text)
    return replacements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_dir", type=Path, help="Assembled preview directory")
    args = parser.parse_args()

    site_dir = args.site_dir.resolve()
    if not site_dir.is_dir():
        parser.error(f"{site_dir} is not a directory")

    html_files = sorted(site_dir.rglob("*.html"))
    if not html_files:
        parser.error(f"{site_dir} contains no HTML files")

    replacements = sum(prepare_html(path) for path in html_files)
    print(
        f"prepared {len(html_files)} preview pages: "
        f"rebased {replacements} local URLs and added noindex metadata"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
