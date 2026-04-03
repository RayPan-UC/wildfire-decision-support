import os
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
