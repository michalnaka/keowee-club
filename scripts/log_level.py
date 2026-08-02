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

API = "https://api.hydro-derived.duke-energy.app/lakes/current-level"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "level-history.json")

def main():
    try:
        with urllib.request.urlopen(API, timeout=30) as r:
            lakes = json.load(r)
    except Exception as e:
        print(f"api unavailable, skipping: {e}")
        return 0
    vals = {}
    for l in lakes:
        if l.get("LakeName") in ("KEOWEE", "JOCASSEE"):
            try:
                vals[l["LakeName"]] = round(float(l["Actual"]), 2)
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
    return 0

if __name__ == "__main__":
    sys.exit(main())
