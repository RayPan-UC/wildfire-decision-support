from flask import Blueprint, jsonify

hotspots_bp = Blueprint('hotspots', __name__)

@hotspots_bp.route('/', methods=['GET'])
def get_hotspots():
    
    # Testing mock GeoJSON data for the hotspots
    hotspots_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-111.38, 56.73]},
                "properties": {"intensity": "High"}
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-111.45, 56.68]},
                "properties": {"intensity": "Extreme"}
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-111.30, 56.70]},
                "properties": {"intensity": "Medium"}
            }
        ]
    }
    
    # Send the data back to the frontend
    return jsonify(hotspots_geojson), 200