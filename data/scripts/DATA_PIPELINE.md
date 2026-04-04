# Data Pipeline

## Overview

Data is split into two layers:

- **Static data** (`data/static/`) — national datasets downloaded once, shared across all events
- **Event data** (`data/events/{yyyy}_{id:04d}/`) — clipped to each fire event's AOI

The pipeline is controlled by `data/scripts/pipeline.py`.

---

## Directory Layout

```
data/
├── static/
│   ├── landcover/
│   │   ├── 2014/   nat_fbpfuels_2014b.tif
│   │   └── 2024/   FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif
│   ├── community/
│   │   ├── 2011/   gcsd000a11a_e.shp  (Census Subdivision)
│   │   ├── 2016/   lcsd000a16a_e.shp
│   │   ├── 2021/   lcsd000a21a_e.shp
│   │   └── 2025/   lcsd000a25a_e.shp
│   └── population/
│       ├── 2011/   gda_000a11a_e.shp  (Dissemination Area)
│       ├── 2016/   lda_000a16a_e.shp
│       └── 2021/   lda_000b21a_e.shp
│
└── events/
    └── 2016_0001/              ← fire_events.year=2016, id=1
        ├── AOI/
        │   └── aoi.geojson     ← auto-generated on event insert
        ├── terrain/
        │   └── dem_dtm.tif
        ├── landcover/
        │   └── fuel_type.tif
        ├── osm/
        │   └── roads.gpkg
        ├── community/
        │   └── census_subdivisions.gpkg
        ├── population/
        │   └── dissemination_areas.gpkg
        ├── firms/
        │   └── 2016-05-03T00:00:00.csv   ← one file per 3h snapshot
        └── perimeter/
            └── 2016-05-03.geojson        ← one file per day
```

---

## Scripts Layout

```
data/scripts/
├── pipeline.py          ← entry point
├── utils.py             ← shared: bbox_from_db, event_dir, pick_firms_dataset
├── downloader/          ← populate data/static/ (run once)
│   ├── dl_landcover.py
│   ├── dl_community.py
│   └── dl_population.py
└── clipper/             ← clip to event AOI → data/events/{id}/
    ├── clip_terrain.py
    ├── clip_landcover.py
    ├── clip_osm.py
    ├── clip_firms.py
    ├── clip_community.py
    ├── clip_population.py
    └── clip_perimeter.py
```

---

## Stage 0: AOI Generation (automatic)

When a `fire_event` row is inserted into the database, a SQLAlchemy `after_insert` listener
in `backend/db/models.py` automatically creates:

```
data/events/{yyyy}_{id:04d}/AOI/aoi.geojson
```

No manual step required.

---

## Stage 1: Download Static Data (run once per dataset/year)

Populates `data/static/`. Safe to re-run — skips existing files.

```bash
python pipeline.py download --all

# Or selectively:
python pipeline.py download --landcover
python pipeline.py download --community
python pipeline.py download --population
```

| Script | Source | Output |
|---|---|---|
| `dl_landcover.py` | NRCan FBP fuel type (TODO: URL) | `static/landcover/{year}/*.tif` |
| `dl_community.py` | Statistics Canada CSD | `static/community/{year}/*.shp` |
| `dl_population.py` | Statistics Canada DA | `static/population/{year}/*.shp` |

> **Note:** Landcover TIFs are large (~1 GB). They are currently pre-placed manually.
> Census year is selected as the closest year ≤ event year.

---

## Stage 2: Clip to Event AOI (run once per event)

Clips static/remote data to the event's bbox. Run after creating the event in the DB.

```bash
python pipeline.py clip <event_id> --all

# Or selectively:
python pipeline.py clip 1 --terrain --landcover --osm
```

| Script | Source | Output | CRS |
|---|---|---|---|
| `clip_terrain.py` | MRDEM-30 COG (remote stream) | `terrain/dem_dtm.tif` | EPSG:3979 |
| `clip_landcover.py` | `static/landcover/` | `landcover/fuel_type.tif` | EPSG:3978 |
| `clip_osm.py` | OpenStreetMap via osmnx | `osm/roads.gpkg` | EPSG:4326 |
| `clip_community.py` | `static/community/` | `community/census_subdivisions.gpkg` | EPSG:4326 |
| `clip_population.py` | `static/population/` | `population/dissemination_areas.gpkg` | EPSG:4326 |

---

## Stage 3: Realtime Updates (run during active event)

Time-stamped files accumulate under the event directory.

```bash
# FIRMS hotspots — every 3 hours
python clipper/clip_firms.py <event_id>

# Fire perimeter from CWFIS hotspot buffer — daily
python clipper/clip_perimeter.py <event_id> [YYYY-MM-DD]
```

| Script | Source | Frequency | Output |
|---|---|---|---|
| `clip_firms.py` | NASA FIRMS API (VIIRS/MODIS) | Every 3h | `firms/YYYY-MM-DDTHH:MM:SS.csv` |
| `clip_perimeter.py` | CWFIS M3 hotspot CSV + 2 km buffer | Daily | `perimeter/YYYY-MM-DD.geojson` |

> **FIRMS vs CWFIS:** FIRMS is used for realtime hotspot snapshots (NRT, ~3h delay).
> CWFIS M3 is the Canadian official daily product. They are kept separate.
