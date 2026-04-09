"""
pipeline/check/builder.py
--------------------------
Pre-compute all event data before Flask starts.

Per-event pipeline:
  1. Load Study + fire_state → discover satellite overpass timesteps
  2. Upsert EventTimestep rows in DB
  3. Per timestep (skip if stage status == 'done'):
     a. predict  → GeoJSON files + fire_context.json (pipeline/predict/)
     b. spatial  → community risk GeoJSON + DB counts (pipeline/spatial/)

AI report (ai_summary.json) is generated on-demand via POST /api/timesteps/{id}/report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


# ── Path helpers ──────────────────────────────────────────────────────────────

def event_dir(event_id: int, year: int) -> Path:
    return _DATA_DIR / "events" / f"{year}_{event_id:04d}"


def timestep_dir(event_id: int, year: int, slot_time: pd.Timestamp) -> Path:
    return event_dir(event_id, year) / "timesteps" / slot_time.strftime("%Y-%m-%dT%H%M")


# ── Study / model loaders ─────────────────────────────────────────────────────

_MODELS_DIR = _DATA_DIR / "static" / "models"


def _load_study(event):
    import wildfire_hotspot_prediction as whp
    from shapely import wkb

    geom = wkb.loads(bytes(event.bbox.data))
    lon_min, lat_min, lon_max, lat_max = geom.bounds

    project_dir = _DATA_DIR / "events" / f"{event.year}_{event.id:04d}"
    return whp.Study(
        name        = event.name,
        bbox        = (lon_min, lat_min, lon_max, lat_max),
        start_date  = event.start_date.strftime("%Y-%m-%d"),
        end_date    = event.end_date.strftime("%Y-%m-%d"),
        project_dir = project_dir,
    )


def _load_fire_state(study):
    from wildfire_hotspot_prediction.training.fire_state import load_fire_state
    path = study.data_processed_dir / "training" / "fire_state.pkl"
    if not path.exists():
        raise FileNotFoundError(f"fire_state.pkl not found: {path}")
    return load_fire_state(path)


def _load_predictor():
    import wildfire_hotspot_prediction as whp
    return whp.WildfirePredictor(models_dir=_MODELS_DIR, model_name="lr_steps")


def _load_threshold() -> float:
    from pipeline.predict.risk_zones import load_youden_threshold
    return load_youden_threshold(_MODELS_DIR)


# ── Playback entry point ──────────────────────────────────────────────────────

def build_playback_events() -> None:
    """Pre-compute all replay events (end_date is set).
    Must be called inside an active Flask app context.
    """
    from db.models import FireEvent
    events = FireEvent.query.filter(FireEvent.end_date.isnot(None)).all()
    log.info("[builder] %d playback event(s) to process", len(events))
    for event in events:
        try:
            _build_event(event)
        except Exception as e:
            log.error("[builder] event %d (%s) failed: %s", event.id, event.name, e)


# ── Realtime entry point ──────────────────────────────────────────────────────

def build_realtime_events() -> None:
    """Start polling for realtime events (end_date is None).
    Must be called inside an active Flask app context.
    TODO: implement scheduler / FIRMS polling.
    """
    from db.models import FireEvent
    events = FireEvent.query.filter(FireEvent.end_date.is_(None)).all()
    if events:
        log.warning("[builder] %d realtime event(s) found — realtime pipeline not yet implemented",
                    len(events))


# ── Per-event orchestration ───────────────────────────────────────────────────

def _build_event(event) -> None:
    log.info("[builder] building event %d: %s", event.id, event.name)

    try:
        study      = _load_study(event)
        fire_state = _load_fire_state(study)
        predictor  = _load_predictor()
        threshold  = _load_threshold()
    except Exception as e:
        log.error("[builder] event %d setup failed: %s", event.id, e)
        return

    import wildfire_hotspot_prediction as whp
    try:
        pred_cache = whp.build_prediction_cache(study)
    except Exception as e:
        log.error("[builder] prediction cache failed: %s", e)
        return

    steps = sorted(fire_state.steps)
    slots = _generate_slots(event)
    print(f"[builder] {event.name}: {len(slots)} slots, {len(steps)} overpasses")

    timesteps = _upsert_timesteps(event.id, slots, steps)

    from tqdm import tqdm
    with tqdm(timesteps, desc=f"  {event.name}", unit="ts", dynamic_ncols=True) as pbar:
        for ts in pbar:
            _build_timestep(event, ts, study, fire_state, predictor, threshold, pred_cache, pbar)


# ── Slot generation ───────────────────────────────────────────────────────────

def _generate_slots(event) -> list[pd.Timestamp]:
    """Generate 3-hour canonical slots from event.start_date to event.end_date (tz-naive)."""
    from datetime import timedelta

    start = pd.Timestamp(event.start_date).floor("3h")
    # end_date is a date — treat end-of-day as the inclusive upper bound
    end = pd.Timestamp(event.end_date) + pd.Timedelta(hours=23, minutes=59)
    slots, t = [], start
    while t <= end:
        slots.append(t)
        t += timedelta(hours=3)
    return slots


def _nearest_past_t1(slot: pd.Timestamp, steps: list[pd.Timestamp]):
    """Return the most recent overpass at or before slot, or None."""
    past = [s for s in steps if s <= slot]
    return max(past) if past else None


# ── DB helpers ────────────────────────────────────────────────────────────────

_GAP_WARN_H = 12.0


def _upsert_timesteps(event_id: int, slots: list, steps: list) -> list:
    from db.models import EventTimestep
    from db.connection import db

    result = []
    for slot in slots:
        t1 = _nearest_past_t1(slot, steps)
        if t1 is None:
            continue   # no observation yet — skip slot

        gap_h = (slot - t1).total_seconds() / 3600.0
        if gap_h > _GAP_WARN_H:
            log.warning("[builder] slot %s: nearest T1 is %.1fh ago (%s)", slot, gap_h, t1)

        ts = EventTimestep.query.filter_by(event_id=event_id, slot_time=slot).first()
        if ts is None:
            ts = EventTimestep(
                event_id      = event_id,
                slot_time     = slot,
                nearest_t1    = t1,
                gap_hours     = round(gap_h, 2),
                data_gap_warn = gap_h > _GAP_WARN_H,
            )
            db.session.add(ts)
            db.session.flush()
        result.append(ts)

    db.session.commit()
    return result


def _set_status(ts_id: int, field: str, value: str) -> None:
    from db.models import EventTimestep
    from db.connection import db
    ts = EventTimestep.query.get(ts_id)
    if ts:
        setattr(ts, field, value)
        db.session.commit()


# ── Per-timestep orchestration ────────────────────────────────────────────────

def _build_timestep(event, ts, study, fire_state, predictor, threshold, pred_cache, pbar=None) -> None:
    from db.models import EventTimestep
    ts = EventTimestep.query.get(ts.id)

    if ts.prediction_status not in ("done", "failed"):
        _run_prediction_stage(event, ts, study, fire_state, predictor, threshold, pred_cache, pbar)
        ts = EventTimestep.query.get(ts.id)

    if ts.prediction_status == "done" and ts.spatial_analysis_status not in ("done", "failed"):
        _run_spatial_stage(event, ts, pbar)

    _run_weather_stage(event, ts, study, pbar)


def _run_prediction_stage(event, ts, study, fire_state, predictor, threshold, pred_cache, pbar=None) -> None:
    from pipeline.predict import run_prediction
    from tqdm import tqdm

    out_dir = timestep_dir(event.id, event.year, ts.slot_time) / "prediction"
    _set_status(ts.id, "prediction_status", "running")
    try:
        t1 = pd.Timestamp(ts.nearest_t1)
        if t1.tzinfo is not None:
            t1 = t1.tz_localize(None)   # strip tz only — fire_state keys are naive local time
        run_prediction(
            ts_id         = ts.id,
            overpass_time = t1,
            study         = study,
            fire_state    = fire_state,
            predictor     = predictor,
            threshold     = threshold,
            out_dir       = out_dir,
            pred_cache    = pred_cache,
        )
        _set_status(ts.id, "prediction_status", "done")
    except Exception as e:
        tqdm.write(f"[builder] prediction failed for ts {ts.id}: {e}")
        _set_status(ts.id, "prediction_status", "failed")


def _run_weather_stage(event, ts, study, pbar=None) -> None:
    from pipeline.weather import build_weather_forecast
    from tqdm import tqdm

    out_dir = timestep_dir(event.id, event.year, ts.slot_time) / "weather"
    if (out_dir / "forecast.json").exists():
        return
    try:
        t1 = pd.Timestamp(ts.nearest_t1)
        if t1.tzinfo is not None:
            t1 = t1.tz_localize(None)
        build_weather_forecast(study=study, t1=t1, out_dir=out_dir)
    except Exception as e:
        tqdm.write(f"[builder] weather forecast failed for ts {ts.id}: {e}")


def _run_spatial_stage(event, ts, pbar=None) -> None:
    from pipeline.spatial import run_spatial_analysis
    from db.models import EventTimestep
    from db.connection import db
    from tqdm import tqdm

    out_dir = timestep_dir(event.id, event.year, ts.slot_time) / "spatial_analysis"
    _set_status(ts.id, "spatial_analysis_status", "running")
    try:
        counts = run_spatial_analysis(event.id, ts.id, out_dir)
        if counts:
            # write road_summary into fire_context.json (not stored in DB)
            road_summary = counts.pop("road_summary", None)
            if road_summary is not None:
                _merge_fire_context(out_dir, road_summary)
            # store numeric counts in DB
            row = EventTimestep.query.get(ts.id)
            for k, v in counts.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            db.session.commit()
        _set_status(ts.id, "spatial_analysis_status", "done")
    except Exception as e:
        tqdm.write(f"[builder] spatial analysis failed for ts {ts.id}: {e}")
        _set_status(ts.id, "spatial_analysis_status", "failed")


def _merge_fire_context(spatial_out_dir: Path, road_summary: list) -> None:
    """Append road_summary into the sibling prediction/fire_context.json."""
    import math

    ctx_path = spatial_out_dir.parent / "prediction" / "fire_context.json"
    if not ctx_path.exists():
        return
    try:
        ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        ctx["road_summary"] = road_summary
        # Sanitize NaN/Inf values that json.dumps would write as non-standard tokens
        text = json.dumps(ctx, ensure_ascii=False, indent=2)
        import re
        text = re.sub(r'\bNaN\b', 'null', text)
        text = re.sub(r'\bInfinity\b', 'null', text)
        ctx_path.write_text(text, encoding="utf-8")
    except Exception as e:
        log.warning("[builder] could not merge road_summary into fire_context: %s", e)
