"""Fetch Overture Maps Buildings and Places for Ettimadai campus, diff with OSM, and export audit JSON."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

import duckdb
import requests
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
from shapely.ops import unary_union

try:
    from . import config, terrain_utils
except ImportError:
    import config
    import terrain_utils

TERRAIN_EDGE_MARGIN_M = 25.0
MIN_BUILDING_AREA_M2 = 18.0
OSM_MATCH_MIN_IOU = 0.18
OSM_MATCH_MIN_CONTAIN = 0.35
DEDUP_OVERLAP_RATIO = 0.35
PLACE_MIN_CONFIDENCE = 0.40
PLACE_SNAP_MAX_DIST_M = 25.0
PLACE_SMALL_BLDG_PROMOTE_DIST_M = 15.0

GENERIC_UNIVERSITY_NAMES = {
    "amrita vishwa vidyapeetham",
    "amrita vishwa vidyapeetham coimbatore",
    "amrita vishwa vidyapeetham, coimbatore",
    "amrita university",
    "amrita campus",
    "amrita nagar",
    "ettimadai",
    "coimbatore",
}


def latlon_to_xy(lat: float, lon: float) -> tuple[float, float]:
    """Project (lat, lon) to Blender XY meters (+X East, +Y North) matching build_scene.py."""
    x_east, z_south = config.latlon_to_local_xz(lat, lon)
    return (x_east, -z_south)


def is_generic_place_name(name: str | None) -> bool:
    """Return True for broad campus-wide names that should not rename individual structures."""
    if not name:
        return True
    norm = " ".join(name.lower().replace("-", " ").split()).strip(" ,.")
    if not norm or norm in GENERIC_UNIVERSITY_NAMES:
        return True
    if "amrita vishwa vidyapeetham" in norm and len(norm) < 48:
        return True
    return False


def fetch_latest_release() -> str:
    """Read the latest Overture Maps release identifier from the STAC catalog root."""
    resp = requests.get(config.OVERTURE_STAC_URL, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    release = payload.get("latest")
    if not release or not isinstance(release, str):
        raise RuntimeError(f"Could not find 'latest' release in {config.OVERTURE_STAC_URL}: {payload!r}")
    return release


def _describe_parquet_columns(con: duckdb.DuckDBPyConnection, parquet_url: str) -> dict[str, str]:
    """Return lowercase column_name -> column_type mapping from DESCRIBE."""
    rows = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{parquet_url}', filename=true, hive_partitioning=1) LIMIT 0"
    ).fetchall()
    return {str(r[0]).lower(): str(r[1]) for r in rows}


def _extract_primary_source(sources: Any) -> str:
    """Extract readable primary dataset/provider label from Overture sources column."""
    if not sources or not isinstance(sources, (list, tuple)):
        return "Overture Maps"
    datasets: list[str] = []
    for entry in sources:
        if isinstance(entry, dict):
            ds = entry.get("dataset") or entry.get("provider")
            if ds and str(ds) not in datasets:
                datasets.append(str(ds))
    return ", ".join(datasets) if datasets else "Overture Maps"


def _clamp_height_m(val: Any) -> float | None:
    if val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num) or num <= 0.0:
        return None
    return round(min(28.0, max(3.0, num)), 2)


def _clamp_floors(val: Any) -> int | None:
    if val is None:
        return None
    try:
        num = int(round(float(val)))
    except (TypeError, ValueError):
        return None
    if num <= 0:
        return None
    return min(8, max(1, num))


def map_overture_category(raw_cat: str | None, hierarchy: list[str] | None, name: str | None) -> str:
    """Map Overture Places taxonomy + name into campus viewer categories."""
    tokens = [raw_cat or ""] + list(hierarchy or []) + [name or ""]
    text = " ".join(str(t) for t in tokens if t).lower().replace("_", " ")

    if any(
        kw in text
        for kw in (
            "restaurant",
            "cafe",
            "coffee",
            "bakery",
            "fast food",
            "food",
            "canteen",
            "mess",
            "juice",
            "ice cream",
            "snack",
            "tea",
            "dining",
            "bistro",
            "eatery",
            "sweet",
        )
    ):
        return "food"
    if any(
        kw in text
        for kw in (
            "dormitory",
            "hostel",
            "bhavan",
            "bhavanam",
            "guest house",
            "hotel",
            "lodging",
            "residence",
            "residential",
            "apartment",
        )
    ):
        return "hostel"
    if any(
        kw in text
        for kw in (
            "sport",
            "gym",
            "fitness",
            "stadium",
            "swimming",
            "pool",
            "cricket",
            "football",
            "basketball",
            "tennis",
            "badminton",
            "playground",
            "athletic",
        )
    ):
        return "sports"
    if any(
        kw in text
        for kw in (
            "bank",
            "atm",
            "post office",
            "administrative",
            "office",
            "placement",
            "corporate",
            "registrar",
            "medical",
            "clinic",
            "hospital",
            "pharmacy",
            "security",
            "gate",
        )
    ):
        return "admin"
    if any(
        kw in text
        for kw in (
            "library",
            "auditorium",
            "temple",
            "shrine",
            "church",
            "mosque",
            "worship",
            "landmark",
            "monument",
            "museum",
            "hall",
        )
    ):
        return "landmark"
    if any(
        kw in text
        for kw in (
            "college",
            "university",
            "school",
            "academic",
            "department",
            "faculty",
            "engineering",
            "computing",
            "science",
            "research",
            "lab",
            "laboratory",
            "classroom",
            "lecture",
            "education",
            "institute",
        )
    ):
        return "academic"
    return "default"


def _lonlat_geom_to_xy_polys(geom_dict: dict[str, Any]) -> list[tuple[Polygon, dict[str, Any]]]:
    """Convert GeoJSON Polygon/MultiPolygon into validated local-XY Shapely Polygons paired with single-Polygon GeoJSON."""
    gtype = geom_dict.get("type")
    coords = geom_dict.get("coordinates") or []
    poly_rings_list = [coords] if gtype == "Polygon" else coords if gtype == "MultiPolygon" else []

    out: list[tuple[Polygon, dict[str, Any]]] = []
    for raw_poly_rings in poly_rings_list:
        if not raw_poly_rings or len(raw_poly_rings[0]) < 4:
            continue
        xy_outer = [latlon_to_xy(float(pt[1]), float(pt[0])) for pt in raw_poly_rings[0]]
        xy_holes = [
            [latlon_to_xy(float(pt[1]), float(pt[0])) for pt in hole]
            for hole in raw_poly_rings[1:]
            if len(hole) >= 4
        ]
        poly = Polygon(xy_outer, xy_holes)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        if isinstance(poly, MultiPolygon):
            for sub in poly.geoms:
                if sub.area >= MIN_BUILDING_AREA_M2:
                    sub_geo = {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [
                                    round(config.local_xz_to_latlon(p[0], -p[1])[1], 7),
                                    round(config.local_xz_to_latlon(p[0], -p[1])[0], 7),
                                ]
                                for p in sub.exterior.coords
                            ]
                        ],
                    }
                    out.append((sub, sub_geo))
        elif isinstance(poly, Polygon) and poly.area >= MIN_BUILDING_AREA_M2:
            out.append((poly, {"type": "Polygon", "coordinates": raw_poly_rings}))
    return out


def _osm_geom_to_xy_poly(geom_dict: dict[str, Any]) -> Polygon | MultiPolygon | None:
    """Convert raw_osm GeoJSON geometry into a valid local-XY Shapely Polygon/MultiPolygon."""
    gtype = geom_dict.get("type")
    coords = geom_dict.get("coordinates") or []
    if gtype == "Polygon":
        if not coords or len(coords[0]) < 3:
            return None
        xy_outer = [latlon_to_xy(float(pt[1]), float(pt[0])) for pt in coords[0]]
        xy_holes = [
            [latlon_to_xy(float(pt[1]), float(pt[0])) for pt in h]
            for h in coords[1:]
            if len(h) >= 3
        ]
        poly = Polygon(xy_outer, xy_holes)
    elif gtype == "MultiPolygon":
        parts = []
        for p_coords in coords:
            if not p_coords or len(p_coords[0]) < 3:
                continue
            xy_outer = [latlon_to_xy(float(pt[1]), float(pt[0])) for pt in p_coords[0]]
            xy_holes = [
                [latlon_to_xy(float(pt[1]), float(pt[0])) for pt in h]
                for h in p_coords[1:]
                if len(h) >= 3
            ]
            sub = Polygon(xy_outer, xy_holes).buffer(0)
            if not sub.is_empty:
                parts.append(sub)
        if not parts:
            return None
        poly = unary_union(parts)
    else:
        return None

    if not poly.is_valid:
        poly = poly.buffer(0)
    return None if poly.is_empty or poly.area <= 0.5 else poly


def _query_overture_buildings(
    con: duckdb.DuckDBPyConnection,
    release: str,
    bbox: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    south, west, north, east = bbox
    url = f"s3://overturemaps-us-west-2/release/{release}/theme=buildings/type=building/*"
    cols = _describe_parquet_columns(con, url)

    select_parts = [
        "id",
        "names.primary AS primary_name" if "names" in cols else "NULL::VARCHAR AS primary_name",
        "height" if "height" in cols else "NULL::DOUBLE AS height",
        "num_floors" if "num_floors" in cols else "NULL::INTEGER AS num_floors",
        "min_height" if "min_height" in cols else "NULL::DOUBLE AS min_height",
        "min_floor" if "min_floor" in cols else "NULL::INTEGER AS min_floor",
        "is_underground" if "is_underground" in cols else "FALSE AS is_underground",
        "subtype" if "subtype" in cols else "NULL::VARCHAR AS subtype",
        "class AS bclass" if "class" in cols else "NULL::VARCHAR AS bclass",
        "roof_shape" if "roof_shape" in cols else "NULL::VARCHAR AS roof_shape",
        "sources" if "sources" in cols else "NULL AS sources",
        "ST_AsGeoJSON(geometry) AS geom_json",
    ]

    sql = f"""
        SELECT {", ".join(select_parts)}
        FROM read_parquet('{url}', filename=true, hive_partitioning=1)
        WHERE bbox.xmin <= ? AND bbox.xmax >= ?
          AND bbox.ymin <= ? AND bbox.ymax >= ?
    """
    cur = con.execute(sql, [east, west, north, south])
    col_names = [d[0] for d in cur.description]
    return [dict(zip(col_names, row)) for row in cur.fetchall()]


def _query_overture_places(
    con: duckdb.DuckDBPyConnection,
    release: str,
    bbox: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    south, west, north, east = bbox
    url = f"s3://overturemaps-us-west-2/release/{release}/theme=places/type=place/*"
    cols = _describe_parquet_columns(con, url)

    if "taxonomy" in cols:
        cat_primary_expr = "taxonomy.primary AS raw_category"
        cat_hier_expr = "taxonomy.hierarchy AS category_hierarchy"
    elif "categories" in cols:
        cat_primary_expr = "categories.primary AS raw_category"
        cat_hier_expr = "categories.alternate AS category_hierarchy"
    else:
        cat_primary_expr = "NULL::VARCHAR AS raw_category"
        cat_hier_expr = "NULL::VARCHAR[] AS category_hierarchy"

    select_parts = [
        "id",
        "names.primary AS primary_name" if "names" in cols else "NULL::VARCHAR AS primary_name",
        cat_primary_expr,
        cat_hier_expr,
        "confidence" if "confidence" in cols else "NULL::DOUBLE AS confidence",
        "operating_status" if "operating_status" in cols else "NULL::VARCHAR AS operating_status",
        "sources" if "sources" in cols else "NULL AS sources",
        "ST_AsGeoJSON(geometry) AS geom_json",
    ]

    sql = f"""
        SELECT {", ".join(select_parts)}
        FROM read_parquet('{url}', filename=true, hive_partitioning=1)
        WHERE bbox.xmin <= ? AND bbox.xmax >= ?
          AND bbox.ymin <= ? AND bbox.ymax >= ?
    """
    cur = con.execute(sql, [east, west, north, south])
    col_names = [d[0] for d in cur.description]
    return [dict(zip(col_names, row)) for row in cur.fetchall()]


def main() -> None:
    """Fetch Overture Maps Buildings + Places, compare against OSM, and write overture_campus.json."""
    if not config.RAW_OSM_PATH.exists():
        raise FileNotFoundError(f"Missing OSM baseline at {config.RAW_OSM_PATH}; run fetch_osm.py first.")
    if not config.ELEVATION_PATH.exists():
        raise FileNotFoundError(f"Missing elevation grid at {config.ELEVATION_PATH}; run fetch_elevation.py first.")

    raw_osm = json.loads(config.RAW_OSM_PATH.read_text(encoding="utf-8"))
    elevation = json.loads(config.ELEVATION_PATH.read_text(encoding="utf-8"))
    campus_ctx = terrain_utils.extract_campus_boundary_and_rail(raw_osm)

    # Compute terrain core XY bounds matching build_scene.py
    lats = elevation["lats"]
    lons = elevation["lons"]
    core_min_y = latlon_to_xy(lats[0], config.ORIGIN[1])[1]
    core_max_y = latlon_to_xy(lats[-1], config.ORIGIN[1])[1]
    core_min_x = latlon_to_xy(config.ORIGIN[0], lons[0])[0]
    core_max_x = latlon_to_xy(config.ORIGIN[0], lons[-1])[0]
    margin_min_x = core_min_x + TERRAIN_EDGE_MARGIN_M
    margin_max_x = core_max_x - TERRAIN_EDGE_MARGIN_M
    margin_min_y = core_min_y + TERRAIN_EDGE_MARGIN_M
    margin_max_y = core_max_y - TERRAIN_EDGE_MARGIN_M

    # Parse baseline OSM features into local XY Shapely geometries
    osm_buildings: list[tuple[str, Polygon | MultiPolygon, dict[str, Any]]] = []
    excl_polys: list[Any] = []
    osm_path_lines: list[LineString] = []

    for feat in raw_osm.get("features", []):
        fid = str(feat["id"])
        props = feat.get("properties", {})
        layer = props.get("layer")
        geom = feat.get("geometry", {})
        if layer == "building":
            poly = _osm_geom_to_xy_poly(geom)
            if poly is not None:
                osm_buildings.append((fid, poly, props))
        elif layer in {"water", "sports"}:
            poly = _osm_geom_to_xy_poly(geom)
            if poly is not None:
                excl_polys.append(poly)
        elif layer == "path" and geom.get("type") == "LineString":
            pts = [latlon_to_xy(float(p[1]), float(p[0])) for p in geom.get("coordinates", [])]
            if len(pts) >= 2:
                osm_path_lines.append(LineString(pts))

    road_polys: list[Polygon] = []
    if config.ROADS_MERGED_PATH.exists():
        roads_merged = json.loads(config.ROADS_MERGED_PATH.read_text(encoding="utf-8"))
        for rings in roads_merged.get("asphaltPolygons", []):
            if not rings or len(rings[0]) < 3:
                continue
            outer = [(float(p[0]), float(p[1])) for p in rings[0]]
            holes = [[(float(p[0]), float(p[1])) for p in h] for h in rings[1:] if len(h) >= 3]
            rp = Polygon(outer, holes).buffer(0)
            if not rp.is_empty and rp.area > 0.5:
                road_polys.append(rp)

    excl_union = unary_union(excl_polys).buffer(0) if excl_polys else None
    road_union = unary_union(road_polys).buffer(0) if road_polys else None
    campus_refs: list[Any] = [poly for _, poly, _ in osm_buildings] + osm_path_lines

    print(f"Checking latest Overture Maps release at {config.OVERTURE_STAC_URL}...")
    release = fetch_latest_release()
    print(f"Latest Overture release: {release}")
    print(f"Querying Overture Buildings & Places over S3 for BBOX {config.BBOX}...")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")

    raw_ov_buildings = _query_overture_buildings(con, release, config.BBOX)
    raw_ov_places = _query_overture_places(con, release, config.BBOX)
    con.close()

    print(f"Fetched {len(raw_ov_buildings)} Overture building records and {len(raw_ov_places)} Overture places.")

    # Track sources breakdown across raw buildings
    sources_breakdown: dict[str, int] = {}
    matched_osm_ids: set[str] = set()
    osm_enrichments: dict[str, dict[str, Any]] = {}
    unmatched_candidates: list[dict[str, Any]] = []

    for row in raw_ov_buildings:
        if row.get("is_underground"):
            continue
        geom_json = row.get("geom_json")
        if not geom_json:
            continue
        geom_dict = json.loads(geom_json)
        parts = _lonlat_geom_to_xy_polys(geom_dict)
        if not parts:
            continue

        src_label = _extract_primary_source(row.get("sources"))
        sources_breakdown[src_label] = sources_breakdown.get(src_label, 0) + 1

        ov_height = _clamp_height_m(row.get("height"))
        ov_floors = _clamp_floors(row.get("num_floors"))
        raw_name = row.get("primary_name")
        clean_name = str(raw_name).strip() if raw_name and not is_generic_place_name(str(raw_name)) else None
        ov_full_id = str(row["id"])

        for part_idx, (ov_poly, ov_geojson) in enumerate(parts):
            ov_area = float(ov_poly.area)
            ov_b = ov_poly.bounds

            # Compare against all OSM buildings using quick AABB reject + Shapely intersection
            best_osm_id: str | None = None
            best_score = 0.0
            for osm_id, osm_poly, _ in osm_buildings:
                ob = osm_poly.bounds
                if ov_b[2] < ob[0] or ov_b[0] > ob[2] or ov_b[3] < ob[1] or ov_b[1] > ob[3]:
                    continue
                inter = ov_poly.intersection(osm_poly).area
                if inter <= 0.0:
                    continue
                union_area = ov_area + osm_poly.area - inter
                iou = inter / union_area if union_area > 0 else 0.0
                contain_ov = inter / ov_area if ov_area > 0 else 0.0
                contain_osm = inter / osm_poly.area if osm_poly.area > 0 else 0.0
                if iou >= OSM_MATCH_MIN_IOU or contain_ov >= OSM_MATCH_MIN_CONTAIN or contain_osm >= OSM_MATCH_MIN_CONTAIN:
                    score = iou + 0.5 * max(contain_ov, contain_osm)
                    if score > best_score:
                        best_score = score
                        best_osm_id = osm_id

            if best_osm_id is not None:
                matched_osm_ids.add(best_osm_id)
                if ov_height is not None or ov_floors is not None or clean_name:
                    cur_enr = osm_enrichments.setdefault(
                        best_osm_id,
                        {"height_m": None, "num_floors": None, "name": None, "source": src_label, "overture_ids": []},
                    )
                    if ov_full_id not in cur_enr["overture_ids"]:
                        cur_enr["overture_ids"].append(ov_full_id)
                    if ov_height is not None and (cur_enr["height_m"] is None or ov_height > cur_enr["height_m"]):
                        cur_enr["height_m"] = ov_height
                    if ov_floors is not None and (cur_enr["num_floors"] is None or ov_floors > cur_enr["num_floors"]):
                        cur_enr["num_floors"] = ov_floors
                    if clean_name and not cur_enr["name"]:
                        cur_enr["name"] = clean_name
                continue

            # Unmatched footprint: check exclusion overlap against water/sports and roads
            water_sports_ratio = (
                excl_union.intersection(ov_poly).area / ov_area
                if excl_union is not None and excl_union.intersects(ov_poly)
                else 0.0
            )
            road_ratio = (
                road_union.intersection(ov_poly).area / ov_area
                if road_union is not None and road_union.intersects(ov_poly)
                else 0.0
            )
            if water_sports_ratio > 0.25 or road_ratio > 0.25:
                continue

            cent = ov_poly.centroid
            in_margin = (
                margin_min_x <= cent.x <= margin_max_x
                and margin_min_y <= cent.y <= margin_max_y
            )
            in_campus = terrain_utils.is_point_in_campus(
                cent.x,
                cent.y,
                campus_ctx["boundary_ring"],
                campus_ctx["rail_lines"],
                pad_m=8.0,
                rail_margin_m=10.0,
            )
            dist_to_campus = min((ov_poly.distance(ref) for ref in campus_refs), default=999.0)

            short_suffix = f"_{part_idx + 1}" if len(parts) > 1 else ""
            fid = f"overture/{ov_full_id[:12]}{short_suffix}"
            n_verts = max(0, len(ov_geojson["coordinates"][0]) - 1)
            quality_score = (
                (2000.0 if clean_name else 0.0)
                + (500.0 if (ov_height is not None or ov_floors is not None) else 0.0)
                + ov_area
                + min(n_verts, 20) * 5.0
            )

            subtype = str(row.get("subtype") or row.get("bclass") or "yes")
            tags: dict[str, Any] = {
                "building": subtype,
                "source": src_label,
                "overture_id": ov_full_id,
            }
            if clean_name:
                tags["name"] = clean_name
            if row.get("bclass"):
                tags["overture:class"] = str(row["bclass"])
            if row.get("roof_shape"):
                tags["roof:shape"] = str(row["roof_shape"])
            if ov_floors is not None:
                tags["building:levels"] = str(ov_floors)
            if ov_height is not None:
                tags["height"] = str(ov_height)

            unmatched_candidates.append(
                {
                    "fid": fid,
                    "overture_id": ov_full_id,
                    "poly": ov_poly,
                    "geojson": ov_geojson,
                    "area_m2": round(ov_area, 1),
                    "in_margin": in_margin,
                    "in_campus": in_campus,
                    "dist_to_campus_m": round(float(dist_to_campus), 1),
                    "name": clean_name,
                    "height_m": ov_height,
                    "num_floors": ov_floors,
                    "subtype": subtype,
                    "tags": tags,
                    "source_dataset": src_label,
                    "quality_score": quality_score,
                }
            )

    # Deduplicate overlapping unmatched Overture polygons (prefer richer/named/height-bearing polygons)
    unmatched_candidates.sort(key=lambda c: c["quality_score"], reverse=True)
    accepted_new: list[dict[str, Any]] = []
    seen_fids: set[str] = set()
    for cand in unmatched_candidates:
        cpoly = cand["poly"]
        cb = cpoly.bounds
        is_dup = False
        for existing in accepted_new:
            epoly = existing["poly"]
            eb = epoly.bounds
            if cb[2] < eb[0] or cb[0] > eb[2] or cb[3] < eb[1] or cb[1] > eb[3]:
                continue
            inter = cpoly.intersection(epoly).area
            if inter <= 0.0:
                continue
            min_area = min(cpoly.area, epoly.area)
            if min_area > 0 and (inter / min_area) > DEDUP_OVERLAP_RATIO:
                is_dup = True
                break
        if is_dup:
            continue

        fid = cand["fid"]
        while fid in seen_fids:
            fid = f"{fid}_x"
        seen_fids.add(fid)
        cand["fid"] = fid

        area_m2 = cand["area_m2"]
        cand["include_in_scene"] = bool(
            cand["in_margin"]
            and cand["in_campus"]
            and (area_m2 >= 60.0 or (area_m2 >= 30.0 and cand["name"] is not None))
        )
        accepted_new.append(cand)

    # Process Overture Places and snap them to OSM or included Overture buildings
    all_building_targets: list[tuple[str, Any, dict[str, Any]]] = [
        (fid, poly, {"kind": "osm"}) for fid, poly, _ in osm_buildings
    ] + [
        (c["fid"], c["poly"], {"kind": "overture", "ref": c})
        for c in accepted_new
        if c["include_in_scene"]
    ]
    small_unincluded_ov = [
        c
        for c in accepted_new
        if (not c["include_in_scene"]) and c["in_margin"] and c["in_campus"] and c["area_m2"] >= 25.0
    ]

    building_places: dict[str, list[dict[str, Any]]] = {}
    unmatched_places: list[dict[str, Any]] = []
    places_total = 0
    places_matched_count = 0

    for row in raw_ov_places:
        op_status = str(row.get("operating_status") or "").strip().lower()
        if op_status in {"closed", "permanently_closed"}:
            continue
        pname = str(row.get("primary_name") or "").strip()
        if not pname:
            continue
        conf_raw = row.get("confidence")
        conf = float(conf_raw) if conf_raw is not None else None
        if conf is not None and conf < PLACE_MIN_CONFIDENCE:
            continue
        geom_json = row.get("geom_json")
        if not geom_json:
            continue
        gdict = json.loads(geom_json)
        if gdict.get("type") != "Point":
            continue
        lon, lat = float(gdict["coordinates"][0]), float(gdict["coordinates"][1])
        px, py = latlon_to_xy(lat, lon)
        pt = Point(px, py)
        places_total += 1

        raw_cat = str(row.get("raw_category")) if row.get("raw_category") else None
        hier = list(row.get("category_hierarchy") or [])
        campus_cat = map_overture_category(raw_cat, hier, pname)
        src_label = _extract_primary_source(row.get("sources"))

        best_target_id: str | None = None
        best_dist = PLACE_SNAP_MAX_DIST_M + 1e-6

        for target_id, tpoly, _ in all_building_targets:
            d = float(pt.distance(tpoly))
            if d < best_dist:
                best_dist = d
                best_target_id = target_id

        # If not closely matched yet, check if a small valid Overture building (25-45m2) sits right under this Place
        if best_target_id is None or best_dist > 12.0:
            for cand in small_unincluded_ov:
                d_small = float(pt.distance(cand["poly"]))
                if d_small <= PLACE_SMALL_BLDG_PROMOTE_DIST_M and d_small < best_dist:
                    best_dist = d_small
                    best_target_id = cand["fid"]
                    if not cand["include_in_scene"]:
                        cand["include_in_scene"] = True
                        all_building_targets.append((cand["fid"], cand["poly"], {"kind": "overture", "ref": cand}))

        place_record = {
            "id": f"overture_place/{str(row['id'])[:12]}",
            "overture_id": str(row["id"]),
            "name": pname,
            "is_generic_name": is_generic_place_name(pname),
            "category": campus_cat,
            "raw_category": raw_cat,
            "confidence": round(conf, 3) if conf is not None else None,
            "source": src_label,
            "latLon": [round(lat, 6), round(lon, 6)],
            "centerXZ": [round(px, 2), round(-py, 2)],
        }

        if best_target_id is not None and best_dist <= PLACE_SNAP_MAX_DIST_M:
            place_record["dist_m"] = round(best_dist, 1)
            building_places.setdefault(best_target_id, []).append(place_record)
            places_matched_count += 1
        elif (
            core_min_x <= px <= core_max_x
            and core_min_y <= py <= core_max_y
            and terrain_utils.is_point_in_campus(
                px,
                py,
                campus_ctx["boundary_ring"],
                campus_ctx["rail_lines"],
                pad_m=8.0,
                rail_margin_m=8.0,
            )
        ):
            unmatched_places.append(place_record)

    # Sort attached places cleanly (non-generic + closest + highest confidence first)
    for plist in building_places.values():
        plist.sort(
            key=lambda p: (
                p["is_generic_name"],
                p.get("dist_m", 99.0),
                -(p["confidence"] if p["confidence"] is not None else 0.5),
            )
        )

    # Convert accepted unmatched footprints to raw_osm-compatible Feature dicts
    new_building_features: list[dict[str, Any]] = []
    included_new_count = 0
    for cand in accepted_new:
        if cand["include_in_scene"]:
            included_new_count += 1
        cent = cand["poly"].centroid
        clat, clon = config.local_xz_to_latlon(cent.x, -cent.y)
        feat = {
            "type": "Feature",
            "id": cand["fid"],
            "geometry": cand["geojson"],
            "properties": {
                "osm_id": cand["fid"],
                "overture_id": cand["overture_id"],
                "layer": "building",
                "subtype": cand["subtype"],
                "name": cand["name"],
                "building_levels": cand["num_floors"],
                "height_m": cand["height_m"],
                "source_dataset": cand["source_dataset"],
                "area_m2": cand["area_m2"],
                "in_terrain_margin": cand["in_margin"],
                "dist_to_campus_m": cand["dist_to_campus_m"],
                "include_in_scene": cand["include_in_scene"],
                "centroidLatLon": [clat, clon],
                "tags": cand["tags"],
            },
        }
        new_building_features.append(feat)

    height_enriched_count = sum(
        1 for v in osm_enrichments.values() if v.get("height_m") is not None or v.get("num_floors") is not None
    )

    output = {
        "metadata": {
            "release": release,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bbox": list(config.BBOX),
            "origin": list(config.ORIGIN),
            "counts": {
                "raw_buildings": len(raw_ov_buildings),
                "matched_osm_buildings": len(matched_osm_ids),
                "osm_height_enrichments": height_enriched_count,
                "new_buildings_total": len(new_building_features),
                "new_buildings_included": included_new_count,
                "places_total": places_total,
                "places_matched_to_buildings": places_matched_count,
                "places_unmatched": len(unmatched_places),
            },
            "sources_breakdown": dict(sorted(sources_breakdown.items(), key=lambda kv: -kv[1])),
        },
        "osm_enrichments": osm_enrichments,
        "new_buildings": new_building_features,
        "building_places": building_places,
        "unmatched_places": unmatched_places,
    }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with config.OVERTURE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    size_kb = config.OVERTURE_PATH.stat().st_size / 1024.0
    print(f"\nSaved {config.OVERTURE_PATH} ({size_kb:.1f} KB)")
    print("=== Overture Maps Campus Audit ===")
    print(f"Release          : {release}")
    print(f"Sources breakdown: {output['metadata']['sources_breakdown']}")
    print(
        f"OSM diff         : {len(matched_osm_ids)} OSM buildings matched | "
        f"{height_enriched_count} enriched with Overture height/floors"
    )
    print(
        f"New footprints   : {included_new_count} included in 3D scene "
        f"({len(new_building_features)} total unmatched Overture polygons)"
    )

    included_feats = [f for f in new_building_features if f["properties"]["include_in_scene"]]
    included_feats.sort(key=lambda f: f["properties"]["area_m2"], reverse=True)
    print("\nTop new included buildings missing from OSM:")
    for feat in included_feats[:25]:
        p = feat["properties"]
        fid = feat["id"]
        places_str = ", ".join(pl["name"] for pl in building_places.get(fid, []) if not pl["is_generic_name"])
        label = p["name"] or places_str or "(unnamed)"
        h_str = f"{p['building_levels']}F" if p.get("building_levels") else f"{p['height_m']}m" if p.get("height_m") else "-"
        latlon = p["centroidLatLon"]
        print(
            f"  {fid:<24s} | {p['area_m2']:>7.1f} m2 | h={h_str:<5s} | "
            f"d_osm={p['dist_to_campus_m']:>5.1f}m | {latlon[0]:.5f},{latlon[1]:.5f} | "
            f"{p['source_dataset']:<22s} | {label}"
        )

    print(f"\nOverture Places found ({places_total} active with confidence >= {PLACE_MIN_CONFIDENCE}):")
    all_place_rows: list[tuple[str, dict[str, Any]]] = []
    for target_id, plist in building_places.items():
        for pl in plist:
            all_place_rows.append((f"{target_id} ({pl['dist_m']}m)", pl))
    for pl in unmatched_places:
        all_place_rows.append(("UNMATCHED", pl))
    all_place_rows.sort(key=lambda item: (item[0] == "UNMATCHED", -(item[1]["confidence"] or 0.0), item[1]["name"]))
    for target_str, pl in all_place_rows:
        conf_s = f"{pl['confidence']:.2f}" if pl["confidence"] is not None else "-"
        print(
            f"  [{pl['category']:<8s}] {pl['name']:<38s} | conf={conf_s} | "
            f"{pl['latLon'][0]:.5f},{pl['latLon'][1]:.5f} -> {target_str}"
        )


if __name__ == "__main__":
    main()
