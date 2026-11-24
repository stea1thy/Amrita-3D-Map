"""Academic Block 1 (AB-1) Main Block portico & Lotus Fountain roundabout Blender generators."""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_glass_panel,
    add_hipped_roof_vc,
    add_tri_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# Exact OSM south portico center & alignment from way/380925364: (235.4,-287.9)->(251.2,-286.7)
AB1_PORTICO_CX = 243.3
AB1_PORTICO_CY = -284.2
AB1_PORTICO_ROT = 0.0758  # ~4.3 deg

# Centered cleanly inside driveway roundabout loop way/546394550
AB1_FOUNTAIN_CX = 245.0
AB1_FOUNTAIN_CY = -300.5


def append_ab1_hero_details(
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
    """Append AB-1 symmetrical portico, pilaster towers, 4th-floor curtain wall, gable roof & wing solar arrays."""
    cx, cy, rot = AB1_PORTICO_CX, AB1_PORTICO_CY, AB1_PORTICO_ROT
    ox, oy, oz = offset_xyz
    pz0 = terrain.sample(cx, cy) - 2.0
    hero_h = max(8.0, z_eave - z_plinth)

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_roof = srgb_hex_to_linear_rgba(HERO_PALETTE["ab1_tile_roof"])
    c_roof_ridge = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_col_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_maroon = srgb_hex_to_linear_rgba(HERO_PALETTE["amrita_maroon"])
    c_recess = srgb_hex_to_linear_rgba(HERO_PALETTE["recess_shadow"])
    c_solar = srgb_hex_to_linear_rgba(HERO_PALETTE["solar_panel"])

    # 1. Ground-floor projecting porte-cochere drive-through canopy & clean low entry step (keep drive-through open!)
    p_wx, p_wy = local_to_world_2d(cx, cy, 0.0, -5.8, rot)
    p_ground = terrain.sample(p_wx, p_wy)
    add_box_vc(
        bm, col_layer, p_wx, p_wy, pz0, p_ground + 0.24,
        7.8, 3.6, c_white, c_cream, rot_rad=rot, offset_xyz=offset_xyz,
    )
    z_canopy0 = z_plinth + hero_h * 0.255
    z_canopy1 = z_plinth + hero_h * 0.325
    add_box_vc(
        bm, col_layer, p_wx, p_wy, z_canopy0, z_canopy1,
        8.6, 4.0, c_white, c_cream, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    # Dark maroon-charcoal Amrita signboard fascia on south canopy front
    sign_wx, sign_wy = local_to_world_2d(cx, cy, 0.0, -9.85, rot)
    add_box_vc(
        bm, col_layer, sign_wx, sign_wy, z_canopy0 + 0.08, z_canopy1 - 0.08,
        5.0, 0.14, c_maroon, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )

    # 4 dark-charcoal front porte-cochere columns on low white bases (open drive-through between piers)
    for lx in (-6.2, -2.5, 2.5, 6.2):
        col_wx, col_wy = local_to_world_2d(cx, cy, lx, -8.8, rot)
        col_g = terrain.sample(col_wx, col_wy)
        add_box_vc(
            bm, col_layer, col_wx, col_wy, pz0, col_g + 0.85,
            0.52, 0.52, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
        add_box_vc(
            bm, col_layer, col_wx, col_wy, col_g + 0.82, z_canopy0 + 0.04,
            0.40, 0.40, c_col_dark, c_col_dark, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # 2. Twin full-height white corner pilaster towers with vertical groove ribs
    for side in (-1.0, 1.0):
        tx_w, ty_w = local_to_world_2d(cx, cy, side * 8.6, -2.2, rot)
        add_box_vc(
            bm, col_layer, tx_w, ty_w, pz0, z_top + 0.35,
            1.15, 4.6, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
        rib_wx, rib_wy = local_to_world_2d(cx, cy, side * 8.6, -6.9, rot)
        add_box_vc(
            bm, col_layer, rib_wx, rib_wy, pz0, z_top + 0.35,
            0.30, 0.18, c_cream, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # 3. Recessed upper foyer shadow cavity + tiered horizontal white floor slabs
    rec_wx, rec_wy = local_to_world_2d(cx, cy, 0.0, -3.9, rot)
    add_box_vc(
        bm, col_layer, rec_wx, rec_wy, z_plinth + hero_h * 0.26, z_eave - 0.1,
        7.35, 1.8, c_recess, c_cream, rot_rad=rot, offset_xyz=offset_xyz,
    )
    for frac in (0.52, 0.76, 1.0):
        tz = z_plinth + hero_h * frac
        tier_wx, tier_wy = local_to_world_2d(cx, cy, 0.0, -3.1, rot)
        add_box_vc(
            bm, col_layer, tier_wx, tier_wy, tz - 0.45, tz,
            7.8, 3.6, c_white, c_white, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
        )
    # White corner balcony parapets + 3rd floor warm terracotta central relief panel
    par_wx, par_wy = local_to_world_2d(cx, cy, 0.0, -6.4, rot)
    add_box_vc(
        bm, col_layer, par_wx, par_wy, z_plinth + hero_h * 0.52, z_plinth + hero_h * 0.59,
        7.5, 0.24, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    pan_wx, pan_wy = local_to_world_2d(cx, cy, 0.0, -5.6, rot)
    add_box_vc(
        bm, col_layer, pan_wx, pan_wy, z_plinth + hero_h * 0.56, z_plinth + hero_h * 0.71,
        2.6, 0.32, c_roof_ridge, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )

    # 4. Top-floor (Floor 4) 6-bay panoramic reflective curtain glass + crisp white vertical mullions
    z_pan0 = z_plinth + hero_h * 0.775
    z_pan1 = z_eave - 0.48
    glass_wx, glass_wy = local_to_world_2d(cx, cy, 0.0, -6.55, rot)
    add_box_vc(
        bm, col_layer, glass_wx, glass_wy, z_pan0, z_pan1,
        7.3, 0.14, c_col_dark, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    for bay in range(-3, 3):
        bay_cx_local = (bay + 0.5) * 2.25
        bw_x, bw_y = local_to_world_2d(cx, cy, bay_cx_local, 0.0, rot)
        add_glass_panel(win_lit_bm, bw_x, bw_y, z_pan0 + 0.06, z_pan1 - 0.06, 0.92, -6.74, rot_rad=rot, facing_south=True)
    for mx in (-4.5, -2.25, 0.0, 2.25, 4.5):
        mw_x, mw_y = local_to_world_2d(cx, cy, mx, -6.68, rot)
        add_box_vc(
            bm, col_layer, mw_x, mw_y, z_pan0, z_pan1,
            0.12, 0.12, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # 5. Overhanging hipped terracotta-sandstone tiled roof with white gable pediment & eave fascia
    roof_wx, roof_wy = local_to_world_2d(cx, cy, 0.0, -0.6, rot)
    add_box_vc(
        bm, col_layer, roof_wx, roof_wy, z_top - 0.35, z_top + 0.06,
        10.5, 6.9, c_white, c_white, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_hipped_roof_vc(
        bm, col_layer, roof_wx, roof_wy, z_top + 0.04, z_top + 4.3,
        10.7, 7.1, c_roof, rot_rad=rot, gable_rgba=c_white, soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )

    # 6. Wing solar panel arrays seated flush on AB-1 flat upper roof inside sloped eaves
    for sx, sy, srot in ((268.0, -252.0, -0.68), (213.0, -254.0, 0.70)):
        add_box_vc(
            bm, col_layer, sx, sy, z_top - 0.15, z_top + 0.16,
            7.2, 1.5, c_solar, c_solar, rot_rad=srot, offset_xyz=offset_xyz,
        )
    if win_dark_bm is not None:
        pass  # Keep unused param explicit for uniform hero builder signature


def append_ab1_fountain_plaza(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
) -> None:
    """Build AB-1's circular Lotus/Saraswati Fountain Roundabout with terracotta bollards & tiered lotus pedestal."""
    fx, fy = AB1_FOUNTAIN_CX, AB1_FOUNTAIN_CY
    rim_zs = [terrain.sample(fx, fy)]
    for i in range(8):
        ang = (2.0 * math.pi * i) / 8.0
        rim_zs.append(terrain.sample(fx + 8.2 * math.cos(ang), fy + 8.2 * math.sin(ang)))
    fz = max(rim_zs) + 0.08
    fz_bot = min(rim_zs) - 1.5

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_terracotta = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_water = srgb_hex_to_linear_rgba(HERO_PALETTE["fountain_water"])
    c_bronze = srgb_hex_to_linear_rgba(HERO_PALETTE["bronze_gold"])
    c_grass = srgb_hex_to_linear_rgba(HERO_PALETTE["lawn_green"])

    # Outer white circular curb wall + manicured grass flowerbed band (r = 7.0..8.2m, clear of loop road)
    segs = 24
    r_out, r_in = 8.2, 7.0
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs
        a1 = (2.0 * math.pi * (i + 1)) / segs
        p_in0 = (fx + r_in * math.cos(a0), fy + r_in * math.sin(a0))
        p_in1 = (fx + r_in * math.cos(a1), fy + r_in * math.sin(a1))
        p_ou0 = (fx + r_out * math.cos(a0), fy + r_out * math.sin(a0))
        p_ou1 = (fx + r_out * math.cos(a1), fy + r_out * math.sin(a1))
        vi0, vi1 = bm.verts.new((p_in0[0], p_in0[1], fz_bot)), bm.verts.new((p_in1[0], p_in1[1], fz_bot))
        vo0, vo1 = bm.verts.new((p_ou0[0], p_ou0[1], fz_bot)), bm.verts.new((p_ou1[0], p_ou1[1], fz_bot))
        ti0, ti1 = bm.verts.new((p_in0[0], p_in0[1], fz + 0.66)), bm.verts.new((p_in1[0], p_in1[1], fz + 0.66))
        to0, to1 = bm.verts.new((p_ou0[0], p_ou0[1], fz + 0.66)), bm.verts.new((p_ou1[0], p_ou1[1], fz + 0.66))
        add_tri_vc(bm, col_layer, (vo0, vo1, to1), c_white)
        add_tri_vc(bm, col_layer, (vo0, to1, to0), c_white)
        add_tri_vc(bm, col_layer, (vi1, vi0, ti0), c_white)
        add_tri_vc(bm, col_layer, (vi1, ti0, ti1), c_white)
        add_tri_vc(bm, col_layer, (to0, to1, ti1), c_grass)
        add_tri_vc(bm, col_layer, (to0, ti1, ti0), c_grass)

    # Inner reflective turquoise water basin disc level above highest rim terrain sample (zero uphill bleed)
    add_cylinder_vc(bm, col_layer, fx, fy, fz_bot, fz + 0.48, 7.05, 7.05, 24, c_water, c_water)

    # 16 terracotta rim bollards around the white outer curb
    for i in range(16):
        ang = (2.0 * math.pi * i) / 16.0
        bx = fx + 7.65 * math.cos(ang)
        by = fy + 7.65 * math.sin(ang)
        add_cylinder_vc(bm, col_layer, bx, by, fz + 0.55, fz + 1.02, 0.16, 0.18, 6, c_white, c_terracotta)

    # Sculpted multi-tier white Lotus Fountain pedestal + central lotus spire
    add_cylinder_vc(bm, col_layer, fx, fy, fz - 0.4, fz + 0.95, 2.75, 2.45, 14, c_white, c_white)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 0.95, fz + 1.75, 2.90, 2.15, 12, c_white, c_water)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 1.70, fz + 2.75, 1.45, 1.75, 12, c_white, c_white)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 2.75, fz + 3.85, 1.55, 0.85, 12, c_white, c_white)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 3.85, fz + 4.75, 0.42, 0.14, 10, c_bronze, c_bronze)

    # Flanking sandstone courtyard planters on AB-1 approach
    c_stone = srgb_hex_to_linear_rgba(HERO_PALETTE["stone_masonry"])
    for px, py in ((221.0, -295.0), (266.0, -294.0)):
        pz = terrain.sample(px, py)
        add_box_vc(bm, col_layer, px, py, pz - 0.5, pz + 0.48, 3.2, 1.3, c_stone, c_white, rot_rad=AB1_PORTICO_ROT)
        add_box_vc(bm, col_layer, px, py, pz + 0.48, pz + 0.64, 2.85, 0.98, c_grass, c_grass, rot_rad=AB1_PORTICO_ROT)
