"""Diagnostic: max flood class at growing distances from each route point (advisory 24)."""
import csv, glob
import rasterio
from rasterio.windows import from_bounds

tif = glob.glob("data/processed/adv24/**/*.tif", recursive=True)[0]
radii = {"100m": 0.001, "300m": 0.003, "600m": 0.006, "1km": 0.01}

with open("config/routes.csv", encoding="utf-8-sig") as f:
    routes = list(csv.DictReader(f))

with rasterio.open(tif) as src:
    for r in routes:
        lat, lon = float(r["lat"]), float(r["lon"])
        out = []
        for label, d in radii.items():
            win = from_bounds(lon - d, lat - d, lon + d, lat + d, src.transform)
            data = src.read(1, window=win)
            out.append(f"{label}={int(data.max())}")
        print(f"{r['name']:42s}", "  ".join(out))