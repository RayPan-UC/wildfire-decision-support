# data/scripts/pipeline.py
# Top-level pipeline for the wildfire data system
#
# Two entry points:
#   download_static()  — populate data/static/ (run once per dataset/year)
#   clip_by_AOI()      — generate all event data under data/events/{yyyy}_{id:04d}/
#
# Usage:
#   python pipeline.py download --landcover --community --population
#   python pipeline.py clip <event_id> [--terrain] [--landcover] [--osm]
#                                      [--firms] [--community] [--population]
#                                      [--perimeter]

import sys
import argparse


def download_static(
    landcover:  bool = True,
    community:  bool = True,
    population: bool = True,
    osm:        bool = True,
):
    """Download shared datasets to data/static/. Safe to re-run (skips existing)."""
    if landcover:
        from downloader.dl_landcover import download_all as dl_lc
        print("=== landcover ===")
        dl_lc()

    if community:
        from downloader.dl_community import download_all as dl_com
        print("=== community ===")
        dl_com()

    if population:
        from downloader.dl_population import download_all as dl_pop
        print("=== population ===")
        dl_pop()

    if osm:
        from downloader.dl_osm import download as dl_osm
        print("=== osm ===")
        dl_osm()


def clip_by_AOI(
    event_id:   int,
    aoi:        bool = True,
    terrain:    bool = True,
    landcover:  bool = True,
    osm:        bool = True,
    firms:      bool = True,
    community:  bool = True,
    population: bool = True,
    perimeter:  bool = True,
    weather:    bool = True,
):
    """Clip all static/remote data to a fire event AOI."""
    if aoi:
        from clipper.clip_aoi import clip as c_aoi
        print("=== aoi ===")
        c_aoi(event_id)

    if terrain:
        from clipper.clip_terrain import clip as c_terrain
        print("=== terrain ===")
        c_terrain(event_id)

    if landcover:
        from clipper.clip_landcover import clip as c_lc
        print("=== landcover ===")
        c_lc(event_id)

    if osm:
        from clipper.clip_osm import clip as c_osm
        print("=== osm ===")
        c_osm(event_id)

    if firms:
        from clipper.clip_firms import clip as c_firms
        print("=== firms ===")
        c_firms(event_id)

    if community:
        from clipper.clip_community import clip as c_com
        print("=== community ===")
        c_com(event_id)

    if population:
        from clipper.clip_population import clip as c_pop
        print("=== population ===")
        c_pop(event_id)

    if perimeter:
        from clipper.clip_perimeter import clip as c_perim
        print("=== perimeter ===")
        c_perim(event_id)

    if weather:
        from clipper.clip_weather import clip as c_weather
        print("=== weather ===")
        c_weather(event_id)


def _parse_args():
    parser = argparse.ArgumentParser(description="Wildfire data pipeline")
    sub = parser.add_subparsers(dest="command")

    # --- download ---
    dl = sub.add_parser("download", help="Populate data/static/")
    dl.add_argument("--landcover",  action="store_true", default=False)
    dl.add_argument("--community",  action="store_true", default=False)
    dl.add_argument("--population", action="store_true", default=False)
    dl.add_argument("--osm",        action="store_true", default=False)
    dl.add_argument("--all",        action="store_true", default=False,
                    help="Download all datasets")

    # --- clip ---
    cl = sub.add_parser("clip", help="Clip data to event AOI")
    cl.add_argument("event_id", type=int)
    cl.add_argument("--aoi",        action="store_true", default=False)
    cl.add_argument("--terrain",    action="store_true", default=False)
    cl.add_argument("--landcover",  action="store_true", default=False)
    cl.add_argument("--osm",        action="store_true", default=False)
    cl.add_argument("--firms",      action="store_true", default=False)
    cl.add_argument("--community",  action="store_true", default=False)
    cl.add_argument("--population", action="store_true", default=False)
    cl.add_argument("--perimeter",  action="store_true", default=False)
    cl.add_argument("--weather",    action="store_true", default=False)
    cl.add_argument("--all",        action="store_true", default=False,
                    help="Clip all datasets")

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.command == "download":
        use_all = args.all
        download_static(
            landcover  = use_all or args.landcover,
            community  = use_all or args.community,
            population = use_all or args.population,
            osm        = use_all or args.osm,
        )

    elif args.command == "clip":
        use_all = args.all
        clip_by_AOI(
            event_id   = args.event_id,
            aoi        = use_all or args.aoi,
            terrain    = use_all or args.terrain,
            landcover  = use_all or args.landcover,
            osm        = use_all or args.osm,
            firms      = use_all or args.firms,
            community  = use_all or args.community,
            population = use_all or args.population,
            perimeter  = use_all or args.perimeter,
            weather    = use_all or args.weather,
        )

    else:
        print("Usage:")
        print("  python pipeline.py download --all")
        print("  python pipeline.py clip <event_id> --all")
        sys.exit(1)
