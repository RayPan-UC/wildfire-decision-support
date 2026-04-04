# clipper/clip_community.py
# Clip Statistics Canada Census Subdivision (CSD) boundaries for a fire event AOI
# Source: data/static/community/{year}/*.shp (already downloaded)
#
# Usage:
#   python clip_community.py <event_id>
#
# Output:
#   data/events/{yyyy}_{id:04d}/community/census_subdivisions.gpkg

import sys
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR   = _SCRIPTS_DIR.parent / "static" / "community"

# Shapefile name by census year
COMMUNITY_FILES = {
    2011: STATIC_DIR / "2011" / "gcsd000a11a_e.shp",
    2016: STATIC_DIR / "2016" / "lcsd000a16a_e.shp",
    2021: STATIC_DIR / "2021" / "lcsd000a21a_e.shp",
    2025: STATIC_DIR / "2025" / "lcsd000a25a_e.shp",
}


def nearest_year(event_year: int) -> int:
    years      = sorted(COMMUNITY_FILES.keys())
    candidates = [y for y in years if y <= event_year]
    return candidates[-1] if candidates else years[0]


def clip(event_id: int):
    bbox_4326, year = bbox_from_db(event_id)
    out_dir  = event_dir(year, event_id) / "community"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "census_subdivisions.gpkg"

    csd_year = nearest_year(year)
    src_path = COMMUNITY_FILES[csd_year]

    print(f"[community] event={event_id} event_year={year} → csd_year={csd_year}")
    print(f"[community] source → {src_path}")
    print(f"[community] output → {out_path}")

    gdf  = gpd.read_file(src_path).to_crs(epsg=4326)
    poly = box(bbox_4326[0], bbox_4326[1], bbox_4326[2], bbox_4326[3])

    clipped = gpd.clip(gdf, poly)
    print(f"[community] {len(clipped)} features clipped")

    clipped.to_file(out_path, driver="GPKG")
    print(f"[community] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    clip(event_id)
