import glob, zipfile, pathlib
import numpy as np
import rasterio
import geopandas as gpd

# Unzip advisory 22 into data/raw/inundation/adv22/
zip_path = "data/raw/inundation/AL0922_22_inundation.zip"
out_dir = pathlib.Path("data/raw/inundation/adv22")
with zipfile.ZipFile(zip_path) as z:
    z.extractall(out_dir)
    print("Files in zip:", z.namelist())

tif = glob.glob(str(out_dir / "**" / "*.tif"), recursive=True)[0]
print("\nFile:", tif)

with rasterio.open(tif) as src:
    print("CRS:", src.crs)
    print("Size:", src.width, "x", src.height)
    print("Pixel size:", src.res)
    print("Bounds:", src.bounds)
    print("NoData:", src.nodata)
    data = src.read(1, out_shape=(max(1, src.height // 20), max(1, src.width // 20)))
    nodata = src.nodata

vals = data[data != nodata] if nodata is not None else data.ravel()
print("Unique values (first 20):", np.unique(vals)[:20])

dbf = glob.glob(str(out_dir / "**" / "*.dbf"), recursive=True)
if dbf:
    print("\nAttribute table:")
    print(gpd.read_file(dbf[0]))