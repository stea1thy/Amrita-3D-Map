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
DEBUG_BLEND_PATH: Path = PIPELINE_DIR / "debug_campus.blend"
HEROES_DIR: Path = PIPELINE_DIR / "heroes"
HERO_MODELS_DIR: Path = PIPELINE_DIR / "hero_models"
RENDERS_DIR: Path = PIPELINE_DIR / "renders"
REFS_DIR: Path = PIPELINE_DIR / "refs"

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

# Front-yard OSM paths & stray ponds suppressed inside AB-1's custom scalloped plaza clear_zone
AB1_FRONT_SUPPRESS_IDS: frozenset[str] = frozenset({
    "way/546394550",  # Old skinny striped fountain loop
    "way/528944019",  # Old striped entry stem (replaced by flared plaza entry road)
    "way/531088149",  # Stray footpath east of AB-1
    "way/531088154",  # Stray footpath east lawn
    "way/531088176",  # Stray footpath SE lawn
    "way/531088179",  # Stray footpath SW lawn
    "way/531088181",  # Stray footpath south-west lawn
    "way/531288690",  # Stray footpath west lawn
})
AB1_FRONT_WATER_SUPPRESS_IDS: frozenset[str] = frozenset({
    "way/531088129",  # Stray light-blue pond blob NE of plaza
    "way/531088183",  # Stray light-blue pond blob east of plaza
})


# OSM paths whose first N vertices are dropped (map way id -> N)
PATH_HEAD_TRIM: dict[str, int] = {
    "way/531088202": 1,  # Footpath drawn straight through the AB-2 Nataraja fountain
}


def path_coords(feature: dict) -> list:
    """GeoJSON line coordinates of a path feature with the campus-specific trims applied."""
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    return coords[PATH_HEAD_TRIM.get(str(feature.get("id", "")), 0):]


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
