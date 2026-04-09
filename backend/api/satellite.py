"""
api/satellite.py
----------------
Date-aware Sentinel-2 satellite imagery via Sentinel Hub APIs.

Routes:
    GET /api/satellite/scene?date=YYYY-MM-DD&event_id=<id>
        → Catalog API: find nearest S2 scene within ±15 days
        → Returns { acquired, cloud_cover, collection }

    GET /api/satellite/tile/<int:z>/<int:x>/<int:y>?date=YYYY-MM-DD
        → Process API tile proxy (256×256 PNG)
        → OAuth2 token cached server-side; credentials never exposed to browser

Collections used:
    2015-11 → 2016-12 : sentinel-2-l1c  (L2A not yet globally available)
    2017-01 → present  : sentinel-2-l2a
"""

from __future__ import annotations

import math
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from flask import Blueprint, Response, jsonify, request
from utils.auth_middleware import token_required

satellite_bp = Blueprint("satellite", __name__)
log = logging.getLogger(__name__)

_SH_TOKEN_URL   = "https://services.sentinel-hub.com/oauth/token"
_SH_CATALOG_URL = "https://services.sentinel-hub.com/api/v1/catalog/1.0.0/search"
_SH_PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"

_SEARCH_WINDOW_DAYS = 15   # look ±15 days for nearest scene
_TILE_SIZE  = 256
_TILE_CACHE = Path(__file__).resolve().parents[2] / "data" / "cache" / "satellite"

# ── OAuth2 token cache ────────────────────────────────────────────────────────

_token_cache: dict = {"token": None, "expires": 0.0}


def _get_token() -> str | None:
    client_id     = os.environ.get("SENTINELHUB_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SENTINELHUB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    if time.time() < _token_cache["expires"] - 60:
        return _token_cache["token"]

    try:
        r = requests.post(
            _SH_TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        _token_cache["token"]   = data["access_token"]
        _token_cache["expires"] = time.time() + data.get("expires_in", 3600)
        return _token_cache["token"]
    except Exception as e:
        log.error("[satellite] token request failed: %s", e)
        return None


# ── Collection selection ──────────────────────────────────────────────────────

def _collection(date_str: str) -> str:
    """L2A is globally available from 2017-01-01; use L1C before that."""
    try:
        if datetime.strptime(date_str, "%Y-%m-%d") < datetime(2017, 1, 1):
            return "sentinel-2-l1c"
    except ValueError:
        pass
    return "sentinel-2-l2a"


# ── Catalog search ────────────────────────────────────────────────────────────

_scene_cache: dict = {}   # (event_id, date) → scene dict or None


def _get_event_bbox(event_id: int):
    try:
        from db.models import FireEvent
        from flask import current_app
        with current_app.app_context():
            event = FireEvent.query.get(event_id)
            if not event:
                return None
            from geoalchemy2.shape import to_shape
            return list(to_shape(event.bbox).bounds)   # [minx, miny, maxx, maxy]
    except Exception as e:
        log.error("[satellite] bbox lookup: %s", e)
        return None


def _search_nearest_scene(token: str, date_str: str, bbox: list) -> dict | None:
    collection = _collection(date_str)
    d = datetime.strptime(date_str, "%Y-%m-%d")
    d_from = (d - timedelta(days=_SEARCH_WINDOW_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    d_to   = d.strftime("%Y-%m-%dT23:59:59Z")   # never look into the future

    payload = {
        "bbox":        bbox,
        "datetime":    f"{d_from}/{d_to}",
        "collections": [collection],
        "limit":       50,
        "fields": {
            "include": ["id", "properties.datetime", "properties.eo:cloud_cover"],
        },
    }

    try:
        r = requests.post(
            _SH_CATALOG_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        features = r.json().get("features", [])
    except Exception as e:
        log.error("[satellite] catalog search failed: %s", e)
        return None

    if not features:
        return None

    # Pick feature closest to target date (by acquisition time)
    target_ts = d.timestamp()
    def date_diff(f):
        acq = f["properties"].get("datetime", "")[:10]
        try:
            return abs(datetime.strptime(acq, "%Y-%m-%d").timestamp() - target_ts)
        except ValueError:
            return 1e9

    best = min(features, key=date_diff)
    props = best["properties"]
    raw_dt = props.get("datetime", "")
    acquired = raw_dt[:16].replace("T", " ") if len(raw_dt) >= 16 else raw_dt[:10]
    return {
        "acquired":     acquired,          # "YYYY-MM-DD HH:MM"
        "cloud_cover":  round(props.get("eo:cloud_cover", 0.0) / 100, 3),
        "collection":   collection,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@satellite_bp.route("/scene", methods=["GET"])
@token_required
def get_scene():
    """Find nearest Sentinel-2 scene for event + date.

    Returns: { acquired, cloud_cover, collection }
    """
    token = _get_token()
    if not token:
        return jsonify({"error": "Sentinel Hub credentials not configured"}), 503

    date_str = request.args.get("date", "")
    event_id = request.args.get("event_id", type=int)
    if not date_str or not event_id:
        return jsonify({"error": "date and event_id required"}), 400

    cache_key = (event_id, date_str)
    if cache_key in _scene_cache:
        cached = _scene_cache[cache_key]
        if cached is None:
            return jsonify({"error": "no scene found"}), 404
        return jsonify(cached), 200

    bbox = _get_event_bbox(event_id)
    if bbox is None:
        return jsonify({"error": "event not found"}), 404

    scene = _search_nearest_scene(token, date_str, bbox)
    _scene_cache[cache_key] = scene
    if scene is None:
        return jsonify({"error": f"no Sentinel-2 scene near {date_str}"}), 404

    return jsonify(scene), 200


@satellite_bp.route("/tile/<int:z>/<int:x>/<int:y>", methods=["GET"])
@token_required
def get_tile(z: int, x: int, y: int):
    """Proxy a 256×256 Sentinel-2 true-colour tile from the Processing API.

    Query params:
        date       (YYYY-MM-DD): target acquisition date
        collection (optional):   sentinel-2-l1c | sentinel-2-l2a
    """
    token = _get_token()
    if not token:
        return Response(status=503)

    date_str   = request.args.get("date", "")
    collection = request.args.get("collection") or _collection(date_str)
    if not date_str:
        return Response(status=400)

    # Serve from file cache if available
    cache_file = _TILE_CACHE / date_str / str(z) / str(x) / f"{y}.png"
    if cache_file.exists():
        log.debug("[satellite] cache hit %s/%d/%d/%d", date_str, z, x, y)
        return Response(cache_file.read_bytes(), mimetype="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})

    bbox = _tile_to_bbox(z, x, y)
    px   = _required_pixels(z, y)   # ensure ≤ 200 m/px for S2L1C

    # Use exact-day window; the frontend already chose the best acquisition date
    d_from = date_str + "T00:00:00Z"
    d_to   = date_str + "T23:59:59Z"

    evalscript = """
//VERSION=3
function setup() {
  return { input: ["B04","B03","B02","dataMask"], output: { bands: 4 } };
}
function evaluatePixel(s) {
  return [3.5*s.B04, 3.5*s.B03, 3.5*s.B02, s.dataMask];
}
"""

    payload = {
        "input": {
            "bounds": {
                "bbox":       bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [{
                "type": collection,
                "dataFilter": {
                    "timeRange":       {"from": d_from, "to": d_to},
                    "maxCloudCoverage": 100,
                    "mosaickingOrder":  "leastCC",
                },
            }],
        },
        "output": {
            "width":  px,
            "height": px,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
        },
        "evalscript": evalscript,
    }

    try:
        r = requests.post(
            _SH_PROCESS_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if r.status_code == 200:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(r.content)
            log.debug("[satellite] cached %s/%d/%d/%d", date_str, z, x, y)
            return Response(r.content, mimetype="image/png",
                            headers={"Cache-Control": "public, max-age=86400"})
        log.warning("[satellite] tile %d/%d/%d failed: %d — %s",
                    z, x, y, r.status_code, r.text[:400])
        return Response(status=r.status_code)
    except Exception as e:
        log.error("[satellite] tile proxy error: %s", e)
        return Response(status=502)


# ── Tile math ─────────────────────────────────────────────────────────────────

def _required_pixels(z: int, y: int, max_mpp: float = 200.0) -> int:
    """Return pixel count needed so the tile stays within max_mpp metres/pixel."""
    n = 2 ** z
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n)))
    tile_deg = 360.0 / n
    tile_m   = tile_deg * 111_320 * math.cos(lat_rad)
    return min(2048, max(_TILE_SIZE, math.ceil(tile_m / max_mpp)))


def _tile_to_bbox(z: int, x: int, y: int) -> list[float]:
    """Convert slippy map tile coordinates to [west, south, east, north] WGS84."""
    n = 2 ** z
    west  =  x / n * 360.0 - 180.0
    east  = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return [west, south, east, north]
