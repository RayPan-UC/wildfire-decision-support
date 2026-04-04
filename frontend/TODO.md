# Frontend TODO

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
