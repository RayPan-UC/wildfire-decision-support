# clipper/clip_osm.py
# Clip drivable roads from local Canada roads GPKG for a fire event AOI.
# Requires data/static/osm/{yyyy}/roads_canada.gpkg (run dl_osm.py first).
#
# Usage:
#   python clip_osm.py <event_id>
#
# Output:
#   data/events/{yyyy}_{id:04d}/osm/roads.gpkg

import sys
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR   = _SCRIPTS_DIR.parent / "static" / "osm"


def _find_gpkg() -> Path:
    candidate = STATIC_DIR / "roads_canada.gpkg"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"No roads_canada.gpkg found in {STATIC_DIR}. Run: python pipeline.py download --osm"
    )


def clip(event_id: int):
    bbox_4326, year = bbox_from_db(event_id)
    out_dir  = event_dir(year, event_id) / "osm"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "roads.gpkg"

    gpkg = _find_gpkg()
    print(f"[osm] event={event_id} bbox={bbox_4326}")
    print(f"[osm] reading {gpkg} ...")

    aoi   = box(*bbox_4326)
    roads = gpd.read_file(gpkg, bbox=tuple(bbox_4326))
    roads = roads[roads.intersects(aoi)]

    print(f"[osm] {len(roads)} road features clipped")
    roads.to_file(out_path, driver="GPKG")
    print(f"[osm] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    clip(event_id)
