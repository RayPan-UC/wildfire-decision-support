# clipper/clip_landcover.py
# Clip FBP fuel type from local static rasters for a fire event AOI
# Source: data/static/landcover/{year}/*.tif (already downloaded)
#
# Usage:
#   python clip_landcover.py <event_id>
#
# Output:
#   data/events/{yyyy}_{id:04d}/landcover/fuel_type.tif

import sys
from pathlib import Path
import rasterio
import rasterio.windows
from rasterio.crs import CRS
from rasterio.warp import transform_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir

_SCRIPTS_DIR  = Path(__file__).resolve().parent.parent
LANDCOVER_DIR = _SCRIPTS_DIR.parent / "static" / "landcover"

LANDCOVER_FILES = {
    2014: LANDCOVER_DIR / "2014" / "nat_fbpfuels_2014b.tif",
    2024: LANDCOVER_DIR / "2024" / "FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif",
}


def nearest_year(event_year: int) -> int:
    years      = sorted(LANDCOVER_FILES.keys())
    candidates = [y for y in years if y <= event_year]
    return candidates[-1] if candidates else years[0]


def clip(event_id: int):
    bbox_4326, year = bbox_from_db(event_id)
    out_dir  = event_dir(year, event_id) / "landcover"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "fuel_type.tif"

    lc_year  = nearest_year(year)
    src_path = LANDCOVER_FILES[lc_year]

    print(f"[landcover] event={event_id} event_year={year} → landcover_year={lc_year}")
    print(f"[landcover] source → {src_path}")
    print(f"[landcover] output → {out_path}")

    with rasterio.open(src_path) as src:
        src_crs = src.crs
        minx, miny, maxx, maxy = transform_bounds(
            CRS.from_epsg(4326), src_crs,
            bbox_4326[0], bbox_4326[1], bbox_4326[2], bbox_4326[3]
        )

        print(f"[landcover] bbox EPSG:4326 → {bbox_4326}")
        print(f"[landcover] bbox {src_crs.to_epsg()} → ({minx:.0f}, {miny:.0f}, {maxx:.0f}, {maxy:.0f})")

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

    print(f"[landcover] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    clip(event_id)
