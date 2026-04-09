import json
from pathlib import Path

import geopandas as gpd
from flask import Blueprint, jsonify
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from db.models import FireEvent
from utils.auth_middleware import token_required

events_bp = Blueprint('events', __name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "events"


def _event_dir(event) -> Path:
    return DATA_DIR / f"{event.year}_{event.id:04d}"


def _serialize(e):
    bounds = to_shape(e.bbox).bounds  # (minx, miny, maxx, maxy)
    return {
        'id':          e.id,
        'name':        e.name,
        'year':        e.year,
        'start_date':  e.start_date.isoformat() if e.start_date else None,
        'end_date':    e.end_date.isoformat() if e.end_date else None,
        'description': e.description,
        'bbox':        list(bounds),  # [minLon, minLat, maxLon, maxLat]
    }


@events_bp.route('/', methods=['GET'])
def list_events():
    events = FireEvent.query.order_by(FireEvent.year.desc()).all()
    return jsonify([_serialize(e) for e in events]), 200


@events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id: int):
    event = FireEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'event not found'}), 404
    return jsonify(_serialize(event)), 200


@events_bp.route('/<int:event_id>/layers/aoi', methods=['GET'])
@token_required
def get_aoi(event_id: int):
    event = FireEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'event not found'}), 404
    shape = to_shape(event.bbox)
    fc = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': mapping(shape), 'properties': {'name': event.name}}
    ]}
    return jsonify(fc), 200


@events_bp.route('/<int:event_id>/layers/community', methods=['GET'])
@token_required
def get_community(event_id: int):
    event = FireEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'event not found'}), 404
    lm_path = _event_dir(event) / 'landmarks.json'
    if not lm_path.exists():
        return jsonify({'type': 'FeatureCollection', 'features': []}), 200
    landmarks = json.loads(lm_path.read_text(encoding='utf-8'))
    features = [
        {'type': 'Feature',
         'geometry': {'type': 'Point', 'coordinates': [lm['lon'], lm['lat']]},
         'properties': {'name': lm['name'], 'type': lm.get('type', '')}}
        for lm in landmarks
    ]
    return jsonify({'type': 'FeatureCollection', 'features': features}), 200


@events_bp.route('/<int:event_id>/layers/roads', methods=['GET'])
@token_required
def get_static_roads(event_id: int):
    event = FireEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'event not found'}), 404
    roads_path = _event_dir(event) / 'data_processed' / 'roads' / 'roads_clipped.gpkg'
    if not roads_path.exists():
        return jsonify({'type': 'FeatureCollection', 'features': []}), 200
    gdf = gpd.read_file(roads_path)
    return jsonify(json.loads(gdf.to_json())), 200
