# Project Structure

```
wildfire-decision-support/
│
├── .env                          # Environment variables (local, not committed)
├── .env.example                  # Template for .env
├── requirements.txt              # Python dependencies
├── PROJECT_STRUCTURE.md
│
├── backend/                      # Flask application
│   ├── main.py                   # Entry point: setup_db (sync) → Flask; pipeline in background thread
│   ├── config.py                 # Loads .env variables
│   │
│   ├── api/                      # API route blueprints
│   │   ├── __init__.py
│   │   ├── auth.py               # POST /api/auth/register, login, verify; is_admin in JWT + verify response
│   │   ├── config.py             # GET  /api/config — frontend feature flags
│   │   ├── events.py             # GET  /api/events, /api/events/:id; GET/POST /events/:id/replay-time (shared virtual clock, persisted to fire_events.replay_ms)
│   │   ├── firms.py              # GET  /api/firms/realtime, POST /api/firms/refresh
│   │   ├── satellite.py          # GET  /api/satellite/scene, /api/satellite/tile/:z/:x/:y
│   │   ├── timesteps.py          # Blueprint + helpers + control routes (/status, /run-prediction, /chat)
│   │   │                         #   /run-prediction: {force, crowd} params; crowd branch → build_single_timestep_ondemand_crowd
│   │   │                         #   /status: prediction_status, spatial_analysis_status, crowd_prediction_status, spatial_crowd_status
│   │   ├── ts_prediction_routes.py  # perimeter(?crowd=true→perimeter_crowd.geojson), hotspots(?crowd=true), risk-zones(?crowd=true), risk-zones-wind, actual-perimeter, fire-context
│   │   ├── ts_data_routes.py     # weather, wind-field, roads, population, report, report-with-crowd
│   │   │                         #   _build_road_summary(): major non-clear roads from roads.geojson → evacuation agent input
│   │   │                         #   generate_report: loads landmarks.json → passes (fire_context, road_summary, landmarks) to evacuation agent
│   │   │   ├── crowd.py              # field-reports, themes, comments, likes
│   │   │                         #   clear_field_reports: deletes DB rows + purges crowd disk files (hotspots_crowd, perimeter_crowd, ML_crowd/, spatial_analysis_crowd/)
│   │   │                         #   bg_assess_and_cluster disabled — no theme generation
│   │   └── crowd_processing.py   # bg_assess_and_cluster (disabled), _maybe_generate_theme, _haversine_km
│   │
│   ├── build_env/                # Startup pipeline (runs before Flask)
│   │   ├── __init__.py
│   │   ├── db/
│   │   │   └── __init__.py       # setup_db(app): ensure_db + migrate + create_all + seed_db
│   │   ├── env.py                # prepare_all_events(): ERA5 + FIRMS + fire_state + landmarks
│   │   ├── check/
│   │   │   ├── __init__.py       # run_checks()
│   │   │   ├── builder.py        # build_slots_only() · build_single_timestep_ondemand(app, ts_id)
│   │   │   │                     #   build_single_timestep_ondemand_crowd(app, ts_id) — crowd pipeline (ML_crowd/ + spatial_crowd/)
│   │   │   │                     #     Step3: hotspots_crowd.geojson (avg FRP from VIIRS, fallback 30.0 MW); Step4: perimeter_crowd.geojson
│   │   │   │                     #   _augment_with_crowd() uses avg_frp from existing hotspots
│   │   │   │                     #   _get_event_assets(event) → module-level cache
│   │   │   │                     #   _predictor_cache, _threshold_cache (loaded once per process)
│   │   │   │                     #   _patch_whp_caches() — caches whp disk reads
│   │   │   │                     #   _build_selectors_parquet() — pre-builds selectors.parquet at startup
│   │   │   │                     #   No-crowd early return writes _write_status(sp_crowd,"done") to unblock poll
│   │   │   ├── builder_slots.py  # _generate_slots, _nearest_past_t1, _upsert_timesteps
│   │   │   │                     #   _running: set[str] — in-memory "running" status (never written to disk; vanishes on restart)
│   │   │   │                     #   _write_status("running") → _mark_running() only; _read_status() checks set before STATUS.json
│   │   │   └── builder_stages.py # _run_prediction_stage, _run_weather_stage, _run_perimeter_stage, _run_spatial_stage
│   │   │                         #   _run_spatial_stage_crowd(event, ts, crow_dir, sp_crowd) — crowd spatial analysis
│   │   ├── predict/
│   │   │   ├── __init__.py
│   │   │   ├── prediction.py     # ML inference → GeoJSON files + fire_context.json
│   │   │   └── risk_zones.py     # build_risk_geojson(), load_youden_threshold()
│   │   ├── spatial/
│   │   │   ├── __init__.py
│   │   │   ├── spatial.py        # roads + population overlay → roads.geojson + DB counts
│   │   │   │                     #   status: burning (active hotspot) | burned (perimeter, no hotspot) | at_risk_{3,6,12}h | clear
│   │   │   │                     #   sections: [{section_id, from, to}] per road feature; 2 km gap-merge; exclusive zone clipping
│   │   │                     #   sections serialized as JSON string in GeoJSON (fiona compat); deserialized in API + frontend
│   │   │   └── spatial_helpers.py  # population_counts, load_geom, load_landmarks, event_bbox, haversine_km, bearing_label, describe_point
│   │   └── weather/
│   │       ├── __init__.py
│   │       └── weather_forecast.py  # ERA5 → forecast.json + wind_field.json per timestep
│   │
│   ├── agents/                   # AI agents (on-demand + background)
│   │   ├── __init__.py
│   │   ├── _client.py            # call_llm() / stream_llm() — Claude or Gemini
│   │   ├── prompts.py            # System prompts for all agents
│   │   ├── risk_agent.py         # fire_context → risk analysis text
│   │   ├── impact_agent.py       # fire_context + population → impact text
│   │   ├── evacuation_agent.py   # (fire_context, road_summary, landmarks) → TOP ROUTE + ALTERNATIVE ROUTE with landmark waypoints
│   │   ├── summary_agent.py      # 3 agent outputs → executive briefing
│   │   ├── chat_agent.py         # Stateless streaming chat
│   │   └── crowd_agent.py        # assess_photo_intensity() + generate_theme()
│   │
│   ├── db/
│   │   ├── connection.py         # db, get_db_uri(), ensure_db(), seed_db() [seeds admin/admin with is_admin=True]
│   │   └── models.py             # ORM: User (is_admin), FireEvent, EventTimestep,
│   │                             #      FieldReport (like_count, flag_count), FieldReportComment (like_count),
│   │                             #      Theme, ThemeComment
│   │
│   ├── sim_ai/                   # Self-contained field-report simulator (GIS-informed AI)
│   │   ├── __init__.py           # exposes simulate_bp
│   │   ├── prompt.py             # SIMULATE_REPORTS_SYSTEM: 10h window, fire/road placement, 6 info scenarios, 3-4 comments/report, assembly point ≥5km from fire
│   │   ├── geospatial.py         # extract_gis_context(event, ts_row) → GisContext (perimeter_pts, road_pts, landmark_pts, slot_time)
│   │   ├── generator.py          # generate_reports(bbox, n, hints, ctx) → list[dict] with created_at + comments[]
│   │   └── routes.py             # POST /<event_id>/field-reports/simulate — persists reports + comments with backfilled created_at
│   │
│   └── utils/
│       ├── auth_middleware.py    # JWT verification middleware
│       └── background.py        # run_in_background(fn, *args) — threading.Thread wrapper
│
│   # Startup sweep: _sweep_desynced_timesteps(app) in main.py resets "done"/"failed" status
│   # to 'pending' if fire_context.json sentinel is missing (file/status desync after manual cache delete)
│   # "running" status is in-memory only — vanishes automatically on restart, no sweep needed
│
├── frontend/                     # Static frontend (served by Flask via Jinja2)
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── api.js                # HTTP client + all endpoint wrappers (API_BASE = window.location.origin)
│   │   ├── app.js                # SPA controller, routing, DEV console
│   │   ├── map.js                # Leaflet map, risk layers, wind animation
│   │   ├── dashboard.js          # Fire metrics, weather, FWI, population cards
│   │   ├── chat.js               # AI report + streaming chat
│   │   └── crowd.js              # Field report form, theme display, comments/likes
│   └── templates/
│       ├── index.html            # Base template (extends nothing; includes all partials)
│       ├── _header.html          # Nav bar + auth state
│       ├── _home_view.html       # Home: FIRMS heatmap + event list
│       ├── _event_view.html      # Event: map + dashboard + AI panel
│       ├── _auth_modal.html      # Login / register modal
│       ├── _ai_modal.html        # AI report modal
│       └── _crowd_panel.html     # Field report form + theme list
│
├── data/
│   ├── uploads/                  # User-uploaded photos → {report_id}.{ext}
│   ├── cache/                    # FIRMS + satellite tile cache
│   │   └── satellite/            # Sentinel-2 tile cache by date/z/x/y
│   ├── events/                   # Per-event data (generated by pipeline)
│   │   └── 2016_0001/            # {year}_{event_id:04d}
│   │       ├── landmarks.json
│   │       ├── data_processed/
│   │       │   ├── grid_static.parquet
│   │       │   ├── weather/
│   │       │   │   ├── era5.parquet
│   │       │   │   ├── ffmc_daily.parquet
│   │       │   │   ├── isi_hourly.parquet
│   │       │   │   └── ros_hourly.parquet
│   │       │   ├── landcover/
│   │       │   │   └── fuel_type.tif
│   │       │   ├── firms/
│   │       │   │   └── hotspots.parquet
│   │       │   └── training/
│   │       │       └── fire_state.pkl
│   │       └── timesteps/
│   │           └── 2016-05-04T0600/           ← slot_time formatted YYYY-MM-DDTHHMM
│   │               ├── perimeter/             ← Stage 1: observed fire boundary at nearest_t1
│   │               │   ├── perimeter.geojson
│   │               │   └── perimeter_crowd.geojson  ← crowd pipeline: boundary_after union with 500m crowd buffers
│   │               ├── hotspot/               ← Stage 1: FIRMS satellite detections at nearest_t1
│   │               │   ├── hotspots.geojson
│   │               │   └── hotspots_crowd.geojson   ← crowd pipeline: VIIRS + crowd fire_reports (avg FRP)
│   │               ├── actual_perimeter/      ← Stage 1: ROS-weighted ground-truth perimeters
│   │               │   ├── 0h.geojson         #   base = yesterday (T_{-1}) actual perimeter
│   │               │   ├── 3h.geojson         #   base + scale(growth, w, origin=T1_centroid)
│   │               │   ├── 6h.geojson         #   growth = today (T_0) − yesterday (T_{-1}); w = cumROS[slot_h+Δh] / totalROS
│   │               │   └── 12h.geojson        #   scale origin = T1 centroid → growth expands outward from base
│   │               ├── weather/               ← Stage 1: ERA5 weather
│   │               │   ├── forecast.json      #   hourly area-avg +12h
│   │               │   └── wind_field.json    #   leaflet-velocity format
│   │               ├── prediction/            ← Stage 2 (on-demand)
│   │               │   ├── ML/
│   │               │   │   ├── STATUS.json    #   pending|done|failed  ("running" is in-memory only — never written to disk)
│   │               │   │   ├── risk_zones_3h.geojson
│   │               │   │   ├── risk_zones_6h.geojson
│   │               │   │   ├── risk_zones_12h.geojson
│   │               │   │   └── fire_context.json
│   │               │   └── wind_driven/
│   │               │       └── STATUS.json    #   pending (runner TBD)
│   │               └── spatial_analysis/      ← Stage 3 (on-demand, after ML)
│   │                   ├── STATUS.json
│   │                   ├── ML/
│   │                   │   ├── roads.geojson  #   road network with ML-based fire status
│   │                   │   │                  #   status: burning | burned | at_risk_3h | at_risk_6h | at_risk_12h | clear
│   │                   │   │                  #   sections: [{section_id, from, to}, ...] (empty for clear)
│   │                   │   └── population.json #  {affected_population, at_risk_3h/6h/12h}
│   │                   ├── wind_driven/
│   │                   │   ├── roads.geojson  #   placeholder (wind_driven runner TBD)
│   │                   │   └── population.json
│   │                   └── ai_summary.json    #   generated on first POST /report, cached
│   │
│   └── static/
│       ├── models/               # ML models (Zenodo: records/19435138)
│       │   ├── model_full_rf.pkl
│       │   ├── model_full_xgb.pkl
│       │   ├── model_full_lr.pkl
│       │   └── model_full_thresholds.json
│       ├── actual_perimeter/
│       │   └── actual_perimeter.gpkg  # Zenodo: records/19502692 — daily fire perimeters (date col required)
│       ├── population.gpkg       # Zenodo: records/19434352
│       └── roads_canada.gpkg     # Zenodo: records/19436338
│
└── docs/
    └── api.yaml
```

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/login` | Login → JWT |
| GET  | `/api/auth/verify` | Verify token |
| GET  | `/api/events` | List all fire events |
| GET  | `/api/events/:id` | Event detail + bbox |
| GET  | `/api/events/:id/replay-time` | Get shared virtual clock (ms) for this event |
| POST | `/api/events/:id/replay-time` | Admin only — set shared virtual clock |
| GET  | `/api/events/:id/timesteps` | List 1h slots (replay scrubber) |
| GET  | `/api/events/:id/timesteps/:ts_id/perimeter` | Fire perimeter GeoJSON (`?crowd=true` → `perimeter_crowd.geojson`) |
| GET  | `/api/events/:id/timesteps/:ts_id/hotspots` | Satellite hotspots GeoJSON |
| GET  | `/api/events/:id/timesteps/:ts_id/risk-zones` | Risk zones (3h/6h/12h combined) |
| GET  | `/api/events/:id/timesteps/:ts_id/roads?model=ML` | Roads GeoJSON (`ML` or `wind_driven`, default ML) |
| GET  | `/api/events/:id/timesteps/:ts_id/population?model=ML` | Population counts (`ML` or `wind_driven`, default ML) |
| GET  | `/api/events/:id/timesteps/:ts_id/weather` | ERA5 +12h area-avg forecast (pre-built at startup) |
| GET  | `/api/events/:id/timesteps/:ts_id/wind-field?hour=N` | Leaflet-velocity wind field per hour |
| GET  | `/api/events/:id/timesteps/:ts_id/risk-zones-wind` | Wind-driven risk zones rooted at T1 hotspot boundary (WHP-inspired) |
| GET  | `/api/events/:id/timesteps/:ts_id/actual-perimeter` | Pre-built ROS-weighted perimeters (0h/3h/6h/12h); base = T_{-1}, growth = T_0 − T_{-1}, scaled outward from T1 centroid; weight = cumROS[slot_h+Δh] / totalROS |
| GET  | `/api/events/:id/timesteps/:ts_id/fire-context` | Fire metrics, weather, FWI, wind forecast, road summary |
| GET  | `/api/events/:id/timesteps/:ts_id/status` | `{prediction_status, spatial_analysis_status}` |
| POST | `/api/events/:id/timesteps/:ts_id/run-prediction` | Trigger on-demand prediction for one timestep |
| POST | `/api/events/:id/timesteps/:ts_id/report` | Generate AI situation report (cached) |
| POST | `/api/events/:id/chat` | Stateless streaming chat (`{message, timestep_id, history[]}`) |
| POST | `/api/events/:id/field-reports` | Submit field report (multipart: photo + form fields) |
| GET  | `/api/events/:id/field-reports?before=<ISO>` | List field reports (optional `before` → 24h window ending at that time) |
| GET  | `/api/events/:id/themes` | List all AI-aggregated themes |
| POST | `/api/events/:id/themes/:theme_id/like` | Like a theme |
| POST | `/api/events/:id/themes/:theme_id/comments` | Add comment to a theme |
| POST | `/api/events/:id/field-reports/simulate` | AI-generate N fake field reports with GIS placement + comments (`{n, hints, ts_id}`) |
| POST | `/api/events/:id/field-reports/clear` | DEV — delete all field reports + comments for event |
| POST | `/api/events/:id/field-reports/:rid/like` | Like a field report |
| POST | `/api/events/:id/field-reports/:rid/flag` | Flag a field report as inappropriate |
| GET  | `/api/events/:id/field-reports/:rid/comments` | List comments (24h expiry unless liked) |
| POST | `/api/events/:id/field-reports/:rid/comments` | Add comment to a field report |
| POST | `/api/events/:id/field-reports/:rid/comments/:cid/like` | Like a comment |
| POST | `/api/events/:id/field-reports/:rid/comments/:cid/unlike` | Unlike a comment |

## DB Schema

```
fire_events        → id, name, year, bbox (POLYGON/4326), time_start, time_end,
                     description, end_date

event_timesteps    → id, event_id (FK),
                     slot_time        ← canonical 1h grid timestamp
                     nearest_t1       ← most recent satellite overpass ≤ slot_time
                     gap_hours        ← slot_time − nearest_t1 [h] (always ≥ 0)
                     data_gap_warn    ← True if gap_hours > 12
                     created_at
                     (prediction_status / spatial_analysis_status / population counts
                      are stored as STATUS.json + population.json files, not DB columns)

users              → id, username, password, is_admin (bool, default False), created_at
                     [seed: admin/admin with is_admin=True]

field_reports      → id, event_id (FK, nullable), user_id (FK, nullable),
                     post_type       ← 'fire_report' | 'info' | 'request_help' | 'offer_help'
                     lat, lon        ← WGS84
                     bearing         ← degrees from EXIF (nullable; fire_report only)
                     photo_path      ← relative path to uploaded image (nullable)
                     description     ← user-supplied text
                     like_count      ← denormalized counter
                     flag_count      ← inappropriate report counter
                     theme_id        ← FK → themes (nullable; set when report is absorbed into a theme)
                     created_at

field_report_comments → id, report_id (FK), user_id (FK, nullable),
                        content, like_count, created_at
                        (visible if created_at > now()-24h OR like_count > 0)

themes             → id, event_id (FK, nullable),
                     center_lat, center_lon   ← centroid of clustered reports
                     radius_m                 ← cluster radius used to group reports
                     title                    ← AI-generated (≤ 10 words)
                     summary                  ← AI-generated summary of all reports in cluster
                     like_count               ← denormalized counter (incremented on like)
                     generated_at             ← when AI summary was last computed
                     created_at

theme_comments     → id, theme_id (FK), user_id (FK, nullable),
                     content, created_at
```

## Field Report Submission Flow

```
POST /api/events/:id/field-reports  (multipart/form-data)
  ├─ fields: post_type, lat, lon, description
  └─ file:   photo (optional)

  1. Save photo → data/uploads/{report_id}.{ext}  (if provided)
  2. Parse EXIF GPSImgDirection → bearing (float) or null (unavailable)
  3. Insert field_reports row:
       post_type, lat, lon, description, bearing, photo_path
       theme_id = null  (theme generation disabled)
  4. Return 201 { id, bearing_available: bool }
  (bg_assess_and_cluster disabled — steps 5 & 6 not currently active)
```

## Pipeline Flow

```
python main.py
  │
  ├─ [SYNC] build_env/db/setup_db(app)
  │    ├─ ensure_db()           ← create postgres DB + PostGIS extension
  │    ├─ _migrate_event_timesteps()  ← drop table if schema is stale (safe: fully regenerated)
  │    ├─ db.create_all()       ← create/update tables from ORM
  │    └─ seed_db()             ← insert FireEvent rows if table is empty
  │
  ├─ Flask starts (app.run) ← available immediately after DB setup
  │
  └─ [BACKGROUND THREAD] _run_pipeline()
       │
       ├─ build_env/env/prepare_all_events(app)
       │    └─ per FireEvent:
       │         ├─ _fetch_landmarks()              ← Overpass / Nominatim → landmarks.json
       │         ├─ whp.ensure_era5_coverage()      ← download + preprocess ERA5 if needed
       │         ├─ whp.collect_environment([landcover])   ← download fuel_type.tif if needed
       │         ├─ whp.preprocess_environment([landcover]) ← reproject to EPSG:3978
       │         ├─ whp.build_fire_weather_index()  ← ffmc_daily / isi_hourly / ros_hourly
       │         ├─ whp.build_grid()                ← grid_static.parquet
       │         ├─ whp.collect_hotspots()          ← FIRMS satellite data
       │         ├─ whp.preprocess_hotspots()
       │         └─ build_fire_state() → fire_state.pkl
       │
       ├─ build_slots_only()  (playback events)
       │    └─ per playback event:
       │         ├─ load Study + fire_state
       │         ├─ generate 1h slot grid (start_date → end_date) → upsert EventTimestep rows
       │         └─ per slot: _run_weather_stage()
       │              ├─ ERA5 era5.parquet → +12h area-avg forecast
       │              ├─ → weather/forecast.json      ← available immediately in frontend
       │              └─ → weather/wind_field.json    ← leaflet-velocity format
       │
       └─ run_checks(app)
            ├─ verify ML models (data/static/models/)
            ├─ verify static GeoPackages (population.gpkg, roads_canada.gpkg)
            └─ verify per-event files (era5.parquet, fire_state.pkl)

─────────────────────────────────────────────────────────────────
On-demand (replay clock reaches a slot):
  POST /api/events/:id/timesteps/:ts_id/run-prediction
    └─ [BACKGROUND] build_single_timestep_ondemand(app, ts_id)
         ├─ Stage 1 · predict/prediction.py
         │    ├─ run RF prediction × [3h, 6h, 12h]
         │    ├─ → risk_zones_{3,6,12}h.geojson
         │    ├─ → perimeter.geojson, hotspots.geojson
         │    └─ → fire_context.json
         └─ Stage 2 · spatial/spatial.py
              ├─ hotspots.geojson (500 m buffer) → burning vs burned distinction
              ├─ roads_canada.gpkg × perimeter/risk zones → roads.geojson
              │    status: burning | burned | at_risk_3h | at_risk_6h | at_risk_12h | clear
              │    sections: [{section_id, from, to}] per road (exclusive zones, 2 km gap-merge)
              ├─ road_summary → merged into fire_context.json
              └─ population.gpkg × perimeter/risk zones → DB counts

  GET /api/events/:id/timesteps/:ts_id/status  ← frontend polls every 2s
    → {prediction_status, spatial_analysis_status}
    → when 'done': frontend reloads all layers + full dashboard

─────────────────────────────────────────────────────────────────
On-demand (user clicks "Generate Report"):
  POST /api/events/:id/timesteps/:ts_id/report
    ├─ return cached ai_summary.json if exists
    ├─ load fire_context.json
    ├─ read population from spatial_analysis/ML/population.json
    ├─ risk_agent(fire_context) → risk analysis
    ├─ impact_agent(fire_context, population) → impact analysis
    ├─ evacuation_agent(fire_context) → evacuation analysis
    ├─ summary_agent(risk, impact, evacuation) → situation overview
    └─ write ai_summary.json → return JSON
```

## Development Workflow

Each development cycle follows these steps:

1. **Read PROJECT_STRUCTURE.md** — sync with current architecture, pending tasks, and schema
2. **Implement** — make code changes to backend/frontend/pipeline
3. **Test** — start Flask server and verify endpoints manually or via scripts
4. **Commit** (no push) — `git add <files> && git commit -m "..."` (one-line message, no co-author trailer)
5. **Repeat from step 1**

### Pending Implementation Tasks

| # | Task | Files | Status |
|---|------|-------|--------|
| 1 | DB models: `FieldReport`, `Theme`, `ThemeComment` | `db/models.py` | ✅ |
| 2 | Crowd API blueprint | `api/crowd.py` | ✅ |
| 3 | EXIF bearing extraction + async AI intensity | `api/crowd.py`, `agents/crowd_agent.py`, `utils/background.py` | ✅ |
| 4 | Theme aggregation trigger (24h / 1 km / ≥5 posts) | `agents/crowd_agent.py`, `api/crowd.py` | ✅ |
| 5 | Rename `pipeline/` → `build_env/` in all imports | `main.py`, all `pipeline/**` | ⬜ (deferred — pipeline/ is working) |
| 6 | Add Stage 3 weather to builder | `pipeline/check/builder.py` | ✅ |
| 7 | New timestep endpoints: `/weather`, `/wind-field`, `/population` | `api/timesteps.py` | ✅ |
| 8 | New API blueprints: `firms.py`, `satellite.py`, `config.py` | `api/` | ✅ |
| 9 | Jinja2 template split | `frontend/templates/` | ⬜ (deferred — single index.html is sufficient) |
| 10 | Frontend crowd module | `frontend/js/crowd.js` | ✅ |
| 11 | DEV Simulator (GEOSPATIAL+AI fake reports) | `sim_ai/`, `frontend/js/app.js` | ✅ |
| 12 | Field report popup modal (like/comment/flag/Maps) | `frontend/js/crowd.js`, `frontend/index.html`, `frontend/css/style.css` | ✅ |
| 13 | Comment likes with toggle (like/unlike) | `backend/db/models.py`, `backend/api/crowd.py`, `frontend/js/crowd.js` | ✅ |
| 14 | DEV clear all reports button | `backend/api/crowd.py`, `frontend/js/app.js`, `frontend/index.html` | ✅ |
| 15 | `perimeter_crowd.geojson` — satellite boundary union with 500m buffers around crowd fire_reports; served via `/perimeter?crowd=true`; frontend reloads on crowd poll completion and when `_crowdMode=true` | `pipeline/check/builder.py`, `api/ts_prediction_routes.py`, `frontend/js/api.js`, `frontend/js/app.js` | ✅ |

---

## Static Data Sources

| File | Zenodo Record | Contents |
|------|--------------|----------|
| `data/static/models/` | [19435138](https://zenodo.org/records/19435138) | Trained RF/XGBoost/LR models + thresholds |
| `data/static/population.gpkg` | [19434352](https://zenodo.org/records/19434352) | Dissemination areas + census population 2011/2016/2021 |
| `data/static/roads_canada.gpkg` | [19436338](https://zenodo.org/records/19436338) | OSM Canada major roads |
