"""
pipeline/db/
------------
DB setup: create database, enable PostGIS, create tables, seed initial data.
Runs once at startup before checks and pipeline stages.
"""

from __future__ import annotations


# Canonical column set for event_timesteps — drop & recreate if stale.
_REQUIRED_COLS = {
    "id", "event_id", "slot_time", "nearest_t1", "gap_hours", "data_gap_warn",
    "prediction_status", "spatial_analysis_status",
    "affected_population", "at_risk_3h", "at_risk_6h", "at_risk_12h",
    "created_at",
}


def setup_db(app) -> None:
    """Create DB + PostGIS, create all tables, seed fire events if empty."""
    from db.connection import ensure_db, seed_db, db

    ensure_db()
    with app.app_context():
        _migrate_event_timesteps(db)
        db.create_all()
        seed_db()


def _migrate_event_timesteps(db) -> None:
    """Drop event_timesteps if its columns don't match the current schema.

    event_timesteps is fully rebuilt by the pipeline on every run, so dropping
    it is always safe — no data is lost that can't be regenerated.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "event_timesteps" not in inspector.get_table_names():
        return  # table doesn't exist yet — create_all() will handle it

    existing = {col["name"] for col in inspector.get_columns("event_timesteps")}
    if existing == _REQUIRED_COLS:
        return  # schema is current

    print(f"[db] event_timesteps schema mismatch — dropping and recreating")
    with db.engine.connect() as conn:
        conn.execute(text("DROP TABLE event_timesteps CASCADE"))
        conn.commit()
