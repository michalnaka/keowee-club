#!/usr/bin/env python3
"""Build the 3D depth-map asset for /depth/.

Stitches AWS open terrain tiles (terrarium encoding) for the Keowee-Jocassee
basin, detects the two flat lake surfaces in the DEM, carves a modeled lakebed
(chamfer distance-from-shore scaled to each lake's published max depth -- the
same approach GLOBathy uses), and bakes everything into depth/basin.png:

  R,G  packed elevation in 0.05 m units, offset -- see depth/meta.json
  B    water mask: 0 land, 120 Lake Keowee, 240 Lake Jocassee

Modeled depths are illustrative, not navigational. Requires numpy + pillow.
"""
import io, json, math, os, urllib.request
import numpy as np
from PIL import Image

ZOOM = 12
BBOX = (-83.08, 34.64, -82.75, 35.10)          # W, S, E, N
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
LAKES = [  # name, candidate open-water seeds (lon, lat), max depth m (published)
    ("keowee", [(-82.91, 34.78), (-82.92, 34.75), (-82.885, 34.80),
                (-82.90, 34.85), (-82.895, 34.72)], 47.2),        # 155 ft (SCDNR)
    ("jocassee", [(-82.92, 34.97), (-82.94, 34.99)], 107.0),      # 351 ft (SCDNR)
]
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "depth")
ELEV_OFF, ELEV_SCALE = 100.0, 0.05              # packed = (m + off) / scale


def tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def fetch_dem():
    x0, y0 = tile_xy(BBOX[0], BBOX[3], ZOOM)
    x1, y1 = tile_xy(BBOX[2], BBOX[1], ZOOM)
    tx0, ty0, tx1, ty1 = int(x0), int(y0), int(x1), int(y1)
    cols, rows = tx1 - tx0 + 1, ty1 - ty0 + 1
    dem = np.zeros((rows * 256, cols * 256), np.float32)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            with urllib.request.urlopen(TILE_URL.format(z=ZOOM, x=tx, y=ty), timeout=30) as r:
                px = np.asarray(Image.open(io.BytesIO(r.read())).convert("RGB"), np.float32)
            h = px[:, :, 0] * 256 + px[:, :, 1] + px[:, :, 2] / 256 - 32768
            dem[(ty - ty0) * 256:(ty - ty0 + 1) * 256,
                (tx - tx0) * 256:(tx - tx0 + 1) * 256] = h
    # geographic frame of the stitched image (web-mercator aligned)
    lon_w = tx0 / 2 ** ZOOM * 360 - 180
    lon_e = (tx1 + 1) / 2 ** ZOOM * 360 - 180
    lat_n = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty0 / 2 ** ZOOM))))
    lat_s = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty1 + 1) / 2 ** ZOOM))))
    return dem, (lon_w, lat_s, lon_e, lat_n)


def flood(band, seed):
    """Connected component of boolean `band` containing seed (iterative dilation)."""
    reg = np.zeros_like(band)
    reg[seed] = band[seed]
    while True:
        grown = reg.copy()
        grown[1:, :] |= reg[:-1, :]
        grown[:-1, :] |= reg[1:, :]
        grown[:, 1:] |= reg[:, :-1]
        grown[:, :-1] |= reg[:, 1:]
        grown &= band
        if (grown == reg).all():
            return reg
        reg = grown


def shore_distance(mask):
    """Exact Euclidean distance (px) to the nearest non-mask cell."""
    from scipy.ndimage import distance_transform_edt, gaussian_filter
    d = distance_transform_edt(mask).astype(np.float32)
    # soften so modeled contours read as organic basins, not stamped offsets
    d = gaussian_filter(d, sigma=2.0)
    d[~mask] = 0
    return d


def main():
    print("fetching tiles...")
    dem, frame = fetch_dem()
    rows, cols = dem.shape
    print(f"dem {cols}x{rows}, frame {frame}")
    mask_all = np.zeros(dem.shape, np.uint8)
    surfaces = {}
    for name, seeds, maxd in LAKES:
        lake, surf = None, None
        for lon, lat in seeds:
            px = int((lon - frame[0]) / (frame[2] - frame[0]) * cols)
            py = int((frame[3] - lat) / (frame[3] - frame[1]) * rows)
            s = float(dem[py, px])
            band = np.abs(dem - s) <= 2.5
            reg = flood(band, (py, px))
            if lake is None or reg.sum() > lake.sum():
                lake, surf = reg, s
        print(f"{name}: surface {surf:.1f} m, {lake.sum()} px")
        d = shore_distance(lake)
        depth = maxd * (d / d.max()) ** 0.8
        dem[lake] = surf - depth[lake]
        mask_all[lake] = 120 if name == "keowee" else 240
        surfaces[name] = {"surface_m": round(surf, 1), "max_depth_m": maxd}
    packed = np.clip((dem + ELEV_OFF) / ELEV_SCALE, 0, 65535).astype(np.uint32)
    img = np.zeros((rows, cols, 3), np.uint8)
    img[:, :, 0] = packed >> 8
    img[:, :, 1] = packed & 255
    img[:, :, 2] = mask_all
    os.makedirs(OUT_DIR, exist_ok=True)
    Image.fromarray(img).save(os.path.join(OUT_DIR, "basin.png"), optimize=True)
    meta = {"frame": frame, "width": cols, "height": rows,
            "elev_offset_m": ELEV_OFF, "elev_scale_m": ELEV_SCALE,
            "lakes": surfaces, "zoom": ZOOM,
            "note": "Lakebed is modeled from shoreline distance, not sonar."}
    json.dump(meta, open(os.path.join(OUT_DIR, "meta.json"), "w"), indent=1)
    print("wrote depth/basin.png + depth/meta.json")


if __name__ == "__main__":
    main()
