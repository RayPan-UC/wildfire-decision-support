"""
pipeline/predict/risk_zones.py
------------------------------
Convert ML prediction output (500m grid cells) → risk zone GeoJSON polygons.

Risk level thresholds (relative to Youden's J threshold):
    high   : prob >= youden_threshold
    medium : prob >= youden_threshold * 0.5
    low    : prob >= youden_threshold * 0.25
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

_MEDIUM_RATIO = 0.5
_LOW_RATIO    = 0.25


def load_youden_threshold(models_dir: Path, model_name: str = "rf") -> float:
    """Load Youden's J threshold from model_full_thresholds.json."""
    path = models_dir / "model_full_thresholds.json"
    if path.exists():
        return json.loads(path.read_text()).get(model_name, 0.5)
    log.warning("[risk_zones] thresholds.json not found — using 0.5")
    return 0.5


def _risk_level(prob: float, high_thresh: float) -> str | None:
    if prob >= high_thresh:
        return "high"
    if prob >= high_thresh * _MEDIUM_RATIO:
        return "medium"
    if prob >= high_thresh * _LOW_RATIO:
        return "low"
    return None


def build_risk_geojson(df: pd.DataFrame, high_thresh: float, horizon: str) -> dict:
    """Convert 500m grid cell predictions to merged risk-level polygons.

    Args:
        df:          DataFrame with b_x, b_y, prob columns (EPSG:3978).
        high_thresh: Youden's J threshold for 'high' risk.
        horizon:     Prediction horizon label, e.g. "3h", "6h", "12h".

    Returns:
        GeoJSON FeatureCollection with up to 3 features (high/medium/low).
    """
    import pyproj
    from shapely.geometry import box
    from shapely.ops import unary_union
    from shapely.ops import transform as shp_transform

    half = 250.0

    df = df.copy()
    df["risk"] = df["prob"].apply(lambda p: _risk_level(p, high_thresh))
    df = df[df["risk"].notna()]

    if df.empty:
        return {"type": "FeatureCollection", "features": []}

    transformer = pyproj.Transformer.from_crs("EPSG:3978", "EPSG:4326", always_xy=True)

    def to_wgs84(geom):
        return shp_transform(transformer.transform, geom)

    features = []
    for level in ("high", "medium", "low"):
        subset = df[df["risk"] == level]
        if subset.empty:
            continue
        polys  = [box(r.b_x - half, r.b_y - half, r.b_x + half, r.b_y + half)
                  for r in subset.itertuples()]
        merged = to_wgs84(unary_union(polys))
        features.append({
            "type": "Feature",
            "geometry": merged.__geo_interface__,
            "properties": {
                "horizon":    horizon,
                "risk_level": level,
                "cell_count": len(subset),
                "prob_mean":  round(float(subset["prob"].mean()), 4),
                "prob_max":   round(float(subset["prob"].max()),  4),
            },
        })

    return {"type": "FeatureCollection", "features": features}


def write_geojson(path: Path, features: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, allow_nan=False),
        encoding="utf-8",
    )
