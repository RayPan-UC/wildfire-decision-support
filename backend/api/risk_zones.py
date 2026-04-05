from flask import Blueprint, jsonify, request
from ml.inference import get_risk_zones

risk_zones_bp = Blueprint('risk_zones', __name__)


@risk_zones_bp.route('/', methods=['GET'])
def risk_zones():
    """Return ML-predicted wildfire spread risk zones as GeoJSON.

    Query params:
        t1        ISO timestamp, e.g. "2016-05-03T08:54:00"
        delta_t_h Hours ahead to predict: 3.0 / 6.0 / 12.0  (default 6.0)

    Response:
        {
          "t1":        "2016-05-03T08:54:00",
          "t2":        "2016-05-03T14:54:00",
          "delta_t_h": 6.0,
          "cached":    false,
          "geojson":   { GeoJSON FeatureCollection }
        }
    """
    t1        = request.args.get("t1", "2016-05-03T08:54:00")
    delta_t_h = float(request.args.get("delta_t_h", 6.0))

    try:
        result = get_risk_zones(t1=t1, delta_t_h=delta_t_h)
        return jsonify(result), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500
