"""Academic Block 2 (AB-2) & Iconic Covered Portal Skybridge Blender generators."""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_glass_panel,
    add_hipped_roof_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)


def append_ab2_hero_details(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_eave: float,
    z_top: float,
) -> None:
    """Append AB-2 corner stairwell towers, south portal frame, and terracotta-framed window reveals."""
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_portal = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_portal"])
    c_roof = srgb_hex_to_linear_rgba(HERO_PALETTE["ab2_dark_roof"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])

    # 1. Twin rooftop stairwell towers with pitched terracotta hipped caps
    for tx, ty in ((-286.0, 112.0), (-205.0, 240.0)):
        add_box_vc(
            bm, col_layer, tx, ty, z_top - 0.4, z_top + 2.1,
            3.3, 3.3, c_cream, c_white, rot_rad=0.11, offset_xyz=offset_xyz,
        )
        add_hipped_roof_vc(
            bm, col_layer, tx, ty, z_top + 2.08, z_top + 3.45,
            3.7, 3.7, c_tile, rot_rad=0.11, offset_xyz=offset_xyz,
        )

    # 2. South entrance terrace portal at (-240.6, 91.9) matching AB-2's signature terracotta portal arch
    sx, sy, srot = -240.6, 91.9, 0.11
    sz0 = terrain.sample(sx, sy) - 1.8
    hero_h = max(6.0, z_eave - z_plinth)
    z_beam0 = z_plinth + min(4.3, hero_h * 0.34)
    z_beam1 = z_beam0 + 0.95
    for side in (-1.0, 1.0):
        px, py = local_to_world_2d(sx, sy, side * 5.2, -1.8, srot)
        add_box_vc(
            bm, col_layer, px, py, sz0, z_beam1,
            0.78, 1.4, c_portal, c_white, rot_rad=srot, offset_xyz=offset_xyz,
        )
    lx, ly = local_to_world_2d(sx, sy, 0.0, -1.8, srot)
    add_box_vc(
        bm, col_layer, lx, ly, z_beam0, z_beam1,
        5.9, 1.45, c_portal, c_white, rot_rad=srot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_hipped_roof_vc(
        bm, col_layer, lx, ly, z_beam1 - 0.02, z_beam1 + 1.65,
        6.4, 2.2, c_roof, rot_rad=srot, offset_xyz=offset_xyz,
    )

    # 3. Protruding terracotta-orange window surround frames along prominent south-east facade corner
    step_h = hero_h / 4.0
    for fl in (1, 2, 3):
        wz0 = z_plinth + fl * step_h + step_h * 0.22
        wz1 = wz0 + min(1.38, step_h * 0.48)
        for dx in (-267.0, -259.5, -217.0, -209.5):
            fx, fy = dx, (98.0 if dx < -240 else 108.5)
            add_box_vc(
                bm, col_layer, fx, fy, wz0, wz1,
                1.25, 0.26, c_portal, c_portal, rot_rad=0.11, offset_xyz=offset_xyz,
            )
            add_glass_panel(win_lit_bm, fx, fy, wz0 + 0.14, wz1 - 0.14, 0.96, -0.32, rot_rad=0.11, facing_south=True)


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
    c_roof = srgb_hex_to_linear_rgba(HERO_PALETTE["ab2_dark_roof"])
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
