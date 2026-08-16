#!/usr/bin/env python3
"""Append the current Duke Energy lake levels to data/level-history.json.

Run by .github/workflows/level-log.yml on a schedule. Each entry:
  {"t": "2026-07-23T18:17Z", "k": 96.9, "j": 89.2}
where k/j are percent-of-full-pond for Keowee/Jocassee (Duke's "Actual",
a 100-ft local gauge where 100 = full pond, so feet below full = 100 - value).
Exits 0 without writing if the API is unreachable, so the workflow only
commits when there is a fresh reading.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - stdlib since 3.9, fall back to UTC
    ET = timezone.utc

API = "https://api.hydro-derived.duke-energy.app/lakes/current-level"
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "level-history.json")
PAGE = os.path.join(ROOT, "lake-level", "index.html")
FULL_POND_FT = {"KEOWEE": 800, "JOCASSEE": 1110}


def replace_between(text, start, end, body):
    """Swap the content between two marker comments. Returns text unchanged
    if either marker is missing, so a page refactor can never break the bot."""
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        return text
    return text[: i + len(start)] + body + text[j:]


def down_ft(actual):
    """Duke's 'Actual' is a 100-ft gauge where 100 = full pond."""
    return max(0.0, round(100 - actual, 1))


def fmt(n):
    """1100.0 -> '1,100', 796.6 -> '796.6'."""
    s = f"{n:,.1f}"
    return s[:-2] if s.endswith(".0") else s


def phrase(name, actual):
    """'3.5 ft below full pond (796.5 ft)' — the shape Google shows in a snippet."""
    d = down_ft(actual)
    elev = round(FULL_POND_FT[name] - d, 1)
    if d <= 0.05:
        return f"at full pond ({fmt(FULL_POND_FT[name])} ft)", d, elev
    return f"{d} ft below full pond ({fmt(elev)} ft)", d, elev


def reading_date(raw):
    """Duke stamps each reading, e.g. '2026-08-13T19:04:37'. Their gauges update
    irregularly (Keowee can lag Jocassee by days), so we quote their date rather
    than ours — the number is only as fresh as the gauge that reported it."""
    try:
        d = datetime.fromisoformat(str(raw).replace("Z", ""))
    except (TypeError, ValueError):
        return None
    return f"{d:%b} {d.day}, {d.year}"


def patch_page(readings):
    """Write the current reading into the page's meta description and a static
    line of body text, so crawlers see a number instead of a JS placeholder.
    `readings` maps lake name -> (actual, duke_date_string)."""
    if not os.path.exists(PAGE) or "KEOWEE" not in readings:
        return False
    html = original = open(PAGE).read()
    k_actual, k_raw = readings["KEOWEE"]
    k_phrase, _, _ = phrase("KEOWEE", k_actual)
    k_date = reading_date(k_raw)
    j = readings.get("JOCASSEE")
    if j:
        _, j_down, j_elev = phrase("JOCASSEE", j[0])
        j_date = reading_date(j[1])

    desc = f"Lake Keowee is {k_phrase}"
    desc += f", per Duke Energy's gauge on {k_date}." if k_date else ", live from Duke Energy."
    if j:
        desc += f" Jocassee is {j_down} ft down."
    desc += " History chart plus what the level means for boat ramps."
    html = replace_between(
        html, "<!-- live-desc:start -->", "<!-- live-desc:end -->",
        f'<meta name="description" content="{desc}">')

    body = f"<b>Latest reading:</b> Lake Keowee is {k_phrase}"
    body += f", from Duke Energy's gauge on {k_date}." if k_date else "."
    if j:
        body += f" Lake Jocassee is {j_down} ft below its 1,110 ft full pond ({fmt(j_elev)} ft)"
        body += f", reported {j_date}." if j_date else "."
    body += " Duke's two gauges report on their own schedules, so one can lag the other; we check four times a day."
    html = replace_between(
        html, "<!-- live-static:start -->", "<!-- live-static:end -->",
        f'<p class="live-static">{body}</p>')

    if html == original:
        return False
    open(PAGE, "w").write(html)
    return True

def main():
    try:
        with urllib.request.urlopen(API, timeout=30) as r:
            lakes = json.load(r)
    except Exception as e:
        print(f"api unavailable, skipping: {e}")
        return 0
    vals, readings = {}, {}
    for l in lakes:
        if l.get("LakeName") in ("KEOWEE", "JOCASSEE"):
            try:
                vals[l["LakeName"]] = round(float(l["Actual"]), 2)
                readings[l["LakeName"]] = (vals[l["LakeName"]], l.get("Date"))
            except (TypeError, ValueError):
                pass
    if "KEOWEE" not in vals:
        print("no keowee reading, skipping")
        return 0
    hist = []
    if os.path.exists(OUT):
        hist = json.load(open(OUT))
    entry = {"t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
             "k": vals.get("KEOWEE"), "j": vals.get("JOCASSEE")}
    hist.append(entry)
    json.dump(hist, open(OUT, "w"), separators=(",", ":"))
    print(f"logged {entry}")
    if patch_page(readings):
        print("patched lake-level page with current readings")
    return 0

if __name__ == "__main__":
    sys.exit(main())
