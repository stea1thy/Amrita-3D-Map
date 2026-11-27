"""Central Library: tiled hip-roof pavilions around a glass-pyramid atrium, with its south entrance.

The plan is traced in the `campus_frame` (u, v) frame (see `pipeline/refs/ab2_library_sources.md`).
"""

from __future__ import annotations

from typing import Any

import bmesh

from campus_frame import ring_to_xy, uv_to_xy

from .facade_kit import SIDES, Kit, Rect, color, edge_of, side_length

FLOORS = 3
FLOOR_STEP_M = 3.6
PLINTH_RISE_M = 1.2
FOUNDATION_M = 1.5

# (rect, visible wall sides, roof rise, eave drop below the main eave)
PAVILIONS: tuple[tuple[Rect, str, float, float], ...] = (
    ((16.8, 36.4, 32.0, 53.7), "senw", 5.2, 0.0),  # north-west
    ((40.9, 56.4, 38.0, 55.0), "enw", 4.4, 0.25),  # north centre
    ((61.0, 84.4, 31.7, 54.8), "senw", 5.4, 0.05),  # north-east
    ((16.8, 37.8, -14.4, 8.0), "senw", 5.3, 0.1),  # south-west
    ((61.7, 85.5, -13.3, 9.0), "senw", 5.4, 0.0),  # south-east
    ((37.8, 61.7, -7.8, 0.5), "s", 2.8, 1.5),  # south centre
    ((18.0, 28.0, 17.0, 31.5), "sw", 2.6, 1.8),  # west bay
    ((70.0, 82.8, 23.0, 32.0), "se", 2.6, 1.8),  # east bay
)

BODY: Rect = (27.8, 70.0, -1.0, 40.0)
BODY_SIDES = "enw"
SKYLIGHT: Rect = (40.5, 55.5, 14.4, 29.4)
BODY_RISE_M = 4.4
SKYLIGHT_RISE_M = 3.4

ENTRANCE: Rect = (43.0, 57.0, -16.0, -7.8)
STEPS_END_V = -23.0
PATH_END_V = -62.5
SIGN_UV: tuple[float, float] = (44.0, -59.0)

_OUTLINE_UV: list[tuple[float, float]] = [
    (16.8, -14.4), (37.8, -14.4), (37.8, -7.8), (43.0, -7.8), (43.0, -16.0), (57.0, -16.0),
    (57.0, -7.8), (61.7, -7.8), (61.7, -13.3), (85.5, -13.3), (85.5, 9.0), (70.0, 9.0),
    (70.0, 23.0), (82.8, 23.0), (82.8, 31.7), (84.4, 31.7), (84.4, 54.8), (61.0, 54.8),
    (61.0, 40.0), (56.4, 40.0), (56.4, 55.0), (40.9, 55.0), (40.9, 40.0), (36.4, 40.0),
    (36.4, 53.7), (16.8, 53.7), (16.8, 32.0), (18.0, 31.5), (18.0, 17.0), (27.8, 17.0),
    (27.8, 8.0), (16.8, 8.0),
]


def normalize_library_footprint_rings() -> list[list[tuple[float, float]]]:
    """Traced outline (CCW) in world Blender XY."""
    return [ring_to_xy(_OUTLINE_UV)]


def _levels(terrain: Any) -> tuple[float, float]:
    zs = [terrain.sample(*uv_to_xy(u, v)) for u, v in _OUTLINE_UV]
    return min(zs) - FOUNDATION_M, max(zs) + PLINTH_RISE_M


def build_central_library(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build the library walls, tiled roofs, atrium skylight and entrance. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz)
    z_bottom, z_floor = _levels(terrain)
    z_eave = z_floor + FLOORS * FLOOR_STEP_M
    tile = color("library_tile")

    for rect, sides, rise, drop in PAVILIONS:
        _walls(kit, rect, sides, z_bottom, z_floor, z_eave - drop)
        kit.hip_roof(rect, z_eave - drop, rise, tile, overhang=0.9)

    _walls(kit, BODY, BODY_SIDES, z_bottom, z_floor, z_eave)
    z_ring = z_eave + BODY_RISE_M
    outer = (BODY[0] - 0.9, BODY[1] + 0.9, BODY[2] - 0.9, BODY[3] + 0.9)
    kit.frustum_roof(outer, SKYLIGHT, z_eave + 0.05, z_ring, tile)
    kit.pyramid(SKYLIGHT, z_ring, z_ring + SKYLIGHT_RISE_M, color("skylight_glass"))
    _skylight_ribs(kit, z_ring)

    _entrance(kit, terrain, z_floor)
    return kit.world_pts


def _walls(kit: Kit, rect: Rect, sides: str, z_bottom: float, z_floor: float, z_eave: float) -> None:
    white, band = color("stucco_white"), color("terracotta_portal")
    for side in SIDES:
        if side not in sides:
            continue
        length = side_length(rect, side)
        kit.panel(rect, side, 0.0, length, z_bottom, z_floor, color("sandstone_plinth"))
        kit.panel(rect, side, 0.0, length, z_floor, z_eave - 0.45, white)
        kit.panel(rect, side, 0.0, length, z_eave - 0.45, z_eave, band)
        for level in range(FLOORS):
            za = z_floor + level * FLOOR_STEP_M
            if za + 1.0 >= z_eave - 0.9:
                continue
            kit.panel(rect, side, 0.0, length, za + 0.55, za + 0.75, color("stucco_cream"), proud=0.1)
            kit.window_row(rect, side, za + 0.85, min(za + 2.9, z_eave - 0.6), 3.4, 1.7, margin=1.1)


def _skylight_ribs(kit: Kit, z_ring: float) -> None:
    """Pale glazing bars along the four pyramid hips."""
    u0, u1, v0, v1 = SKYLIGHT
    apex = ((u0 + u1) / 2.0, (v0 + v1) / 2.0, z_ring + SKYLIGHT_RISE_M + 0.08)
    frame = color("skylight_vault")
    for cu, cv in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
        du = 0.35 if cu == u0 else -0.35
        kit.tri([(cu, cv, z_ring + 0.08), (cu + du, cv, z_ring + 0.1), apex], frame)
        kit.tri([(cu + du, cv, z_ring + 0.1), (cu, cv, z_ring + 0.08), apex], frame)


def _entrance(kit: Kit, terrain: Any, z_floor: float) -> None:
    """Raised portico with square white columns, name board, and the flight of steps to the garden path."""
    u0, u1, v0, v1 = ENTRANCE
    z_ground = terrain.sample(*uv_to_xy((u0 + u1) / 2.0, STEPS_END_V))
    white, stone = color("stucco_white"), color("sandstone_plinth")
    kit.box(ENTRANCE, z_ground - 0.8, z_floor, stone, color("path_stone"))
    z_beam = z_floor + 3.9
    for u in (u0 + 0.8, u0 + 4.2, u1 - 4.2, u1 - 0.8):
        kit.box((u - 0.34, u + 0.34, v0 + 0.5, v0 + 1.18), z_floor, z_beam, white)
    kit.box(ENTRANCE, z_beam, z_beam + 0.95, white)
    kit.panel(ENTRANCE, "s", 4.3, side_length(ENTRANCE, "s") - 4.3, z_beam + 0.22, z_beam + 0.72,
              color("portico_dark"), proud=0.08)
    kit.hip_roof(ENTRANCE, z_beam + 0.95, 2.3, color("porch_tile"), overhang=0.8)
    door = (u0 + 4.4, u1 - 4.4, -7.8, 0.5)
    kit.panel(door, "s", 0.0, side_length(door, "s"), z_floor, z_floor + 3.4, color("recess_shadow"), proud=0.12)

    count = 6
    run = (v0 - STEPS_END_V) / count
    for i in range(count):
        v_hi = v0 - i * run
        z_top = z_floor - (z_floor - z_ground - 0.18) * (i + 1) / count
        kit.box((46.2, 53.8, v_hi - run, v_hi), z_ground - 0.8, z_top, stone, color("path_stone"))


def library_ground_rings() -> list[tuple[list[tuple[float, float]], float, int]]:
    """(ring, z offset, ground material index) for the landing and the stone path to the front road."""
    landing = ring_to_xy([(45.0, -29.0), (55.0, -29.0), (57.0, -27.0), (57.0, STEPS_END_V),
                          (43.0, STEPS_END_V), (43.0, -27.0)])
    path = ring_to_xy([(48.3, PATH_END_V), (51.7, PATH_END_V), (51.7, -29.0), (48.3, -29.0)])
    return [(landing, 0.15, 6), (path, 0.145, 6)]


def append_library_sign(bm: bmesh.types.BMesh, col_layer: Any, terrain: Any) -> None:
    """Red CENTRAL LIBRARY board on two white posts beside the path, facing the front road."""
    kit = Kit(bm, col_layer, None, None)
    u, v = SIGN_UV
    z = terrain.sample(*uv_to_xy(u, v))
    for du in (-1.5, 1.5):
        kit.box((u + du - 0.09, u + du + 0.09, v - 0.09, v + 0.09), z - 0.3, z + 1.2, color("stucco_white"))
    kit.box((u - 1.9, u + 1.9, v - 0.12, v + 0.12), z + 1.2, z + 2.5, color("sign_red"))
    board: Rect = (u - 1.9, u + 1.9, v - 0.12, v + 0.12)
    (au, av), (bu, bv) = edge_of(board, "s")
    for z0, z1 in ((z + 1.55, z + 1.72), (z + 1.95, z + 2.22)):
        kit.quad([(au + 0.5, av - 0.03, z0), (bu - 0.5, bv - 0.03, z0),
                  (bu - 0.5, bv - 0.03, z1), (au + 0.5, av - 0.03, z1)], color("stucco_white"))


def library_front_tree_spots() -> list[tuple[float, float, int, tuple[float, float]]]:
    """Hand-placed trees flanking the entrance path (0 = palm, 1 = canopy)."""
    spots: list[tuple[float, float, int, tuple[float, float]]] = []
    for v, kind, scale in ((-20.0, 1, (0.9, 1.05)),(-34.0, 0, (0.85, 1.0)), (-44.0, 1, (0.85, 1.0)),
                           (-53.0, 0, (0.8, 0.95))):
        for u in (42.4, 57.6):
            spots.append((*uv_to_xy(u, v), kind, scale))
    return spots
