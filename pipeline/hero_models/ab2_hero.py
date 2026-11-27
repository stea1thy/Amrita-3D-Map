"""Academic Block 2 (AB-2) & covered portal skybridge Blender generators.

The plan is traced as rectangles in the `campus_frame` (u, v) frame from Esri and
Google satellite views (see `pipeline/refs/ab2_library_sources.md`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import bmesh

from campus_frame import ring_to_xy, uv_to_xy

from .facade_kit import SIDES, Kit, Rect, color, edge_of, side_length
from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_glass_panel,
    add_hipped_roof_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

FLOOR_STEP_M = 3.6
SKIRT_RISE_M = 1.2
FOUNDATION_M = 1.5


@dataclass(frozen=True)
class Volume:
    """One rectangular wing. `faces` maps side -> "o" (stucco), "v" (verandah) or "p" (front portal)."""

    rect: Rect
    group: str
    faces: dict[str, str]
    roof: str = "none"  # "skirt" | "hip" | "none"
    skirt: dict[str, float] = field(default_factory=dict)
    solar: tuple[Rect, ...] = ()
    eave_extra: float = 0.0
    rise: float = 2.4


EAST_CORRIDOR: Rect = (2.5, 9.2, 33.0, 73.0)

GROUP_FLOORS: dict[str, int] = {"south": 4, "link": 3, "north": 3}

VOLUMES: tuple[Volume, ...] = (
    # South (front) wing with solar roof and the central entrance step
    Volume((-89.8, -50.5, -50.0, -34.0), "south", {"s": "o", "w": "o", "n": "v"}, "skirt",
           {"s": 3.6, "n": 2.2, "w": 2.8}, ((-85.0, -52.0, -45.6, -37.0),)),
    Volume((-27.0, 6.5, -49.5, -34.0), "south", {"s": "o", "e": "o", "n": "v"}, "skirt",
           {"s": 3.6, "n": 2.2, "e": 2.8}, ((-25.5, 2.5, -45.2, -37.0),)),
    Volume((-50.5, -27.0, -56.0, -34.0), "south", {"s": "p", "e": "o", "w": "o"}, "skirt",
           {"s": 3.6, "w": 2.2, "e": 2.2}, ((-46.5, -31.0, -50.5, -41.5),), eave_extra=0.8),
    Volume((-43.0, -36.0, -56.0, -34.0), "south", {"n": "v"}, eave_extra=0.8),
    # West courtyard block
    Volume((-89.0, -49.5, -1.0, 13.0), "south", {"n": "o", "w": "o", "s": "v"}, "skirt",
           {"s": 3.2, "n": 1.0, "w": 1.6}),
    Volume((-89.0, -49.5, -24.5, -10.0), "south", {"s": "o", "w": "o", "n": "v"}, "skirt",
           {"s": 3.2, "n": 1.4, "w": 1.6}),
    Volume((-89.0, -80.0, -10.0, -1.0), "south", {"w": "o", "e": "v"}, "skirt", {"w": 1.6, "e": 2.0}),
    Volume((-56.0, -49.5, -10.0, -1.0), "south", {"w": "v"}, "skirt", {"w": 1.6}),
    # Central spine around the water-channel courtyard
    Volume((-49.5, -43.0, -32.0, 12.0), "south", {"e": "v"}, "hip", rise=2.2),
    Volume((-36.0, -29.5, -32.0, 12.0), "south", {"w": "v"}, "hip", rise=2.2),
    Volume((-49.5, -43.0, -32.0, -24.5), "south", {"w": "o"}),
    Volume((-36.0, -29.5, -32.0, -24.5), "south", {"e": "o"}),
    Volume((-43.0, -36.0, 2.0, 12.0), "south", {"s": "v", "n": "o"}, "hip", rise=2.0),
    # East courtyard block (solar roofs)
    Volume((-29.5, 3.0, 0.0, 13.0), "south", {"n": "o", "e": "o", "s": "v"}, "skirt",
           {"s": 3.2, "n": 1.0, "e": 1.4}, ((-19.0, 0.0, 4.2, 10.6),)),
    Volume((-29.5, 3.0, -24.5, -10.0), "south", {"s": "o", "n": "v"}, "skirt",
           {"s": 3.2, "n": 1.4}, ((-27.0, -5.0, -20.2, -12.0),)),
    Volume((3.0, 9.3, -24.5, 2.0), "south", {"s": "o", "e": "o", "n": "o", "w": "v"}, "skirt",
           {"s": 1.6, "e": 2.4, "n": 1.4, "w": 1.4}),
    Volume((-29.5, -22.0, -10.0, 0.0), "south", {"e": "v"}, "skirt", {"e": 0.8}),
    # Corridor wing climbing north to the Mass Communication block
    Volume((-39.0, -32.0, 12.0, 31.0), "link", {"w": "o", "e": "v"}, "hip"),
    Volume((-39.0, 2.5, 31.0, 38.8), "link", {"s": "v", "e": "o"}, "hip"),
    Volume((-49.0, 2.5, 38.8, 51.0), "link", {"n": "o", "w": "o", "e": "o"}, "skirt",
           {"n": 1.0, "w": 1.4, "e": 1.4}),
    Volume((-49.0, -39.0, 24.0, 38.8), "link", {"s": "o", "w": "o"}, "skirt", {"s": 0.8, "w": 0.8}),
    # East corridor and the long north wing behind the Central Library
    Volume(EAST_CORRIDOR, "north", {"e": "o", "w": "o", "s": "o"}, "hip", rise=2.0),
    Volume((2.5, 85.5, 73.0, 86.5), "north", {"n": "o", "s": "v", "e": "o", "w": "o"}, "skirt",
           {"s": 4.2, "n": 0.8, "e": 1.6, "w": 1.6}),
    Volume((46.0, 54.0, 86.5, 94.0), "north", {"n": "o", "e": "o", "w": "o"}, "skirt",
           {"n": 0.6, "e": 0.6, "w": 0.6}),
)

# Four square stair towers with gabled white faces and pyramidal tile caps
TOWERS: tuple[Rect, ...] = (
    (-50.5, -43.0, -40.0, -32.0),
    (-36.0, -28.5, -40.0, -32.0),
    (-50.0, -43.0, 6.0, 13.5),
    (-36.0, -29.0, 6.0, 13.5),
)

SOUTH_PORCH: Rect = (-46.0, -29.5, -62.2, -56.0)
STATUE_UV: tuple[float, float] = (-37.3, -83.5)

_OUTLINE_UV: list[tuple[float, float]] = [
    (-89.8, -50.0), (-50.5, -50.0), (-50.5, -56.0), (-46.0, -56.0), (-46.0, -62.2), (-29.5, -62.2),
    (-29.5, -56.0), (-27.0, -56.0), (-27.0, -49.5), (6.5, -49.5), (6.5, -34.0), (-28.5, -34.0),
    (-28.5, -32.0), (-29.5, -32.0), (-29.5, -24.5), (9.3, -24.5), (9.3, 2.0), (3.0, 2.0),
    (3.0, 13.0), (-29.0, 13.0), (-29.0, 13.5), (-32.0, 13.5), (-32.0, 31.0), (2.5, 31.0),
    (2.5, 33.0), (9.2, 33.0), (9.2, 73.0), (85.5, 73.0), (85.5, 86.5), (54.0, 86.5),
    (54.0, 94.0), (46.0, 94.0), (46.0, 86.5), (2.5, 86.5), (2.5, 51.0), (-49.0, 51.0),
    (-49.0, 24.0), (-39.0, 24.0), (-39.0, 13.5), (-50.0, 13.5), (-50.0, 13.0), (-89.0, 13.0),
    (-89.0, -24.5), (-49.5, -24.5), (-49.5, -32.0), (-50.5, -32.0), (-50.5, -34.0), (-89.8, -34.0),
]

# Courtyard voids, spine first: (u0, u1, v0, v1)
COURTYARDS: tuple[Rect, ...] = (
    (-43.0, -36.0, -34.0, 2.0),
    (-80.0, -56.0, -10.0, -1.0),
    (-22.0, 3.0, -10.0, 0.0),
)


def normalize_ab2_footprint_rings() -> list[list[tuple[float, float]]]:
    """Traced outline (CCW) plus courtyard holes (CW) in world Blender XY."""
    rings = [ring_to_xy(_OUTLINE_UV)]
    for u0, u1, v0, v1 in COURTYARDS:
        rings.append(ring_to_xy([(u0, v0), (u0, v1), (u1, v1), (u1, v0)]))
    return rings


def _group_levels(terrain: Any) -> dict[str, tuple[float, float]]:
    """(foundation bottom, ground floor level) per wing group, sampled from the terrain under it."""
    levels: dict[str, tuple[float, float]] = {}
    for group in GROUP_FLOORS:
        zs: list[float] = []
        for vol in VOLUMES:
            if vol.group != group:
                continue
            u0, u1, v0, v1 = vol.rect
            for i in range(5):
                for j in range(3):
                    zs.append(terrain.sample(*uv_to_xy(u0 + (u1 - u0) * i / 4.0, v0 + (v1 - v0) * j / 2.0)))
        levels[group] = (min(zs) - FOUNDATION_M, max(zs) + 0.15)
    return levels


def build_ab2_complex(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build every AB-2 wing, tower, courtyard floor and the south porch. Returns world vertices."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz)
    levels = _group_levels(terrain)
    for vol in VOLUMES:
        _build_volume(kit, vol, *levels[vol.group])
    bottom, floor = levels["south"]
    for tower in TOWERS:
        _build_tower(kit, tower, floor)
    _build_front_portal(kit, floor)
    _build_south_porch(kit, floor, terrain)
    _build_courtyards(kit, floor)
    _build_footbridge_passage(kit, terrain)
    _build_skylight_vault(kit, levels["link"][1])
    return kit.world_pts


def _build_volume(kit: Kit, vol: Volume, z_bottom: float, z_floor: float) -> None:
    floors = GROUP_FLOORS[vol.group]
    step = FLOOR_STEP_M + vol.eave_extra / floors
    z_eave = z_floor + floors * step
    wall, band = color("stucco_cream"), color("ab2_salmon")
    for side in SIDES:
        style = vol.faces.get(side)
        if style == "v":
            kit.verandah_facade(vol.rect, side, z_bottom, z_floor, floors, step)
        elif style in ("o", "p"):
            kit.stucco_facade(vol.rect, side, z_bottom, z_floor, floors, step, wall, band)
    if vol.roof == "skirt":
        z_cap = kit.skirt_roof(vol.rect, z_eave, vol.skirt, SKIRT_RISE_M, color("roof_concrete"))
        for rows in vol.solar:
            kit.solar_rows(rows, z_cap)
    elif vol.roof == "hip":
        kit.hip_roof(vol.rect, z_eave, vol.rise, color("ab2_tile"))


def _build_tower(kit: Kit, rect: Rect, z_floor: float) -> None:
    z_roofline = z_floor + 4 * FLOOR_STEP_M
    z_top = z_roofline + 3.8
    white, tile = color("stucco_white"), color("ab2_tile")
    for side in SIDES:
        length = side_length(rect, side)
        kit.panel(rect, side, 0.0, length, z_roofline, z_top, color("stucco_cream"), proud=0.05)
        kit.window_row(rect, side, z_roofline + 1.6, z_top - 0.7, 2.4, 1.1, margin=1.0, proud=0.12)
        (au, av), (bu, bv) = edge_of(rect, side)
        nu, nv = {"s": (0.0, -0.18), "e": (0.18, 0.0), "n": (0.0, 0.18), "w": (-0.18, 0.0)}[side]
        mu, mv = (au + bu) / 2.0 + nu, (av + bv) / 2.0 + nv
        kit.tri(
            [(au + (bu - au) * 0.2 + nu, av + (bv - av) * 0.2 + nv, z_top - 0.1),
             (au + (bu - au) * 0.8 + nu, av + (bv - av) * 0.8 + nv, z_top - 0.1),
             (mu, mv, z_top + 1.7)],
            white,
        )
    kit.hip_roof(rect, z_top, 3.4, tile, overhang=0.9)
    uc, vc = (rect[0] + rect[1]) / 2.0, (rect[2] + rect[3]) / 2.0
    kit.pyramid((uc - 0.35, uc + 0.35, vc - 0.35, vc + 0.35), z_top + 3.1, z_top + 5.0, color("bronze_gold"))


def _build_front_portal(kit: Kit, z_floor: float) -> None:
    """South front: salmon side bays, white pilasters and a tall shaded entrance."""
    rect: Rect = (-50.5, -27.0, -56.0, -34.0)
    length = side_length(rect, "s")
    top = z_floor + 4 * FLOOR_STEP_M + 0.45
    salmon, white = color("ab2_salmon"), color("stucco_white")
    for d0, d1 in ((0.0, 5.6), (length - 5.6, length)):
        kit.panel(rect, "s", d0, d1, z_floor, top, salmon, proud=0.12)
        for level in range(4):
            za = z_floor + level * 3.8
            kit.window_row(rect_slice(rect, d0, d1), "s", za + 1.0, za + 2.7, 2.6, 1.4, margin=0.5, proud=0.2)
    for d in (5.6, 9.2, length - 9.2, length - 5.6):
        kit.panel(rect, "s", d - 0.28, d + 0.28, z_floor, top, white, proud=0.35)
    kit.panel(rect, "s", 7.6, length - 7.6, z_floor, z_floor + 3.7, color("recess_shadow"), proud=0.16)


def rect_slice(rect: Rect, d0: float, d1: float) -> Rect:
    """Sub-rectangle spanning distances d0..d1 along the south edge."""
    return (rect[0] + d0, rect[0] + d1, rect[2], rect[3])


def _build_south_porch(kit: Kit, z_floor: float, terrain: Any) -> None:
    u0, u1, v0, v1 = SOUTH_PORCH
    z_ground = terrain.sample(*uv_to_xy((u0 + u1) / 2.0, v0)) - 0.6
    z_beam = z_floor + 4.3
    white = color("stucco_white")
    for u in (u0 + 0.7, u0 + 4.6, u1 - 4.6, u1 - 0.7):
        kit.box((u - 0.35, u + 0.35, v0 + 0.35, v0 + 1.05), z_ground, z_beam, white)
    for u in (u0 + 0.7, u1 - 0.7):
        kit.box((u - 0.35, u + 0.35, v1 - 2.6, v1 - 1.9), z_ground, z_beam, color("ab2_salmon"))
    kit.box(SOUTH_PORCH, z_beam, z_beam + 0.7, white)
    kit.hip_roof(SOUTH_PORCH, z_beam + 0.7, 2.6, color("ab2_tile"), overhang=0.6)


def _build_courtyards(kit: Kit, z_floor: float) -> None:
    """Spine courtyard: lawn, red tile walkways and central water channel; plain lawns elsewhere."""
    lawn, walk, water = color("lawn_green"), color("walkway_red"), color("channel_water")
    for rect in COURTYARDS:
        kit.flat(rect, z_floor + 0.05, lawn)
    for u0, u1 in ((-41.4, -40.2), (-38.8, -37.6)):
        kit.flat((u0, u1, -33.5, 1.5), z_floor + 0.12, walk)
    kit.flat((-40.2, -38.8, -32.0, 0.0), z_floor + 0.14, water)
    kit.flat((-43.0, -36.0, -17.2, -15.0), z_floor + 0.18, walk)


def _build_footbridge_passage(kit: Kit, terrain: Any) -> None:
    """Open doorways on both sides of the east corridor where the walk to the footbridge passes under it."""
    u0, u1, v0, v1 = EAST_CORRIDOR
    for side, v_mid in (("e", 63.9), ("w", 66.6)):
        d_mid = v_mid - v0 if side == "e" else v1 - v_mid
        z = terrain.sample(*uv_to_xy(u1 if side == "e" else u0, v_mid))
        kit.panel(EAST_CORRIDOR, side, d_mid - 2.4, d_mid + 2.4, z - 0.3, z + 3.7, color("stucco_white"), proud=0.12)
        kit.panel(EAST_CORRIDOR, side, d_mid - 1.8, d_mid + 1.8, z - 0.3, z + 3.2, color("recess_shadow"), proud=0.18)


def _build_skylight_vault(kit: Kit, z_floor: float) -> None:
    z_cap = z_floor + 3 * FLOOR_STEP_M + SKIRT_RISE_M
    kit.hip_roof((-8.5, -1.5, 40.0, 49.5), z_cap + 0.25, 2.1, color("skylight_vault"), overhang=0.0)


def ab2_statue_xy() -> tuple[float, float]:
    return uv_to_xy(*STATUE_UV)


def ab2_front_tree_spots() -> list[tuple[float, float, int, tuple[float, float]]]:
    """Hand-placed palms: lining the front garden, ringing the statue and inside the spine courtyard."""
    spots: list[tuple[float, float, int, tuple[float, float]]] = []
    for u in (-66.0, -60.5, -55.0, -49.5, -25.5, -20.0, -14.5, -9.0):
        spots.append((*uv_to_xy(u, -58.5), 0, (0.78, 0.94)))
    su, sv = STATUE_UV
    for deg in (20.0, 55.0, 125.0, 160.0, 200.0, 235.0, 305.0, 340.0):
        a = math.radians(deg)
        spots.append((*uv_to_xy(su + 15.5 * math.cos(a), sv + 15.5 * math.sin(a)), 0, (0.80, 1.0)))
    for v in (-29.0, -23.0, -9.5, -3.5):
        for u in (-41.8, -37.2):
            spots.append((*uv_to_xy(u, v), 0, (0.46, 0.56)))
    return spots


def ab2_ground_rings() -> list[tuple[list[tuple[float, float]], float, int]]:
    """(ring, z offset, ground material index) for the circular granite plaza under the statue."""
    cx, cy = ab2_statue_xy()
    ring = [(cx + 10.0 * math.cos(math.tau * i / 24), cy + 10.0 * math.sin(math.tau * i / 24)) for i in range(24)]
    return [(ring, 0.14, 8)]


def append_nataraja_fountain(bm: bmesh.types.BMesh, col_layer: Any, terrain: Any) -> None:
    """Stepped circular granite fountain carrying the bronze Mahadev Nataraja, facing the front road."""
    cx, cy = ab2_statue_xy()
    z = terrain.sample(cx, cy)
    granite, granite_top = color("granite_dark"), color("granite_light")
    for tier, radius in enumerate((7.8, 6.2, 4.6)):
        add_cylinder_vc(
            bm, col_layer, cx, cy, z - 0.6 + tier * 0.45 if tier == 0 else z + tier * 0.45 - 0.05,
            z + (tier + 1) * 0.45, radius, radius, 20, granite, granite_top,
        )
    water_z = z + 1.38
    add_cylinder_vc(bm, col_layer, cx, cy, water_z - 0.05, water_z, 3.9, 3.9, 20,
                    color("channel_water"), color("channel_water"))
    bronze = color("bronze_patina")
    add_cylinder_vc(bm, col_layer, cx, cy, water_z, water_z + 1.5, 1.7, 1.15, 10, bronze, bronze)
    _append_nataraja_figure(bm, col_layer, cx, cy, water_z + 1.45, bronze)


def _append_nataraja_figure(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z_base: float,
    bronze: tuple[float, float, float, float],
) -> None:
    """Flame ring and dancing silhouette drawn in the vertical plane that faces south."""
    ux, uy = math.cos(0.118), math.sin(0.118)
    nx, ny = uy, -ux  # outward (south) normal of the statue plane
    zc = z_base + 3.05

    def pt(a: float, h: float, depth: float) -> bmesh.types.BMVert:
        return bm.verts.new((cx + ux * a + nx * depth, cy + uy * a + ny * depth, h))

    def tri(p0, p1, p2) -> None:
        face = bm.faces.new((p0, p1, p2))
        face.smooth = False
        for loop in face.loops:
            loop[col_layer] = bronze

    def bar(a0: float, h0: float, a1: float, h1: float, half: float) -> None:
        """Flat slab limb with front and back faces plus its four edges."""
        length = max(1e-4, math.hypot(a1 - a0, h1 - h0))
        pa, ph = -(h1 - h0) / length * half, (a1 - a0) / length * half
        corners = ((a0 - pa, h0 - ph), (a1 - pa, h1 - ph), (a1 + pa, h1 + ph), (a0 + pa, h0 + ph))
        front = [pt(a, h, 0.22) for a, h in corners]
        back = [pt(a, h, -0.22) for a, h in corners]
        tri(front[0], front[1], front[2])
        tri(front[0], front[2], front[3])
        tri(back[2], back[1], back[0])
        tri(back[3], back[2], back[0])
        for i in range(4):
            j = (i + 1) % 4
            tri(front[j], front[i], back[i])
            tri(front[j], back[i], back[j])

    segments, outer, inner = 20, 3.0, 2.6
    for i in range(segments):
        a0, a1 = math.tau * i / segments, math.tau * (i + 1) / segments
        bar(
            0.5 * (outer + inner) * math.cos(a0), zc + 0.5 * (outer + inner) * math.sin(a0),
            0.5 * (outer + inner) * math.cos(a1), zc + 0.5 * (outer + inner) * math.sin(a1),
            0.5 * (outer - inner),
        )
        am = 0.5 * (a0 + a1)
        if math.sin(am) > -0.75:  # flame tongues around the ring, none under the pedestal
            base = [(outer * math.cos(a), zc + outer * math.sin(a)) for a in (am - 0.09, am + 0.09)]
            tip = ((outer + 0.65) * math.cos(am), zc + (outer + 0.65) * math.sin(am))
            tri(pt(base[0][0], base[0][1], 0.0), pt(tip[0], tip[1], 0.0), pt(base[1][0], base[1][1], 0.0))
            tri(pt(base[1][0], base[1][1], 0.0), pt(tip[0], tip[1], 0.0), pt(base[0][0], base[0][1], 0.0))
    limbs = (
        (0.35, -2.65, 0.15, -1.25, 0.2), (0.15, -1.25, 0.0, -0.45, 0.28),  # standing leg
        (0.0, -0.45, -1.15, -0.55, 0.22), (-1.15, -0.55, -1.7, -1.35, 0.17),  # raised leg
        (0.0, -0.55, 0.0, 0.95, 0.42),  # torso
        (0.0, 1.0, 0.0, 1.65, 0.28),  # head
        (0.0, 1.65, 0.0, 2.15, 0.14),  # crown
        (0.2, 0.7, 1.55, 1.55, 0.13), (-0.2, 0.7, -1.55, 1.5, 0.13),  # raised arms
        (0.2, 0.45, -0.9, -0.05, 0.12), (0.25, 0.4, 1.2, 0.1, 0.12),  # lower arms
    )
    for a0, h0, a1, h1, half in limbs:
        bar(a0, zc + h0, a1, zc + h1, half)


def build_ab2_skybridge_hero(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    terrain: Any,
    z_bottom: float,
    z_top: float,
    bridge_width: float,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build Photo-2-accurate AB-2 <-> Central Library road portal arch, signage fascia & hipped upper walkway."""
    dx, dy = bx - ax, by - ay
    seg_len = max(2.0, math.hypot(dx, dy))
    rot = math.atan2(dy, dx)
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)

    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_portal = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_portal"])
    c_roof = srgb_hex_to_linear_rgba(HERO_PALETTE["ab2_tile"])
    c_charcoal = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])

    half_l = seg_len * 0.5
    half_w = max(1.9, bridge_width * 0.52)

    # Place twin grounded terracotta-orange portal piers well OUTSIDE the 5.64m curbed road center (~+-5.1m from center)
    pier_offset = max(4.9, half_l - 1.35)
    z_pier_top = z_bottom + 0.55

    world_pts: list[tuple[float, float, float]] = [
        (ax, ay, z_bottom),
        (bx, by, z_bottom),
        (ax, ay, z_top + 1.8),
        (bx, by, z_top + 1.8),
    ]

    for side in (-1.0, 1.0):
        px, py = local_to_world_2d(mx, my, side * pier_offset, 0.0, rot)
        pz_ground = terrain.sample(px, py) - 2.2
        # Main terracotta pier flank (clear of the road asphalt & curb)
        add_box_vc(
            bm, col_layer, px, py, pz_ground, z_pier_top,
            1.10, half_w + 0.35, c_portal, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
        # Outer white interior jamb pilaster for pedestrian walk detail
        jx, jy = local_to_world_2d(mx, my, side * (pier_offset + 1.2), 0.0, rot)
        add_box_vc(
            bm, col_layer, jx, jy, pz_ground, z_pier_top,
            0.36, half_w + 0.15, c_cream, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # Bold terracotta-orange overhead portal lintel beam spanning cleanly above the road
    add_box_vc(
        bm, col_layer, mx, my, z_bottom - 0.45, z_bottom + 0.55,
        pier_offset + 1.4, half_w + 0.42, c_portal, c_white,
        rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )

    # White signage plaque "ACADEMIC BLOCK - II" on BOTH south and north faces of the portal lintel
    for face_sign in (-1.0, 1.0):
        sx, sy = local_to_world_2d(mx, my, 0.0, face_sign * (half_w + 0.48), rot)
        add_box_vc(
            bm, col_layer, sx, sy, z_bottom - 0.12, z_bottom + 0.42,
            2.45, 0.08, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
        tx, ty = local_to_world_2d(mx, my, 0.0, face_sign * (half_w + 0.54), rot)
        add_box_vc(
            bm, col_layer, tx, ty, z_bottom + 0.04, z_bottom + 0.24,
            2.15, 0.05, c_charcoal, c_charcoal, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # Enclosed cream upper skybridge gallery above the lintel
    z_gal0 = z_bottom + 0.55
    z_eave = z_top - 0.15
    add_box_vc(
        bm, col_layer, mx, my, z_gal0, z_eave,
        half_l + 0.35, half_w, c_cream, c_white,
        rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )

    # Square mullioned gallery windows along both sides (glowing warm amber at night)
    for w_lx in (-3.8, -1.3, 1.3, 3.8):
        for face_sign in (-1.0, 1.0):
            wx_g, wy_g = local_to_world_2d(mx, my, w_lx, 0.0, rot)
            add_glass_panel(
                win_lit_bm, wx_g, wy_g,
                z_gal0 + 0.55, z_eave - 0.45, 0.88,
                face_sign * (half_w + 0.07), rot_rad=rot, facing_south=(face_sign < 0),
            )
            # Crisp dark window frame border backing
            fx_g, fy_g = local_to_world_2d(mx, my, w_lx, face_sign * (half_w + 0.02), rot)
            add_box_vc(
                bm, col_layer, fx_g, fy_g, z_gal0 + 0.48, z_eave - 0.38,
                0.96, 0.05, c_charcoal, c_white, rot_rad=rot, offset_xyz=offset_xyz,
            )

    # White overhanging soffit & deep dark-brown hipped roof matching Photo 2
    add_box_vc(
        bm, col_layer, mx, my, z_eave, z_eave + 0.22,
        half_l + 0.95, half_w + 0.72, c_white, c_white,
        rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_hipped_roof_vc(
        bm, col_layer, mx, my, z_eave + 0.20, z_eave + 1.85,
        half_l + 1.1, half_w + 0.85, c_roof,
        rot_rad=rot, soffit_rgba=c_white, offset_xyz=offset_xyz,
    )

    return world_pts
