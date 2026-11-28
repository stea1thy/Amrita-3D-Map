"""Amrita School of Business (ASB): a four-storey block round an open, tree-filled courtyard.

Plan traced from Google satellite (roof outlines moved back to the ground for the camera tilt): a deep
south block on ASB Road, narrower west, east and north wings, solar panels on the south and east roofs.
Walls follow the Google Maps photos: peach plaster, terracotta-orange pilasters, cream floor bands and
narrow windows outside; three tiers of open verandahs with orange columns and cream railings round
the courtyard lawn. The porch at the south-east corner has a red tiled pyramid roof on tall dark round
columns and spans the drive. Local frame: `campus_frame.south_to_xy` (u east, v north).
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from campus_frame import south_to_xy

from .facade_kit import Kit, Rect, bay_centres, color
from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

FLOORS = 4
FLOOR_STEP_M = 3.5
PARAPET_M = 0.9
FOUNDATION_M = 1.2

OUTER: Rect = (-66.8, -22.8, -24.5, 29.5)
COURT: Rect = (-57.1, -36.5, -9.0, 20.4)
PORCH: Rect = (-31.5, -22.5, -35.0, -24.5)
PORCH_EAVE_M = 5.4
PORCH_RISE_M = 2.4
PILASTER_PITCH_M = 4.4
VERANDAH_PITCH_M = 3.6
ROOF_BOX: Rect = (-31.0, -24.5, 22.0, 28.0)
SOLAR: tuple[Rect, ...] = ((-35.6, -23.8, -8.2, 19.6), (-65.6, -24.0, -23.6, -10.0))
COURT_BED_RADIUS_M = 2.6

# Satellite: the courtyard is full of trees, with one big tree in the round central bed
_COURT_TREES_UV: tuple[tuple[float, float, int, tuple[float, float]], ...] = (
    (-46.8, 5.7, 1, (1.15, 1.3)),
    (-53.5, 16.5, 1, (0.8, 0.95)), (-40.0, 16.8, 1, (0.8, 0.95)),
    (-53.8, -5.5, 1, (0.75, 0.9)), (-40.2, -5.2, 1, (0.75, 0.9)),
    (-54.2, 5.5, 0, (0.8, 0.95)), (-39.6, 6.0, 0, (0.8, 0.95)),
)


def _ring(rect: Rect, clockwise: bool = False) -> list[tuple[float, float]]:
    u0, u1, v0, v1 = rect
    ring = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return ring[::-1] if clockwise else ring


def normalize_asb_footprint_rings() -> list[list[tuple[float, float]]]:
    return [[south_to_xy(*p) for p in _ring(OUTER)], [south_to_xy(*p) for p in _ring(COURT, clockwise=True)]]


def asb_tree_spots() -> list[tuple[float, float, int, tuple[float, float], int]]:
    """Hand-placed courtyard trees (world XY, type, scale range, light garden shade)."""
    return [(*south_to_xy(u, v), kind, scale, 5 if kind == 0 else 4) for u, v, kind, scale in _COURT_TREES_UV]


def build_asb(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build walls, courtyard verandahs, roofs, the porch and the courtyard garden. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=south_to_xy)
    zs = [terrain.sample(*south_to_xy(*p)) for p in (*_ring(OUTER), *_ring(PORCH), (-46.8, 5.7))]
    z_bottom, z_floor = min(zs) - FOUNDATION_M, max(zs) + 0.25
    z_roof = z_floor + FLOORS * FLOOR_STEP_M

    outer = _ring(OUTER)
    for a, b in zip(outer, outer[1:] + outer[:1]):
        _outer_wall(kit, a, b, z_bottom, z_floor, z_roof)
    court = _ring(COURT, clockwise=True)
    for a, b in zip(court, court[1:] + court[:1]):
        _verandah_wall(kit, a, b, z_floor, z_roof)
    _roofs(kit, z_roof)
    _porch(kit, z_bottom, z_floor)
    _court_garden(kit, terrain)
    return kit.world_pts


def _outer_wall(kit: Kit, a, b, z_bottom: float, z_floor: float, z_roof: float) -> None:
    """Peach wall with cream floor bands, orange pilasters between narrow windows, parapet both sides."""
    length = math.dist(a, b)
    z_top = z_roof + PARAPET_M
    kit.strip(a, b, 0.0, length, z_bottom, z_floor + 0.45, color("sandstone_plinth"))
    kit.strip(a, b, 0.0, length, z_floor + 0.45, z_top - 0.22, color("asb_wall"))
    kit.strip(a, b, 0.0, length, z_top - 0.22, z_top, color("asb_cream"))
    kit.strip(b, a, 0.0, length, z_roof, z_top, color("asb_cream", 0.85))  # parapet seen from the roof
    for level in range(1, FLOORS + 1):
        z = z_floor + level * FLOOR_STEP_M
        kit.strip(a, b, 0.0, length, z - 0.3, z + 0.12, color("asb_cream"), proud=0.06)
    bays = bay_centres(length, PILASTER_PITCH_M, 1.4, 1.2)
    for left, right in zip(bays, bays[1:]):
        mid = (left + right) / 2.0
        kit.strip(a, b, mid - 0.32, mid + 0.32, z_floor + 0.45, z_roof - 0.3, color("asb_pilaster"), proud=0.12)
    for d in bays:
        for level in range(FLOORS):
            za = z_floor + level * FLOOR_STEP_M
            kit.strip_window(a, b, d - 0.65, d + 0.65, za + 0.95, za + 2.85, proud=0.08)


def _verandah_wall(kit: Kit, a, b, z_floor: float, z_roof: float) -> None:
    """Open corridor tiers: cream railing, shaded corridor, cream slab edge, orange columns."""
    length = math.dist(a, b)
    for level in range(FLOORS):
        za = z_floor + level * FLOOR_STEP_M
        zb = za + FLOOR_STEP_M
        rail_top = za + (0.0 if level == 0 else 1.0)
        if level:
            kit.strip(a, b, 0.0, length, za, rail_top, color("asb_cream"))
        kit.strip(a, b, 0.0, length, rail_top, zb - 0.45, color("asb_verandah"))
        kit.strip(a, b, 0.0, length, zb - 0.45, zb, color("asb_cream"))
    kit.strip(a, b, 0.0, length, z_roof, z_roof + PARAPET_M, color("asb_cream"))
    kit.strip(b, a, 0.0, length, z_roof, z_roof + PARAPET_M, color("asb_cream", 0.85))
    for d in bay_centres(length, VERANDAH_PITCH_M, 0.4, 0.3):
        kit.strip(a, b, d - 0.2, d + 0.2, z_floor, z_roof - 0.45, color("asb_pilaster"), proud=0.12)


def _roofs(kit: Kit, z: float) -> None:
    """Concrete roofs per wing (west wing weathered brown, north wing cream), solar rows south and east."""
    u0, u1, v0, v1 = OUTER
    cu0, cu1, cv0, cv1 = COURT
    kit.flat((u0, u1, v0, cv0), z, color("ab4_concrete"))
    kit.flat((u0, u1, cv1, v1), z, color("asb_roof"))
    kit.flat((u0, cu0, cv0, cv1), z, color("asb_roof_old"))
    kit.flat((cu1, u1, cv0, cv1), z, color("ab4_concrete"))
    for rect in SOLAR:
        kit.solar_rows(rect, z, pitch=2.6, depth=1.5)
    kit.box(ROOF_BOX, z, z + 2.6, color("asb_wall"), color("asb_cream"))


def _porch(kit: Kit, z_bottom: float, z_floor: float) -> None:
    """Porte-cochere over the drive: four tall dark round columns, cream fascia with the red ASB sign,
    and a red tiled pyramid roof."""
    u0, u1, v0, v1 = PORCH
    z_eave = z_floor + PORCH_EAVE_M
    for u in (u0 + 0.7, u1 - 0.7):
        for v in (v0 + 0.7, v1 - 2.2):
            x, y = south_to_xy(u, v)
            add_cylinder_vc(kit.bm, kit.col, x, y, z_bottom, z_eave, 0.38, 0.38, 6,
                            color("asb_column"), color("asb_column"), offset_xyz=kit.offset)
            kit.world_pts.append((x, y, z_bottom))
    kit.box(PORCH, z_eave, z_eave + 0.7, color("asb_cream"), color("asb_cream"))
    kit.quad([(u, v, z_eave) for u, v in reversed(_ring(PORCH))], color("asb_cream", 0.8))  # soffit
    kit.panel(PORCH, "s", 2.0, 7.0, z_eave + 0.1, z_eave + 0.6, color("asb_sign"), proud=0.04)
    kit.pyramid((u0 - 0.6, u1 + 0.6, v0 - 0.6, v1), z_eave + 0.7, z_eave + 0.7 + PORCH_RISE_M, color("asb_porch_tile"))


def _court_garden(kit: Kit, terrain: Any) -> None:
    """Lawn with cross paths and a round central bed (trees are placed separately)."""
    cu0, cu1, cv0, cv1 = COURT
    z = terrain.sample(*south_to_xy((cu0 + cu1) / 2.0, (cv0 + cv1) / 2.0)) + 0.06
    kit.flat(COURT, z, color("lawn_green"))
    cu, cv = -46.8, 5.7
    kit.flat((cu - 0.9, cu + 0.9, cv0, cv1), z + 0.02, color("sandstone_plinth"))
    kit.flat((cu0, cu1, cv - 0.9, cv + 0.9), z + 0.02, color("sandstone_plinth"))
    bed = [(cu + COURT_BED_RADIUS_M * math.cos(i * math.pi / 4.0), cv + COURT_BED_RADIUS_M * math.sin(i * math.pi / 4.0))
           for i in range(8)]
    kit.polygon(bed, [], z + 0.05, color("asb_hedge"))


def append_asb_driveway_planter(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
) -> None:
    """Stone-masonry median island planter with a heritage lamp post on the ASB drive."""
    px, py, rot = 132.5, 157.2, 0.088
    pz = terrain.sample(px, py)
    c_stone = srgb_hex_to_linear_rgba(HERO_PALETTE["stone_masonry"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_grass = srgb_hex_to_linear_rgba(HERO_PALETTE["lawn_green"])
    c_bronze = srgb_hex_to_linear_rgba(HERO_PALETTE["bronze_gold"])

    # Rounded end stone drums capped in white coping
    for side in (-1.0, 1.0):
        ex, ey = local_to_world_2d(px, py, side * 3.55, 0.0, rot)
        add_cylinder_vc(bm, col_layer, ex, ey, pz - 0.6, pz + 0.65, 1.34, 1.34, 10, c_stone, c_white)
        add_cylinder_vc(bm, col_layer, ex, ey, pz + 0.65, pz + 0.80, 1.44, 1.44, 10, c_white, c_white)

    add_box_vc(bm, col_layer, px, py, pz - 0.6, pz + 0.65, 3.55, 1.35, c_stone, c_white, rot_rad=rot)
    add_box_vc(bm, col_layer, px, py, pz + 0.65, pz + 0.82, 3.62, 1.46, c_white, c_white, rot_rad=rot)
    add_box_vc(bm, col_layer, px, py, pz + 0.82, pz + 0.98, 3.35, 1.06, c_grass, c_grass, rot_rad=rot)

    # Heritage lamp pole in the centre of the planter
    add_box_vc(bm, col_layer, px, py, pz + 0.80, pz + 1.45, 0.42, 0.42, c_white, c_stone, rot_rad=rot)
    add_cylinder_vc(bm, col_layer, px, py, pz + 1.42, pz + 4.35, 0.14, 0.08, 8, c_bronze, c_bronze)
    add_cylinder_vc(bm, col_layer, px, py, pz + 4.35, pz + 4.85, 0.24, 0.12, 8, c_white, c_bronze)
