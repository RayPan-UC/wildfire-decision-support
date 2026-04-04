# Frontend TODO

## Task Status

| Task | Assignee | Status |
|------|----------|--------|
| Data Pipeline Status UI | | ⬜ Not started |
| Fire Event Hotspots on Home | | ⬜ Not started |

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

## Fire Event Hotspots on Home

On page load, fetch `GET /api/events/` and display each fire event as a hotspot marker on the map.

### Behaviour
- Call `GET /api/events/` on home load
- For each event, place a marker at the center of its `bbox`
- Clicking a marker shows event name, year, and description in a popup
- Marker style should visually distinguish fire events (e.g. flame icon or red circle)
