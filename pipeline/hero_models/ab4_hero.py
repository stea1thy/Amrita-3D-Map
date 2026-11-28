"""Academic Block 4 (AB-4), Amrita School of Artificial Intelligence.

A north-south wing, an east wing along Play Ground Road and a round tower with an open core at the
north end. The plan is traced from Google Maps satellite imagery; the south front (white wings, brick
bays, dark glass strip, framed ribbon windows and rooftop pavilion) follows the owner's photos taken
across the sports ground, and the west entrance follows their mark-up. See `refs/ab4_trace.md`.
Local frame: u east, v north of the Google "AB 4" pin, turned by `AB4_ROT_RAD`.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from campus_frame import AB4_ORIGIN_XY, AB4_ROT_RAD

from .facade_kit import SIDES, Kit, Rect, color, edge_of

FLOORS = 5
FLOOR_STEP_M = 3.4
ROOF_SLAB_M = 0.6
FOUNDATION_M = 1.5
BAND_MIN_EDGE_M = 7.5  # shorter return walls stay blank
BAND_MARGIN_M = 0.6

# Ground outline, counter-clockwise
OUTLINE: tuple[tuple[float, float], ...] = (
    (11.5, -31.0), (30.5, -31.0), (30.5, -33.0), (33.0, -33.0), (33.0, -38.5), (43.0, -38.5), (43.0, -33.0),
    (53.0, -33.0), (53.0, -38.5), (75.2, -38.5), (75.2, -33.0), (85.0, -33.0), (85.0, -38.5), (94.0, -38.5),
    (94.0, -33.0), (99.0, -33.0), (99.0, -38.5), (109.5, -38.5), (109.5, -12.5), (103.0, -12.5),
    (103.0, -20.0), (100.0, -20.0), (100.0, -12.5), (90.5, -12.5), (90.5, -20.0), (85.0, -20.0),
    (85.0, -12.5), (75.2, -12.5), (75.2, -17.5), (57.0, -17.5), (57.0, -11.0), (46.8, -11.0), (46.8, -17.5),
    (42.0, -17.5), (42.0, -11.0), (31.0, -11.0), (31.0, -17.0), (11.5, -17.0), (11.5, -9.0), (25.5, -9.0),
    (26.5, 37.5), (25.5, 37.5), (25.5, 57.2), (23.5, 57.2), (23.5, 68.0), (25.5, 68.0), (25.5, 75.5),
    # round tower
    (28.0, 74.2), (36.0, 74.2), (43.1, 77.7), (48.0, 83.9), (49.8, 91.6), (48.0, 99.3), (43.1, 105.5),
    (36.0, 109.0), (28.0, 109.0), (20.9, 105.5), (16.0, 99.3), (14.2, 91.6), (15.7, 85.0),
    # west face, north to south
    (8.0, 85.0), (8.0, 82.0), (-2.5, 82.0), (-3.2, 57.0), (-0.6, 57.0), (-0.6, 37.5), (-4.0, 37.5),
    (-4.0, 26.0), (-1.2, 26.0), (-1.2, 8.0), (-5.5, 8.0), (-5.5, -1.0), (-0.5, -1.0), (-0.5, -8.5),
    (-6.0, -8.5), (-6.0, -37.5), (11.5, -37.5),
)
TOWER_CENTRE = (32.0, 91.6)
ATRIUM_RADIUS_M = 4.8
ATRIUM_SIDES = 8

# South front, seen from the sports ground
BRICK_SPANS_U: tuple[tuple[float, float], ...] = ((32.9, 43.1), (52.9, 85.1))
BRICK_MAX_V = -32.0  # only the front walls and bay returns are brick
GLASS_STRIP: Rect = (45.0, 51.0, -33.0, -33.0)  # full-height dark glazing in the recess between brick bays
CENTRAL_BAY: Rect = (53.0, 75.2, -38.5, -33.5)  # the tall brick block with framed ribbon windows
SIDE_BAY: Rect = (33.0, 43.0, -38.5, -33.0)
PAVILION: Rect = (57.0, 73.0, -37.0, -26.0)
# Unfinished frame in front of the east wing: still under construction, not an entrance in use
CONSTRUCTION_FRAME: Rect = (61.5, 74.0, -47.0, -40.0)
# Entrance in use: the recess on the west face
DOOR_SPAN: tuple[tuple[float, float], tuple[float, float]] = ((-0.5, -1.6), (-0.5, -7.9))
CANOPY: Rect = (-6.4, -0.5, -8.4, -1.1)
# Stair heads and water tanks on the roof
ROOF_BOXES: tuple[Rect, ...] = ((77.0, 84.0, -23.0, -15.0), (11.0, 22.0, 48.0, 55.0), (11.0, 20.0, 12.0, 19.0))


def to_xy(u: float, v: float) -> tuple[float, float]:
    ca, sa = math.cos(AB4_ROT_RAD), math.sin(AB4_ROT_RAD)
    return (AB4_ORIGIN_XY[0] + u * ca - v * sa, AB4_ORIGIN_XY[1] + u * sa + v * ca)


def _atrium_uv() -> list[tuple[float, float]]:
    """Open core of the tower, clockwise so it reads as a hole."""
    cu, cv = TOWER_CENTRE
    return [
        (cu + ATRIUM_RADIUS_M * math.cos(-2.0 * math.pi * i / ATRIUM_SIDES),
         cv + ATRIUM_RADIUS_M * math.sin(-2.0 * math.pi * i / ATRIUM_SIDES))
        for i in range(ATRIUM_SIDES)
    ]


def normalize_ab4_footprint_rings() -> list[list[tuple[float, float]]]:
    return [[to_xy(*p) for p in OUTLINE], [to_xy(*p) for p in _atrium_uv()]]


def build_ab4(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build the walls with ribbon windows, flat roof, tower core and entrances. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=to_xy)
    zs = [terrain.sample(*to_xy(*p)) for p in (*OUTLINE, TOWER_CENTRE, (50.0, -24.0), (9.0, 30.0))]
    z_bottom, z_floor = min(zs) - FOUNDATION_M, max(zs) + 0.2
    z_top = z_floor + FLOORS * FLOOR_STEP_M + ROOF_SLAB_M

    for ring in (list(OUTLINE), _atrium_uv()):
        for a, b in zip(ring, ring[1:] + ring[:1]):
            _wall(kit, a, b, z_bottom, z_floor, z_top)
    _roof(kit, z_top)
    _south_front(kit, z_floor, z_top)
    _construction_frame(kit, z_bottom, z_floor)
    _west_entrance(kit, z_bottom, z_floor)
    for rect in ROOF_BOXES:
        kit.box(rect, z_top, z_top + 2.4, color("ab4_wall"), color("ab4_trim"))
    return kit.world_pts


def _is_brick(a: tuple[float, float], b: tuple[float, float]) -> bool:
    mu, mv = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    return mv <= BRICK_MAX_V and any(lo <= mu <= hi for lo, hi in BRICK_SPANS_U)


def _wall(kit: Kit, a, b, z_bottom: float, z_floor: float, z_top: float) -> None:
    kit.quad([(*a, z_bottom), (*b, z_bottom), (*b, z_top), (*a, z_top)],
             color("ab4_brick" if _is_brick(a, b) else "ab4_wall"))
    if math.dist(a, b) < BAND_MIN_EDGE_M:
        return
    mu, mv = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    if GLASS_STRIP[0] < mu < GLASS_STRIP[1] and mv == GLASS_STRIP[2]:
        return  # covered by the glass strip
    central = CENTRAL_BAY[0] < mu < CENTRAL_BAY[1] and mv == CENTRAL_BAY[2]
    levels = range(2) if central else range(FLOORS)  # the upper floors of the central bay are framed separately
    margin = 3.0 if _is_brick(a, b) else BAND_MARGIN_M
    for level in levels:
        za = z_floor + level * FLOOR_STEP_M
        kit.glass_span(a, b, za + 1.0, za + 2.5, margin)


def _face_south(kit: Kit, u0: float, u1: float, v: float, z0: float, z1: float, key: str) -> None:
    kit.quad([(u0, v, z0), (u1, v, z0), (u1, v, z1), (u0, v, z1)], color(key))


def _south_front(kit: Kit, z_floor: float, z_top: float) -> None:
    """Dark glass strip, the central bay's framed ribbons, raised brick parapets and the roof pavilion."""
    u0, u1, v, _ = GLASS_STRIP
    _face_south(kit, u0, u1, v - 0.08, z_floor + 0.4, z_top - 0.4, "ab4_glass")

    front = CENTRAL_BAY[2]
    left, right = CENTRAL_BAY[0] + 2.0, CENTRAL_BAY[1] - 1.2
    low = z_floor + 2 * FLOOR_STEP_M + 0.4
    _face_south(kit, left, right, front - 0.06, low, low + 2 * FLOOR_STEP_M - 0.3, "ab4_wall")
    for level in (2, 3):
        za = z_floor + level * FLOOR_STEP_M
        kit.glass_span((left, front), (right, front), za + 1.1, za + 2.8, 0.7, proud=0.14)

    for rect, lift in ((CENTRAL_BAY, 1.1), (SIDE_BAY, 0.6)):
        kit.box(rect, z_top, z_top + lift, color("ab4_brick"), color("ab4_trim"))

    kit.box(PAVILION, z_top, z_top + 3.2, color("ab4_wall"))
    _face_south(kit, PAVILION[0] + 1.2, PAVILION[1] - 1.2, PAVILION[2] - 0.06, z_top + 1.5, z_top + 2.7, "ab4_glass")
    slab = (PAVILION[0] - 1.2, PAVILION[1] + 1.2, PAVILION[2] - 1.6, PAVILION[3] + 0.8)
    kit.box(slab, z_top + 3.2, z_top + 3.65, color("ab4_wall"), color("ab4_trim"))


def _roof(kit: Kit, z: float) -> None:
    """Flat roof over the outline with the tower core left open."""
    outer, hole = list(OUTLINE), _atrium_uv()
    points = outer + hole
    loops = [[Vector((u, v, 0.0)) for u, v in outer], [Vector((u, v, 0.0)) for u, v in hole]]
    for i, j, k in tessellate_polygon(loops):
        a, b, c = points[i], points[j], points[k]
        if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) < 0.0:
            b, c = c, b  # keep every triangle facing up
        kit.tri([(*a, z), (*b, z), (*c, z)], color("ab4_roof"))


def _construction_frame(kit: Kit, z_bottom: float, z_floor: float) -> None:
    """Bare concrete columns and slabs of the block that is still being built."""
    u0, u1, v0, v1 = CONSTRUCTION_FRAME
    concrete = color("ab4_concrete")
    for u in (u0, (u0 + u1) / 2.0 - 0.3, u1 - 0.6):
        for v in (v0, v1 - 0.6):
            for side in SIDES:
                a, b = edge_of((u, u + 0.6, v, v + 0.6), side)
                kit.quad([(*a, z_bottom), (*b, z_bottom), (*b, z_floor + 3.3), (*a, z_floor + 3.3)], concrete)
    kit.box(CONSTRUCTION_FRAME, z_floor + 3.3, z_floor + 3.65, concrete)


def _west_entrance(kit: Kit, z_bottom: float, z_floor: float) -> None:
    """Glazed doors in the west recess under a flat canopy on two columns."""
    a, b = DOOR_SPAN
    length = math.dist(a, b)
    kit.quad([(a[0] - 0.08, a[1], z_floor), (b[0] - 0.08, b[1], z_floor),
              (b[0] - 0.08, b[1], z_floor + 3.0), (a[0] - 0.08, a[1], z_floor + 3.0)], color("ab4_glass"))
    kit.glass_span(a, b, z_floor + 0.25, z_floor + 2.7, length * 0.18, proud=0.14)
    kit.box(CANOPY, z_floor + 3.3, z_floor + 3.8, color("ab4_brick"), color("ab4_trim"))
    u0, _, v0, v1 = CANOPY
    for v in (v0 + 0.2, v1 - 0.6):
        kit.box((u0 + 0.2, u0 + 0.6, v, v + 0.4), z_bottom, z_floor + 3.3, color("ab4_wall"))
