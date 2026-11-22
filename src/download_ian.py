import pathlib, urllib.request

# Storm surge flooding forecasts (advisories 12-25, before/at Florida landfall)
out = pathlib.Path("data/raw/inundation")
out.mkdir(parents=True, exist_ok=True)
base = "https://www.nhc.noaa.gov/gis/inundation/forecasts"

for adv in [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 24, 25]:
    for kind in ["inundation", "tidalmask"]:
        name = f"AL0922_{adv}_{kind}.zip"
        try:
            urllib.request.urlretrieve(f"{base}/{name}", out / name)
            print("got", name)
        except Exception as e:
            print("missed", name, e)

# Ian's actual track
best = pathlib.Path("data/raw/nhc")
best.mkdir(parents=True, exist_ok=True)
urllib.request.urlretrieve(
    "https://www.nhc.noaa.gov/gis/best_track/al092022_best_track.zip",
    best / "al092022_best_track.zip",
)
print("got best track")