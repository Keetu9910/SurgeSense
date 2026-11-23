"""
deadlines.py – Compute hurricane evacuation deadlines for Lee County routes.

For each route, finds:
  - surge_flag_utc  : issued time of the first NHC advisory where the route
                      was marked impassable by surge (from route_flood.csv).
  - wind_arrival_utc: earliest 6-hourly best-track time whose 34-kt polygon
                      contains the route point (6-h resolution per NHC data).
  - wind_deadline_utc: wind_arrival_utc - CLEARANCE_HOURS.
  - lead_hours      : wind_deadline_utc - surge_flag_utc (positive means
                      SurgeSense flagged the route before the wind-only deadline).

Writes data/processed/deadlines.csv, docs/timeline.png, and prints the table.
"""

import pathlib
import tempfile
import zipfile
from datetime import datetime, timezone

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from shapely.geometry import Point

matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CLEARANCE_HOURS = 41  # Lee County worst-case in-county clearance time

ROUTES_CSV     = pathlib.Path("config/routes.csv")
ADVISORIES_CSV = pathlib.Path("config/advisories.csv")
FLOOD_CSV      = pathlib.Path("data/processed/route_flood.csv")
BEST_TRACK_ZIP = pathlib.Path("data/raw/nhc/al092022_best_track.zip")

PROC_DIR = pathlib.Path("data/processed")
DOCS_DIR = pathlib.Path("docs")
OUT_CSV  = PROC_DIR / "deadlines.csv"
OUT_PNG  = DOCS_DIR / "timeline.png"

IAN_LANDFALL_UTC = datetime(2022, 9, 28, 19, 0, tzinfo=timezone.utc)

# SYNOPTIME field format in the NHC radii shapefile
SYNOPTIME_FMT = "%Y%m%d%H"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_routes() -> pd.DataFrame:
    df = pd.read_csv(ROUTES_CSV, encoding="utf-8-sig")
    df["name"] = df["name"].str.strip()
    return df


def load_advisories() -> pd.DataFrame:
    df = pd.read_csv(ADVISORIES_CSV)
    df["issued_utc"] = pd.to_datetime(df["issued_utc"], utc=True)
    return df


def load_flood() -> pd.DataFrame:
    df = pd.read_csv(FLOOD_CSV)
    df["impassable"] = df["impassable"].astype(str).str.lower().isin(["true", "1", "yes"])
    return df


def extract_radii_34kt() -> gpd.GeoDataFrame:
    """Extract the best-track radii shapefile and return only 34-kt polygons."""
    with zipfile.ZipFile(BEST_TRACK_ZIP) as z:
        tmpdir = pathlib.Path(tempfile.mkdtemp())
        for name in z.namelist():
            if "radii" in name:
                z.extract(name, tmpdir)

    shp = next(tmpdir.rglob("*radii*.shp"))
    gdf = gpd.read_file(str(shp))

    # Keep only 34-kt wind radii polygons
    gdf34 = gdf[gdf["RADII"] == 34.0].copy()

    # Parse SYNOPTIME (YYYYMMDDHH, UTC) into a timezone-aware datetime
    gdf34["time_utc"] = pd.to_datetime(
        gdf34["SYNOPTIME"].astype(str), format=SYNOPTIME_FMT, utc=True
    )
    gdf34 = gdf34.sort_values("time_utc").reset_index(drop=True)
    return gdf34


def find_wind_arrival(gdf34: gpd.GeoDataFrame, lon: float, lat: float) -> datetime | None:
    """
    Return the earliest 34-kt synoptic time whose polygon contains (lon, lat).
    Resolution is 6-hourly (per NHC best-track data); one anomalous 2-h entry
    at 2022-09-28T02Z is included as-is — it is real data from the NHC file.
    Returns None if the point is never inside any 34-kt polygon.
    """
    pt = Point(lon, lat)
    for _, row in gdf34.iterrows():
        if row.geometry.contains(pt):
            return row["time_utc"].to_pydatetime()
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    routes     = load_routes()
    advisories = load_advisories()
    flood      = load_flood()
    gdf34      = extract_radii_34kt()

    # Build advisory → issued_utc lookup
    adv_time = dict(zip(advisories["advisory"], advisories["issued_utc"]))

    # First impassable advisory per route
    first_flag = (
        flood[flood["impassable"]]
        .sort_values("advisory")
        .groupby("route", sort=False)
        .first()
        .reset_index()[["route", "advisory"]]
    )
    first_flag["surge_flag_utc"] = first_flag["advisory"].map(adv_time)

    results = []
    for _, rt in routes.iterrows():
        name = rt["name"]
        lon, lat = rt["lon"], rt["lat"]

        wind_arrival = find_wind_arrival(gdf34, lon, lat)
        if wind_arrival is None:
            print(f"  WARNING: {name} — no 34-kt polygon ever contained this point")
            wind_deadline = None
            lead_hours = None
        else:
            wind_deadline = wind_arrival - pd.Timedelta(hours=CLEARANCE_HOURS)

        flag_row = first_flag[first_flag["route"] == name]
        if flag_row.empty:
            surge_flag = None
            lead_hours = None
        else:
            surge_flag = flag_row.iloc[0]["surge_flag_utc"]
            if wind_arrival is not None:
                lead_hours = round(
                    (wind_deadline - surge_flag).total_seconds() / 3600, 1
                )
            else:
                lead_hours = None

        results.append({
            "route":             name,
            "surge_flag_utc":    surge_flag,
            "wind_arrival_utc":  wind_arrival,
            "wind_deadline_utc": wind_deadline if wind_arrival else None,
            "lead_hours":        lead_hours,
        })

    df_out = pd.DataFrame(results)
    df_out.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV}\n")
    print(df_out.to_string(index=False))

    # -----------------------------------------------------------------------
    # Timeline plot
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5))

    route_names = df_out["route"].tolist()
    y_ticks = range(len(route_names))

    marker_surge    = dict(marker="^", s=80, color="#e05c2a", zorder=5, label="surge_flag_utc")
    marker_deadline = dict(marker="D", s=60, color="#2a6ee0", zorder=5, label="wind_deadline_utc")
    marker_arrival  = dict(marker="o", s=60, color="#2ab05c", zorder=5, label="wind_arrival_utc")

    for i, row in df_out.iterrows():
        y = i
        if pd.notna(row["surge_flag_utc"]):
            ax.scatter(row["surge_flag_utc"], y, **marker_surge)
        if pd.notna(row["wind_deadline_utc"]):
            ax.scatter(row["wind_deadline_utc"], y, **marker_deadline)
        if pd.notna(row["wind_arrival_utc"]):
            ax.scatter(row["wind_arrival_utc"], y, **marker_arrival)

    # Landfall vertical line
    ax.axvline(IAN_LANDFALL_UTC, color="#888888", linewidth=1.2, linestyle="--", zorder=3)
    ax.text(
        IAN_LANDFALL_UTC, len(route_names) - 0.4,
        "Ian landfall\n(approx.)",
        fontsize=8, ha="center", va="top", color="#555555",
    )

    ax.set_yticks(list(y_ticks))
    ax.set_yticklabels(route_names, fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%HZ"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    fig.autofmt_xdate(rotation=0, ha="center")

    ax.set_xlabel("UTC time")
    ax.set_title("SurgeSense: Surge flag vs. Wind deadlines — Lee County routes, Hurricane Ian 2022")
    ax.grid(axis="x", linestyle=":", linewidth=0.6, alpha=0.7)

    # Deduplicate legend handles
    handles, labels = ax.get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        seen.setdefault(l, h)
    ax.legend(seen.values(), seen.keys(), loc="lower right", fontsize=8)

    plt.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    print(f"\nWrote {OUT_PNG}")


if __name__ == "__main__":
    main()
