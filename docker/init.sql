-- wildfire-spread-ai\docker\init.sql

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;


-- Users table (used by auth API)
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(255) UNIQUE NOT NULL,
    password   VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Fire event 
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS fire_events (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    year        INT,
    bbox        GEOMETRY(POLYGON, 4326),
    time_start  TIMESTAMPTZ,
    time_end    TIMESTAMPTZ,
    description TEXT
);

CREATE INDEX idx_events_bbox ON fire_events USING GIST (bbox);

-- fire_perimeters

-- hotspots

-- communities

-- roads



-----------------------------------------------------------------------------------------------------------

-- Insert 2016 Fort McMurray fire event
INSERT INTO fire_events (name, year, bbox, time_start, time_end, description)
VALUES (
    'Fort McMurray Wildfire 2016',
    2016,
    ST_GeomFromText(
        'POLYGON((
            -112.634 56.157,
            -110.002 56.157,
            -110.002 57.380,
            -112.634 57.380,
            -112.634 56.157
        ))',
        4326
    ),
    '2016-05-01 00:00:00+00',
    '2016-05-31 23:59:59+00',
    'The 2016 Horse River Wildfire (MWF-009) forced the evacuation of approximately 88,000 residents from Fort McMurray, Alberta. It burned approximately 590,000 hectares and is the costliest disaster in Canadian history.'
);

