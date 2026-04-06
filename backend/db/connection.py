import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def get_db_uri():
    return (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}"
        f":{os.getenv('DB_PASSWORD', 'password')}"
        f"@{os.getenv('DB_HOST', 'localhost')}"
        f":{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME', 'wildfire_db')}"
    )


def ensure_db():
    """Create the database and enable PostGIS if they don't already exist.

    SQLAlchemy's create_all() can only create tables — not the database itself.
    This function runs before create_all() to guarantee the database exists
    and PostGIS is enabled, so the app can start without any manual setup.
    """
    db_name = os.getenv('DB_NAME', 'wildfire_db')
    conn_args = dict(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', ''),
    )

    # Step 1: connect to the default 'postgres' DB to create our database
    conn = psycopg2.connect(**conn_args, dbname='postgres')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{db_name}"')
        print(f"[db] created database '{db_name}'")
    cur.close()
    conn.close()

    # Step 2: connect to our database and enable the PostGIS extension
    conn2 = psycopg2.connect(**conn_args, dbname=db_name)
    conn2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur2 = conn2.cursor()
    cur2.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    cur2.close()
    conn2.close()


def seed_db():
    """Insert initial data if the database is empty.

    Only runs when fire_events has no rows, so it's safe to call on every startup
    without duplicating data.
    """
    from db.models import FireEvent
    if FireEvent.query.count() > 0:
        return

    from geoalchemy2 import WKTElement
    events = [
        FireEvent(
            name        = 'Fort McMurray Wildfire 2016',
            year        = 2016,
            bbox        = WKTElement(
                'POLYGON((-112.634 56.157, -110.002 56.157, -110.002 57.380, -112.634 57.380, -112.634 56.157))',
                srid=4326
            ),
            time_start  = '2016-05-01 00:00:00+00',
            time_end    = '2016-05-15 23:59:59+00',
            end_date    = '2016-05-15',
            description = (
                'The 2016 Horse River Wildfire (MWF-009) forced the evacuation of approximately '
                '88,000 residents from Fort McMurray, Alberta. It burned approximately 590,000 '
                'hectares and is the costliest disaster in Canadian history.'
            ),
        ),
    ]

    db.session.add_all(events)
    db.session.commit()
    print(f"[db] seeded {len(events)} fire event(s)")
