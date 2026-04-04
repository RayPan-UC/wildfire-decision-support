# downloader/dl_osm.py
# Download Canada OSM PBF from Geofabrik, extract drivable roads to GPKG,
# then delete the PBF to save space.
#
# Tries git lfs pull first; falls back to Geofabrik (~6 GB) if not available.
# Output: data/static/osm/roads_canada.gpkg

import subprocess
import urllib.request
from pathlib import Path
import osmium
import geopandas as gpd
from shapely.geometry import LineString

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR   = _SCRIPTS_DIR.parent / "static" / "osm"

GEOFABRIK_URL = "https://download.geofabrik.de/north-america/canada-latest.osm.pbf"
PBF_NAME      = "canada-latest.osm.pbf"
GPKG_NAME     = "roads_canada.gpkg"

HIGHWAY_TYPES = {
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "unclassified", "residential",
}


class RoadExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.roads = []

    def way(self, w):
        highway = w.tags.get("highway")
        if highway not in HIGHWAY_TYPES:
            return
        coords = [(n.lon, n.lat) for n in w.nodes if n.location.valid()]
        if len(coords) < 2:
            return
        self.roads.append({
            "osm_id":  w.id,
            "highway": highway,
            "name":    w.tags.get("name", ""),
            "geometry": LineString(coords),
        })


def download():
    out_gpkg = STATIC_DIR / GPKG_NAME

    if out_gpkg.exists():
        print(f"[osm-dl] Already exists → {out_gpkg}, skipping.")
        return

    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Try LFS first
    print(f"[osm-dl] Trying git lfs pull ...")
    repo_root = _SCRIPTS_DIR.parent.parent
    subprocess.run(
        ["git", "lfs", "pull", "--include", f"data/static/osm/{GPKG_NAME}"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if out_gpkg.exists():
        print(f"[osm-dl] Pulled from LFS → {out_gpkg}")
        return
    print(f"[osm-dl] Not in LFS, falling back to Geofabrik PBF ...")

    pbf_path = STATIC_DIR / PBF_NAME

    # Download PBF
    print(f"[osm-dl] Downloading Canada PBF from Geofabrik (~6 GB) ...")

    def _progress(block_count, block_size, total_size):
        downloaded = block_count * block_size
        if total_size > 0:
            pct = min(downloaded / total_size * 100, 100)
            print(f"\r[osm-dl] {pct:.1f}%  ({downloaded // 1_048_576} / {total_size // 1_048_576} MB)", end="", flush=True)

    urllib.request.urlretrieve(GEOFABRIK_URL, pbf_path, reporthook=_progress)
    print()

    # Extract drivable roads
    print(f"[osm-dl] Extracting drivable roads ...")
    extractor = RoadExtractor()
    extractor.apply_file(str(pbf_path), locations=True)
    print(f"[osm-dl] {len(extractor.roads)} road features extracted")

    gdf = gpd.GeoDataFrame(extractor.roads, crs="EPSG:4326")
    gdf.to_file(out_gpkg, driver="GPKG")
    print(f"[osm-dl] Saved → {out_gpkg}")

    pbf_path.unlink()
    print(f"[osm-dl] Deleted {PBF_NAME}")


if __name__ == "__main__":
    download()
