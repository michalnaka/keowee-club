#!/usr/bin/env python3
"""Bake major highways for the /depth/ scene into depth/roads.json.

Queries OSM Overpass for the named routes inside the basin frame,
simplifies geometry to ~2 decimal-degree*1e-4 tolerance, and writes
[{ref, pts:[[lon,lat],...]}, ...]. Run rarely; roads don't move.
"""
import json, os, time, urllib.request, urllib.parse

FRAME = (-83.09028625488281, 34.652132475112666, -82.76206970214844, 35.088169640679645)
REFS = {"SC 11", "SC 130", "SC 133", "SC 183", "SC 28", "US 123", "US 76", "US 178"}
OUT = os.path.join(os.path.dirname(__file__), "..", "depth", "roads.json")

q = f"""
[out:json][timeout:150];
way["highway"~"^(motorway|trunk|primary|secondary)$"]["ref"]({FRAME[1]},{FRAME[0]},{FRAME[3]},{FRAME[2]});
out geom;
"""
MIRRORS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
data = None
for m in MIRRORS:
    try:
        req = urllib.request.Request(
            m, data=urllib.parse.urlencode({"data": q}).encode(),
            headers={"User-Agent": "keowee.club depth map builder"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        print("mirror ok:", m)
        break
    except Exception as e:
        print("mirror failed:", m, e)
        time.sleep(3)
if data is None:
    raise SystemExit("all Overpass mirrors failed")

def simplify(pts, tol=2.5e-4):
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for p in pts[1:-1]:
        if abs(p[0]-out[-1][0]) + abs(p[1]-out[-1][1]) >= tol:
            out.append(p)
    out.append(pts[-1])
    return out

roads = []
kept = set()
for el in data.get("elements", []):
    ref = el.get("tags", {}).get("ref", "")
    ref_main = ref.split(";")[0].strip()
    if ref_main not in REFS:
        continue
    pts = [[round(g["lon"], 5), round(g["lat"], 5)] for g in el.get("geometry", [])]
    if len(pts) < 2:
        continue
    roads.append({"ref": ref_main, "pts": simplify(pts)})
    kept.add(ref_main)

json.dump(roads, open(OUT, "w"), separators=(",", ":"))
n = sum(len(r["pts"]) for r in roads)
print(f"{len(roads)} ways, {n} points, refs: {sorted(kept)}, {os.path.getsize(OUT)} bytes")
