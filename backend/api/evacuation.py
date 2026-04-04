from flask import Blueprint, jsonify

evacuation_bp = Blueprint('evacuation', __name__)

@evacuation_bp.route('/', methods=['GET'])
def get_evacuation_data():
    # Test mock GeoJSON for the routes and safe zones
    evac_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-111.38, 56.73], 
                        [-111.30, 56.80], 
                        [-111.20, 56.85]  # End point (Safe Zone)
                    ]
                },
                "properties": {
                    "type": "route",
                    "name": "Highway 63 North Escape Route"
                }
            },
            {
                
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [-111.20, 56.85]
                },
                "properties": {
                    "type": "assembly",
                    "name": "Northern Safe Camp"
                }
            }
        ]
    }
    
    # Send the data back
    return jsonify(evac_geojson), 200