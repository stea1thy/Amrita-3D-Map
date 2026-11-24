"""Amrita School of Business (ASB) slate porte-cochere, glass atrium & curved stone planter."""

from __future__ import annotations

from typing import Any

import bmesh

from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_glass_panel,
    add_hipped_roof_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# Aligned to ASB south-east recessed entrance notch (way/380829759) & driveway way/546394570/546394571
ASB_PORTICO_CX = 151.4
ASB_PORTICO_CY = 166.8
ASB_ROT = 0.088


def append_asb_hero_details(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_eave: float,
    z_top: float,
) -> None:
    """Append Photo-4-accurate ASB slate-tile porte-cochere with white pediment, grille parapet & glass atrium."""
    cx, cy, rot = ASB_PORTICO_CX, ASB_PORTICO_CY, ASB_ROT
    pz0 = terrain.sample(cx, cy) - 2.0
    hero_h = max(8.0, z_eave - z_plinth)

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_slate = srgb_hex_to_linear_rgba(HERO_PALETTE["asb_slate_tile"])
    c_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_recess = srgb_hex_to_linear_rgba(HERO_PALETTE["recess_shadow"])

    # 1. Ground porte-cochere extending south over driveway bay (drive-through stays clear under canopy)
    z_eave_canopy = z_plinth + min(4.3, hero_h * 0.31)
    can_wx, can_wy = local_to_world_2d(cx, cy, 0.0, -3.0, rot)

    # 4 white square entrance pillars on low plinth bases
    for col_lx, col_ly in ((-4.8, -5.6), (-1.9, -5.6), (1.9, -5.6), (4.8, -5.6)):
        cwx, cwy = local_to_world_2d(cx, cy, col_lx, col_ly, rot)
        add_box_vc(
            bm, col_layer, cwx, cwy, pz0, z_plinth + 0.65,
            0.48, 0.48, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
        add_box_vc(
            bm, col_layer, cwx, cwy, z_plinth + 0.62, z_eave_canopy + 0.05,
            0.34, 0.34, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # Flat canopy fascia soffit + overhanging slate-grey hipped Mangalore-tile canopy roof + white front gable pediment
    add_box_vc(
        bm, col_layer, can_wx, can_wy, z_eave_canopy - 0.38, z_eave_canopy + 0.06,
        5.8, 3.2, c_white, c_cream, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_hipped_roof_vc(
        bm, col_layer, can_wx, can_wy, z_eave_canopy + 0.04, z_eave_canopy + 1.95,
        6.2, 3.55, c_slate, rot_rad=rot, gable_rgba=c_white, soffit_rgba=c_white, offset_xyz=offset_xyz,
    )

    # Decorative filigree parapet wall rising just behind the canopy roof (3 dark recessed lattice grilles in white frame)
    rail_wx, rail_wy = local_to_world_2d(cx, cy, 0.0, -0.4, rot)
    z_rail0 = z_eave_canopy + 0.85
    z_rail1 = z_eave_canopy + 1.85
    add_box_vc(
        bm, col_layer, rail_wx, rail_wy, z_rail0, z_rail1,
        5.2, 0.35, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    for gx_loc in (-3.1, 0.0, 3.1):
        gwx, gwy = local_to_world_2d(cx, cy, gx_loc, -0.78, rot)
        add_box_vc(
            bm, col_layer, gwx, gwy, z_rail0 + 0.22, z_rail1 - 0.22,
            1.15, 0.06, c_recess, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )

    # 2. Tall reflective blue-slate vertical glass atrium curtain tower grounded down into terrain plinth
    atr_wx, atr_wy = local_to_world_2d(cx, cy, -5.2, 2.5, rot)
    atr_z0 = terrain.sample(atr_wx, atr_wy) - 2.2
    add_box_vc(
        bm, col_layer, atr_wx, atr_wy, atr_z0, z_top + 0.45,
        3.4, 2.2, c_dark, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    add_glass_panel(
        win_lit_bm, atr_wx, atr_wy, z_plinth + 0.4, z_top - 0.3, 2.9, -2.28, rot_rad=rot, facing_south=True,
    )

    # 3. Tiered overhanging cool-slate hipped roof crown capping ASB's main hall
    crown_wx, crown_wy = 133.5, 195.0
    add_hipped_roof_vc(
        bm, col_layer, crown_wx, crown_wy, z_eave - 0.10, z_top + 3.15,
        18.2, 22.8, c_slate, rot_rad=rot, soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )


def append_asb_driveway_planter(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
) -> None:
    """Build Photo-4's signature stone-masonry driveway median island planter & heritage lamp post."""
    px, py, rot = 132.5, 157.2, ASB_ROT
    pz = terrain.sample(px, py)
    c_stone = srgb_hex_to_linear_rgba(HERO_PALETTE["stone_masonry"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_grass = srgb_hex_to_linear_rgba(HERO_PALETTE["lawn_green"])
    c_bronze = srgb_hex_to_linear_rgba(HERO_PALETTE["bronze_gold"])

    # Rounded end stone drums strictly capped in white coping (zero overlap with elevated turf bed)
    for side in (-1.0, 1.0):
        ex, ey = local_to_world_2d(px, py, side * 3.55, 0.0, rot)
        add_cylinder_vc(bm, col_layer, ex, ey, pz - 0.6, pz + 0.65, 1.34, 1.34, 10, c_stone, c_white)
        add_cylinder_vc(bm, col_layer, ex, ey, pz + 0.65, pz + 0.80, 1.44, 1.44, 10, c_white, c_white)

    add_box_vc(bm, col_layer, px, py, pz - 0.6, pz + 0.65, 3.55, 1.35, c_stone, c_white, rot_rad=rot)
    add_box_vc(bm, col_layer, px, py, pz + 0.65, pz + 0.82, 3.62, 1.46, c_white, c_white, rot_rad=rot)
    add_box_vc(bm, col_layer, px, py, pz + 0.82, pz + 0.98, 3.35, 1.06, c_grass, c_grass, rot_rad=rot)

    # Classical heritage lamp pole in center of the median planter
    add_box_vc(bm, col_layer, px, py, pz + 0.80, pz + 1.45, 0.42, 0.42, c_white, c_stone, rot_rad=rot)
    add_cylinder_vc(bm, col_layer, px, py, pz + 1.42, pz + 4.35, 0.14, 0.08, 8, c_bronze, c_bronze)
    add_cylinder_vc(bm, col_layer, px, py, pz + 4.35, pz + 4.85, 0.24, 0.12, 8, c_white, c_bronze)
