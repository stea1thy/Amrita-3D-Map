"""Academic Block 3 (AB-3) facade & Amrita Playground stepped bleachers + goalposts."""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_glass_panel,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# Exact East entrance wall center & alignment from way/380829415: (-273.79, 366.83) -> (-277.89, 424.88)
AB3_EAST_CX = -275.84
AB3_EAST_CY = 395.86
AB3_EAST_ROT = 1.6413  # +94.04 deg: +lx runs S->N along East wall, -ly faces outward East toward road


def normalize_ab3_footprint_rings(
    outer_ring: list[tuple[float, float]],
) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]]]:
    """Replace notched OSM AB-3 polygon with clean rectangle + two symmetric internal courtyard holes."""
    if len(outer_ring) < 4:
        return ([outer_ring], [])

    sw = min(outer_ring, key=lambda p: p[0] + p[1])
    ne = max(outer_ring, key=lambda p: p[0] + p[1])
    nw = min(outer_ring, key=lambda p: p[0] - p[1])
    se = max(outer_ring, key=lambda p: p[0] - p[1])
    rect_outer = [sw, se, ne, nw]

    def _bilerp(u: float, v: float) -> tuple[float, float]:
        sx = sw[0] * (1.0 - u) + se[0] * u
        sy = sw[1] * (1.0 - u) + se[1] * u
        nx = nw[0] * (1.0 - u) + ne[0] * u
        ny = nw[1] * (1.0 - u) + ne[1] * u
        return (sx * (1.0 - v) + nx * v, sy * (1.0 - v) + ny * v)

    west_ccw = [_bilerp(0.125, 0.26), _bilerp(0.435, 0.26), _bilerp(0.435, 0.74), _bilerp(0.125, 0.74)]
    east_ccw = [_bilerp(0.565, 0.26), _bilerp(0.875, 0.26), _bilerp(0.875, 0.74), _bilerp(0.565, 0.74)]
    return ([rect_outer, list(reversed(west_ccw)), list(reversed(east_ccw))], [west_ccw, east_ccw])


def append_ab3_hero_details(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_eave: float,
    z_top: float,
) -> None:
    """Append East-facing AB-3 terracotta masonry bays, tall glass slot, entrance canopy & rooftop blocks."""
    cx, cy, rot = AB3_EAST_CX, AB3_EAST_CY, AB3_EAST_ROT
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_brick = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_brick"])
    c_recess = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_slate = srgb_hex_to_linear_rgba(HERO_PALETTE["asb_slate_tile"])

    hero_h = max(6.0, z_eave - z_plinth)
    step_h = hero_h / 3.0

    # 1. Twin projecting rust-terracotta architectural masonry wings along the East entrance wall
    for wing_lx, wing_hx in ((-16.5, 6.8), (16.5, 6.8)):
        wx, wy = local_to_world_2d(cx, cy, wing_lx, -1.4, rot)
        wz0 = terrain.sample(wx, wy) - 2.2
        add_box_vc(
            bm, col_layer, wx, wy, wz0, z_eave + 0.35,
            wing_hx, 2.0, c_brick, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
        # White horizontal cornice sun-breaker ledges + ribbon glass per floor
        for fl in range(3):
            fz0 = z_plinth + fl * step_h + step_h * 0.24
            fz1 = fz0 + min(1.42, step_h * 0.46)
            lw_x, lw_y = local_to_world_2d(cx, cy, wing_lx, -3.45, rot)
            add_box_vc(
                bm, col_layer, lw_x, lw_y, fz1 + 0.04, fz1 + 0.24,
                wing_hx - 0.5, 0.24, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
            )
            add_glass_panel(
                win_lit_bm if fl > 0 else win_dark_bm,
                wx, wy, fz0, fz1, wing_hx - 1.0, -2.06, rot_rad=rot, facing_south=True,
            )

    # 2. Iconic vertical full-height dark glass stairwell atrium slot grounded down into terrain plinth
    slot_wx, slot_wy = local_to_world_2d(cx, cy, 5.8, -2.8, rot)
    sz0 = terrain.sample(slot_wx, slot_wy) - 2.2
    add_box_vc(
        bm, col_layer, slot_wx, slot_wy, sz0, z_top + 0.65,
        2.4, 0.85, c_recess, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    add_glass_panel(
        win_lit_bm, slot_wx, slot_wy, z_plinth + 0.5, z_top + 0.25, 2.0, -0.92, rot_rad=rot, facing_south=True,
    )

    # 3. Ground entrance porte-cochere canopy with twin crisp white pillars cleanly centered between south wing & glass slot
    ent_wx, ent_wy = local_to_world_2d(cx, cy, -2.8, -3.2, rot)
    ez0 = terrain.sample(ent_wx, ent_wy) - 1.5
    add_box_vc(
        bm, col_layer, ent_wx, ent_wy, z_plinth + step_h * 0.92, z_plinth + step_h * 1.08,
        5.2, 2.6, c_white, c_brick, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    for col_dx in (-6.8, 1.2):
        col_x, col_y = local_to_world_2d(cx, cy, col_dx, -5.2, rot)
        add_box_vc(
            bm, col_layer, col_x, col_y, ez0, z_plinth + step_h * 0.94,
            0.38, 0.38, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # 4. Asymmetric white stepped rooftop stairwell/penthouse blocks along the East wing slab
    for rx_loc, ry_loc, rhx, rhy, rh in (
        (-15.0, 6.2, 4.8, 3.2, 2.5),
        (4.0, 6.2, 5.8, 3.6, 3.2),
        (20.0, 6.2, 4.5, 3.0, 2.2),
    ):
        rwx, rwy = local_to_world_2d(cx, cy, rx_loc, ry_loc, rot)
        add_box_vc(
            bm, col_layer, rwx, rwy, z_top - 0.1, z_top + rh,
            rhx, rhy, c_white, c_slate, rot_rad=rot, offset_xyz=offset_xyz,
        )
        add_glass_panel(win_dark_bm, rwx, rwy, z_top + 0.45, z_top + rh * 0.72, rhx * 0.72, -rhy - 0.06, rot_rad=rot, facing_south=True)


def append_playground_bleachers_and_goals(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
    gcx: float,
    gcy: float,
    pitch_ang_rad: float,
    pg_flat_z: float | None,
) -> None:
    """Build Photo-3-accurate 6-tier white bleachers with terracotta stair aisles, charcoal track wall & football goals."""
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["bleacher_white"])
    c_stair = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_portal"])
    c_wall = srgb_hex_to_linear_rgba(HERO_PALETTE["charcoal_wall"])
    c_goal = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])

    # Placed north of way/531088132 (ends at y=-29.8) & strictly west of athletics track oval (x>=181)
    stand_cx, stand_cy = 171.8, 16.0
    stand_rot = -0.108
    pg_z = pg_flat_z if pg_flat_z is not None else terrain.sample(stand_cx, stand_cy)
    base_z = pg_z - 1.2

    # 1. Long dark-charcoal perimeter retaining wall with white coping overlooking pitch (foreground of Photo 3)
    wx_wall, wy_wall = local_to_world_2d(stand_cx, stand_cy, 5.6, 0.0, stand_rot)
    add_box_vc(bm, col_layer, wx_wall, wy_wall, base_z, pg_z + 1.35, 0.48, 29.0, c_wall, c_white, rot_rad=stand_rot)
    add_box_vc(bm, col_layer, wx_wall, wy_wall, pg_z + 1.35, pg_z + 1.56, 0.56, 29.2, c_white, c_white, rot_rad=stand_rot)

    # 2. 6-tier stepped white concrete bleachers with 3 terracotta-orange stair aisles
    for tier in range(6):
        lx = 3.2 - tier * 1.15
        z1 = pg_z + 0.55 + tier * 0.58
        tx, ty = local_to_world_2d(stand_cx, stand_cy, lx, 0.0, stand_rot)
        add_box_vc(bm, col_layer, tx, ty, base_z, z1, 0.62, 28.0, c_white, c_white, rot_rad=stand_rot)

    for stair_ly in (-18.0, 0.0, 18.0):
        for tier in range(6):
            lx = 3.25 - tier * 1.15
            z1 = pg_z + 0.61 + tier * 0.58
            sx, sy = local_to_world_2d(stand_cx, stand_cy, lx, stair_ly, stand_rot)
            add_box_vc(bm, col_layer, sx, sy, base_z, z1, 0.64, 1.15, c_stair, c_stair, rot_rad=stand_rot)

    # 3. Twin white football goalposts at both ends of central soccer pitch
    ca, sa = math.cos(pitch_ang_rad), math.sin(pitch_ang_rad)
    goal_z = pg_z - 0.1
    goal_h = 2.6
    goal_hw = 3.7
    nx, ny = -sa, ca
    for end_sign in (-1.0, 1.0):
        gx = gcx + end_sign * ca * 48.0
        gy = gcy + end_sign * sa * 48.0
        for p_sign in (-1.0, 1.0):
            px, py = gx + p_sign * nx * goal_hw, gy + p_sign * ny * goal_hw
            add_cylinder_vc(bm, col_layer, px, py, goal_z, pg_z + goal_h, 0.11, 0.11, 6, c_goal, c_goal)
        add_box_vc(
            bm, col_layer, gx, gy, pg_z + goal_h - 0.14, pg_z + goal_h + 0.04,
            0.11, goal_hw + 0.11, c_goal, c_goal, rot_rad=pitch_ang_rad, emit_bottom=True,
        )
