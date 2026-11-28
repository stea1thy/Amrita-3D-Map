"""Corporate and Industry Relations (CIR): a three-storey pink block with a glazed barrel-vault atrium.

Plan traced from Google satellite (roof features moved back to the ground for the camera tilt): a deep
square block with bays projecting east, a curved ribbed vault over the central garden atrium, a small
open light well north of it, a single-storey front block with a red tiled roof on the west side and a
red-paved south entrance. Walls follow the Google Maps photos: pink plaster with darker pink floor
lines and brown wooden windows; the west front block has pale pillars and the blue
"CORPORATE AND INDUSTRY RELATIONS" sign. Local frame: `campus_frame.cir_to_xy` (u east, v north).
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from campus_frame import cir_to_xy

from .facade_kit import Kit, Rect, bay_centres, color

FLOORS = 3
FLOOR_STEP_M = 3.6
PARAPET_M = 0.9
FOUNDATION_M = 1.2
WINDOW_PITCH_M = 4.2

# Main block outline, counter-clockwise (east bays project out past u = 36.1)
MAIN: tuple[tuple[float, float], ...] = (
    (-23.3, -17.0), (36.1, -17.0), (36.1, -8.2), (44.4, -8.2), (44.4, 12.3), (36.1, 12.3), (36.1, 29.8),
    (-23.3, 29.8),
)
FRONT_BLOCK: Rect = (-33.3, -23.3, -1.4, 15.3)
FRONT_EAVE_M, FRONT_RISE_M = 4.2, 2.2
FOOTPRINT: tuple[tuple[float, float], ...] = (
    *MAIN[:7], (-23.3, 29.8), (-23.3, 15.3), (-33.3, 15.3), (-33.3, -1.4), (-23.3, -1.4),
)
LIGHT_WELL: Rect = (0.6, 9.2, 14.9, 23.4)
VAULT: Rect = (-6.3, 16.1, -3.2, 13.4)  # ridge runs east-west
VAULT_RISE_M = 4.4
VAULT_SEGMENTS = 6
VAULT_RIBS = 5
SOUTH_PORCH: Rect = (3.5, 11.5, -21.0, -17.0)
FORECOURT: Rect = (1.5, 15.5, -28.0, -17.0)


def normalize_cir_footprint_rings() -> list[list[tuple[float, float]]]:
    return [[cir_to_xy(*p) for p in FOOTPRINT]]


def cir_tree_spots() -> list[tuple[float, float, int, tuple[float, float], int]]:
    """A tree in the light well and palms either side of the west front block (world XY)."""
    spots = ((4.9, 19.2, 1, (0.75, 0.9)), (-37.0, -4.0, 0, (0.9, 1.05)), (-37.0, 18.5, 0, (0.9, 1.05)))
    return [(*cir_to_xy(u, v), kind, scale, 5 if kind == 0 else 4) for u, v, kind, scale in spots]


def build_cir(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build walls, roof, vault, light well, front block and south entrance. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=cir_to_xy)
    zs = [terrain.sample(*cir_to_xy(*p)) for p in (*FOOTPRINT, (6.0, 6.0), (8.5, -25.0))]
    z_bottom, z_floor = min(zs) - FOUNDATION_M, max(zs) + 0.25
    z_roof = z_floor + FLOORS * FLOOR_STEP_M

    ring = list(MAIN)
    for a, b in zip(ring, ring[1:] + ring[:1]):
        _wall(kit, a, b, z_bottom, z_floor, z_roof, front_block=a[0] == b[0] == -23.3)
    well = _rect_ring(LIGHT_WELL)[::-1]
    for a, b in zip(well, well[1:] + well[:1]):
        _wall(kit, a, b, z_floor, z_floor, z_roof, front_block=False, parapet_back=False)
    kit.polygon(ring, [well], z_roof, color("cir_roof"))
    _vault(kit, z_roof)
    _front_block(kit, z_bottom, z_floor)
    _south_entrance(kit, z_bottom, z_floor, terrain)
    ground = terrain.sample(*cir_to_xy(4.9, 19.2))
    kit.flat(LIGHT_WELL, ground + 0.06, color("lawn_green"))
    return kit.world_pts


def _rect_ring(rect: Rect) -> list[tuple[float, float]]:
    u0, u1, v0, v1 = rect
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def _wall(
    kit: Kit, a, b, z_bottom: float, z_floor: float, z_roof: float, front_block: bool, parapet_back: bool = True,
) -> None:
    """Pink wall, darker pink floor lines, brown-framed windows; the ground floor stays blank behind the
    west front block."""
    length = math.dist(a, b)
    z_top = z_roof + PARAPET_M
    kit.strip(a, b, 0.0, length, z_bottom, z_top - 0.2, color("cir_pink"))
    kit.strip(a, b, 0.0, length, z_top - 0.2, z_top, color("cir_line"))
    if parapet_back:
        kit.strip(b, a, 0.0, length, z_roof, z_top, color("cir_pink", 0.85))
    for level in range(1, FLOORS + 1):
        z = z_floor + level * FLOOR_STEP_M
        kit.strip(a, b, 0.0, length, z - 0.28, z - 0.04, color("cir_line"), proud=0.05)
    for d in bay_centres(length, WINDOW_PITCH_M, 1.7, 1.0):
        for level in range(1 if front_block else 0, FLOORS):
            za = z_floor + level * FLOOR_STEP_M
            kit.strip(a, b, d - 0.85, d + 0.85, za + 0.85, za + 2.65, color("cir_wood"), proud=0.06)
            kit.strip_window(a, b, d - 0.6, d + 0.6, za + 1.0, za + 2.5, proud=0.1)


def _vault(kit: Kit, z_roof: float) -> None:
    """Curved glazed vault on the roof with pale ribs."""
    u0, u1, v0, v1 = VAULT
    profile = [(v0 + (v1 - v0) * i / VAULT_SEGMENTS, z_roof + VAULT_RISE_M * math.sin(math.pi * i / VAULT_SEGMENTS))
               for i in range(VAULT_SEGMENTS + 1)]
    for (va, za), (vb, zb) in zip(profile, profile[1:]):
        kit.quad([(u1, va, za), (u1, vb, zb), (u0, vb, zb), (u0, va, za)], color("cir_vault"))
    for (va, za), (vb, zb) in zip(profile, profile[1:]):
        kit.tri([(u0, va, za), (u0, vb, zb), (u0, (v0 + v1) / 2.0, z_roof)], color("cir_vault", 0.8))
        kit.tri([(u1, vb, zb), (u1, va, za), (u1, (v0 + v1) / 2.0, z_roof)], color("cir_vault", 0.8))
    for i in range(VAULT_RIBS):
        u = u0 + (u1 - u0) * (i + 0.5) / VAULT_RIBS
        for (va, za), (vb, zb) in zip(profile, profile[1:]):
            kit.quad([(u + 0.25, va, za + 0.06), (u + 0.25, vb, zb + 0.06), (u - 0.25, vb, zb + 0.06),
                      (u - 0.25, va, za + 0.06)], color("cir_vault_rib"))


def _front_block(kit: Kit, z_bottom: float, z_floor: float) -> None:
    """Single-storey front block: pale pillars before a shaded verandah, blue sign, red tiled hip roof."""
    u0, u1, v0, v1 = FRONT_BLOCK
    z_eave = z_floor + FRONT_EAVE_M
    kit.box(FRONT_BLOCK, z_bottom, z_eave, color("cir_pink"), color("cir_roof"))
    length = v1 - v0
    kit.panel(FRONT_BLOCK, "w", 1.0, length - 1.0, z_floor, z_eave - 0.7, color("verandah_shadow"), proud=0.03)
    for d in bay_centres(length, 3.3, 0.5, 0.4):
        kit.panel(FRONT_BLOCK, "w", d - 0.25, d + 0.25, z_floor, z_eave - 0.7, color("stucco_white"), proud=0.12)
    kit.panel(FRONT_BLOCK, "w", length / 2.0 - 4.0, length / 2.0 + 4.0, z_eave - 0.65, z_eave - 0.1,
              color("cir_sign"), proud=0.08)
    kit.hip_roof(FRONT_BLOCK, z_eave, FRONT_RISE_M, color("asb_porch_tile"), overhang=0.7)


def _south_entrance(kit: Kit, z_bottom: float, z_floor: float, terrain: Any) -> None:
    """Brown wooden doors under a small red tiled porch, opening onto a red-paved forecourt."""
    door = ((SOUTH_PORCH[0] + 1.5, -17.0), (SOUTH_PORCH[1] - 1.5, -17.0))
    kit.strip(door[0], door[1], 0.0, math.dist(*door), z_floor, z_floor + 2.8, color("cir_wood"), proud=0.12)
    u0, u1, v0, _ = SOUTH_PORCH
    for u in (u0 + 0.4, u1 - 0.8):
        kit.box((u, u + 0.4, v0 + 0.3, v0 + 0.7), z_bottom, z_floor + 3.3, color("stucco_white"))
    kit.hip_roof(SOUTH_PORCH, z_floor + 3.3, 1.4, color("asb_porch_tile"), overhang=0.4)
    ground = terrain.sample(*cir_to_xy((FORECOURT[0] + FORECOURT[1]) / 2.0, -22.0))
    kit.flat(FORECOURT, max(ground, z_floor - 0.35) + 0.05, color("cir_paving"))
