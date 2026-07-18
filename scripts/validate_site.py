#!/usr/bin/env python3
"""Validate source data and basic static-site contracts using the stdlib."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
HTML_FILES = (
    ROOT / "index.html",
    ROOT / "eat-and-drink" / "index.html",
    ROOT / "map" / "index.html",
    ROOT / "lake-level" / "index.html",
)
REQUIRED_SPOT_FIELDS = ("name", "emoji", "art", "blurb", "maps")
VALID_ARTS = {"a", "b", "c", "d"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.titles = 0
        self.h1s = 0
        self.canonicals = 0
        self.main_navs = 0
        self.ids: set[str] = set()
        self.duplicate_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)
        if tag == "title":
            self.titles += 1
        elif tag == "h1":
            self.h1s += 1
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonicals += 1
        elif tag == "nav" and values.get("aria-label") == "Main":
            self.main_navs += 1


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_spots(errors: list[str]) -> tuple[int, int]:
    source = ROOT / "data" / "spots.json"
    try:
        data = json.loads(source.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{source.relative_to(ROOT)}: {exc}")
        return 0, 0

    sections = data.get("sections")
    require(isinstance(sections, list) and bool(sections), "spots.json: sections must be a non-empty list", errors)
    if not isinstance(sections, list):
        return 0, 0

    section_ids: set[str] = set()
    spot_names: set[str] = set()
    visible = 0
    mappable = 0

    for section_index, section in enumerate(sections):
        label = f"spots.json: sections[{section_index}]"
        require(isinstance(section, dict), f"{label} must be an object", errors)
        if not isinstance(section, dict):
            continue
        section_id = section.get("id")
        require(isinstance(section_id, str) and bool(section_id), f"{label}.id is required", errors)
        if isinstance(section_id, str):
            require(section_id not in section_ids, f"spots.json: duplicate section id {section_id!r}", errors)
            section_ids.add(section_id)
        spots = section.get("spots")
        require(isinstance(spots, list), f"{label}.spots must be a list", errors)
        if not isinstance(spots, list):
            continue

        for spot_index, spot in enumerate(spots):
            spot_label = f"spots.json: {section_id or section_index}[{spot_index}]"
            require(isinstance(spot, dict), f"{spot_label} must be an object", errors)
            if not isinstance(spot, dict):
                continue
            for field in REQUIRED_SPOT_FIELDS:
                require(bool(spot.get(field)), f"{spot_label}.{field} is required", errors)
            name = spot.get("name")
            if isinstance(name, str):
                require(name not in spot_names, f"spots.json: duplicate spot name {name!r}", errors)
                spot_names.add(name)
            require(spot.get("art") in VALID_ARTS, f"{spot_label}.art must be one of {sorted(VALID_ARTS)}", errors)

            lat, lng = spot.get("lat"), spot.get("lng")
            require((lat is None) == (lng is None), f"{spot_label}: lat and lng must be supplied together", errors)
            if lat is not None and lng is not None:
                require(isinstance(lat, (int, float)) and -90 <= lat <= 90, f"{spot_label}.lat is invalid", errors)
                require(isinstance(lng, (int, float)) and -180 <= lng <= 180, f"{spot_label}.lng is invalid", errors)
                if not spot.get("hidden"):
                    mappable += 1

            website = spot.get("website")
            if website:
                parsed = urlparse(website)
                require(parsed.scheme == "https" and bool(parsed.netloc), f"{spot_label}.website must be an https URL", errors)

            if not section.get("hidden") and not spot.get("hidden"):
                visible += 1

    return visible, mappable


def validate_pages(errors: list[str]) -> None:
    for path in HTML_FILES:
        relative = path.relative_to(ROOT)
        require(path.exists(), f"{relative}: file is missing", errors)
        if not path.exists():
            continue
        parser = PageParser()
        try:
            parser.feed(path.read_text())
            parser.close()
        except Exception as exc:  # HTMLParser can surface malformed declarations.
            errors.append(f"{relative}: unable to parse HTML: {exc}")
            continue
        require(parser.titles == 1, f"{relative}: expected exactly one <title>", errors)
        require(parser.h1s == 1, f"{relative}: expected exactly one <h1>", errors)
        require(parser.canonicals == 1, f"{relative}: expected exactly one canonical link", errors)
        require(parser.main_navs == 1, f"{relative}: expected one main navigation", errors)
        require(not parser.duplicate_ids, f"{relative}: duplicate ids {sorted(parser.duplicate_ids)}", errors)


def main() -> int:
    errors: list[str] = []
    visible, mappable = validate_spots(errors)
    validate_pages(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"validation failed with {len(errors)} error(s)")
        return 1
    print(f"validation passed: {visible} guide spots, {mappable} mapped spots, {len(HTML_FILES)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
