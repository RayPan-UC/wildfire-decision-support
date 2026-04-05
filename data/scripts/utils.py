# data/scripts/utils.py
# Shared utilities for downloader and clipper scripts

from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent


def event_dir(year: int, event_id: int) -> Path:
    """Return the data directory for a given fire event, e.g. data/events/2016_0001/"""
    path = DATA_ROOT / "events" / f"{year}_{event_id:04d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def pick_firms_dataset(api_key: str, event_start, event_end) -> str:
    """Query FIRMS data_availability API and pick best dataset for event time range.

    Priority order (SP preferred over NRT, VIIRS preferred over MODIS):
      1. VIIRS_NOAA21_SP  — newest sensor, highest resolution (375m)
      2. VIIRS_NOAA20_SP  — available from 2018
      3. VIIRS_SNPP_SP    — available from 2012, covers most historical events
      4. MODIS_SP         — fallback for pre-2012 events
      5. NRT variants     — only if no SP covers the period
    """
    import pandas as pd

    url = f"https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{api_key}/all"
    df  = pd.read_csv(url)

    df["min_date"] = pd.to_datetime(df["min_date"]).dt.tz_localize(None)
    df["max_date"] = pd.to_datetime(df["max_date"]).dt.tz_localize(None)

    event_start = pd.Timestamp(event_start).tz_localize(None)
    event_end   = pd.Timestamp(event_end).tz_localize(None)

    available = df[
        (df["min_date"] <= event_start) &
        (df["max_date"] >= event_end)
    ]

    if available.empty:
        raise ValueError(f"No FIRMS dataset covers {event_start} to {event_end}")

    priority = [
        "VIIRS_NOAA21_SP",
        "VIIRS_NOAA20_SP",
        "VIIRS_SNPP_SP",
        "MODIS_SP",
        "VIIRS_NOAA21_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_SNPP_NRT",
        "MODIS_NRT",
    ]
    ids = set(available["data_id"])
    for candidate in priority:
        if candidate in ids:
            return candidate

    return available.iloc[0]["data_id"]


def _get_flask_app():
    """Bootstrap a minimal Flask app connected to the database."""
    import sys
    sys.path.insert(0, str(DATA_ROOT.parent / "backend"))
    import config  # loads .env
    from db.connection import db, get_db_uri
    from flask import Flask

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
    db.init_app(app)
    return app, db


def bbox_from_db(event_id: int):
    """Fetch bbox [minLon, minLat, maxLon, maxLat] and year from fire_events table."""
    app, db = _get_flask_app()
    with app.app_context():
        from geoalchemy2.shape import to_shape
        from db.models import FireEvent
        event = FireEvent.query.get(event_id)
        if not event:
            raise ValueError(f"fire_event id={event_id} not found")
        bounds = to_shape(event.bbox).bounds  # (minx, miny, maxx, maxy)
        return list(bounds), event.year


def event_from_db(event_id: int) -> dict:
    """Fetch full event metadata from fire_events table.

    Returns a dict with: id, name, year, bbox, time_start, time_end, description
    bbox is [minLon, minLat, maxLon, maxLat] in EPSG:4326.
    """
    app, db = _get_flask_app()
    with app.app_context():
        from geoalchemy2.shape import to_shape
        from db.models import FireEvent
        event = FireEvent.query.get(event_id)
        if not event:
            raise ValueError(f"fire_event id={event_id} not found")
        bounds = list(to_shape(event.bbox).bounds)
        return {
            "id":          event.id,
            "name":        event.name,
            "year":        event.year,
            "bbox":        bounds,
            "time_start":  event.time_start.isoformat() if event.time_start else None,
            "time_end":    event.time_end.isoformat()   if event.time_end   else None,
            "description": event.description,
        }
