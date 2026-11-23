"""
flood_check.py – For each NHC advisory and each Lee County evacuation route
point, extract the maximum inundation class within a per-route search radius
using a rasterio window read (never loading the full raster).  Writes
data/processed/route_flood.csv and prints the first advisory that flagged each
route impassable under two rules:
  - impassable           : elevation-aware (flood depth lower bound >= road_height_ft)
  - impassable_depth_only: original rule (class >= 2, i.e. >1 ft above ground)

NOTE: road_height_ft for low causeways is an assumption (~3 ft); actual
roadway elevation varies and has not been surveyed here.  High-bridge
approaches can still flood from surge at the abutments — that is not modeled.
"""

import csv
import pathlib
import zipfile

import rasterio
from rasterio.windows import from_bounds

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ADVISORIES = [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 24, 25]
RAW_DIR = pathlib.Path("data/raw/inundation")
PROC_DIR = pathlib.Path("data/processed")
ROUTES_CSV = pathlib.Path("config/routes.csv")
OUT_CSV = PROC_DIR / "route_flood.csv"

# Default half-width of the sampling window in degrees (~0.001° ≈ 100 m).
HALF_DEG = 0.001

IMPASSABLE_CLASS = 2  # depth-only rule: class >= 2 means >1 ft above ground

# Lower-bound water depth (ft above ground) for each uint8 flood class.
# Class 0 = nodata/dry; class 1 = 0–1 ft; 2 = >1 ft; 3 = >3 ft; 4 = >6 ft; 5 = >9 ft.
CLASS_LOWER_BOUND = {0: 0, 1: 0, 2: 1, 3: 3, 4: 6, 5: 9}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_advisory(adv: int) -> pathlib.Path:
    """Extract the advisory zip into data/processed/adv{adv}/ if not already done."""
    out_dir = PROC_DIR / f"adv{adv}"
    if out_dir.exists() and any(out_dir.rglob("*.tif")):
        return out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / f"AL0922_{adv}_inundation.zip"
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out_dir)
    return out_dir


def find_tif(adv_dir: pathlib.Path) -> pathlib.Path:
    tifs = list(adv_dir.rglob("*.tif"))
    if not tifs:
        raise FileNotFoundError(f"No .tif found under {adv_dir}")
    return tifs[0]


def sample_point(src, lon: float, lat: float, half_deg: float = HALF_DEG) -> int:  # CHANGED
    """Return the max flood class within half_deg of (lon, lat), or 0 if outside raster."""
    bnd = src.bounds
    left = max(lon - half_deg, bnd.left)
    right = min(lon + half_deg, bnd.right)
    bottom = max(lat - half_deg, bnd.bottom)
    top = min(lat + half_deg, bnd.top)

    if left >= right or bottom >= top:
        return 0  # point outside raster

    win = from_bounds(left, bottom, right, top, src.transform)
    data = src.read(1, window=win)

    nodata = src.nodata if src.nodata is not None else 0
    valid = data[data != nodata]
    return int(valid.max()) if valid.size > 0 else 0


def load_routes() -> list[dict]:
    routes = []
    with open(ROUTES_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            routes.append({
                "name": row["name"].strip(),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "radius_deg": float(row.get("radius_m") or 100) / 100_000,
                "road_height_ft": float(row.get("road_height_ft") or 3),
            })
    return routes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    routes = load_routes()

    rows = []
    for adv in ADVISORIES:
        adv_dir = extract_advisory(adv)
        tif_path = find_tif(adv_dir)
        with rasterio.open(tif_path) as src:
            for route in routes:
                cls = sample_point(src, route["lon"], route["lat"], route["radius_deg"])
                depth_lb = CLASS_LOWER_BOUND.get(cls, 0)
                impassable = depth_lb >= route["road_height_ft"]
                impassable_depth_only = cls >= IMPASSABLE_CLASS
                rows.append({
                    "advisory": adv,
                    "route": route["name"],
                    "flood_class": cls,
                    "impassable": impassable,
                    "impassable_depth_only": impassable_depth_only,
                })

    fieldnames = ["advisory", "route", "flood_class", "impassable", "impassable_depth_only"]
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_CSV}")

    first_flag: dict[str, int] = {}
    for r in rows:
        if r["impassable"] and r["route"] not in first_flag:
            first_flag[r["route"]] = r["advisory"]

    print("\nFirst advisory flagging each route impassable (elevation-aware):")
    for route in routes:
        adv_flag = first_flag.get(route["name"])
        if adv_flag is not None:
            print(f"  {route['name']}: advisory {adv_flag}")
        else:
            print(f"  {route['name']}: never flagged")


if __name__ == "__main__":
    main()