from flask import Blueprint, jsonify

# Create the blueprint
risk_zones_bp = Blueprint('risk_zones', __name__)

@risk_zones_bp.route('/', methods=['GET'])
def get_risk_zones():
    # In the future, ML models (Random Forest/XGBoost) will generate this data.
    # For now, we test mock GeoJSON polygons near Fort McMurray.
    
    risk_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-111.45, 56.65], [-111.35, 56.65], 
                        [-111.35, 56.70], [-111.45, 56.70], 
                        [-111.45, 56.65]
                    ]]
                },
                "properties": {
                    "level": "High",
                    "description": "+3h Spread Risk"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-111.30, 56.72], [-111.20, 56.72], 
                        [-111.20, 56.78], [-111.30, 56.78], 
                        [-111.30, 56.72]
                    ]]
                },
                "properties": {
                    "level": "Medium",
                    "description": "+6h Spread Risk"
                }
            }
        ]
    }
    
    # Send the GeoJSON to the frontend
    return jsonify(risk_geojson), 200