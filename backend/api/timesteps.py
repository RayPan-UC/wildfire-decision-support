"""
api/timesteps.py
----------------
All per-timestep endpoints.

Routes (registered under /api):
    GET  /events/<id>/timesteps
    GET  /events/<id>/timesteps/<ts_id>/perimeter
    GET  /events/<id>/timesteps/<ts_id>/hotspots
    GET  /events/<id>/timesteps/<ts_id>/risk-zones
    GET  /events/<id>/timesteps/<ts_id>/roads
    GET  /events/<id>/timesteps/<ts_id>/analysis
    GET  /events/<id>/timesteps/<ts_id>/fire-context
    POST /events/<id>/timesteps/<ts_id>/report      ← on-demand AI report
    POST /events/<id>/chat
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context

timesteps_bp = Blueprint("timesteps", __name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# ── Path helpers ──────────────────────────────────────────────────────────────

def _pred_dir(event_id: int, year: int, slot_time) -> Path:
    import pandas as pd
    ts_str = pd.Timestamp(slot_time).strftime("%Y-%m-%dT%H%M")
    return _DATA_DIR / "events" / f"{year}_{event_id:04d}" / "timesteps" / ts_str / "prediction"


def _spatial_dir(event_id: int, year: int, slot_time) -> Path:
    import pandas as pd
    ts_str = pd.Timestamp(slot_time).strftime("%Y-%m-%dT%H%M")
    return _DATA_DIR / "events" / f"{year}_{event_id:04d}" / "timesteps" / ts_str / "spatial_analysis"


def _get_event_and_ts(event_id: int, ts_id: int):
    """Load FireEvent + EventTimestep, or return (None, error_response)."""
    from db.models import FireEvent, EventTimestep
    event = FireEvent.query.get(event_id)
    if not event:
        return None, (jsonify({"error": "event not found"}), 404)
    ts = EventTimestep.query.filter_by(id=ts_id, event_id=event_id).first()
    if not ts:
        return None, (jsonify({"error": "timestep not found"}), 404)
    return (event, ts), None


def _read_geojson(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"type": "FeatureCollection", "features": []}


def _read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


# ── Routes ────────────────────────────────────────────────────────────────────

@timesteps_bp.route("/events/<int:event_id>/timesteps", methods=["GET"])
def list_timesteps(event_id: int):
    from db.models import FireEvent, EventTimestep
    event = FireEvent.query.get(event_id)
    if not event:
        return jsonify({"error": "event not found"}), 404

    rows = (
        EventTimestep.query
        .filter_by(event_id=event_id)
        .order_by(EventTimestep.slot_time)
        .all()
    )
    return jsonify([{
        "id":                      ts.id,
        "slot_time":               ts.slot_time.isoformat(),
        "nearest_t1":              ts.nearest_t1.isoformat(),
        "gap_hours":               ts.gap_hours,
        "data_gap_warn":           ts.data_gap_warn,
        "prediction_status":       ts.prediction_status,
        "spatial_analysis_status": ts.spatial_analysis_status,
    } for ts in rows]), 200


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/perimeter", methods=["GET"])
def get_perimeter(event_id: int, ts_id: int):
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result
    return jsonify(_read_geojson(_pred_dir(event.id, event.year, ts.slot_time) / "perimeter.geojson")), 200


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/hotspots", methods=["GET"])
def get_hotspots(event_id: int, ts_id: int):
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result
    return jsonify(_read_geojson(_pred_dir(event.id, event.year, ts.slot_time) / "hotspots.geojson")), 200


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/risk-zones", methods=["GET"])
def get_risk_zones(event_id: int, ts_id: int):
    """Return all 3 horizons combined as one FeatureCollection."""
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result
    pred = _pred_dir(event.id, event.year, ts.slot_time)

    features = []
    for h in ("3h", "6h", "12h"):
        fc = _read_geojson(pred / f"risk_zones_{h}.geojson")
        features.extend(fc.get("features", []))

    return jsonify({"type": "FeatureCollection", "features": features}), 200


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/roads", methods=["GET"])
def get_roads(event_id: int, ts_id: int):
    """Return roads.geojson — major roads with status (burned/at_risk_Xh/clear)
    and cut_at/cut_location for threatened segments."""
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result
    path = _spatial_dir(event.id, event.year, ts.slot_time) / "roads.geojson"
    return jsonify(_read_geojson(path)), 200


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/analysis", methods=["GET"])
def get_analysis(event_id: int, ts_id: int):
    """Return population counts from DB."""
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    _, ts = result
    return jsonify({
        "affected_population": ts.affected_population,
        "at_risk_3h":          ts.at_risk_3h,
        "at_risk_6h":          ts.at_risk_6h,
        "at_risk_12h":         ts.at_risk_12h,
    }), 200


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/fire-context", methods=["GET"])
def get_fire_context(event_id: int, ts_id: int):
    """Return fire_context.json (fire metrics, weather, FWI, wind forecast, road summary)."""
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result
    path = _pred_dir(event.id, event.year, ts.slot_time) / "fire_context.json"
    if not path.exists():
        return jsonify({"error": "fire context not yet available"}), 404
    return Response(path.read_text(encoding="utf-8"), mimetype="application/json"), 200


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/report", methods=["POST"])
def generate_report(event_id: int, ts_id: int):
    """Generate AI situation report on-demand. Returns cached result if available.

    Response:
        {
            "situation_overview":  "...",
            "risk_analysis":       "...",
            "impact_analysis":     "...",
            "evacuation_analysis": "..."
        }
    """
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result

    report_path = _spatial_dir(event.id, event.year, ts.slot_time) / "ai_summary.json"

    if report_path.exists():
        return Response(report_path.read_text(encoding="utf-8"), mimetype="application/json"), 200

    fire_context = _read_json(_pred_dir(event.id, event.year, ts.slot_time) / "fire_context.json")
    if not fire_context:
        return jsonify({"error": "fire context not available — run prediction first"}), 422

    population = {
        "affected_population": ts.affected_population,
        "at_risk_3h":          ts.at_risk_3h,
        "at_risk_6h":          ts.at_risk_6h,
        "at_risk_12h":         ts.at_risk_12h,
    }

    from agents import (
        run_risk_agent, run_impact_agent,
        run_evacuation_agent, run_summary_agent,
    )

    try:
        summary = {
            "risk_analysis":       run_risk_agent(fire_context),
            "impact_analysis":     run_impact_agent(fire_context, population),
            "evacuation_analysis": run_evacuation_agent(fire_context),
        }
        summary["situation_overview"] = run_summary_agent(
            summary["risk_analysis"],
            summary["impact_analysis"],
            summary["evacuation_analysis"],
        )
    except Exception as e:
        return jsonify({"error": f"AI agent failed: {e}"}), 502

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify(summary), 200


@timesteps_bp.route("/events/<int:event_id>/chat", methods=["POST"])
def chat(event_id: int):
    """Stateless chat endpoint. Streams response from chat_agent.

    Request body:
        {
            "message":     "...",
            "timestep_id": 42,
            "history":     [{"role": "user"|"assistant", "content": "..."}]
        }
    """
    body       = request.get_json(force=True)
    message    = body.get("message", "").strip()
    ts_id      = body.get("timestep_id")
    history    = body.get("history", [])

    if not message:
        return jsonify({"error": "message required"}), 400

    summary = ""
    road_summary = []
    if ts_id:
        result, _ = _get_event_and_ts(event_id, ts_id)
        if result:
            event_obj, ts_obj = result
            ai_data = _read_json(_spatial_dir(event_obj.id, event_obj.year, ts_obj.slot_time) / "ai_summary.json")
            summary = ai_data.get("situation_overview", "")
            ctx = _read_json(_pred_dir(event_obj.id, event_obj.year, ts_obj.slot_time) / "fire_context.json")
            road_summary = ctx.get("road_summary", [])

    from agents.chat_agent import run_chat_agent

    return Response(
        stream_with_context(run_chat_agent(summary=summary, road_summary=road_summary, message=message, history=history)),
        mimetype="text/plain",
    )
