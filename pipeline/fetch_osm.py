"""Fetch campus OSM features via Overpass API and save clean GeoJSON-like output."""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from datetime import datetime, timezone
from typing import Any

import requests
from shapely.geometry import Polygon

try:
    from . import config
except ImportError:
    import config

CAMPUS_BOUNDARY_WAY_IDS: tuple[int, ...] = (128964693,)
RAILWAY_WAY_IDS: tuple[int, ...] = (128964718, 1327801976)
RAILWAY_NODE_IDS: tuple[int, ...] = (1423798452, 1423798465, 1423798471)
OSM_API_BASE: str = "https://api.openstreetmap.org/api/0.6"

WATER_LANDUSES = {"reservoir", "basin"}
SPORTS_LEISURES = {"pitch", "sports_centre", "stadium", "track"}
GREEN_NATURALS = {"wood", "scrub", "grassland", "heath", "tree_row"}
GREEN_LANDUSES = {
    "forest",
    "grass",
    "meadow",
    "orchard",
    "recreation_ground",
    "village_green",
    "greenfield",
    "farmland",
}
GREEN_LEISURES = {"park", "garden", "nature_reserve"}


def build_overpass_query(bbox_str: str) -> str:
    """Build Overpass QL query for campus boundary, railway, buildings, paths, water, sports, and green areas."""
    return f"""[out:json][timeout:60][bbox:{bbox_str}];
(
  way["amenity"="university"];
  relation["amenity"="university"];
  way["railway"="rail"];
  node["railway"~"^(station|level_crossing)$"];
  way["building"];
  relation["building"];
  way["highway"];
  way["natural"="water"];
  relation["natural"="water"];
  way["waterway"];
  relation["waterway"];
  way["landuse"~"^(reservoir|basin)$"];
  relation["landuse"~"^(reservoir|basin)$"];
  way["leisure"="swimming_pool"];
  way["leisure"~"^(pitch|sports_centre|stadium|track)$"];
  relation["leisure"~"^(pitch|sports_centre|stadium|track)$"];
  way["sport"];
  relation["sport"];
  way["natural"~"^(wood|scrub|grassland|heath|tree_row)$"];
  relation["natural"~"^(wood|scrub|grassland|heath)$"];
  way["landuse"~"^(forest|grass|meadow|orchard|recreation_ground|village_green|greenfield|farmland)$"];
  relation["landuse"~"^(forest|grass|meadow|orchard|recreation_ground|village_green|greenfield|farmland)$"];
  way["leisure"~"^(park|garden|nature_reserve)$"];
  relation["leisure"~"^(park|garden|nature_reserve)$"];
);
out body;
>;
out skel qt;"""


def _parse_retry_after(header_value: str | None) -> float | None:
    """Parse numeric Retry-After header seconds if present."""
    if not header_value:
        return None
    try:
        return max(1.0, float(header_value.strip()))
    except ValueError:
        return None


def query_overpass(query: str, max_retries: int = 5) -> tuple[dict[str, Any], str]:
    """Execute Overpass QL query with retries, mirror rotation, and polite headers."""
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json",
    }
    session = requests.Session()
    endpoints = config.OVERPASS_ENDPOINTS
    last_error: Exception | None = None

    for attempt in range(max_retries):
        endpoint = endpoints[attempt % len(endpoints)]
        try:
            response = session.post(
                endpoint,
                data={"data": query},
                headers=headers,
                timeout=75,
            )

            if response.status_code in (429, 500, 502, 503, 504):
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                wait_s = retry_after or (min(30.0, 2.0 * (2**attempt)) + random.uniform(0.2, 1.0))
                last_error = RuntimeError(f"HTTP {response.status_code} from {endpoint}")
                print(f"[retry {attempt + 1}/{max_retries}] {last_error}; waiting {wait_s:.1f}s...")
                time.sleep(wait_s)
                continue

            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
                raise ValueError(f"Unexpected Overpass JSON structure from {endpoint}")

            remark = str(payload.get("remark", ""))
            if remark and any(tok in remark.lower() for tok in ("error", "timed out", "runtime")):
                raise RuntimeError(f"Overpass error remark from {endpoint}: {remark}")

            return payload, endpoint

        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                wait_s = min(30.0, 2.0 * (2**attempt)) + random.uniform(0.2, 1.0)
                print(f"[retry {attempt + 1}/{max_retries}] {exc}; waiting {wait_s:.1f}s...")
                time.sleep(wait_s)

    raise RuntimeError(f"Failed to fetch OSM data from Overpass after {max_retries} attempts: {last_error}")


def classify_tags(tags: dict[str, Any]) -> tuple[str, str] | None:
    """Classify OSM element tags into (layer, subtype)."""
    if not tags:
        return None

    building = tags.get("building")
    if building and building != "no":
        return ("building", str(building))

    if tags.get("amenity") == "university":
        return ("boundary", "campus")

    if tags.get("railway") == "rail":
        return ("railway", "rail")

    if (
        tags.get("natural") == "water"
        or "waterway" in tags
        or tags.get("landuse") in WATER_LANDUSES
        or tags.get("leisure") == "swimming_pool"
    ):
        subtype = (
            tags.get("waterway")
            or tags.get("water")
            or tags.get("landuse")
            or tags.get("leisure")
            or tags.get("natural")
            or "water"
        )
        return ("water", str(subtype))

    if tags.get("leisure") in SPORTS_LEISURES or "sport" in tags:
        subtype = tags.get("sport") or tags.get("leisure") or "sports"
        return ("sports", str(subtype))

    if "highway" in tags:
        return ("path", str(tags["highway"]))

    if (
        tags.get("natural") in GREEN_NATURALS
        or tags.get("landuse") in GREEN_LANDUSES
        or tags.get("leisure") in GREEN_LEISURES
    ):
        subtype = tags.get("landuse") or tags.get("natural") or tags.get("leisure") or "green"
        return ("green", str(subtype))

    return None


def _parse_float(raw: Any) -> float | None:
    """Parse a positive/numeric OSM measurement string such as '12.5 m'."""
    if raw is None:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(raw).strip())
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_levels(raw: Any) -> int | float | None:
    """Parse building:levels tag as int when whole, else float."""
    val = _parse_float(raw)
    if val is None or val <= 0:
        return None
    if val.is_integer():
        return int(val)
    return val


def _way_coords(
    node_ids: list[int],
    nodes_by_id: dict[int, tuple[float, float]],
) -> list[list[float]]:
    """Resolve OSM node IDs into GeoJSON [lon, lat] coordinate list."""
    return [
        [nodes_by_id[nid][0], nodes_by_id[nid][1]]
        for nid in node_ids
        if nid in nodes_by_id
    ]


def stitch_ways_to_rings(
    way_ids: list[int],
    ways_by_id: dict[int, dict[str, Any]],
    nodes_by_id: dict[int, tuple[float, float]],
) -> list[list[list[float]]]:
    """Stitch ordered/unordered OSM member ways into closed GeoJSON [lon, lat] rings."""
    rings: list[list[list[float]]] = []
    open_segments: list[list[int]] = []

    for wid in way_ids:
        way = ways_by_id.get(wid)
        if not way:
            continue
        nids = [nid for nid in way.get("nodes", []) if nid in nodes_by_id]
        if len(nids) < 2:
            continue
        if len(nids) >= 4 and nids[0] == nids[-1]:
            coords = _way_coords(nids, nodes_by_id)
            if len(coords) >= 4:
                rings.append(coords)
        else:
            open_segments.append(nids)

    while open_segments:
        current = open_segments.pop(0)
        changed = True
        while current[0] != current[-1] and changed:
            changed = False
            for idx, seg in enumerate(open_segments):
                if seg[0] == current[-1]:
                    current = current + seg[1:]
                elif seg[-1] == current[-1]:
                    current = current + list(reversed(seg[:-1]))
                elif seg[-1] == current[0]:
                    current = seg[:-1] + current
                elif seg[0] == current[0]:
                    current = list(reversed(seg[1:])) + current
                else:
                    continue
                open_segments.pop(idx)
                changed = True
                break

        if current[0] == current[-1] and len(current) >= 4:
            coords = _way_coords(current, nodes_by_id)
            if len(coords) >= 4:
                rings.append(coords)

    return rings


def _to_valid_polygon(ring: list[list[float]]) -> Polygon | None:
    """Convert a closed coordinate ring into a valid non-empty Shapely Polygon."""
    if len(ring) < 4:
        return None
    poly = Polygon(ring)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or poly.area <= 0:
        return None
    return poly


def build_relation_geometry(
    relation: dict[str, Any],
    ways_by_id: dict[int, dict[str, Any]],
    nodes_by_id: dict[int, tuple[float, float]],
) -> tuple[dict[str, Any] | None, list[int]]:
    """Build Polygon/MultiPolygon GeoJSON geometry from a relation and return member way IDs."""
    outer_way_ids: list[int] = []
    inner_way_ids: list[int] = []

    for member in relation.get("members", []):
        if member.get("type") != "way":
            continue
        ref = member.get("ref")
        if ref is None:
            continue
        role = member.get("role", "")
        if role in ("outer", ""):
            outer_way_ids.append(int(ref))
        elif role == "inner":
            inner_way_ids.append(int(ref))

    outer_rings = stitch_ways_to_rings(outer_way_ids, ways_by_id, nodes_by_id)
    if not outer_rings:
        return None, []

    inner_rings = stitch_ways_to_rings(inner_way_ids, ways_by_id, nodes_by_id)
    outer_polys = [_to_valid_polygon(ring) for ring in outer_rings]

    grouped_rings: list[list[list[list[float]]]] = [[ring] for ring in outer_rings]

    for inner_ring in inner_rings:
        inner_poly = _to_valid_polygon(inner_ring)
        if inner_poly is None:
            continue
        for idx, outer_poly in enumerate(outer_polys):
            if outer_poly is not None and outer_poly.covers(inner_poly):
                grouped_rings[idx].append(inner_ring)
                break

    used_way_ids = outer_way_ids + inner_way_ids
    if len(grouped_rings) == 1:
        return {"type": "Polygon", "coordinates": grouped_rings[0]}, used_way_ids
    return {"type": "MultiPolygon", "coordinates": grouped_rings}, used_way_ids


def build_way_geometry(
    way: dict[str, Any],
    layer: str,
    tags: dict[str, Any],
    nodes_by_id: dict[int, tuple[float, float]],
) -> dict[str, Any] | None:
    """Convert an OSM way into a GeoJSON LineString or Polygon geometry."""
    coords = _way_coords(way.get("nodes", []), nodes_by_id)
    if len(coords) < 2:
        return None

    is_closed = len(coords) >= 4 and coords[0] == coords[-1]

    if layer == "railway":
        return {"type": "LineString", "coordinates": coords}

    if layer == "boundary":
        if is_closed:
            return {"type": "Polygon", "coordinates": [coords]}
        distinct_pts = {(pt[0], pt[1]) for pt in coords}
        if len(distinct_pts) >= 3:
            closed = coords + [coords[0]]
            return {"type": "Polygon", "coordinates": [closed]}
        return None

    if layer == "path":
        if tags.get("area") == "yes" and is_closed:
            return {"type": "Polygon", "coordinates": [coords]}
        return {"type": "LineString", "coordinates": coords}

    if (
        layer == "water"
        and "waterway" in tags
        and tags.get("natural") != "water"
        and tags.get("landuse") not in WATER_LANDUSES
    ):
        if tags.get("area") == "yes" and is_closed:
            return {"type": "Polygon", "coordinates": [coords]}
        return {"type": "LineString", "coordinates": coords}

    if layer == "green" and tags.get("natural") == "tree_row":
        return {"type": "LineString", "coordinates": coords}

    if is_closed:
        return {"type": "Polygon", "coordinates": [coords]}

    if layer == "building":
        distinct_pts = {(pt[0], pt[1]) for pt in coords}
        if len(distinct_pts) >= 3:
            closed = coords + [coords[0]]
            return {"type": "Polygon", "coordinates": [closed]}
        return None

    if layer == "sports":
        return {"type": "LineString", "coordinates": coords}

    return None


def build_properties(
    osm_type: str,
    osm_numeric_id: int,
    layer: str,
    subtype: str,
    tags: dict[str, Any],
) -> dict[str, Any]:
    """Construct clean feature properties for a parsed OSM feature."""
    name = tags.get("name") or tags.get("short_name") or tags.get("alt_name")
    props: dict[str, Any] = {
        "osm_id": f"{osm_type}/{osm_numeric_id}",
        "osm_type": osm_type,
        "osm_numeric_id": osm_numeric_id,
        "layer": layer,
        "subtype": subtype,
        "name": name,
        "tags": tags,
    }
    if layer == "building":
        props["building_levels"] = _parse_levels(tags.get("building:levels"))
        props["height_m"] = _parse_float(tags.get("height"))
    return props


def parse_osm_elements(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Parse raw Overpass elements into GeoJSON-like features and layer counts."""
    elements = payload.get("elements", [])
    nodes_by_id: dict[int, tuple[float, float]] = {}
    tagged_rail_nodes: list[dict[str, Any]] = []
    ways_by_id: dict[int, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []

    for el in elements:
        el_type = el.get("type")
        if el_type == "node" and "lat" in el and "lon" in el:
            nodes_by_id[int(el["id"])] = (float(el["lon"]), float(el["lat"]))
            r_tag = (el.get("tags") or {}).get("railway")
            if r_tag in {"station", "level_crossing"}:
                tagged_rail_nodes.append(el)
        elif el_type == "way":
            ways_by_id[int(el["id"])] = el
        elif el_type == "relation":
            relations.append(el)

    features: list[dict[str, Any]] = []
    consumed_way_ids: set[int] = set()

    for rn in tagged_rail_nodes:
        nid = int(rn["id"])
        tags = rn.get("tags") or {}
        subtype = str(tags.get("railway"))
        features.append(
            {
                "type": "Feature",
                "id": f"node/{nid}",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(rn["lon"]), float(rn["lat"])],
                },
                "properties": build_properties("node", nid, "railway_node", subtype, tags),
            }
        )

    for rel in relations:
        tags = rel.get("tags") or {}
        classified = classify_tags(tags)
        if not classified:
            continue
        layer, subtype = classified
        geometry, used_way_ids = build_relation_geometry(rel, ways_by_id, nodes_by_id)
        if geometry is None:
            continue

        rel_id = int(rel["id"])
        for wid in used_way_ids:
            member_way = ways_by_id.get(wid)
            if not member_way:
                continue
            member_tags = member_way.get("tags") or {}
            member_cls = classify_tags(member_tags)
            if not member_tags or (member_cls and member_cls[0] == layer):
                consumed_way_ids.add(wid)

        features.append(
            {
                "type": "Feature",
                "id": f"relation/{rel_id}",
                "geometry": geometry,
                "properties": build_properties("relation", rel_id, layer, subtype, tags),
            }
        )

    for wid, way in ways_by_id.items():
        if wid in consumed_way_ids:
            continue
        tags = way.get("tags") or {}
        classified = classify_tags(tags)
        if not classified:
            continue
        layer, subtype = classified
        geometry = build_way_geometry(way, layer, tags, nodes_by_id)
        if geometry is None:
            continue

        features.append(
            {
                "type": "Feature",
                "id": f"way/{wid}",
                "geometry": geometry,
                "properties": build_properties("way", wid, layer, subtype, tags),
            }
        )

    features.sort(key=lambda f: (f["properties"]["layer"], f["id"]))

    counts = {
        "building": 0,
        "path": 0,
        "water": 0,
        "sports": 0,
        "green": 0,
        "boundary": 0,
        "railway": 0,
        "railway_node": 0,
    }
    for feat in features:
        layer = feat["properties"]["layer"]
        if layer in counts:
            counts[layer] += 1
    counts["total"] = len(features)
    return features, counts


def fetch_boundary_and_railway_from_osm_api() -> list[dict[str, Any]]:
    """Fetch campus boundary way, railway tracks, and rail nodes directly from OSM v0.6 REST API."""
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json",
    }
    session = requests.Session()
    elements_by_key: dict[tuple[str, int], dict[str, Any]] = {}

    def _ingest(elements: list[dict[str, Any]]) -> None:
        for el in elements:
            etype = str(el.get("type", ""))
            eid = el.get("id")
            if not etype or eid is None:
                continue
            key = (etype, int(eid))
            existing = elements_by_key.get(key)
            if existing is None or (el.get("tags") and not existing.get("tags")):
                elements_by_key[key] = el

    for wid in CAMPUS_BOUNDARY_WAY_IDS + RAILWAY_WAY_IDS:
        resp = session.get(f"{OSM_API_BASE}/way/{wid}/full.json", headers=headers, timeout=30)
        resp.raise_for_status()
        _ingest(resp.json().get("elements", []))

    for nid in RAILWAY_NODE_IDS:
        resp = session.get(f"{OSM_API_BASE}/node/{nid}.json", headers=headers, timeout=30)
        resp.raise_for_status()
        _ingest(resp.json().get("elements", []))

    features, _ = parse_osm_elements({"elements": list(elements_by_key.values())})
    return features


def merge_supplement_into_raw_osm(supplement_features: list[dict[str, Any]]) -> dict[str, int]:
    """Upsert supplement features into existing raw_osm.json and recompute layer counts."""
    if not config.RAW_OSM_PATH.exists():
        raise FileNotFoundError(f"Cannot supplement missing file: {config.RAW_OSM_PATH}")

    existing_payload = json.loads(config.RAW_OSM_PATH.read_text(encoding="utf-8"))
    by_id: dict[str, dict[str, Any]] = {
        str(feat["id"]): feat for feat in existing_payload.get("features", [])
    }
    for feat in supplement_features:
        by_id[str(feat["id"])] = feat

    merged_features = sorted(
        by_id.values(),
        key=lambda f: (str(f.get("properties", {}).get("layer", "")), str(f.get("id", ""))),
    )

    counts = {
        "building": 0,
        "path": 0,
        "water": 0,
        "sports": 0,
        "green": 0,
        "boundary": 0,
        "railway": 0,
        "railway_node": 0,
    }
    for feat in merged_features:
        layer = feat.get("properties", {}).get("layer")
        if layer in counts:
            counts[layer] += 1
    counts["total"] = len(merged_features)

    meta = existing_payload.setdefault("metadata", {})
    meta["counts"] = counts
    meta["supplemented_at"] = datetime.now(timezone.utc).isoformat()
    meta["supplement_source"] = "OpenStreetMap REST API v0.6"
    existing_payload["features"] = merged_features

    with config.RAW_OSM_PATH.open("w", encoding="utf-8") as fh:
        json.dump(existing_payload, fh, indent=2, ensure_ascii=False)
    return counts


def _print_summary(counts: dict[str, int], source_label: str) -> None:
    size_kb = config.RAW_OSM_PATH.stat().st_size / 1024.0
    print(f"Saved {config.RAW_OSM_PATH} ({size_kb:.1f} KB) via {source_label}")
    print(
        "OSM summary: "
        f"buildings={counts['building']}, "
        f"paths={counts['path']}, "
        f"water={counts['water']}, "
        f"sports={counts['sports']}, "
        f"green={counts['green']}, "
        f"boundary={counts['boundary']}, "
        f"railway={counts['railway']}, "
        f"railway_nodes={counts['railway_node']}, "
        f"total={counts['total']}"
    )


def main() -> None:
    """Fetch OSM data for Amrita campus BBOX and write pipeline/data/raw_osm.json."""
    parser = argparse.ArgumentParser(description="Fetch or supplement campus OSM data.")
    parser.add_argument(
        "--supplement-only",
        action="store_true",
        help="Fetch campus boundary & railway features via OSM REST API v0.6 and merge into existing raw_osm.json.",
    )
    args = parser.parse_args()

    if args.supplement_only:
        print("Fetching campus boundary & railway features via OSM REST API v0.6...")
        sup_feats = fetch_boundary_and_railway_from_osm_api()
        counts = merge_supplement_into_raw_osm(sup_feats)
        _print_summary(counts, f"{OSM_API_BASE} (--supplement-only)")
        return

    bbox_str = config.overpass_bbox_str()
    query = build_overpass_query(bbox_str)
    print(f"Querying Overpass API for BBOX ({bbox_str})...")

    payload, used_endpoint = query_overpass(query)
    features, counts = parse_osm_elements(payload)
    try:
        payload, used_endpoint = query_overpass(query)
        features, counts = parse_osm_elements(payload)
    except RuntimeError as exc:
        if config.RAW_OSM_PATH.exists():
            print(f"[warning] {exc}\nFalling back to OSM REST API v0.6 supplement into existing raw_osm.json...")
            sup_feats = fetch_boundary_and_railway_from_osm_api()
            counts = merge_supplement_into_raw_osm(sup_feats)
            _print_summary(counts, f"{OSM_API_BASE} (fallback supplement)")
            return
        raise

    output = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "OpenStreetMap Overpass API",
            "endpoint": used_endpoint,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bbox": list(config.BBOX),
            "origin": list(config.ORIGIN),
            "coordinate_order": "lon,lat",
            "counts": counts,
        },
        "features": features,
    }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with config.RAW_OSM_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    size_kb = config.RAW_OSM_PATH.stat().st_size / 1024.0
    print(f"Saved {config.RAW_OSM_PATH} ({size_kb:.1f} KB) via {used_endpoint}")
    print(
        "OSM summary: "
        f"buildings={counts['building']}, "
        f"paths={counts['path']}, "
        f"water={counts['water']}, "
        f"sports={counts['sports']}, "
        f"green={counts['green']}, "
        f"boundary={counts['boundary']}, "
        f"railway={counts['railway']}, "
        f"railway_nodes={counts['railway_node']}, "
        f"total={counts['total']}"
    )
    _print_summary(counts, used_endpoint)


if __name__ == "__main__":
    main()
