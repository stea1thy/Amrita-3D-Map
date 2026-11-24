"""Configuration and coordinate helpers for the Amrita Campus 3D Map pipeline."""

from __future__ import annotations

import math
from pathlib import Path

# Amrita Vishwa Vidyapeetham, Coimbatore (Ettimadai)
BBOX: tuple[float, float, float, float] = (10.8965, 76.8935, 10.9095, 76.9075)  # (south, west, north, east)
ORIGIN: tuple[float, float] = (10.9027, 76.9006)  # local 3D world center (0, 0)

# Directory and file paths
PIPELINE_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = PIPELINE_DIR.parent
DATA_DIR: Path = PIPELINE_DIR / "data"
RAW_OSM_PATH: Path = DATA_DIR / "raw_osm.json"
ELEVATION_PATH: Path = DATA_DIR / "elevation.json"
OVERRIDES_PATH: Path = PIPELINE_DIR / "overrides.json"
WEB_PUBLIC_DIR: Path = REPO_ROOT / "web" / "public"
CAMPUS_GLB_PATH: Path = WEB_PUBLIC_DIR / "models" / "campus.glb"
CAMPUS_META_PATH: Path = WEB_PUBLIC_DIR / "data" / "campus_meta.json"
WALK_GRAPH_PATH: Path = WEB_PUBLIC_DIR / "data" / "walk_graph.json"
TREES_JSON_PATH: Path = WEB_PUBLIC_DIR / "data" / "trees.json"
OVERTURE_PATH: Path = DATA_DIR / "overture_campus.json"
ROADS_MERGED_PATH: Path = DATA_DIR / "roads_merged.json"
STREETLAMP_JSON_PATH: Path = WEB_PUBLIC_DIR / "data" / "streetlamps.json"

# Export budget limits
MAX_TRIANGLES: int = 150_000
MAX_GLB_BYTES: int = 900 * 1024  # 900 KB

# External API settings
OVERTURE_STAC_URL: str = "https://stac.overturemaps.org/catalog.json"
OVERPASS_ENDPOINTS: list[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OPEN_METEO_ELEVATION_URL: str = "https://api.open-meteo.com/v1/elevation"
ELEVATION_GRID_SIZE: int = 25
ELEVATION_BATCH_SIZE: int = 80

USER_AGENT: str = "AmritaCampus3DMapPipeline/1.0 (Ettimadai Campus 3D Map; Python/requests)"

# Allowed override categories
VALID_CATEGORIES: tuple[str, ...] = (
    "academic",
    "hostel",
    "food",
    "sports",
    "admin",
    "landmark",
)

EARTH_RADIUS_M: float = 6378137.0


def overpass_bbox_str() -> str:
    """Return BBOX formatted as 'south,west,north,east' for Overpass QL."""
    south, west, north, east = BBOX
    return f"{south},{west},{north},{east}"


def latlon_to_local_xz(lat: float, lon: float) -> tuple[float, float]:
    """Project (lat, lon) to local Three.js XZ meters around ORIGIN.

    Convention (right-handed Y-up):
      +X -> East (meters)
      +Z -> South, -Z -> North (meters)
    """
    origin_lat, origin_lon = ORIGIN
    lat_rad = math.radians(origin_lat)
    x = math.radians(lon - origin_lon) * EARTH_RADIUS_M * math.cos(lat_rad)
    z = -math.radians(lat - origin_lat) * EARTH_RADIUS_M
    return (x, z)


def local_xz_to_latlon(x_east: float, z_south: float) -> tuple[float, float]:
    """Project local Three.js XZ meters back to (lat, lon) degrees around ORIGIN."""
    origin_lat, origin_lon = ORIGIN
    lat = origin_lat - math.degrees(z_south / EARTH_RADIUS_M)
    lon = origin_lon + math.degrees(x_east / (EARTH_RADIUS_M * math.cos(math.radians(origin_lat))))
    return (round(lat, 6), round(lon, 6))
