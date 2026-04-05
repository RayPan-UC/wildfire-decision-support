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
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import bbox_from_db, event_dir, event_from_db, pick_firms_dataset

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
FIRMS_API_KEY = os.getenv("FIRMS_API_KEY")

FIRMS_BASE  = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def _fetch_day(source: str, bbox_str: str, day: date) -> pd.DataFrame:
    url = f"{FIRMS_BASE}/{FIRMS_API_KEY}/{source}/{bbox_str}/1/{day.strftime('%Y-%m-%d')}"
    df  = pd.read_csv(url)
    return df


def clip(event_id: int):
    bbox_4326, year = bbox_from_db(event_id)
    event           = event_from_db(event_id)
    out_dir         = event_dir(year, event_id) / "firms"
    out_dir.mkdir(exist_ok=True)

    if not FIRMS_API_KEY:
        raise EnvironmentError("FIRMS_API_KEY not set in .env")

    # Determine date range from event
    time_start = event["time_start"]
    time_end   = event["time_end"]
    if not time_start or not time_end:
        raise ValueError(f"Event {event_id} is missing time_start or time_end")

    start_day = date.fromisoformat(time_start[:10])
    end_day   = date.fromisoformat(time_end[:10])

    source = pick_firms_dataset(FIRMS_API_KEY, time_start, time_end)
    bbox_str = f"{bbox_4326[0]},{bbox_4326[1]},{bbox_4326[2]},{bbox_4326[3]}"

    total_days = (end_day - start_day).days + 1
    print(f"[firms] event={event_id}  {start_day} → {end_day}  ({total_days} days)  source={source}")
    print(f"[firms] bbox → {bbox_str}")

    frames = []
    current = start_day
    while current <= end_day:
        df = _fetch_day(source, bbox_str, current)
        if not df.empty:
            frames.append(df)
        current += timedelta(days=1)

    out_path = out_dir / f"{start_day}_{end_day}.csv"
    if frames:
        result = pd.concat(frames).drop_duplicates()
        result.to_csv(out_path, index=False)
        print(f"[firms] {len(result)} hotspot records saved → {out_path}")
    else:
        pd.DataFrame().to_csv(out_path, index=False)
        print(f"[firms] 0 hotspot records saved → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    clip(event_id)
