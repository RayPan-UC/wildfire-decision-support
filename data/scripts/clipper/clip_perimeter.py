# clipper/clip_perimeter.py
# Generate fire perimeter by buffering CWFIS M3 hotspot points for a given date
# Source: https://cwfis.cfs.nrcan.gc.ca/downloads/hotspots/YYYYMMDD.csv
#
# Usage:
#   python clip_perimeter.py <event_id> [YYYY-MM-DD]
#
# Output:
#   data/events/{yyyy}_{id:04d}/perimeter/YYYY-MM-DD.geojson

import sys
import io
import urllib.request
from datetime import date
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir

CWFIS_URL = "https://cwfis.cfs.nrcan.gc.ca/downloads/hotspots/{date}.csv"
BUFFER_KM = 2.0   # buffer radius around each hotspot point (km)
HOTSPOT_CRS = "EPSG:4326"
BUFFER_CRS  = "EPSG:3978"  # equal-area for buffering


def clip(event_id: int, day: date = None):
    bbox_4326, year = bbox_from_db(event_id)
    out_dir  = event_dir(year, event_id) / "perimeter"
    out_dir.mkdir(exist_ok=True)

    if day is None:
        day = date.today()

    out_path = out_dir / (day.strftime("%Y-%m-%d") + ".geojson")
    url      = CWFIS_URL.format(date=day.strftime("%Y%m%d"))

    print(f"[perimeter] event={event_id} date={day}")
    print(f"[perimeter] hotspot CSV → {url}")
    print(f"[perimeter] output → {out_path}")

    with urllib.request.urlopen(url) as resp:
        df = pd.read_csv(io.BytesIO(resp.read()))

    # Clip hotspots to event bbox before buffering
    bbox_poly = box(bbox_4326[0], bbox_4326[1], bbox_4326[2], bbox_4326[3])
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs=HOTSPOT_CRS
    )
    gdf = gdf[gdf.intersects(bbox_poly)]

    if gdf.empty:
        print(f"[perimeter] no hotspots in AOI for {day}, skipping.")
        return

    # Buffer in equal-area CRS, dissolve, reproject back to 4326
    gdf_proj = gdf.to_crs(BUFFER_CRS)
    buffered = gdf_proj.buffer(BUFFER_KM * 1000).unary_union
    perimeter = gpd.GeoDataFrame(
        geometry=[buffered],
        crs=BUFFER_CRS
    ).to_crs(epsg=4326)

    perimeter.to_file(out_path, driver="GeoJSON")
    print(f"[perimeter] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else None
    clip(event_id, day)
