"""Five-floor white courtyard hostel south-east of the Nataraja fountain.

Plan and facade bays traced from Google Maps satellite imagery (the project's older Esri tiles show
the site still under construction). Local frame: u = metres east, v = metres north of the centre.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from campus_frame import HOSTEL_RING_XY

from .facade_kit import SIDES, Kit, Rect, color, edge_of, side_length

FLOORS = 5
FLOOR_STEP_M = 3.1
PARAPET_M = 0.9
FOUNDATION_M = 1.5
ROTATION_RAD = 0.075
U0, U1, V0, V1 = -33.5, 34.0, -33.5, 33.5

# (rect, wall sides that are visible)
WINGS: tuple[tuple[Rect, str], ...] = (
    ((U0, U1, 26.0, V1), "snew"),  # north
    ((U0, U1, V0, -23.5), "snew"),  # south
    ((U0, -24.0, -23.5, 26.0), "ew"),  # west
    ((21.0, U1, -23.5, 26.0), "ew"),  # east
    ((-14.0, -4.5, -23.5, 26.0), "ew"),  # central spine
    ((-24.0, -14.0, -3.0, 2.5), "sn"),  # west cross wing
    ((-4.5, 3.0, -1.0, 2.5), "sn"),  # link to the east block
    ((3.0, 13.5, -16.0, 18.0), "snew"),  # east inner block
)
# (side of the outer wall, bay centres along it, width, projection)
BAYS: tuple[tuple[str, tuple[float, ...], float, float], ...] = (
    ("s", (-28.0, -18.5, -9.0, 0.5, 10.0, 19.5, 28.5), 4.6, 1.7),
    ("e", (-22.0, -11.0, 0.0, 11.0, 22.0), 5.0, 1.3),
    ("w", (-26.0, -15.5, -5.0, 5.5, 16.0, 26.0), 5.6, 1.5),
    ("n", (-26.0, -13.0, 0.0, 13.0, 26.0), 4.4, 1.1),
)
# Small rooftop stair heads and tanks
ROOF_BOXES: tuple[Rect, ...] = (
    (-31.5, -26.0, -31.0, -26.0), (13.0, 18.0, 20.0, 24.5), (5.5, 11.0, -14.0, -9.0), (-12.5, -7.0, 27.0, 31.5),
)


def to_xy(u: float, v: float) -> tuple[float, float]:
    cx = sum(p[0] for p in HOSTEL_RING_XY) / 4.0
    cy = sum(p[1] for p in HOSTEL_RING_XY) / 4.0
    ca, sa = math.cos(ROTATION_RAD), math.sin(ROTATION_RAD)
    return (cx + u * ca - v * sa, cy + u * sa + v * ca)


def normalize_hostel_footprint_rings() -> list[list[tuple[float, float]]]:
    """Square outline (CCW) with the courtyards as clockwise holes."""
    outer = [(U0, V0), (U1, V0), (U1, V1), (U0, V1)]
    holes = [
        [(-24.0, 2.5), (-24.0, 26.0), (-14.0, 26.0), (-14.0, 2.5)],
        [(-24.0, -23.5), (-24.0, -3.0), (-14.0, -3.0), (-14.0, -23.5)],
        [(-4.5, -23.5), (-4.5, -1.0), (3.0, -1.0), (3.0, -16.0), (13.5, -16.0), (13.5, 18.0), (3.0, 18.0),
         (3.0, 2.5), (-4.5, 2.5), (-4.5, 26.0), (21.0, 26.0), (21.0, -23.5)],
    ]
    return [[to_xy(*p) for p in outer]] + [[to_xy(*p) for p in hole] for hole in holes]


def build_new_hostel(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build the wings, courtyard walls, projecting bays and flat roofs. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=to_xy)
    zs = [terrain.sample(*to_xy(U0 + (U1 - U0) * i / 6.0, V0 + (V1 - V0) * j / 6.0))
          for i in range(7) for j in range(7)]
    z_bottom, z_floor = min(zs) - FOUNDATION_M, max(zs) + 0.2
    z_roof = z_floor + FLOORS * FLOOR_STEP_M
    z_top = z_roof + PARAPET_M

    for rect, sides in WINGS:
        for side in SIDES:
            if side in sides:
                _wall(kit, rect, side, z_bottom, z_floor, z_top, pitch=3.7)
        kit.flat(rect, z_roof + 0.15, color("hostel_roof"))
        for side in SIDES:  # parapet rim along every open edge
            if side in sides:
                (au, av), (bu, bv) = edge_of(rect, side)
                kit.quad([(bu, bv, z_roof), (au, av, z_roof), (au, av, z_top), (bu, bv, z_top)], color("hostel_trim"))
    _bays(kit, z_bottom, z_floor, z_top)
    for rect in ROOF_BOXES:
        kit.box(rect, z_roof, z_roof + 2.2, color("hostel_white"), color("hostel_trim"))
    return kit.world_pts


def _wall(kit: Kit, rect: Rect, side: str, z_bottom: float, z_floor: float, z_top: float, pitch: float) -> None:
    length = side_length(rect, side)
    kit.panel(rect, side, 0.0, length, z_bottom, z_floor, color("sandstone_plinth"))
    kit.panel(rect, side, 0.0, length, z_floor, z_top - 0.3, color("hostel_white"))
    kit.panel(rect, side, 0.0, length, z_top - 0.3, z_top, color("hostel_trim"))
    for level in range(FLOORS):
        za = z_floor + level * FLOOR_STEP_M
        kit.window_row(rect, side, za + 0.95, za + 2.35, pitch, 1.5, margin=0.9)


def _bays(kit: Kit, z_bottom: float, z_floor: float, z_top: float) -> None:
    """Rooms that step out from the outer walls, each with one window per floor."""
    for side, centres, width, depth in BAYS:
        for c in centres:
            half = width / 2.0
            if side == "s":
                rect, faces = (c - half, c + half, V0 - depth, V0), "sew"
            elif side == "n":
                rect, faces = (c - half, c + half, V1, V1 + depth), "new"
            elif side == "e":
                rect, faces = (U1, U1 + depth, c - half, c + half), "esn"
            else:
                rect, faces = (U0 - depth, U0, c - half, c + half), "wsn"
            for face in faces:
                length = side_length(rect, face)
                kit.panel(rect, face, 0.0, length, z_bottom, z_floor, color("sandstone_plinth"))
                kit.panel(rect, face, 0.0, length, z_floor, z_top, color("hostel_white"))
            for level in range(FLOORS):
                za = z_floor + level * FLOOR_STEP_M
                kit.window_row(rect, side, za + 0.9, za + 2.4, 2.4, 1.4, margin=0.35)
            kit.flat(rect, z_top, color("hostel_roof"))
