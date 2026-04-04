# downloader/dl_community.py
# Download Statistics Canada Census Subdivision (CSD) shapefiles
# to data/static/community/{year}/
# Run this once to populate static data.
#
# Usage:
#   python dl_community.py [--year 2021]

import sys
import io
import zipfile
import urllib.request
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR   = _SCRIPTS_DIR.parent / "static" / "community"

COMMUNITY_URLS = {
    2011: "https://www12.statcan.gc.ca/census-recensement/2011/geo/bound-limit/files-fichiers/gcsd000a11a_e.zip",
    2016: "https://www12.statcan.gc.ca/census-recensement/2011/geo/bound-limit/files-fichiers/2016/lcsd000a16a_e.zip",
    2021: "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000a21a_e.zip",
    # 2025: TODO add URL when published
}


def download(year: int = 2021):
    url = COMMUNITY_URLS.get(year)
    if url is None:
        print(f"[community-dl] No URL configured for year {year}. Available: {sorted(COMMUNITY_URLS)}")
        return

    out_dir = STATIC_DIR / str(year)
    if out_dir.exists() and any(out_dir.glob("*.shp")):
        print(f"[community-dl] Already exists → {out_dir}, skipping.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[community-dl] Downloading {year} CSD from {url} ...")

    with urllib.request.urlopen(url) as resp:
        data = resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(out_dir)

    print(f"[community-dl] Extracted → {out_dir}")


def download_all():
    for year in sorted(COMMUNITY_URLS):
        download(year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if year:
        download(year)
    else:
        download_all()
