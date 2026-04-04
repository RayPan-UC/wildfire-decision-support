# clipper/clip_aoi.py
# Generate AOI GeoJSON from fire_events.bbox
#
# Usage:
#   python clip_aoi.py <event_id>
#
# Output:
#   data/events/{yyyy}_{id:04d}/AOI/aoi.geojson

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import event_from_db, event_dir


def clip(event_id: int):
    event    = event_from_db(event_id)
    bbox     = event["bbox"]  # [minLon, minLat, maxLon, maxLat]
    minx, miny, maxx, maxy = bbox

    aoi_dir  = event_dir(event["year"], event_id) / "AOI"
    aoi_dir.mkdir(exist_ok=True)
    out_path = aoi_dir / "aoi.geojson"

    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [minx, miny], [maxx, miny], [maxx, maxy],
                    [minx, maxy], [minx, miny]
                ]]
            },
            "properties": {
                "event_id":   event["id"],
                "name":       event["name"],
                "year":       event["year"],
                "time_start": event["time_start"],
                "time_end":   event["time_end"],
            }
        }]
    }

    with open(out_path, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"[aoi] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    clip(event_id)
