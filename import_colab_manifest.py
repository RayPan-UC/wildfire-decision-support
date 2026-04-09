#!/usr/bin/env python3
"""
import_colab_manifest.py
========================
Import the timestep manifest produced by pipeline_for_colab.py into
the local PostgreSQL database.

Usage (run from the project root after syncing data/ from Drive):
    python import_colab_manifest.py

Prerequisites:
    - PostgreSQL running locally with wildfire_db created (or run main.py once to seed it)
    - data/colab_manifest.json present (produced by pipeline_for_colab.py)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "data" / "colab_manifest.json"

if not MANIFEST_PATH.exists():
    print(f"ERROR: manifest not found at {MANIFEST_PATH}")
    print("       Run pipeline_for_colab.py on Colab first, then sync data/ here.")
    sys.exit(1)

sys.path.insert(0, str(ROOT / "backend"))

import config  # loads .env                                      # noqa: E402
from main import create_app                                      # noqa: E402
from pipeline.db import setup_db                                 # noqa: E402

app = create_app()

print("=== Setting up database ===")
setup_db(app)

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
event_cfg  = manifest["event"]
timesteps  = manifest["timesteps"]

print(f"=== Importing manifest: {event_cfg['name']} — {len(timesteps)} timesteps ===")

with app.app_context():
    from db.connection import db
    from db.models import FireEvent, EventTimestep
    from geoalchemy2 import WKTElement

    # ── Ensure the FireEvent row exists ──────────────────────────────────────
    event = FireEvent.query.get(event_cfg["id"])
    if event is None:
        lon_min, lat_min, lon_max, lat_max = event_cfg["bbox"]
        wkt = (
            f"POLYGON(({lon_min} {lat_min}, {lon_max} {lat_min}, "
            f"{lon_max} {lat_max}, {lon_min} {lat_max}, {lon_min} {lat_min}))"
        )
        event = FireEvent(
            id          = event_cfg["id"],
            name        = event_cfg["name"],
            year        = event_cfg["year"],
            bbox        = WKTElement(wkt, srid=4326),
            start_date  = event_cfg["start_date"],
            end_date    = event_cfg["end_date"],
        )
        db.session.add(event)
        db.session.flush()
        print(f"[import] created FireEvent id={event_cfg['id']} ({event_cfg['name']})")
    else:
        print(f"[import] FireEvent id={event_cfg['id']} already exists — skipping")

    # ── Upsert EventTimestep rows ─────────────────────────────────────────────
    created = updated = skipped = 0

    for ts_data in timesteps:
        from dateutil.parser import parse as _parse

        slot_time  = _parse(ts_data["slot_time"])
        nearest_t1 = _parse(ts_data["nearest_t1"])

        existing = EventTimestep.query.filter_by(
            event_id  = event_cfg["id"],
            slot_time = slot_time,
        ).first()

        if existing is None:
            row = EventTimestep(
                event_id               = event_cfg["id"],
                slot_time              = slot_time,
                nearest_t1             = nearest_t1,
                gap_hours              = ts_data.get("gap_hours", 0.0),
                data_gap_warn          = ts_data.get("data_gap_warn", False),
                prediction_status      = ts_data.get("prediction_status", "pending"),
                spatial_analysis_status= ts_data.get("spatial_analysis_status", "pending"),
                affected_population    = ts_data.get("affected_population"),
                at_risk_3h             = ts_data.get("at_risk_3h"),
                at_risk_6h             = ts_data.get("at_risk_6h"),
                at_risk_12h            = ts_data.get("at_risk_12h"),
            )
            db.session.add(row)
            created += 1
        else:
            # Update status and population counts (don't overwrite with worse status)
            if ts_data.get("prediction_status") == "done":
                existing.prediction_status = "done"
            if ts_data.get("spatial_analysis_status") == "done":
                existing.spatial_analysis_status = "done"
            for col in ("affected_population", "at_risk_3h", "at_risk_6h", "at_risk_12h"):
                v = ts_data.get(col)
                if v is not None:
                    setattr(existing, col, v)
            updated += 1

    db.session.commit()

    print(f"[import] created={created}  updated={updated}  skipped={skipped}")
    total_done = EventTimestep.query.filter_by(
        event_id=event_cfg["id"], prediction_status="done"
    ).count()
    print(f"[import] {total_done} timesteps now marked 'done' in DB")
    print("\nDone. You can now start main.py — it will serve the Colab-generated files.")
