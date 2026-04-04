import sys
import threading
from pathlib import Path
from flask import Blueprint, jsonify

data_bp = Blueprint("data", __name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _BACKEND_DIR.parent / "data" / "scripts"
STATIC_DIR   = _BACKEND_DIR.parent / "data" / "static"

# Expected years per dataset (mirrors downloader URL dicts)
_LANDCOVER_YEARS  = [2014, 2024]
_COMMUNITY_YEARS  = [2011, 2016, 2021]
_POPULATION_YEARS = [2011, 2016, 2021]

# ── In-memory pipeline state ──────────────────────────────────────────────────

_state = {
    "pipeline_running": False,
    "current":          None,   # e.g. "landcover 2024"
    "error":            None,
}
_state_lock = threading.Lock()


def _set_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


# ── Dataset checks ────────────────────────────────────────────────────────────

def _check_landcover():
    ready, missing = [], []
    for year in _LANDCOVER_YEARS:
        d = STATIC_DIR / "landcover" / str(year)
        if d.exists() and any(d.glob("*.tif")):
            ready.append(year)
        else:
            missing.append(year)
    return {"ready": len(missing) == 0, "years": ready, "missing": missing}


def _check_community():
    ready, missing = [], []
    for year in _COMMUNITY_YEARS:
        d = STATIC_DIR / "community" / str(year)
        if d.exists() and any(d.glob("*.shp")):
            ready.append(year)
        else:
            missing.append(year)
    return {"ready": len(missing) == 0, "years": ready, "missing": missing}


def _check_population():
    ready, missing = [], []
    for year in _POPULATION_YEARS:
        d = STATIC_DIR / "population" / str(year)
        if d.exists() and any(d.glob("*.shp")):
            ready.append(year)
        else:
            missing.append(year)
    return {"ready": len(missing) == 0, "years": ready, "missing": missing}


def _check_osm():
    gpkg = STATIC_DIR / "osm" / "roads_canada.gpkg"
    return {"ready": gpkg.exists()}


def get_status() -> dict:
    datasets = {
        "landcover":  _check_landcover(),
        "community":  _check_community(),
        "population": _check_population(),
        "osm":        _check_osm(),
    }
    all_ready = all(v["ready"] for v in datasets.values())
    with _state_lock:
        pipeline_running = _state["pipeline_running"]
        current          = _state["current"]
        error            = _state["error"]

    return {
        "ready":            all_ready,
        "pipeline_running": pipeline_running,
        "current":          current,
        "error":            error,
        "datasets":         datasets,
    }


# ── Background pipeline ───────────────────────────────────────────────────────

def _run_pipeline():
    sys.path.insert(0, str(_SCRIPTS_DIR))
    try:
        from downloader.dl_landcover  import download_all as dl_lc
        from downloader.dl_community  import download_all as dl_com
        from downloader.dl_population import download_all as dl_pop
        from downloader.dl_osm        import download     as dl_osm

        _set_state(current="landcover")
        dl_lc()

        _set_state(current="community")
        dl_com()

        _set_state(current="population")
        dl_pop()

        _set_state(current="osm")
        dl_osm()

        _set_state(pipeline_running=False, current=None)

    except Exception as e:
        _set_state(pipeline_running=False, current=None, error=str(e))


def start_pipeline_if_needed():
    """Launch background download for any missing datasets. Called on app startup."""
    status = get_status()
    if status["ready"] or status["pipeline_running"]:
        return
    missing = [k for k, v in status["datasets"].items() if not v["ready"]]
    print(f"[data] Missing datasets: {missing}. Starting background download ...")
    _set_state(pipeline_running=True, error=None)
    t = threading.Thread(target=_run_pipeline, daemon=True)
    t.start()


# ── API ───────────────────────────────────────────────────────────────────────

@data_bp.route("/status")
def status():
    return jsonify(get_status())
