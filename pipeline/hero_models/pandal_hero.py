"""Amrita Pandal: a long open-sided convocation shed (previously mapped as a courtyard "Auditorium").

Roof plan from Google satellite, west to east: a low lean-to in alternating red and white bays, a grey
metal slope and the white gabled main roof, with a small entrance block at the south end. Walls follow
the campus-tour video: pale pillars on red bases around a shaded interior, and a ramp up to a doorway
on the canteen side. Local frame: `campus_frame.south_to_xy`.
"""

from __future__ import annotations

from typing import Any

import bmesh

from campus_frame import south_to_xy

from .facade_kit import Kit, Rect, color

WEST_U, LEAN_U, HALL_U, EAST_U = 23.0, 30.0, 39.0, 57.0
SOUTH_V, NORTH_V = -45.0, 45.0
ENTRANCE: Rect = (36.0, 50.0, -50.0, -45.0)
FOOTPRINT: tuple[tuple[float, float], ...] = (
    (WEST_U, SOUTH_V), (36.0, SOUTH_V), (36.0, -50.0), (50.0, -50.0), (50.0, SOUTH_V), (EAST_U, SOUTH_V),
    (EAST_U, NORTH_V), (WEST_U, NORTH_V),
)
# Heights above the floor
LEAN_EAVE_M, METAL_LOW_M, HALL_EAVE_M, RIDGE_M = 3.4, 4.5, 5.6, 8.2
ROOF_OVERHANG_M = 0.8
BAY_M = 5.0
PILLAR_M = 0.5
DOOR_V: tuple[float, float] = (-22.0, -18.0)
RAMP_FOOT_U = 14.0


def normalize_pandal_footprint_rings() -> list[list[tuple[float, float]]]:
    return [[south_to_xy(*p) for p in FOOTPRINT]]


def build_pandal(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build walls, the three roof strips, the south entrance and the west ramp. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=south_to_xy)
    zs = [terrain.sample(*south_to_xy(*p)) for p in (*FOOTPRINT, (40.0, 0.0))]
    z_bottom, z_floor = min(zs) - 1.5, max(zs) + 0.25

    _long_walls(kit, z_bottom, z_floor)
    _end_walls(kit, z_bottom, z_floor)
    _roofs(kit, z_floor)
    _south_entrance(kit, z_bottom, z_floor)
    ground = terrain.sample(*south_to_xy(RAMP_FOOT_U, sum(DOOR_V) / 2.0))
    _west_ramp(kit, z_floor, ground)
    kit.flat((WEST_U - 2.0, EAST_U + 0.5, NORTH_V, NORTH_V + 3.0), z_floor - 0.1, color("pandal_paving"))
    return kit.world_pts


def _bay_edges(a: float, b: float) -> list[float]:
    count = max(1, round((b - a) / BAY_M))
    return [a + (b - a) * i / count for i in range(count + 1)]


def _wall_run(
    kit: Kit, a: tuple[float, float], b: tuple[float, float], z_bottom: float, z_floor: float, eave: float,
) -> None:
    """Shaded interior above a low red wall, divided by pale pillars on red bases."""
    length = abs(b[0] - a[0]) + abs(b[1] - a[1])
    kit.strip(a, b, 0.0, length, z_bottom, z_floor + 0.9, color("pandal_red"))
    kit.strip(a, b, 0.0, length, z_floor + 0.9, z_floor + eave, color("pandal_shadow"))
    for d in _bay_edges(PILLAR_M / 2.0, length - PILLAR_M / 2.0):
        d0, d1 = d - PILLAR_M / 2.0, d + PILLAR_M / 2.0
        kit.strip(a, b, d0, d1, z_floor, z_floor + 1.3, color("pandal_red", 0.85), proud=0.16)
        kit.strip(a, b, d0, d1, z_floor + 1.3, z_floor + eave, color("pandal_pillar"), proud=0.16)


def _long_walls(kit: Kit, z_bottom: float, z_floor: float) -> None:
    _wall_run(kit, (WEST_U, NORTH_V), (WEST_U, SOUTH_V), z_bottom, z_floor, LEAN_EAVE_M)
    _wall_run(kit, (EAST_U, SOUTH_V), (EAST_U, NORTH_V), z_bottom, z_floor, HALL_EAVE_M)


def _roof_profile() -> list[tuple[float, float]]:
    """(u, height) across the shed, west to east."""
    return [
        (WEST_U, LEAN_EAVE_M), (LEAN_U, METAL_LOW_M), (HALL_U, HALL_EAVE_M),
        ((HALL_U + EAST_U) / 2.0, RIDGE_M), (EAST_U, HALL_EAVE_M),
    ]


def _end_walls(kit: Kit, z_bottom: float, z_floor: float) -> None:
    """North and south walls closed up to the roof profile."""
    for v, flip in ((NORTH_V, True), (SOUTH_V, False)):
        a, b = ((EAST_U, v), (WEST_U, v)) if flip else ((WEST_U, v), (EAST_U, v))
        _wall_run(kit, a, b, z_bottom, z_floor, LEAN_EAVE_M)
        profile = _roof_profile()
        for (u0, h0), (u1, h1) in zip(profile, profile[1:]):
            pts = [(u0, v, z_floor + LEAN_EAVE_M), (u1, v, z_floor + LEAN_EAVE_M),
                   (u1, v, z_floor + h1), (u0, v, z_floor + h0)]
            if flip:
                pts = [pts[1], pts[0], pts[3], pts[2]]
            kit.quad(pts, color("pandal_band"))


def _slope(kit: Kit, u0: float, h0: float, u1: float, h1: float, v0: float, v1: float, z: float, key: str) -> None:
    kit.quad([(u0, v0, z + h0), (u1, v0, z + h1), (u1, v1, z + h1), (u0, v1, z + h0)], color(key))


def _roofs(kit: Kit, z_floor: float) -> None:
    v0, v1 = SOUTH_V - ROOF_OVERHANG_M, NORTH_V + ROOF_OVERHANG_M
    z = z_floor + 0.04
    low_u = WEST_U - ROOF_OVERHANG_M
    edges = _bay_edges(v0, v1)
    for lo, hi in zip(edges, edges[1:]):
        mid = (lo + hi) / 2.0
        _slope(kit, low_u, LEAN_EAVE_M - 0.12, LEAN_U, METAL_LOW_M, lo, mid, z, "pandal_band")
        _slope(kit, low_u, LEAN_EAVE_M - 0.12, LEAN_U, METAL_LOW_M, mid, hi, z, "pandal_red")
    _slope(kit, LEAN_U, METAL_LOW_M, HALL_U, HALL_EAVE_M, v0, v1, z, "pandal_metal")
    ridge_u = (HALL_U + EAST_U) / 2.0
    _slope(kit, HALL_U, HALL_EAVE_M, ridge_u, RIDGE_M, v0, v1, z, "pandal_roof")
    _slope(kit, ridge_u, RIDGE_M, EAST_U + ROOF_OVERHANG_M, HALL_EAVE_M - 0.2, v0, v1, z, "pandal_roof")
    _slope(kit, ridge_u - 0.35, RIDGE_M + 0.08, ridge_u + 0.35, RIDGE_M + 0.08, v0, v1, z, "pandal_ridge")


def _south_entrance(kit: Kit, z_bottom: float, z_floor: float) -> None:
    u0, u1, v0, _ = ENTRANCE
    kit.box(ENTRANCE, z_bottom, z_floor + 3.2, color("pandal_pillar"), color("pandal_metal"))
    kit.panel(ENTRANCE, "s", 4.5, 9.5, z_floor, z_floor + 2.7, color("pandal_shadow"), proud=0.08)
    for d0 in (1.2, 11.0):
        kit.window(ENTRANCE, "s", d0, d0 + 1.8, z_floor + 1.0, z_floor + 2.4)
    for apron in ((WEST_U + 2.0, u0 - 0.5, v0 - 2.0, SOUTH_V - 0.2), (u1 + 0.5, EAST_U, v0 - 1.0, SOUTH_V - 0.2)):
        kit.flat(apron, z_floor - 0.1, color("pandal_paving"))


def _west_ramp(kit: Kit, z_floor: float, z_ground: float) -> None:
    """Ramp with low red side walls up to the doorway on the canteen side."""
    va, vb = DOOR_V
    foot, head, z_low = RAMP_FOOT_U, WEST_U - 0.1, z_ground + 0.12
    kit.quad([(foot, va, z_low), (head, va, z_floor), (head, vb, z_floor), (foot, vb, z_low)], color("pandal_ridge"))
    south = [(foot, va, z_low - 0.4), (head, va, z_low - 0.4), (head, va, z_floor + 0.55), (foot, va, z_low + 0.55)]
    north = [(head, vb, z_low - 0.4), (foot, vb, z_low - 0.4), (foot, vb, z_low + 0.55), (head, vb, z_floor + 0.55)]
    for pts in (south, north):
        kit.quad(pts, color("pandal_red"))
        kit.quad([pts[1], pts[0], pts[3], pts[2]], color("pandal_red"))  # seen from the ramp too
    door_a, door_b = (WEST_U, vb + 0.2), (WEST_U, va - 0.2)
    width = vb - va + 0.4
    kit.strip(door_a, door_b, 0.0, width, z_floor, z_floor + 2.9, color("mba_door"), proud=0.22)
    for d0 in (-0.35, width):
        kit.strip(door_a, door_b, d0, d0 + 0.35, z_floor, z_floor + 3.1, color("pandal_red"), proud=0.24)
