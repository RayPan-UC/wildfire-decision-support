# Frontend TODO

## Task Status

| Task | Assignee | Status |
|------|----------|--------|
| Data Pipeline Status UI | | ~~❌ Abandoned~~ |
| Fire Event Hotspots on Home | | ✅ Done |
| Risk Zone Layer (ML) | | ⬜ Not started |
| Time Control Axis (T1 slider) | | ⬜ Not started |

> Status options: ⬜ Not started / 🔄 In progress / ✅ Done / 🚧 Blocked

---

## Data Pipeline Status UI

Poll `GET /api/data/status` on app load and show download progress to the user.

Response shape:
```json
{
  "ready": false,
  "pipeline_running": true,
  "current": "osm",
  "error": null,
  "datasets": {
    "landcover":  { "ready": true,  "years": [2014, 2024], "missing": [] },
    "community":  { "ready": true,  "years": [2011, 2016, 2021], "missing": [] },
    "population": { "ready": true,  "years": [2011, 2016, 2021], "missing": [] },
    "osm":        { "ready": false }
  }
}
```

### Behaviour
- If `ready === true` → show app normally
- If `pipeline_running === true` → show loading overlay with current dataset name
- If `error !== null` → show error banner
- Poll every 5s while `pipeline_running === true`, stop when `ready === true`

## Risk Zone Layer (ML)

Fetch `GET /api/risk-zones/?t1=<t1>&delta_t_h=<delta_t>` and render risk polygons on the map.

### Behaviour
- Three polygon layers: `high` (red), `medium` (orange), `low` (yellow)
- Polygons are merged 500m grid cells (not individual pixels)
- Each feature has `risk`, `prob_mean`, `prob_max`, `cell_count` in properties
- Triggered when user changes T1 or delta_t on the time control axis

---

## Time Control Axis (T1 slider)

Let user select a T1 timestamp from the available overpass times and a delta_t offset.

### Behaviour
- Fetch available T1 timestamps from `GET /api/events/` or a dedicated `/api/overpasses/` endpoint
- Slider steps through available overpass times (May 1–27 2016)
- Three delta_t buttons: **+3h**, **+6h**, **+12h** (maps to delta_t_h = 3.0, 6.0, 12.0)
- On change → call `/api/risk-zones/` with selected t1 + delta_t_h → update map

---

## Fire Event Hotspots on Home

On page load, fetch `GET /api/events/` and display each fire event as a hotspot marker on the map.

### Behaviour
- Call `GET /api/events/` on home load
- For each event, place a marker at the center of its `bbox`
- Clicking a marker shows event name, year, and description in a popup
- Marker style should visually distinguish fire events (e.g. flame icon or red circle)
