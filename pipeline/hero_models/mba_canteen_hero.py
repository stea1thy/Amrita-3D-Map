"""MBA (ASB) canteen: one tall storey between the Business School and the Pandal, facing south.

Follows the Google Maps photo and the campus-tour video: stone-tile piers with white-framed windows,
orange stripes under a deep white fascia, a dark central doorway up red steps, a ramp on the west side,
a service annex to the north and a curved raised lawn with a rock in front of the door.
Local frame: `campus_frame.south_to_xy`.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from campus_frame import south_to_xy

from .facade_kit import Kit, Rect, color

MAIN: Rect = (-6.0, 13.0, 4.0, 24.0)
ANNEX: Rect = (-3.0, 10.0, 24.0, 31.0)
FOOTPRINT: tuple[tuple[float, float], ...] = (
    (-6.0, 4.0), (13.0, 4.0), (13.0, 24.0), (10.0, 24.0), (10.0, 31.0), (-3.0, 31.0), (-3.0, 24.0), (-6.0, 24.0),
)
# Heights above the floor
PIER_TOP_M, FASCIA_M, COPING_M, ROOF_M, ANNEX_M = 3.4, 3.9, 5.0, 4.75, 3.3
# Facade bays from the left end of each wall: (kind, width)
SOUTH_BAYS = (("pier", 1.6), ("window", 2.2), ("pier", 2.0), ("window", 2.2), ("pier", 1.6), ("door", 3.4),
              ("pier", 1.6), ("window", 3.0), ("pier", 1.4))
SIDE_BAYS = (("pier", 2.0), ("window", 3.2), ("pier", 2.2), ("window", 3.2), ("pier", 2.2), ("window", 3.2),
             ("pier", 4.0))
PLANTER_CENTRE = (8.0, -0.4)
PLANTER_RADII = (5.6, 2.1)
PLANTER_SIDES = 14
PLANTER_WALL_M = 0.7


def normalize_mba_canteen_footprint_rings() -> list[list[tuple[float, float]]]:
    return [[south_to_xy(*p) for p in FOOTPRINT]]


def build_mba_canteen(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build the dining block, its annex, steps, ramp and front planter. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=south_to_xy)
    zs = [terrain.sample(*south_to_xy(*p)) for p in (*FOOTPRINT, PLANTER_CENTRE)]
    z_bottom, z_floor = min(zs) - 1.2, max(zs) + 0.25

    u0, u1, v0, v1 = MAIN
    walls = (((u0, v0), (u1, v0), SOUTH_BAYS), ((u1, v0), (u1, v1), SIDE_BAYS),
             ((u1, v1), (u0, v1), SOUTH_BAYS), ((u0, v1), (u0, v0), SIDE_BAYS))
    for a, b, bays in walls:
        _facade(kit, a, b, bays, z_bottom, z_floor)
    kit.flat(MAIN, z_floor + ROOF_M, color("mba_roof"))
    _annex(kit, z_bottom, z_floor)
    _front_steps(kit, z_bottom, z_floor)
    _west_ramp(kit, z_bottom, z_floor)
    _planter(kit, terrain)
    return kit.world_pts


def _facade(kit: Kit, a, b, bays, z_bottom: float, z_floor: float) -> None:
    length = math.dist(a, b)
    kit.strip(a, b, 0.0, length, z_bottom, z_floor + PIER_TOP_M, color("mba_white"))
    d = 0.0
    for kind, width in bays:
        if kind == "pier":
            _stone_pier(kit, a, b, d, d + width, z_floor)
        elif kind == "window":
            for z0, z1 in ((0.2, 0.42), (0.62, 0.84)):
                kit.strip(a, b, d, d + width, z_floor + z0, z_floor + z1, color("mba_stripe"), proud=0.05)
            kit.strip(a, b, d + 0.1, d + width - 0.1, z_floor + 1.1, z_floor + 2.85, color("mba_white", 0.92), proud=0.07)
            for half in (0, 1):
                w0 = d + 0.22 + half * (width - 0.44) / 2.0
                kit.strip_window(a, b, w0, w0 + (width - 0.44) / 2.0 - 0.08, z_floor + 1.22, z_floor + 2.73, proud=0.1)
        else:
            kit.strip(a, b, d, d + width, z_floor, z_floor + 3.05, color("mba_door"), proud=0.06)
        d += width
    for z0, z1, key in (
        (PIER_TOP_M, PIER_TOP_M + 0.16, "mba_stripe"),
        (PIER_TOP_M + 0.16, PIER_TOP_M + 0.34, "mba_white"),
        (PIER_TOP_M + 0.34, FASCIA_M, "mba_stripe"),
        (FASCIA_M, COPING_M - 0.14, "mba_white"),
        (COPING_M - 0.14, COPING_M, "mba_coping"),
    ):
        kit.strip(a, b, 0.0, length, z_floor + z0, z_floor + z1, color(key))


def _stone_pier(kit: Kit, a, b, d0: float, d1: float, z_floor: float) -> None:
    """Two tones of stone tile in staggered courses."""
    mid = (d0 + d1) / 2.0
    step = PIER_TOP_M / 4.0
    for course in range(4):
        z0, z1 = z_floor + course * step, z_floor + (course + 1) * step
        for half, (lo, hi) in enumerate(((d0, mid), (mid, d1))):
            shade = "mba_stone" if (course + half) % 2 else "mba_stone_dark"
            kit.strip(a, b, lo, hi, z0, z1, color(shade), proud=0.12)


def _annex(kit: Kit, z_bottom: float, z_floor: float) -> None:
    kit.box(ANNEX, z_bottom, z_floor + ANNEX_M, color("mba_white"))
    u0, u1, v0, v1 = ANNEX
    kit.quad([(u0 - 0.5, v0, z_floor + ANNEX_M + 0.7), (u0 - 0.5, v1 + 0.6, z_floor + ANNEX_M + 0.15),
              (u1 + 0.5, v1 + 0.6, z_floor + ANNEX_M + 0.15), (u1 + 0.5, v0, z_floor + ANNEX_M + 0.7)][::-1],
             color("pandal_metal"))
    kit.window_row(ANNEX, "w", z_floor + 1.5, z_floor + 2.4, 2.4, 0.8)
    kit.window_row(ANNEX, "n", z_floor + 1.5, z_floor + 2.4, 3.2, 1.0)


def _front_steps(kit: Kit, z_bottom: float, z_floor: float) -> None:
    door_start = sum(width for _, width in SOUTH_BAYS[:5])
    u0 = MAIN[0] + door_start - 0.3
    for step, depth in enumerate((0.55, 1.05, 1.55)):
        kit.box((u0, u0 + 4.0, MAIN[2] - depth, MAIN[2]), z_bottom, z_floor - step * 0.14, color("pandal_red"))


def _west_ramp(kit: Kit, z_bottom: float, z_floor: float) -> None:
    """White ramp along the west wall with a steel rail."""
    u0, u1 = MAIN[0] - 1.4, MAIN[0] - 0.1
    low_v, high_v, z_low = 8.0, 17.0, z_floor - 0.22
    kit.quad([(u0, low_v, z_low), (u1, low_v, z_low), (u1, high_v, z_floor + 0.45), (u0, high_v, z_floor + 0.45)],
             color("mba_white"))
    kit.quad([(u0, high_v, z_bottom), (u0, low_v, z_bottom), (u0, low_v, z_low), (u0, high_v, z_floor + 0.45)],
             color("mba_white", 0.9))
    kit.quad([(u0, high_v, z_low + 1.62), (u0, low_v, z_low + 0.95), (u0, low_v, z_low + 1.02),
              (u0, high_v, z_low + 1.69)], color("pandal_metal"))
    for i in range(4):
        v = low_v + (high_v - low_v) * i / 3.0
        base = z_low + (z_floor + 0.45 - z_low) * i / 3.0
        kit.quad([(u0, v + 0.04, base), (u0, v - 0.04, base), (u0, v - 0.04, base + 0.98), (u0, v + 0.04, base + 0.98)],
                 color("pandal_metal"))


def _planter(kit: Kit, terrain: Any) -> None:
    """Oval raised lawn: painted wall, white coping edge, grass top and a boulder at the east end."""
    cu, cv = PLANTER_CENTRE
    ru, rv = PLANTER_RADII
    ring = [(cu + ru * math.cos(2.0 * math.pi * i / PLANTER_SIDES), cv + rv * math.sin(2.0 * math.pi * i / PLANTER_SIDES))
            for i in range(PLANTER_SIDES)]
    ground = terrain.sample(*south_to_xy(cu, cv))
    top = ground + PLANTER_WALL_M
    for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
        paint = "mba_graffiti" if i % 4 == 0 else "mba_white"
        kit.quad([(*a, ground - 0.4), (*b, ground - 0.4), (*b, top), (*a, top)], color(paint))
    inner = [(cu + (u - cu) * 0.92, cv + (v - cv) * 0.85) for u, v in ring]
    for (a, b), (c, d) in zip(zip(ring, ring[1:] + ring[:1]), zip(inner, inner[1:] + inner[:1])):
        kit.quad([(*a, top), (*b, top), (*d, top + 0.02), (*c, top + 0.02)], color("pandal_ridge"))
    kit.polygon(inner, [], top + 0.05, color("lawn_green"))
    rock = (cu + 2.2, cu + 4.4, cv - 0.7, cv + 0.7)
    kit.frustum_roof(rock, (rock[0] + 0.5, rock[1] - 0.7, rock[2] + 0.4, rock[3] - 0.25), top, top + 1.1,
                     color("mba_rock"))
    kit.flat((rock[0] + 0.5, rock[1] - 0.7, rock[2] + 0.4, rock[3] - 0.25), top + 1.1, color("mba_rock", 1.12))
