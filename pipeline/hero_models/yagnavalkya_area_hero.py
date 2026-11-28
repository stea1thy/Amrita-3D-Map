"""Satellite-calibrated Yagnavalkya / Nachiketas hostel quadrangles and the covered court hall beside them.

Reference: `pipeline/refs/yagnavalkya_courts_sat.png` (Google satellite, north-up, ~5.9 px/m), registered
against the OSM outlines of Yagnavalkya, Nachiketas, the court hall and the teal basketball court (residuals 1-4 m).

What the imagery shows (and the plain OSM rectangles miss):
- Yagnavalkya Bhavanam (`way/380925366`): a closed quadrangle (~13 m west/east wings, ~11 m north wing,
  ~10 m south wing) around a tree-filled courtyard, light weathered-concrete roof with solar arrays on the
  north-west, plus a stair/service block projecting ~13 m south from the south-east corner.
- Nachiketas Bhavanam (`way/380925368`): two long ~11 m wings joined by a north wing around a narrow ~9 m
  courtyard, weathered brown brick-tile terrace roof, solar array on the north-west corner.
  The south end is cut off in the reference image; it is modelled as closed by a short south wing.
- `way/380925373`: one tall-storey hall with a terracotta roof (rendered as 3 floors before).
- `overture/76fe4013-10f` (small store south of the turf pitch): terracotta roof, not slate.

Footprints are expressed as fractions of each OSM quad (s: west -> east, t: south -> north) and mapped
bilinearly, so the outer walls stay on the OSM outline that the rest of the map is aligned to.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import add_box_vc, add_quad_vc, srgb_hex_to_linear_rgba

HERO_YAGNAVALKYA_ID = "way/380925366"
HERO_NACHIKETAS_ID = "way/380925368"
HERO_COURT_HALL_ID = "way/380925373"

HOSTEL_QUAD_IDS: tuple[str, ...] = (HERO_YAGNAVALKYA_ID, HERO_NACHIKETAS_ID)

# (s, t) polygons in the OSM quad frame. Outer rings CCW, courtyard rectangles as (s0, s1, t0, t1).
_HOSTEL_SPECS: dict[str, dict[str, Any]] = {
    HERO_YAGNAVALKYA_ID: {
        # Main quadrangle + SE stair/service block flush with the east wall, projecting ~13 m south
        "outer_st": [(0.0, 0.0), (0.80, 0.0), (0.80, -0.25), (1.0, -0.25), (1.0, 1.0), (0.0, 1.0)],
        "courtyard": (0.241, 0.771, 0.20, 0.78),
        "roof_hex": "#C6BDB0",
        # Solar arrays (s0, s1, t0, t1): NW end of west wing + west half of north wing
        "panels": [(0.035, 0.205, 0.80, 0.965), (0.26, 0.52, 0.83, 0.965)],
        # Stair-head cabin at the courtyard's SE inner corner (s, t, half_w, half_d)
        "cabins": [(0.735, 0.165, 1.6, 1.9)],
        # Single-storey entrance porch on the south wing (s0, s1, t0, t1, height_m); kept 3.8 m off the OSM loop road
        "porches": [(0.39, 0.565, -0.16, -0.01, 4.2)],
    },
    HERO_NACHIKETAS_ID: {
        "outer_st": [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        "courtyard": (0.355, 0.656, 0.10, 0.77),
        "roof_hex": "#94705F",
        "panels": [(0.035, 0.33, 0.80, 0.965)],
        "cabins": [],
        "porches": [],
    },
}

# Satellite-verified massing for unnamed structures that must stay static (not interactive): fid -> (floors, height_m)
STRUCTURE_CALIBRATION: dict[str, tuple[int, float]] = {
    HERO_COURT_HALL_ID: (1, 8.0),
}

# Satellite-verified roof colours for non-hostel structures in this area
ROOF_HEX_OVERRIDES: dict[str, str] = {
    "overture/76fe4013-10f": "#B5674A",
}

SOLAR_PANEL_HEX = "#2A3542"
# OSM quad corners captured during footprint normalization (the reshaped outer ring is no longer a quad)
_CORNERS_BY_ID: dict[str, tuple[tuple[float, float], ...]] = {}
CABIN_WALL_HEX = "#E3D9C8"


def _quad_corners(outer_ring: list[tuple[float, float]]) -> tuple[tuple[float, float], ...] | None:
    """Return (SW, SE, NE, NW) corners of a near-rectangular footprint."""
    if len(outer_ring) < 4:
        return None
    sw = min(outer_ring, key=lambda p: p[0] + p[1])
    ne = max(outer_ring, key=lambda p: p[0] + p[1])
    se = max(outer_ring, key=lambda p: p[0] - p[1])
    nw = min(outer_ring, key=lambda p: p[0] - p[1])
    if len({sw, se, ne, nw}) < 4:
        return None
    return (sw, se, ne, nw)


def _bilinear(corners: tuple[tuple[float, float], ...], s: float, t: float) -> tuple[float, float]:
    sw, se, ne, nw = corners
    x = (1 - s) * (1 - t) * sw[0] + s * (1 - t) * se[0] + s * t * ne[0] + (1 - s) * t * nw[0]
    y = (1 - s) * (1 - t) * sw[1] + s * (1 - t) * se[1] + s * t * ne[1] + (1 - s) * t * nw[1]
    return (x, y)


def _signed_area(ring: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1]
        for i in range(len(ring))
    )


def _rect_st(corners: tuple[tuple[float, float], ...], s0: float, s1: float, t0: float, t1: float) -> list[tuple[float, float]]:
    """CCW world ring for an (s, t) rectangle."""
    return [_bilinear(corners, s, t) for s, t in ((s0, t0), (s1, t0), (s1, t1), (s0, t1))]


def normalize_hostel_footprint_rings(
    fid: str,
    outer_ring: list[tuple[float, float]],
) -> list[list[tuple[float, float]]]:
    """Return [outer CCW, courtyard CW] rings for a calibrated hostel quadrangle (falls back to the input)."""
    spec = _HOSTEL_SPECS.get(fid)
    corners = _quad_corners(outer_ring)
    if spec is None or corners is None:
        return [outer_ring]
    _CORNERS_BY_ID[fid] = corners
    outer = [_bilinear(corners, s, t) for s, t in spec["outer_st"]]
    if _signed_area(outer) < 0:
        outer.reverse()
    hole_ccw = _rect_st(corners, *spec["courtyard"])
    return [outer, list(reversed(hole_ccw))]


def get_roof_hex(fid: str) -> str | None:
    spec = _HOSTEL_SPECS.get(fid)
    return str(spec["roof_hex"]) if spec else ROOF_HEX_OVERRIDES.get(fid)


def append_hostel_details(
    fid: str,
    bm: bmesh.types.BMesh,
    col_layer: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_top: float,
) -> None:
    """Flat dark solar arrays, stair-head cabins and entrance porches (part of the hostel's own mesh)."""
    spec = _HOSTEL_SPECS.get(fid)
    if spec is None:
        return
    corners = _CORNERS_BY_ID.get(fid)
    if corners is None:
        return
    ox, oy, oz = offset_xyz
    c_panel = srgb_hex_to_linear_rgba(SOLAR_PANEL_HEX)
    c_cabin = srgb_hex_to_linear_rgba(CABIN_WALL_HEX)
    c_roof = srgb_hex_to_linear_rgba(str(spec["roof_hex"]), scale=0.92)

    z_panel = z_top + 0.16 - oz
    for s0, s1, t0, t1 in spec["panels"]:
        pts = _rect_st(corners, s0, s1, t0, t1)
        v = [bm.verts.new((px - ox, py - oy, z_panel)) for px, py in pts]
        add_quad_vc(bm, col_layer, v[0], v[1], v[2], v[3], c_panel)

    sw, se = corners[0], corners[1]
    rot = math.atan2(se[1] - sw[1], se[0] - sw[0])
    for s, t, hw, hd in spec["cabins"]:
        cx, cy = _bilinear(corners, s, t)
        add_box_vc(
            bm, col_layer, cx, cy, z_top, z_top + 2.1, hw, hd,
            c_cabin, c_roof, rot_rad=rot, offset_xyz=offset_xyz,
        )

    width_m = math.hypot(se[0] - sw[0], se[1] - sw[1])
    depth_m = math.hypot(corners[3][0] - sw[0], corners[3][1] - sw[1])
    for s0, s1, t0, t1, h in spec["porches"]:
        cx, cy = _bilinear(corners, 0.5 * (s0 + s1), 0.5 * (t0 + t1))
        add_box_vc(
            bm, col_layer, cx, cy, z_plinth - 1.0, z_plinth + h,
            0.5 * (s1 - s0) * width_m, 0.5 * (t1 - t0) * depth_m,
            c_cabin, srgb_hex_to_linear_rgba("#ECE6DA"), rot_rad=rot, offset_xyz=offset_xyz,
        )


__all__ = [
    "HERO_YAGNAVALKYA_ID",
    "HERO_NACHIKETAS_ID",
    "HERO_COURT_HALL_ID",
    "HOSTEL_QUAD_IDS",
    "STRUCTURE_CALIBRATION",
    "normalize_hostel_footprint_rings",
    "ROOF_HEX_OVERRIDES",
    "get_roof_hex",
    "append_hostel_details",
]
