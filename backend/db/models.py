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
    time_start  = db.Column(db.DateTime(timezone=True))
    time_end    = db.Column(db.DateTime(timezone=True))
    description = db.Column(db.Text)

    # Pipeline mode control:
    #   NULL  → Realtime: pipeline fetches latest data (FIRMS, perimeter) on each run
    #   value → Replay:   pipeline fetches data up to this date only (historical analysis)
    end_date    = db.Column(db.Date, nullable=True)

    @property
    def is_realtime(self) -> bool:
        return self.end_date is None