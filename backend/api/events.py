from flask import Blueprint, jsonify
from geoalchemy2.shape import to_shape
from db.models import FireEvent

events_bp = Blueprint('events', __name__)


def _serialize(e):
    bounds = to_shape(e.bbox).bounds  # (minx, miny, maxx, maxy)
    return {
        'id':          e.id,
        'name':        e.name,
        'year':        e.year,
        'time_start':  e.time_start.isoformat() if e.time_start else None,
        'time_end':    e.time_end.isoformat() if e.time_end else None,
        'description': e.description,
        'bbox':        list(bounds)  # [minLon, minLat, maxLon, maxLat]
    }


@events_bp.route('/', methods=['GET'])
def list_events():
    events = FireEvent.query.order_by(FireEvent.year.desc()).all()
    return jsonify([_serialize(e) for e in events]), 200
