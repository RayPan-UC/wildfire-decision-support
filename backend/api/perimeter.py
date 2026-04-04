from flask import Blueprint, jsonify

perimeter_bp = Blueprint('perimeter', __name__)

@perimeter_bp.route('/', methods=['GET'])
def get_perimeter():
    # Test mock GeoJSON for a large polygon representing the burned area
    perimeter_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    # A polygon must close itself. The first and last coordinates are the same.
                    "coordinates": [[
                        [-111.40, 56.70], 
                        [-111.35, 56.75], 
                        [-111.25, 56.73], 
                        [-111.30, 56.65], 
                        [-111.40, 56.70]
                    ]]
                },
                "properties": {
                    "name": "Active Fire Perimeter"
                }
            }
        ]
    }
    
    # Send the data back to the frontend
    return jsonify(perimeter_geojson), 200