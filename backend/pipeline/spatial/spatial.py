"""
pipeline/spatial/spatial.py
----------------------------
Stage 2: Spatial analysis per timestep.

Inputs  (files):  prediction/perimeter.geojson
                  prediction/risk_zones_{3,6,12}h.geojson
                  data/events/<year>_<id>/landmarks.json
Inputs  (static): data/static/roads_canada.gpkg
                  data/static/population.gpkg

Outputs (files):  spatial_analysis/roads.geojson
Outputs (DB):     EventTimestep.affected_population, at_risk_*
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import geopandas as gpd
import pandas as pd

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

_ROAD_TYPES = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
}
_HW_RANK = {
    "motorway": 0, "trunk": 1, "primary": 2, "secondary": 3,
    "motorway_link": 4, "trunk_link": 5, "primary_link": 6, "secondary_link": 7,
}
_STATUS_RANK = {"burned": 0, "at_risk_3h": 1, "at_risk_6h": 2, "at_risk_12h": 3, "clear": 4}


# ── Entry point ───────────────────────────────────────────────────────────────

def run_spatial_analysis(event_id: int, ts_id: int, out_dir: Path) -> dict:
    """Run spatial analysis for one timestep.

    Returns dict of EventTimestep population count fields.
    """
    from db.models import FireEvent

    event   = FireEvent.query.get(event_id)
    ev_dir  = _DATA_DIR / "events" / f"{event.year}_{event_id:04d}"
    pred_dir = out_dir.parent / "prediction"
    out_dir.mkdir(parents=True, exist_ok=True)

    perimeter_geom = _load_geom(pred_dir / "perimeter.geojson")
    risk = {
        3:  _load_geom(pred_dir / "risk_zones_3h.geojson"),
        6:  _load_geom(pred_dir / "risk_zones_6h.geojson"),
        12: _load_geom(pred_dir / "risk_zones_12h.geojson"),
    }
    landmarks = _load_landmarks(ev_dir / "landmarks.json")
    bbox      = _event_bbox(event)

    # ── Roads ─────────────────────────────────────────────────────────────────
    roads_gdf = _build_roads(bbox, perimeter_geom, risk, landmarks)
    roads_gdf.to_file(out_dir / "roads.geojson", driver="GeoJSON")
    log.info("[spatial] ts=%d: roads.geojson written (%d features)", ts_id, len(roads_gdf))

    # ── Road summary (for fire_context.json) ──────────────────────────────────
    road_summary = _road_summary(roads_gdf)

    # ── Population ────────────────────────────────────────────────────────────
    counts = _population_counts(bbox, perimeter_geom, risk, event.year)
    counts["road_summary"] = road_summary

    log.info("[spatial] ts=%d: affected_population=%d", ts_id, counts.get("affected_population", 0))
    return counts


# ── Road analysis ─────────────────────────────────────────────────────────────

def _build_roads(bbox, perimeter_geom, risk: dict, landmarks: list) -> gpd.GeoDataFrame:
    roads_path = _DATA_DIR / "static" / "roads_canada.gpkg"
    if not roads_path.exists():
        log.warning("[spatial] roads_canada.gpkg not found — skipping road analysis")
        return gpd.GeoDataFrame(columns=["road_name","highway","status","cut_at","cut_location","geometry"],
                                geometry="geometry", crs="EPSG:4326")

    roads = gpd.read_file(roads_path, bbox=bbox)
    roads = roads[roads["highway"].isin(_ROAD_TYPES)].copy()
    roads["name"] = roads["name"].fillna("").str.strip()
    roads["road_name"] = roads["name"].where(roads["name"] != "", roads["highway"])

    # tag status per segment
    risk_geoms = {h: g for h, g in risk.items() if g is not None}
    burned     = roads.intersects(perimeter_geom) if perimeter_geom else pd.Series(False, index=roads.index)
    at_risk_3  = (roads.intersects(risk_geoms[3])  & ~burned)  if 3  in risk_geoms else pd.Series(False, index=roads.index)
    at_risk_6  = (roads.intersects(risk_geoms[6])  & ~burned & ~at_risk_3)  if 6  in risk_geoms else pd.Series(False, index=roads.index)
    at_risk_12 = (roads.intersects(risk_geoms[12]) & ~burned & ~at_risk_3 & ~at_risk_6) if 12 in risk_geoms else pd.Series(False, index=roads.index)

    roads["status"] = "clear"
    roads.loc[at_risk_12, "status"] = "at_risk_12h"
    roads.loc[at_risk_6,  "status"] = "at_risk_6h"
    roads.loc[at_risk_3,  "status"] = "at_risk_3h"
    roads.loc[burned,     "status"] = "burned"

    # cut point descriptions per named road
    cut_map = _build_cut_map(roads, perimeter_geom, risk_geoms, landmarks)

    # dissolve by road_name + status → MultiLineString
    agg = (
        roads.groupby(["road_name", "status"], as_index=False)
             .agg(highway=("highway", lambda s: min(s, key=lambda h: _HW_RANK.get(h, 99))))
    )
    dissolved = roads.dissolve(by=["road_name", "status"])[["geometry"]].reset_index()
    dissolved = dissolved.merge(agg, on=["road_name", "status"])

    dissolved["cut_at"]       = dissolved["road_name"].map(lambda r: cut_map.get(r, {}).get("cut_at"))
    dissolved["cut_location"] = dissolved["road_name"].map(lambda r: cut_map.get(r, {}).get("cut_location"))

    return gpd.GeoDataFrame(
        dissolved[["road_name", "highway", "status", "cut_at", "cut_location", "geometry"]],
        geometry="geometry", crs="EPSG:4326",
    )


def _build_cut_map(roads, perimeter_geom, risk_geoms: dict, landmarks: list) -> dict:
    zones = {}
    if perimeter_geom:
        zones["perimeter"] = perimeter_geom.boundary
    for h, g in risk_geoms.items():
        zones[f"at_risk_{h}h"] = g.boundary

    cut_map: dict[str, dict] = {}
    for zone_name, zone_boundary in zones.items():
        status_key = "burned" if zone_name == "perimeter" else zone_name
        for _, row in roads.iterrows():
            ix = row.geometry.intersection(zone_boundary)
            if ix.is_empty:
                continue
            pts = list(ix.geoms) if ix.geom_type == "MultiPoint" else [
                ix if ix.geom_type == "Point" else ix.centroid
            ]
            rn = row["road_name"]
            for pt in pts:
                loc = _describe_point(pt.x, pt.y, landmarks)
                entry = cut_map.setdefault(rn, {"cut_at": zone_name, "cut_location": loc})
                if _STATUS_RANK.get(status_key, 99) < _STATUS_RANK.get(
                    "burned" if entry["cut_at"] == "perimeter" else entry["cut_at"], 99
                ):
                    entry["cut_at"] = zone_name
                    entry["cut_location"] = loc
                elif zone_name == entry["cut_at"] and loc != entry["cut_location"]:
                    entry["cut_location"] += f" / {loc}"

    # replace "perimeter" with None in cut_at (already burned, no future cut)
    for v in cut_map.values():
        if v["cut_at"] == "perimeter":
            v["cut_at"] = None
            v["cut_location"] = None

    return cut_map


def _road_summary(roads_gdf: gpd.GeoDataFrame) -> list[dict]:
    """Compact summary of affected major roads for fire_context.json."""
    MAJOR = {"motorway", "trunk", "primary", "secondary"}
    major = roads_gdf[roads_gdf["highway"].isin(MAJOR)].copy()
    summary = []
    for road, grp in major.groupby("road_name"):
        if road in _ROAD_TYPES:        # unnamed segments
            continue
        worst = min(grp["status"], key=lambda s: _STATUS_RANK.get(s, 99))
        if worst == "clear":
            continue
        cut_at  = grp.iloc[0]["cut_at"]
        cut_loc = grp.iloc[0]["cut_location"]
        summary.append({
            "road":         road,
            "highway":      grp.iloc[0]["highway"],
            "worst_status": worst,
            "cut_at":       cut_at,
            "cut_location": cut_loc,
        })
    summary.sort(key=lambda x: _STATUS_RANK.get(x["worst_status"], 99))
    return summary


# ── Population counts ─────────────────────────────────────────────────────────

def _population_counts(bbox, perimeter_geom, risk: dict, fire_year: int | None) -> dict:
    pop_path = _DATA_DIR / "static" / "population.gpkg"
    if not pop_path.exists():
        log.warning("[spatial] population.gpkg not found — population counts unavailable")
        return {f: 0 for f in ["affected_population",
                                "at_risk_3h", "at_risk_6h", "at_risk_12h"]}

    census_year = _nearest_census_year(fire_year)
    da = gpd.read_file(pop_path, bbox=bbox, layer="dissemination_areas")
    da = da[da["census_year"] == census_year].to_crs("EPSG:4326")

    def pop_in(zone_geom, exclude_geom=None):
        if zone_geom is None:
            return 0
        mask = da.intersects(zone_geom)
        if exclude_geom is not None:
            mask &= ~da.intersects(exclude_geom)
        return int(da.loc[mask, "population"].sum())

    r3, r6, r12 = risk.get(3), risk.get(6), risk.get(12)
    return {
        "affected_population": pop_in(perimeter_geom),
        "at_risk_3h":          pop_in(r3, perimeter_geom),
        "at_risk_6h":          pop_in(r6, r3),
        "at_risk_12h":         pop_in(r12, r6),
    }


def _nearest_census_year(fire_year: int | None) -> int:
    for cy in [2021, 2016, 2011]:
        if fire_year is None or fire_year > cy:
            return cy
    return 2011


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_geom(path: Path):
    """Load first geometry from a GeoJSON as a single shapely geometry."""
    if not path.exists():
        return None
    gdf = gpd.read_file(path)
    if gdf.empty:
        return None
    from shapely.ops import unary_union
    return unary_union(gdf.geometry)


def _load_landmarks(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _event_bbox(event) -> tuple[float, float, float, float]:
    from shapely import wkb
    geom = wkb.loads(bytes(event.bbox.data))
    return geom.bounds  # (lon_min, lat_min, lon_max, lat_max)


def _haversine_km(lon1, lat1, lon2, lat2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _bearing_label(lon1, lat1, lon2, lat2) -> str:
    dlon = math.radians(lon2 - lon1)
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon)
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round((math.degrees(math.atan2(x, y)) + 360) % 360 / 45) % 8]


def _describe_point(lon: float, lat: float, landmarks: list) -> str:
    if not landmarks:
        return f"{lat:.3f}N {abs(lon):.3f}W"
    best = min(landmarks, key=lambda p: _haversine_km(lon, lat, p["lon"], p["lat"]))
    dist = _haversine_km(lon, lat, best["lon"], best["lat"])
    bear = _bearing_label(best["lon"], best["lat"], lon, lat)
    return f"near {best['name']}" if dist < 5 else f"{bear} of {best['name']}, {dist:.0f} km"
