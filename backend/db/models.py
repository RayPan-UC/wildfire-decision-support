from db.connection import db
from geoalchemy2 import Geometry


class User(db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(255), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class FireEvent(db.Model):
    __tablename__ = "fire_events"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.Text, nullable=False)
    year        = db.Column(db.Integer)
    bbox        = db.Column(Geometry("POLYGON", srid=4326))
    start_date  = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)

    # Pipeline mode control:
    #   NULL  → Realtime: pipeline fetches latest data on each run
    #   value → Replay:   historical analysis up to this date (inclusive)
    end_date    = db.Column(db.Date, nullable=True)

    timesteps   = db.relationship("EventTimestep", backref="event", lazy=True)

    @property
    def is_realtime(self) -> bool:
        return self.end_date is None


class EventTimestep(db.Model):
    __tablename__ = "event_timesteps"
    id         = db.Column(db.Integer, primary_key=True)
    event_id   = db.Column(db.Integer, db.ForeignKey("fire_events.id"), nullable=False)

    # Canonical 3-hour slot on the regular time grid
    slot_time  = db.Column(db.DateTime(timezone=True), nullable=False)

    # Most recent satellite overpass at or before slot_time (the T1 used for prediction)
    nearest_t1 = db.Column(db.DateTime(timezone=True), nullable=False)

    # Hours between slot_time and nearest_t1 (always >= 0)
    gap_hours      = db.Column(db.Float, nullable=False, default=0.0)

    # True when gap_hours > 12 — prediction may be stale
    data_gap_warn  = db.Column(db.Boolean, nullable=False, default=False)

    # Processing status per stage: 'pending' | 'running' | 'done' | 'failed'
    prediction_status       = db.Column(db.Text, nullable=False, default="pending")
    spatial_analysis_status = db.Column(db.Text, nullable=False, default="pending")

    # Spatial analysis results (numeric, stored in DB)
    affected_population = db.Column(db.Integer)
    at_risk_3h          = db.Column(db.Integer)
    at_risk_6h          = db.Column(db.Integer)
    at_risk_12h         = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
