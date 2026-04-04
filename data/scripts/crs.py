# data/scripts/crs.py
# Sets PROJ_DATA to rasterio's bundled proj_data before any PROJ-dependent import,
# preventing conflicts with system PROJ installations (e.g. PostgreSQL/PostGIS).
#
# Import this module first in any script that uses rasterio or pyproj:
#   import crs  # noqa: F401  (side-effect: fixes PROJ_DATA)

import os
from pathlib import Path

os.environ["PROJ_DATA"] = str(Path(__file__).resolve().parent / "proj_data")
