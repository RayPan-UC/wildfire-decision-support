# clipper/clip_firms.py
# Download NASA FIRMS hotspot data for a fire event AOI
#
# API endpoint:
#   https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{bbox}/{day_range}/{date}
#   bbox format: min_lon,min_lat,max_lon,max_lat
#
# Dataset selection:
#   - Uses pick_firms_dataset() to prefer SP (Standard Product) over NRT (Near Real-Time)
#   - Falls back to VIIRS_SNPP_NRT if no SP dataset covers the event period
#
# Usage:
#   python clip_firms.py <event_id> [YYYY-MM-DD]
#
# Output:
#   data/events/{yyyy}_{id:04d}/firms/YYYY-MM-DD.csv

import os
import sys
from datetime import date, datetime
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir, pick_firms_dataset

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
FIRMS_API_KEY = os.getenv("FIRMS_API_KEY")

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def clip(event_id: int, day: date = None):
    bbox_4326, year = bbox_from_db(event_id)
    out_dir = event_dir(year, event_id) / "firms"
    out_dir.mkdir(exist_ok=True)

    if day is None:
        day = date.today()

    out_path = out_dir / (day.strftime("%Y-%m-%d") + ".csv")

    if not FIRMS_API_KEY:
        raise EnvironmentError("FIRMS_API_KEY not set in .env")

    # Pick best dataset for the event period (SP preferred over NRT)
    event_start = datetime(year, 1, 1)
    event_end   = datetime(year, 12, 31)
    try:
        source = pick_firms_dataset(FIRMS_API_KEY, event_start, event_end)
    except ValueError:
        # Fall back to VIIRS SNPP NRT if no dataset found
        source = "VIIRS_SNPP_NRT"

    # bbox as: min_lon,min_lat,max_lon,max_lat
    bbox_str = f"{bbox_4326[0]},{bbox_4326[1]},{bbox_4326[2]},{bbox_4326[3]}"
    date_str  = day.strftime("%Y-%m-%d")

    # day_range=1 with a specific date fetches exactly that day
    url = f"{FIRMS_BASE}/{FIRMS_API_KEY}/{source}/{bbox_str}/1/{date_str}"

    print(f"[firms] event={event_id} date={day} source={source}")
    print(f"[firms] bbox  → {bbox_str}")
    print(f"[firms] url   → {url}")
    print(f"[firms] output → {out_path}")

    df = pd.read_csv(url)
    df.to_csv(out_path, index=False)

    print(f"[firms] {len(df)} hotspot records saved → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else None
    clip(event_id, day)
