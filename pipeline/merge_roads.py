"""Precompute smooth Shapely-merged road polygons, curb rings, and road-edge streetlamps."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

try:
    from . import campus_frame, config, terrain_utils
except ImportError:
    import campus_frame
    import config
    import terrain_utils

# Half-widths in meters around OSM centerline
ROAD_HALF_WIDTH_M: dict[str, float] = {
    "primary": 3.5,
    "secondary": 3.5,
    "tertiary": 3.5,
    "unclassified": 2.4,
    "residential": 2.4,
    "service": 2.3,
    "pedestrian": 1.2,
    "footway": 1.1,
    "path": 1.1,
    "steps": 1.1,
    "cycleway": 1.1,
}

MAIN_ROAD_MIN_HALF_W = 2.0
LAMP_STEP_M = 28.0
LAMP_MIN_SEPARATION_M = 25.0


def _latlon_to_blender_xy(lat: float, lon: float) -> tuple[float, float]:
    x_east, z_south = config.latlon_to_local_xz(lat, lon)
    return (x_east, -z_south)


class CoreTerrainSampler:
    """Bilinear-triangle core terrain sampler matching TerrainSurface inside campus bounds."""

    def __init__(self, elevation: dict[str, Any], raw_osm: dict[str, Any] | None = None) -> None:
        datum_m = float(elevation["metadata"]["stats"]["origin_elevation_m"])
        raw_z = np.asarray(elevation["elevations"], dtype=float) - datum_m
        up_rows = terrain_utils.upsample_1d_catmull_rom(raw_z)
        up_zs: np.ndarray = terrain_utils.upsample_1d_catmull_rom(up_rows.T).T

        lats = elevation["lats"]
        lons = elevation["lons"]
        south_y = _latlon_to_blender_xy(lats[0], config.ORIGIN[1])[1]
        north_y = _latlon_to_blender_xy(lats[-1], config.ORIGIN[1])[1]
        west_x = _latlon_to_blender_xy(config.ORIGIN[0], lons[0])[0]
        east_x = _latlon_to_blender_xy(config.ORIGIN[0], lons[-1])[0]

        ny, nx = up_zs.shape
        core_xs = np.linspace(west_x, east_x, nx)
        core_ys = np.linspace(south_y, north_y, ny)
        self.zs: np.ndarray = terrain_utils.grade_core_terrain_pads(core_xs, core_ys, up_zs, raw_osm)
        self.min_x = float(west_x)
        self.max_x = float(east_x)
        self.min_y = float(south_y)
        self.max_y = float(north_y)
        self.nx = nx
        self.ny = ny

    def sample(self, x: float, y: float) -> float:
        cx = min(max(x, self.min_x), self.max_x)
        cy = min(max(y, self.min_y), self.max_y)
        fx = (cx - self.min_x) / (self.max_x - self.min_x) * (self.nx - 1)
        fy = (cy - self.min_y) / (self.max_y - self.min_y) * (self.ny - 1)
        c = min(max(int(math.floor(fx)), 0), self.nx - 2)
        r = min(max(int(math.floor(fy)), 0), self.ny - 2)
        u, v = fx - c, fy - r
        z00, z10 = self.zs[r, c], self.zs[r, c + 1]
        z01, z11 = self.zs[r + 1, c], self.zs[r + 1, c + 1]
        z = z00 + u * (z10 - z00) + v * (z11 - z10) if u >= v else z00 + v * (z01 - z00) + u * (z11 - z01)
        return float(z) + campus_frame.rise_offset(cx, cy)


def _extract_polygons(geom: Any) -> list[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom] if geom.area > 0.25 else []
    if isinstance(geom, MultiPolygon) or hasattr(geom, "geoms"):
        out: list[Polygon] = []
        for g in geom.geoms:
            out.extend(_extract_polygons(g))
        return out
    return []


def _ring_signed_area(pts: list[tuple[float, float]]) -> float:
    area2 = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area2 += x1 * y2 - x2 * y1
    return 0.5 * area2


def _clean_ring_coords(coords: Any, want_ccw: bool) -> list[list[float]]:
    pts = [(float(p[0]), float(p[1])) for p in list(coords)[:-1]]
    if len(pts) < 3:
        return []
    deduped: list[tuple[float, float]] = [pts[0]]
    for pt in pts[1:]:
        if math.hypot(pt[0] - deduped[-1][0], pt[1] - deduped[-1][1]) >= 0.08:
            deduped.append(pt)
    if len(deduped) >= 3 and math.hypot(deduped[0][0] - deduped[-1][0], deduped[0][1] - deduped[-1][1]) < 0.08:
        deduped.pop()
    if len(deduped) < 3:
        return []
    area = _ring_signed_area(deduped)
    if want_ccw and area < 0:
        deduped.reverse()
    elif (not want_ccw) and area > 0:
        deduped.reverse()
    return [[round(x, 3), round(y, 3)] for x, y in deduped]


def _ring_outward_sign(pts: list[list[float]], road_geom: Any) -> int:
    """Determine +1 if right normal (ty, -tx) points away from road asphalt, else -1."""
    if len(pts) < 2:
        return 1
    votes_pos = 0
    votes_neg = 0
    step = max(1, len(pts) // 16)
    for i in range(0, len(pts), step):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % len(pts)]
        dx, dy = bx - ax, by - ay
        d = math.hypot(dx, dy)
        if d < 0.2:
            continue
        nx, ny = dy / d, -dx / d
        mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
        p_pos = Point(mx + nx * 0.25, my + ny * 0.25)
        p_neg = Point(mx - nx * 0.25, my - ny * 0.25)
        if not road_geom.contains(p_pos) and road_geom.contains(p_neg):
            votes_pos += 1
        elif road_geom.contains(p_pos) and not road_geom.contains(p_neg):
            votes_neg += 1
    return -1 if votes_neg > votes_pos else 1


def _densify_ring_coords(pts: list[list[float]], max_seg_m: float = 8.5) -> list[list[float]]:
    """Insert intermediate vertices along ring edges exceeding max_seg_m for terrain conformity."""
    n = len(pts)
    if n < 3:
        return pts
    out: list[list[float]] = []
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        out.append([round(ax, 3), round(ay, 3)])
        d = math.hypot(bx - ax, by - ay)
        if d > max_seg_m:
            steps = int(math.ceil(d / max_seg_m))
            for s in range(1, steps):
                t = s / steps
                out.append([round(ax + t * (bx - ax), 3), round(ay + t * (by - ay), 3)])
    return out


def build_merged_roads_and_lamps() -> tuple[Path, Path]:
    """Compute merged campus road polygons, Indian curb rings, and streetlamp placements."""
    raw_osm = json.loads(config.RAW_OSM_PATH.read_text(encoding="utf-8"))
    elevation = json.loads(config.ELEVATION_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(config.OVERRIDES_PATH.read_text(encoding="utf-8"))
    exclude_ids = {str(x) for x in (overrides.get("exclude_ids") or [])}

    terrain = CoreTerrainSampler(elevation, raw_osm)
    clip_box = box(
        terrain.min_x + 2.0,
        terrain.min_y + 2.0,
        terrain.max_x - 2.0,
        terrain.max_y - 2.0,
    )

    campus_ctx = terrain_utils.extract_campus_boundary_and_rail(raw_osm)
    boundary_ring = campus_ctx["boundary_ring"]
    rail_lines = campus_ctx["rail_lines"]

    road_clip_geom: Any = clip_box
    if len(boundary_ring) >= 3:
        campus_poly = Polygon(boundary_ring).buffer(14.0)
        if not campus_poly.is_empty:
            road_clip_geom = road_clip_geom.intersection(campus_poly)
    if rail_lines:
        xs_rail = np.linspace(terrain.min_x - 20.0, terrain.max_x + 20.0, 65)
        north_pts: list[tuple[float, float]] = []
        for xr in xs_rail:
            ry = terrain_utils.rail_north_y_at_x(rail_lines, float(xr))
            if ry is not None:
                # Shift -10.0m south so Main Gate drive reaches cleanly to the level crossing
                north_pts.append((float(xr), ry - 10.0))
        if len(north_pts) >= 2:
            poly_pts = north_pts + [
                (terrain.max_x + 40.0, terrain.max_y + 40.0),
                (terrain.min_x - 40.0, terrain.max_y + 40.0),
            ]
            north_of_rail_poly = Polygon(poly_pts).buffer(0)
            if not north_of_rail_poly.is_empty:
                road_clip_geom = road_clip_geom.intersection(north_of_rail_poly)

    all_bufs = []
    main_bufs = []
    obstacle_polys = []

    for feat in raw_osm.get("features", []):
        fid = str(feat.get("id", ""))
        if fid in exclude_ids or fid in config.AB1_FRONT_SUPPRESS_IDS:
            continue
        props = feat.get("properties", {})
        layer = props.get("layer")
        geom = feat.get("geometry", {})

        if layer == "path" and geom.get("type") == "LineString":
            coords = config.path_coords(feat)
            if len(coords) < 2:
                continue
            subtype = str(props.get("subtype", "path"))
            half_w = ROAD_HALF_WIDTH_M.get(subtype, 1.1)
            pts = [_latlon_to_blender_xy(pt[1], pt[0]) for pt in coords]
            clipped = LineString(pts).intersection(road_clip_geom)
            if clipped.is_empty:
                continue
            buf = clipped.buffer(half_w, cap_style=1, join_style=1, quad_segs=6)
            all_bufs.append(buf)
            if half_w >= MAIN_ROAD_MIN_HALF_W:
                main_bufs.append(buf)

        elif layer in {"building", "water", "sports"} and geom.get("type") == "Polygon":
            ring = [_latlon_to_blender_xy(pt[1], pt[0]) for pt in geom["coordinates"][0]]
            if len(ring) >= 3:
                poly = Polygon(ring).buffer(0)
                if not poly.is_empty:
                    obstacle_polys.append(poly.buffer(1.4 if layer == "building" else 1.0))

    # Append custom campus connector roads from overrides.json
    for custom_road in overrides.get("custom_roads") or []:
        if not isinstance(custom_road, dict) or custom_road.get("render") is False:
            continue
        raw_pts = custom_road.get("points") or []
        if len(raw_pts) < 2:
            continue
        subtype = str(custom_road.get("subtype", "residential"))
        half_w = ROAD_HALF_WIDTH_M.get(subtype, 2.4)
        pts = [_latlon_to_blender_xy(float(pt[0]), float(pt[1])) for pt in raw_pts]
        clipped = LineString(pts).intersection(clip_box)
        if clipped.is_empty:
            continue
        buf = clipped.buffer(half_w, cap_style=1, join_style=1, quad_segs=6)
        all_bufs.append(buf)
        if half_w >= MAIN_ROAD_MIN_HALF_W:
            main_bufs.append(buf)

    # Keep streetlamps clear of railway tracks and included Overture buildings
    for rpts in rail_lines:
        if len(rpts) >= 2:
            obstacle_polys.append(LineString(rpts).buffer(6.0))
    if config.OVERTURE_PATH.exists():
        ov_data = json.loads(config.OVERTURE_PATH.read_text(encoding="utf-8"))
        for feat in ov_data.get("new_buildings") or []:
            if str(feat.get("id", "")) in exclude_ids:
                continue
            if not feat.get("properties", {}).get("include_in_scene"):
                continue
            geom = feat.get("geometry", {})
            if geom.get("type") == "Polygon" and geom.get("coordinates"):
                ring = [_latlon_to_blender_xy(pt[1], pt[0]) for pt in geom["coordinates"][0]]
                if len(ring) >= 3:
                    poly = Polygon(ring).buffer(0)
                    if not poly.is_empty:
                        obstacle_polys.append(poly.buffer(1.4))

    if not all_bufs:
        raise RuntimeError("No roads found inside core terrain box")

    merged_all = unary_union(all_bufs).buffer(0).simplify(0.15, preserve_topology=True)
    merged_main = unary_union(main_bufs).buffer(0).simplify(0.15, preserve_topology=True) if main_bufs else merged_all

    asphalt_polygons: list[list[list[list[float]]]] = []
    for poly in _extract_polygons(merged_all):
        outer = _clean_ring_coords(poly.exterior.coords, want_ccw=True)
        if not outer:
            continue
        rings = [_densify_ring_coords(outer, max_seg_m=8.5)]
        for interior in poly.interiors:
            hole = _clean_ring_coords(interior.coords, want_ccw=False)
            if hole:
                rings.append(_densify_ring_coords(hole, max_seg_m=8.5))
        asphalt_polygons.append(rings)

    curb_rings: list[dict[str, Any]] = []
    for poly in _extract_polygons(merged_main):
        outer = _clean_ring_coords(poly.exterior.coords, want_ccw=True)
        if outer:
            sign = _ring_outward_sign(outer, merged_main)
            curb_rings.append({"pts": outer, "outSign": sign})
        for interior in poly.interiors:
            if interior.length < 18.0:
                continue
            hole = _clean_ring_coords(interior.coords, want_ccw=False)
            if hole:
                sign = _ring_outward_sign(hole, merged_main)
                curb_rings.append({"pts": hole, "outSign": sign})

    # Sample streetlamps along outer main-road curb edges
    obstacle_union = unary_union(obstacle_polys).buffer(0) if obstacle_polys else None
    all_road_guard = merged_all.buffer(0.45)

    placed_xy: list[tuple[float, float]] = []
    lamps_out: list[list[float]] = []
    min_sep_sq = LAMP_MIN_SEPARATION_M ** 2

    for ring_entry in curb_rings:
        pts: list[list[float]] = ring_entry["pts"]
        out_sign = int(ring_entry["outSign"])
        if len(pts) < 3:
            continue

        acc = 0.0
        next_at = 8.0
        n = len(pts)
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            seg_len = math.hypot(bx - ax, by - ay)
            if seg_len < 0.25:
                continue
            dx, dy = (bx - ax) / seg_len, (by - ay) / seg_len
            out_nx, out_ny = (dy * out_sign), (-dx * out_sign)

            while acc + seg_len >= next_at:
                t = (next_at - acc) / seg_len
                ex = ax + t * (bx - ax)
                ey = ay + t * (by - ay)
                lx = ex + out_nx * 0.90
                ly = ey + out_ny * 0.90
                if (
                    terrain.min_x + 28.0 <= lx <= terrain.max_x - 28.0
                    and terrain.min_y + 28.0 <= ly <= terrain.max_y - 28.0
                    and terrain_utils.is_point_in_campus(
                        lx,
                        ly,
                        boundary_ring,
                        rail_lines,
                        pad_m=12.0,
                        rail_margin_m=6.0,
                    )
                ):
                    pt_geom = Point(lx, ly)
                    clear = not all_road_guard.contains(pt_geom)
                    if clear and obstacle_union is not None and obstacle_union.contains(pt_geom):
                        clear = False
                    if clear:
                        for ox, oy in placed_xy:
                            if (lx - ox) ** 2 + (ly - oy) ** 2 < min_sep_sq:
                                clear = False
                                break
                    if clear:
                        placed_xy.append((lx, ly))
                        lz = terrain.sample(lx, ly)
                        # Point arm inward toward the asphalt (-out_nx, -out_ny -> glTF (-out_nx, +out_ny))
                        in_gx = -out_nx
                        in_gz = out_ny
                        rot_y = math.atan2(in_gx, in_gz)
                        lamps_out.append([round(lx, 1), round(lz, 1), round(-ly, 1), round(rot_y, 2)])
                next_at += LAMP_STEP_M
            acc += seg_len

    config.ROADS_MERGED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with config.ROADS_MERGED_PATH.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "asphaltPolygons": asphalt_polygons,
                "curbRings": curb_rings,
            },
            fh,
            separators=(",", ":"),
        )

    config.STREETLAMP_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with config.STREETLAMP_JSON_PATH.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "count": len(lamps_out),
                "format": "[x,y,z,rotY]",
                "lamps": lamps_out,
            },
            fh,
            separators=(",", ":"),
        )

    print(
        f"Merged roads: {len(asphalt_polygons)} asphalt polys, {len(curb_rings)} curb rings; "
        f"exported {len(lamps_out)} streetlamps to {config.STREETLAMP_JSON_PATH}"
    )
    return config.ROADS_MERGED_PATH, config.STREETLAMP_JSON_PATH


if __name__ == "__main__":
    build_merged_roads_and_lamps()
