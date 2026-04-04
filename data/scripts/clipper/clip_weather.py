# clipper/clip_weather.py
# Download ERA5-Land hourly reanalysis weather data for a fire event AOI
# Source: Copernicus Climate Data Store (CDS) via cdsapi
#
# Time range and bbox are read from the event's AOI GeoJSON:
#   data/events/{yyyy}_{id:04d}/AOI/aoi.geojson
#
# Usage:
#   python clip_weather.py <event_id>
#
# Output (one file per month):
#   data/events/{yyyy}_{id:04d}/weather/ERA5_{YYYY}_{MM}.grib
#
# Setup:
#   pip install cdsapi
#   Create ~/.cdsapirc with your CDS API key:
#     url: https://cds.climate.copernicus.eu/api
#     key: <your-key>

import sys
import json
from pathlib import Path
from datetime import date, timedelta
import cdsapi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils import event_dir

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent

VARIABLES = [
    "2m_dewpoint_temperature",
    "2m_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
]

ALL_HOURS = [f"{h:02d}:00" for h in range(24)]


def _read_aoi(event_id: int) -> dict:
    """Read bbox and time range from AOI GeoJSON properties."""
    # Find the event directory by searching for the AOI file
    events_dir = _SCRIPTS_DIR.parent / "events"
    matches = list(events_dir.glob(f"*_{event_id:04d}/AOI/aoi.geojson"))
    if not matches:
        raise FileNotFoundError(
            f"AOI not found for event {event_id}. Run: python pipeline.py clip {event_id} --aoi"
        )

    with open(matches[0]) as f:
        geojson = json.load(f)

    props = geojson["features"][0]["properties"]
    coords = geojson["features"][0]["geometry"]["coordinates"][0]

    # bbox from coordinates: [minLon, minLat] to [maxLon, maxLat]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    return {
        "minLon":     min(lons),
        "minLat":     min(lats),
        "maxLon":     max(lons),
        "maxLat":     max(lats),
        "time_start": props.get("time_start"),
        "time_end":   props.get("time_end"),
        "year":       props.get("year"),
    }


def _months_in_range(start: date, end: date) -> list[tuple[int, int]]:
    """Return list of (year, month) tuples covered by the date range."""
    months = []
    current = date(start.year, start.month, 1)
    while current <= end:
        months.append((current.year, current.month))
        # Advance to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def _days_in_month(year: int, month: int, start: date, end: date) -> list[str]:
    """Return list of day strings ('01','02',...) within the event date range."""
    days = []
    d = date(year, month, 1)
    while d.month == month:
        if start <= d <= end:
            days.append(f"{d.day:02d}")
        d += timedelta(days=1)
    return days


def clip(event_id: int):
    aoi  = _read_aoi(event_id)
    year = aoi["year"]

    out_dir = event_dir(year, event_id) / "weather"
    out_dir.mkdir(exist_ok=True)

    # Parse event date range from AOI properties
    if not aoi["time_start"] or not aoi["time_end"]:
        raise ValueError(f"AOI for event {event_id} is missing time_start / time_end")

    start = date.fromisoformat(aoi["time_start"][:10])
    end   = date.fromisoformat(aoi["time_end"][:10])

    # ERA5 area format: [North, West, South, East]
    area = [
        aoi["maxLat"],  # North
        aoi["minLon"],  # West
        aoi["minLat"],  # South
        aoi["maxLon"],  # East
    ]

    print(f"[weather] event={event_id} range={start} → {end}")
    print(f"[weather] area (N,W,S,E) = {area}")

    client = cdsapi.Client()

    for yr, mo in _months_in_range(start, end):
        days = _days_in_month(yr, mo, start, end)
        if not days:
            continue

        out_path = out_dir / f"ERA5_{yr}_{mo:02d}.grib"
        if out_path.exists():
            print(f"[weather] already exists, skipping → {out_path}")
            continue

        print(f"[weather] downloading {yr}-{mo:02d} ({len(days)} days) → {out_path}")

        request = {
            "variable":        VARIABLES,
            "year":            str(yr),
            "month":           f"{mo:02d}",
            "day":             days,
            "time":            ALL_HOURS,
            "data_format":     "grib",
            "download_format": "unarchived",
            "area":            area,
        }

        client.retrieve("reanalysis-era5-land", request).download(str(out_path))
        print(f"[weather] done → {out_path}")


if __name__ == "__main__":
    event_id = int(sys.argv[1])
    clip(event_id)
