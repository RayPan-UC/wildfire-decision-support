# downloader/dl_landcover.py
# Download NRCan FBP fuel type TIFs to data/static/landcover/{year}/
# Run this once to populate static data (files are large, ~1 GB each)
#
# Usage:
#   python dl_landcover.py [--year 2024]

import sys
import io
import zipfile
import urllib.request
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR   = _SCRIPTS_DIR.parent / "static" / "landcover"

LANDCOVER_URLS = {
    # 2014b: zip archive containing nat_fbpfuels_2014b.tif
    2014: "https://cwfis.cfs.nrcan.gc.ca/downloads/fuels/archive/National_FBP_Fueltypes_version2014b.zip",
    # 2024: single GeoTIFF (EPSG:3978, 100m)
    2024: "https://cwfis.cfs.nrcan.gc.ca/downloads/fuels/current/FBP_fueltypes_Canada_100m_EPSG3978_20240527.tif",
}


def _extract_flat(zf: zipfile.ZipFile, out_dir: Path):
    """Extract zip contents directly into out_dir, stripping any nested folder layers."""
    members = [m for m in zf.infolist() if not m.filename.endswith("/")]

    # Find the common prefix (nested folder) and strip it
    prefix = ""
    names = [m.filename for m in members]
    if names:
        parts = names[0].split("/")
        if len(parts) > 1:
            candidate = "/".join(parts[:-1]) + "/"
            if all(n.startswith(candidate) for n in names):
                prefix = candidate

    for member in members:
        flat_name = member.filename[len(prefix):]  # strip leading folder(s)
        if not flat_name:
            continue
        out_path = out_dir / flat_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(zf.read(member))


def download(year: int = 2024):
    url = LANDCOVER_URLS.get(year)
    if url is None:
        print(f"[landcover-dl] No URL for year {year}. Available: {sorted(LANDCOVER_URLS)}")
        return

    out_dir = STATIC_DIR / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[landcover-dl] Downloading {year} fuel type from {url} ...")
    with urllib.request.urlopen(url) as resp:
        data = resp.read()

    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            _extract_flat(zf, out_dir)
        print(f"[landcover-dl] Extracted → {out_dir}")
    else:
        filename = url.split("/")[-1]
        (out_dir / filename).write_bytes(data)
        print(f"[landcover-dl] Saved → {out_dir / filename}")


def download_all():
    for year in sorted(LANDCOVER_URLS):
        download(year)


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if year:
        download(year)
    else:
        download_all()
