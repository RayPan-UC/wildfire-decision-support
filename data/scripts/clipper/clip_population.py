# clipper/clip_population.py
# Clip Statistics Canada Dissemination Area (DA) boundaries for a fire event AOI
# Source: data/static/population/{year}/*.shp (already downloaded)
#
# Usage:
#   python clip_population.py <event_id>
#
# Output:
#   data/events/{yyyy}_{id:04d}/population/dissemination_areas.gpkg

import sys
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR   = _SCRIPTS_DIR.parent / "static" / "population"

# Shapefile name by census year
POPULATION_FILES = {
    2011: STATIC_DIR / "2011" / "gda_000a11a_e.shp",
    2016: STATIC_DIR / "2016" / "lda_000a16a_e.shp",
    2021: STATIC_DIR / "2021" / "lda_000b21a_e.shp",
}


def nearest_year(event_year: int) -> int:
    years      = sorted(POPULATION_FILES.keys())
    candidates = [y for y in years if y <= event_year]
    return candidates[-1] if candidates else years[0]


def clip(event_id: int):
    bbox_4326, year = bbox_from_db(event_id)
    out_dir  = event_dir(year, event_id) / "population"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "dissemination_areas.gpkg"

    da_year  = nearest_year(year)
    src_path = POPULATION_FILES[da_year]

    print(f"[population] event={event_id} event_year={year} → da_year={da_year}")
    print(f"[population] source → {src_path}")
    print(f"[population] output → {out_path}")

    gdf  = gpd.read_file(src_path).to_crs(epsg=4326)
    poly = box(bbox_4326[0], bbox_4326[1], bbox_4326[2], bbox_4326[3])

    clipped = gpd.clip(gdf, poly)
    print(f"[population] {len(clipped)} features clipped")

    clipped.to_file(out_path, driver="GPKG")
    print(f"[population] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    clip(event_id)
