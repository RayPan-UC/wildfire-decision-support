from db.connection import db
from geoalchemy2 import Geometry
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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