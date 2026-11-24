"""Pure-Python + NumPy terrain grading and campus/railway spatial helpers (Blender-safe)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

try:
    from . import config
except ImportError:
    import config

POOL_COMPLEX_ID = "way/1210976885"
PLAYGROUND_ID = "way/528938316"


def latlon_to_blender_xy(lat: float, lon: float) -> tuple[float, float]:
    """Convert (lat, lon) to Blender XY meters (+X East, +Y North)."""
    x_east, z_south = config.latlon_to_local_xz(lat, lon)
    return (x_east, -z_south)


def upsample_1d_catmull_rom(vals: np.ndarray) -> np.ndarray:
    """Upsample 1D grid axis (N -> 2N - 1) using clamped Catmull-Rom interpolation."""
    n = vals.shape[0]
    out = np.empty((2 * n - 1,) + vals.shape[1:], dtype=float)
    out[0::2] = vals
    for i in range(n - 1):
        p0 = vals[max(0, i - 1)]
        p1 = vals[i]
        p2 = vals[i + 1]
        p3 = vals[min(n - 1, i + 2)]
        mid = (-p0 + 9.0 * p1 + 9.0 * p2 - p3) / 16.0
        lo = np.minimum(p1, p2)
        hi = np.maximum(p1, p2)
        out[2 * i + 1] = np.clip(mid, lo, hi)
    return out


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """Cubic Hermite interpolation clamped to [0, 1]."""
    if abs(edge1 - edge0) < 1e-9:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def signed_area_2d(ring: list[tuple[float, float]]) -> float:
    """Compute signed shoelace area of a 2D polygon ring (> 0 is CCW)."""
    n = len(ring)
    if n < 3:
        return 0.0
    area2 = 0.0
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    return 0.5 * area2


def point_in_ring_2d(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-ring test."""
    n = len(ring)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _dist_point_to_segment_sq(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq <= 1e-12:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    return (px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2


def dist_point_to_ring_2d(x: float, y: float, ring: list[tuple[float, float]]) -> float:
    """Minimum Euclidean distance from (x, y) to any segment of closed ring."""
    n = len(ring)
    if n < 2:
        return float("inf")
    best = float("inf")
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        d2 = _dist_point_to_segment_sq(x, y, ax, ay, bx, by)
        if d2 < best:
            best = d2
    return math.sqrt(best)


def _sample_core_bilinear(
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    x: float,
    y: float,
) -> float:
    nx, ny = len(xs), len(ys)
    min_x, max_x = float(xs[0]), float(xs[-1])
    min_y, max_y = float(ys[0]), float(ys[-1])
    cx = min(max(x, min_x), max_x)
    cy = min(max(y, min_y), max_y)
    c = min(max(int(np.searchsorted(xs, cx, side="right")) - 1, 0), nx - 2)
    r = min(max(int(np.searchsorted(ys, cy, side="right")) - 1, 0), ny - 2)
    u = (cx - float(xs[c])) / (float(xs[c + 1]) - float(xs[c]))
    v = (cy - float(ys[r])) / (float(ys[r + 1]) - float(ys[r]))
    z00, z10 = float(zs[r, c]), float(zs[r, c + 1])
    z01, z11 = float(zs[r + 1, c]), float(zs[r + 1, c + 1])
    if u >= v:
        return z00 + u * (z10 - z00) + v * (z11 - z10)
    return z00 + v * (z01 - z00) + u * (z11 - z01)


def _strip_closed_ring(coords: list[Any]) -> list[tuple[float, float]]:
    pts = [latlon_to_blender_xy(float(pt[1]), float(pt[0])) for pt in coords]
    if len(pts) >= 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-3:
        pts.pop()
    return pts


def grade_core_terrain_pads(
    core_xs: np.ndarray,
    core_ys: np.ndarray,
    core_zs: np.ndarray,
    raw_osm: dict[str, Any] | None,
) -> np.ndarray:
    """Flatten pool, playground, and sports pads smoothly on the core elevation grid."""
    zs_out = np.array(core_zs, dtype=float, copy=True)
    if not raw_osm:
        return zs_out

    pads: list[tuple[list[tuple[float, float]], float, float, float]] = []
    for feat in raw_osm.get("features", []):
        fid = str(feat.get("id", ""))
        props = feat.get("properties", {})
        if props.get("layer") != "sports":
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue
        coords = geom.get("coordinates", [])
        if not coords:
            continue
        ring = _strip_closed_ring(coords[0])
        if len(ring) < 3:
            continue
        area_m2 = abs(signed_area_2d(ring))
        if fid == POOL_COMPLEX_ID:
            pads.append((ring, 8.0, 24.0, area_m2))
        elif fid == PLAYGROUND_ID:
            pads.append((ring, 10.0, 28.0, area_m2))
        elif area_m2 >= 150.0:
            pads.append((ring, 4.0, 14.0, area_m2))

    # Grade larger pads before smaller courts so apron blending stays clean
    pads.sort(key=lambda item: item[3], reverse=True)
    ny, nx = zs_out.shape

    for ring, apron_m, blend_m, _ in pads:
        xs_r = [p[0] for p in ring]
        ys_r = [p[1] for p in ring]
        pad_r = apron_m + blend_m
        bx0, bx1 = min(xs_r) - pad_r, max(xs_r) + pad_r
        by0, by1 = min(ys_r) - pad_r, max(ys_r) + pad_r

        inside_zs: list[float] = []
        for r in range(ny):
            y = float(core_ys[r])
            if y < min(ys_r) or y > max(ys_r):
                continue
            for c in range(nx):
                x = float(core_xs[c])
                if min(xs_r) <= x <= max(xs_r) and point_in_ring_2d(x, y, ring):
                    inside_zs.append(float(zs_out[r, c]))

        if inside_zs:
            target_z = sum(inside_zs) / len(inside_zs)
        else:
            samples = [_sample_core_bilinear(core_xs, core_ys, zs_out, px, py) for px, py in ring]
            cx = sum(xs_r) / len(xs_r)
            cy = sum(ys_r) / len(ys_r)
            samples.append(_sample_core_bilinear(core_xs, core_ys, zs_out, cx, cy))
            target_z = sum(samples) / len(samples)

        for r in range(ny):
            y = float(core_ys[r])
            if y < by0 or y > by1:
                continue
            for c in range(nx):
                x = float(core_xs[c])
                if x < bx0 or x > bx1:
                    continue
                if point_in_ring_2d(x, y, ring):
                    d = 0.0
                else:
                    d = dist_point_to_ring_2d(x, y, ring)
                if d <= apron_m:
                    w = 1.0
                elif d < pad_r:
                    w = 1.0 - smoothstep(apron_m, pad_r, d)
                else:
                    continue
                zs_out[r, c] = zs_out[r, c] * (1.0 - w) + target_z * w

    return zs_out


def extract_campus_boundary_and_rail(raw_osm: dict[str, Any] | None) -> dict[str, Any]:
    """Extract campus boundary ring, railway lines, crossings, and stations in Blender XY."""
    boundary_ring: list[tuple[float, float]] = []
    best_boundary_area = 0.0
    rail_lines: list[list[tuple[float, float]]] = []
    level_crossings: list[tuple[float, float]] = []
    stations: list[tuple[str, float, float]] = []

    if not raw_osm:
        return {
            "boundary_ring": boundary_ring,
            "rail_lines": rail_lines,
            "level_crossings": level_crossings,
            "stations": stations,
        }

    for feat in raw_osm.get("features", []):
        props = feat.get("properties", {})
        layer = props.get("layer")
        geom = feat.get("geometry", {})
        gtype = geom.get("type")

        if layer == "boundary":
            polys = (
                [geom.get("coordinates", [])]
                if gtype == "Polygon"
                else geom.get("coordinates", [])
                if gtype == "MultiPolygon"
                else []
            )
            for poly_rings in polys:
                if not poly_rings:
                    continue
                ring = _strip_closed_ring(poly_rings[0])
                area = signed_area_2d(ring)
                if len(ring) >= 3 and abs(area) > best_boundary_area:
                    if area < 0:
                        ring.reverse()
                    boundary_ring = ring
                    best_boundary_area = abs(area)

        elif layer == "railway" and gtype == "LineString":
            pts = [latlon_to_blender_xy(float(pt[1]), float(pt[0])) for pt in geom.get("coordinates", [])]
            if len(pts) >= 2:
                rail_lines.append(pts)

        elif layer == "railway_node" and gtype == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                xy = latlon_to_blender_xy(float(coords[1]), float(coords[0]))
                subtype = str(props.get("subtype", ""))
                if subtype == "level_crossing":
                    level_crossings.append(xy)
                elif subtype == "station":
                    stations.append((str(props.get("name") or "Ettimadai"), xy[0], xy[1]))

    return {
        "boundary_ring": boundary_ring,
        "rail_lines": rail_lines,
        "level_crossings": level_crossings,
        "stations": stations,
    }


def rail_north_y_at_x(
    rail_lines: list[list[tuple[float, float]]],
    x: float,
) -> float | None:
    """Return the northernmost railway Y coordinate at given Blender X (linearly interpolated)."""
    if not rail_lines:
        return None

    hits_y: list[float] = []
    fallback_y: list[tuple[float, float]] = []

    for line in rail_lines:
        if len(line) < 2:
            continue
        # Record endpoints sorted by X for extrapolation outside polyline X span
        min_pt = min(line, key=lambda p: p[0])
        max_pt = max(line, key=lambda p: p[0])
        if x <= min_pt[0]:
            fallback_y.append((abs(min_pt[0] - x), min_pt[1]))
        elif x >= max_pt[0]:
            fallback_y.append((abs(x - max_pt[0]), max_pt[1]))

        for (x0, y0), (x1, y1) in zip(line, line[1:]):
            lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
            if lo <= x <= hi:
                dx = x1 - x0
                if abs(dx) < 1e-6:
                    hits_y.append(max(y0, y1))
                else:
                    t = (x - x0) / dx
                    hits_y.append(y0 + t * (y1 - y0))

    if hits_y:
        return max(hits_y)
    if fallback_y:
        # Closest endpoint distance -> largest Y among matching
        best_dist = min(d for d, _ in fallback_y)
        return max(y for d, y in fallback_y if abs(d - best_dist) < 5.0)
    return None


def is_point_in_campus(
    x: float,
    y: float,
    boundary_ring: list[tuple[float, float]],
    rail_lines: list[list[tuple[float, float]]],
    pad_m: float = 8.0,
    rail_margin_m: float = 8.0,
) -> bool:
    """Check whether Blender (x, y) lies inside campus boundary (+pad) and north of railway."""
    if boundary_ring:
        inside_bound = point_in_ring_2d(x, y, boundary_ring) or (
            dist_point_to_ring_2d(x, y, boundary_ring) <= pad_m
        )
        if not inside_bound:
            return False

    if rail_lines:
        ry = rail_north_y_at_x(rail_lines, x)
        if ry is not None and y <= ry + rail_margin_m:
            return False

    return True
