# clipper/clip_terrain.py
# Clip terrain (DEM) from MRDEM-30 Cloud-Optimized GeoTIFF for a fire event AOI
# Source: CanElevation MRDEM-30 (remote COG, streams by window)
#
# Usage:
#   python clip_terrain.py <event_id> [dtm|dsm]
#
# Output:
#   data/events/{yyyy}_{id:04d}/terrain/dem_dtm.tif
#   data/events/{yyyy}_{id:04d}/terrain/dem_dsm.tif

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crs  # noqa: F401  fixes PROJ_DATA before rasterio loads
import rasterio
import rasterio.windows
from rasterio.crs import CRS
from rasterio.warp import transform_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir

MRDEM_URLS = {
    'dtm': 'https://canelevation-dem.s3.ca-central-1.amazonaws.com/mrdem-30/mrdem-30-dtm.tif',
    'dsm': 'https://canelevation-dem.s3.ca-central-1.amazonaws.com/mrdem-30/mrdem-30-dsm.tif',
}


def clip(event_id: int, model: str = 'dtm'):
    if model not in MRDEM_URLS:
        raise ValueError(f"model must be 'dtm' or 'dsm', got '{model}'")

    bbox_4326, year = bbox_from_db(event_id)
    out_dir = event_dir(year, event_id) / "terrain"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"dem_{model}.tif"

    # Reproject bbox from EPSG:4326 to EPSG:3979 (MRDEM native CRS)
    minx, miny, maxx, maxy = transform_bounds(
        CRS.from_epsg(4326), CRS.from_epsg(3979),
        bbox_4326[0], bbox_4326[1], bbox_4326[2], bbox_4326[3]
    )

    print(f"[terrain] event={event_id} model={model}")
    print(f"[terrain] bbox EPSG:4326 → {bbox_4326}")
    print(f"[terrain] bbox EPSG:3979 → ({minx:.0f}, {miny:.0f}, {maxx:.0f}, {maxy:.0f})")
    print(f"[terrain] output → {out_path}")

    with rasterio.open(MRDEM_URLS[model]) as src:
        window      = src.window(minx, miny, maxx, maxy)
        raster_data = src.read(window=window)

        metadata = src.meta.copy()
        metadata.update({
            'height':    raster_data.shape[1],
            'width':     raster_data.shape[2],
            'count':     raster_data.shape[0],
            'transform': rasterio.windows.transform(window, src.transform),
        })

        with rasterio.open(out_path, 'w', **metadata) as dst:
            dst.write(raster_data)

    print(f"[terrain] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    model    = sys.argv[2] if len(sys.argv) > 2 else 'dtm'
    clip(event_id, model)
