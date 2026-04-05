"""
backend/ml/inference.py
-----------------------
ML inference layer for wildfire spread risk zones.

Flow:
    1. build_prediction_features(study, t1, delta_t_h) → feature DataFrame
    2. WildfirePredictor.predict(feature_df, threshold) → prob + pred columns
    3. _build_risk_geojson(result_df) → merged GeoJSON polygons (low/med/high)

Results are cached as parquet under:
    <STUDY_DIR>/predictions/live/<t1_safe>_<delta_t>h/risk_zones.parquet
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

# ── Lazy imports (heavy libs loaded once at first call) ───────────────────────
_predictor = None
_study     = None


def _get_study():
    global _study
    if _study is None:
        import wildfire_hotspot_prediction as whp
        study_dir = os.environ.get("STUDY_DIR", "")
        if not study_dir:
            raise RuntimeError("STUDY_DIR not set in environment")
        _study = whp.Study(
            name        = os.environ.get("STUDY_NAME", "fort_mcmurray_2016"),
            bbox        = tuple(float(x) for x in os.environ.get(
                              "STUDY_BBOX", "-113.2,55.8,-109.3,57.6").split(",")),
            start_date  = os.environ.get("STUDY_START", "2016-05-01"),
            end_date    = os.environ.get("STUDY_END",   "2016-05-31"),
            project_dir = Path(study_dir),
        )
    return _study


def _get_predictor():
    global _predictor
    if _predictor is None:
        import wildfire_hotspot_prediction as whp
        study    = _get_study()
        models_dir = study.models_dir
        _predictor = whp.WildfirePredictor(models_dir=models_dir, model_name="xgb")
    return _predictor


# ── Thresholds ────────────────────────────────────────────────────────────────

def _load_threshold() -> float:
    """Return xgb decision threshold from model_full_thresholds.json."""
    study = _get_study()
    path  = study.models_dir / "model_full_thresholds.json"
    if path.exists():
        return json.loads(path.read_text()).get("xgb", 0.5)
    return 0.5


# Risk level probability boundaries
_HIGH_THRESH   = None   # loaded from model_full_thresholds.json (xgb threshold)
_MEDIUM_THRESH = 0.15   # fixed
_LOW_THRESH    = 0.05   # fixed (below this → not shown)


def _risk_level(prob: float, high_thresh: float) -> str | None:
    if prob >= high_thresh:
        return "high"
    if prob >= _MEDIUM_THRESH:
        return "medium"
    if prob >= _LOW_THRESH:
        return "low"
    return None


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(study, t1: pd.Timestamp, delta_t_h: float) -> Path:
    t1_safe = t1.strftime("%Y-%m-%dT%H%M")
    key     = f"{t1_safe}_{delta_t_h:.1f}h"
    return study.project_dir / "predictions" / "live" / key / "risk_zones.parquet"


def _load_cache(study, t1: pd.Timestamp, delta_t_h: float) -> pd.DataFrame | None:
    path = _cache_path(study, t1, delta_t_h)
    if path.exists():
        return pd.read_parquet(path)
    return None


def _save_cache(study, t1: pd.Timestamp, delta_t_h: float, df: pd.DataFrame) -> None:
    path = _cache_path(study, t1, delta_t_h)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


# ── GeoJSON builder ───────────────────────────────────────────────────────────

def _build_risk_geojson(df: pd.DataFrame, high_thresh: float) -> dict:
    """Merge 500m grid cells into risk-level polygons and return GeoJSON.

    Args:
        df: DataFrame with b_x, b_y, prob columns (EPSG:3978 coordinates).
        high_thresh: Probability threshold for "high" risk.

    Returns:
        GeoJSON FeatureCollection with features grouped by risk level.
    """
    import geopandas as gpd
    from shapely.geometry import box
    from shapely.ops import unary_union
    import pyproj
    from shapely.ops import transform as shapely_transform

    half = 250.0  # half of 500m cell

    # Assign risk levels
    df = df.copy()
    df["risk"] = df["prob"].apply(lambda p: _risk_level(p, high_thresh))
    df = df[df["risk"].notna()]

    if df.empty:
        return {"type": "FeatureCollection", "features": []}

    # Build transformer EPSG:3978 → EPSG:4326
    transformer = pyproj.Transformer.from_crs("EPSG:3978", "EPSG:4326", always_xy=True)

    def to_wgs84(geom):
        return shapely_transform(transformer.transform, geom)

    features = []
    for level in ("high", "medium", "low"):
        subset = df[df["risk"] == level]
        if subset.empty:
            continue

        # Build 500m square polygons for each cell
        polys = [
            box(row.b_x - half, row.b_y - half,
                row.b_x + half, row.b_y + half)
            for row in subset.itertuples()
        ]

        # Merge adjacent cells
        merged = unary_union(polys)
        wgs84  = to_wgs84(merged)

        features.append({
            "type": "Feature",
            "geometry": wgs84.__geo_interface__,
            "properties": {
                "risk":       level,
                "cell_count": len(subset),
                "prob_mean":  round(float(subset["prob"].mean()), 4),
                "prob_max":   round(float(subset["prob"].max()), 4),
            },
        })

    return {"type": "FeatureCollection", "features": features}


# ── Public API ────────────────────────────────────────────────────────────────

def get_risk_zones(t1: str, delta_t_h: float) -> dict:
    """Run ML inference and return GeoJSON risk zones.

    Results are cached on disk. Subsequent calls with the same (t1, delta_t_h)
    return the cached result immediately.

    Args:
        t1:        ISO timestamp string (e.g. "2016-05-03T08:54:00").
        delta_t_h: Hours ahead to predict (e.g. 3.0, 6.0, 12.0).

    Returns:
        Dict with keys: t1, t2, delta_t_h, geojson (FeatureCollection).
    """
    import wildfire_hotspot_prediction as whp

    study      = _get_study()
    predictor  = _get_predictor()
    high_thresh = _load_threshold()

    t1_ts = pd.Timestamp(t1)

    # ── Check cache ───────────────────────────────────────────────────────────
    cached = _load_cache(study, t1_ts, delta_t_h)
    if cached is not None:
        t2_ts = cached["t2"].iloc[0] if "t2" in cached.columns else None
        return {
            "t1":        cached["t1"].iloc[0].isoformat() if "t1" in cached.columns else t1,
            "t2":        t2_ts.isoformat() if t2_ts is not None else None,
            "delta_t_h": delta_t_h,
            "cached":    True,
            "geojson":   _build_risk_geojson(cached, high_thresh),
        }

    # ── Build features ────────────────────────────────────────────────────────
    feature_df = whp.build_prediction_features(study, t1=t1_ts, delta_t_h=delta_t_h)
    if feature_df.empty:
        return {
            "t1": t1, "t2": None, "delta_t_h": delta_t_h,
            "cached": False,
            "geojson": {"type": "FeatureCollection", "features": []},
        }

    t1_actual = feature_df["t1"].iloc[0]
    t2_actual = feature_df["t2"].iloc[0]

    # ── Predict ───────────────────────────────────────────────────────────────
    result_df = predictor.predict(feature_df, threshold=high_thresh)

    # ── Save cache ────────────────────────────────────────────────────────────
    cache_df = result_df[["b_grid_id", "b_x", "b_y", "t1", "t2", "prob", "pred"]].copy()
    _save_cache(study, t1_actual, delta_t_h, cache_df)

    return {
        "t1":        t1_actual.isoformat(),
        "t2":        t2_actual.isoformat(),
        "delta_t_h": delta_t_h,
        "cached":    False,
        "geojson":   _build_risk_geojson(result_df, high_thresh),
    }
