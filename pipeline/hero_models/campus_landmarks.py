"""Additional Amrita Coimbatore architectural hero landmarks: Main Gate, Library, Amriteshwari Hall, Shrine & Pool."""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_gabled_roof_vc,
    add_glass_panel,
    add_hipped_roof_vc,
    add_octagonal_dome_vc,
    add_tiered_vimana_roof,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# Main Entrance Gate coordinates straddling way/128964701 asphalt cleanly NORTH of railway level crossing (-55.4, -408.3)
MAIN_GATE_CX = -55.45
MAIN_GATE_CY = -398.5
MAIN_GATE_ROT = 0.01  # perpendicular to N-S entrance boulevard way/128964701


def append_central_library_hero(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_top: float,
) -> None:
    """Crown Central Library (way/380702790) with classical south rotunda dome, portico columns & roof monitors."""
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_gold = srgb_hex_to_linear_rgba(HERO_PALETTE["bronze_gold"])

    # 1. Classical entrance portico & octagonal domed rotunda at real OSM rounded bay (-158.0, 148.0)
    rx, ry, rrot = -158.0, 148.0, 0.08
    rz0 = terrain.sample(rx, ry) - 1.5
    for clx in (-4.8, -1.8, 1.8, 4.8):
        pwx, pwy = local_to_world_2d(rx, ry, clx, -4.6, rrot)
        add_cylinder_vc(
            bm, col_layer, pwx, pwy, rz0, z_top - 1.35,
            0.38, 0.34, 8, c_white, c_white, offset_xyz=offset_xyz,
        )
    add_octagonal_dome_vc(
        bm, col_layer, rx, ry + 1.8, z_top - 0.08,
        radius=6.8, drum_h=2.1, dome_h=3.4,
        drum_rgba=c_cream, dome_rgba=c_tile, gold_rgba=c_gold,
        win_lit_bm=win_lit_bm, segments=10, offset_xyz=offset_xyz,
    )

    # 2. Twin longitudinal daylight roof skylight monitors over East & West library wings
    for mx, my in ((-178.0, 195.0), (-145.0, 195.0)):
        add_box_vc(
            bm, col_layer, mx, my, z_top - 0.1, z_top + 1.25,
            5.8, 12.0, c_cream, c_white, rot_rad=rrot, offset_xyz=offset_xyz,
        )
        add_gabled_roof_vc(
            bm, col_layer, mx, my, z_top + 1.22, z_top + 2.85,
            6.2, 12.4, c_tile, c_white, rot_rad=rrot, ridge_along_x=False,
            soffit_rgba=c_white, offset_xyz=offset_xyz,
        )


def append_amriteshwari_hall_hero(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_eave: float,
    z_top: float,
) -> None:
    """Crown Amriteshwari Hall (way/380925370) with wide-span auditorium gable shell, acoustic lantern & foyer portico."""
    # Exact OSM footprint centroid & orientation: 46.5m x 21.2m @ 0.088 rad
    cx, cy, rot = 351.9, -246.0, 0.088
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_maroon = srgb_hex_to_linear_rgba(HERO_PALETTE["amrita_maroon"])

    # 1. Wide-span vaulted/gabled auditorium shell roof with bold white eave cornice
    add_box_vc(
        bm, col_layer, cx, cy, z_eave - 0.15, z_top + 0.18,
        23.4, 10.8, c_white, c_cream, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_gabled_roof_vc(
        bm, col_layer, cx, cy, z_top + 0.15, z_top + 4.1,
        23.8, 11.2, c_tile, c_white, rot_rad=rot, ridge_along_x=True,
        soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )
    # Central acoustic clerestory monitor strip running down the auditorium ridge
    add_box_vc(
        bm, col_layer, cx, cy, z_top + 2.6, z_top + 4.75,
        13.5, 3.0, c_cream, c_tile, rot_rad=rot, offset_xyz=offset_xyz,
    )
    add_glass_panel(win_lit_bm, cx, cy, z_top + 3.05, z_top + 4.35, 12.2, -3.08, rot_rad=rot, facing_south=True)
    add_glass_panel(win_lit_bm, cx, cy, z_top + 3.05, z_top + 4.35, 12.2, +3.08, rot_rad=rot, facing_south=False)

    # 2. West entrance foyer colonnade facing AB-1 courtyard
    fwx, fwy = local_to_world_2d(cx, cy, -24.4, 0.0, rot)
    fz0 = terrain.sample(fwx, fwy) - 1.5
    add_box_vc(
        bm, col_layer, fwx, fwy, z_plinth + 4.5, z_plinth + 5.2,
        2.2, 7.6, c_white, c_maroon, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    for col_ly in (-6.0, -2.0, 2.0, 6.0):
        cwx, cwy = local_to_world_2d(cx, cy, -25.8, col_ly, rot)
        add_cylinder_vc(
            bm, col_layer, cwx, cwy, fz0, z_plinth + 4.55,
            0.38, 0.34, 8, c_white, c_white, offset_xyz=offset_xyz,
        )


def append_shrine_hero(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_top: float,
) -> None:
    """Crown Campus Shrine (way/531394576) with South Indian mandapa porch, 2-tier Kerala vimana & golden kalasha."""
    # Exact OSM footprint: (44.4..60.9, -71.8..-62.3) -> 16.3m x 9.2m
    cx, cy = 52.6, -67.1
    cz0 = terrain.sample(cx, cy) - 1.5
    c_stone = srgb_hex_to_linear_rgba(HERO_PALETTE["stone_masonry"])
    c_plinth = srgb_hex_to_linear_rgba(HERO_PALETTE["sandstone_plinth"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_gold = srgb_hex_to_linear_rgba(HERO_PALETTE["bronze_gold"])

    # Stepped granite/sandstone adhishthana temple base around perimeter
    add_box_vc(
        bm, col_layer, cx, cy, cz0, z_plinth + 0.35,
        8.6, 5.1, c_stone, c_plinth, offset_xyz=offset_xyz,
    )

    # East Garbhagriha sanctum super-structure + 2-tiered pyramidal terracotta vimana & kalasha
    scx = cx + 3.4
    add_box_vc(
        bm, col_layer, scx, cy, z_plinth + 0.35, z_top + 0.4,
        4.3, 4.3, c_cream, c_white, offset_xyz=offset_xyz,
    )
    add_tiered_vimana_roof(
        bm, col_layer, scx, cy, z_top + 0.38,
        4.4, 4.4, c_tile, c_cream, c_gold, rot_rad=0.0, offset_xyz=offset_xyz,
    )

    # West pillared Mandapa entrance hall tucked flush into Garbhagriha west wall (zero gable gap)
    mcx = cx - 4.0
    for px_off in (-3.6, -1.2, 1.2):
        for py_off in (-3.6, 3.6):
            add_cylinder_vc(
                bm, col_layer, mcx + px_off, cy + py_off, z_plinth + 0.32, z_top + 0.1,
                0.28, 0.24, 8, c_white, c_white, offset_xyz=offset_xyz,
            )
    add_box_vc(
        bm, col_layer, mcx + 0.25, cy, z_top - 0.15, z_top + 0.25,
        4.75, 4.3, c_white, c_cream, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_gabled_roof_vc(
        bm, col_layer, mcx + 0.25, cy, z_top + 0.22, z_top + 2.35,
        5.05, 4.6, c_tile, c_white, ridge_along_x=True, soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )
    add_cylinder_vc(
        bm, col_layer, mcx - 0.2, cy, z_top + 2.25, z_top + 2.85,
        0.16, 0.03, 8, c_gold, c_gold, offset_xyz=offset_xyz,
    )


def append_main_gate_archway(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
) -> None:
    """Build the Grand Amrita Entrance Gate Archway straddling boulevard way/128964701 inside campus entry."""
    gx, gy, rot = MAIN_GATE_CX, MAIN_GATE_CY, MAIN_GATE_ROT
    gz = terrain.sample(gx, gy)
    z0 = gz - 2.0

    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_stone = srgb_hex_to_linear_rgba(HERO_PALETTE["sandstone_plinth"])
    c_maroon = srgb_hex_to_linear_rgba(HERO_PALETTE["amrita_maroon"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_gold = srgb_hex_to_linear_rgba(HERO_PALETTE["bronze_gold"])
    c_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])

    # Clear opening across 5.64m curbed road: towers centered at +-5.2m (inner clearance = 7.7m, height = 5.8m)
    z_clear = gz + 5.8
    for side in (-1.0, 1.0):
        # Tiered sandstone/cream pylon tower
        px, py = local_to_world_2d(gx, gy, side * 5.2, 0.0, rot)
        pz_base = terrain.sample(px, py) - 2.0
        add_box_vc(bm, col_layer, px, py, pz_base, gz + 1.2, 1.45, 1.65, c_stone, c_white, rot_rad=rot)
        add_box_vc(bm, col_layer, px, py, gz + 1.2, gz + 6.4, 1.25, 1.45, c_cream, c_white, rot_rad=rot)
        # Signature Amrita Maroon structural collar band
        add_box_vc(bm, col_layer, px, py, gz + 4.9, gz + 5.6, 1.33, 1.52, c_maroon, c_white, rot_rad=rot)
        # Crown cornice & hipped terracotta cap on each tower
        add_box_vc(bm, col_layer, px, py, gz + 6.4, gz + 7.5, 1.42, 1.62, c_white, c_white, rot_rad=rot)
        add_hipped_roof_vc(bm, col_layer, px, py, gz + 7.48, gz + 8.95, 1.65, 1.85, c_tile, rot_rad=rot)

        # Flanking security checkpoint guard kiosk & wing perimeter walls with stone pier caps
        kx, ky = local_to_world_2d(gx, gy, side * 8.4, -0.5, rot)
        add_box_vc(bm, col_layer, kx, ky, pz_base, gz + 3.0, 1.8, 1.5, c_cream, c_white, rot_rad=rot)
        add_hipped_roof_vc(bm, col_layer, kx, ky, gz + 2.98, gz + 4.15, 2.25, 1.95, c_tile, rot_rad=rot)

        wx, wy = local_to_world_2d(gx, gy, side * 12.2, 0.0, rot)
        add_box_vc(bm, col_layer, wx, wy, pz_base, gz + 1.65, 2.4, 0.45, c_stone, c_white, rot_rad=rot)
        ex, ey = local_to_world_2d(gx, gy, side * 14.8, 0.0, rot)
        add_box_vc(bm, col_layer, ex, ey, pz_base, gz + 2.35, 0.55, 0.55, c_cream, c_maroon, rot_rad=rot)

    # Overhead institutional Amrita Maroon & Cream arch portal lintel spanning +/- 6.0m
    add_box_vc(
        bm, col_layer, gx, gy, z_clear, z_clear + 1.75,
        5.9, 1.05, c_cream, c_white, rot_rad=rot, emit_bottom=True,
    )
    add_box_vc(
        bm, col_layer, gx, gy, z_clear + 0.35, z_clear + 1.38,
        5.2, 1.14, c_maroon, c_white, rot_rad=rot, emit_bottom=True,
    )
    # Centered white nameplate strip ("AMRITA VISHWA VIDYAPEETHAM") on south & north portal faces
    for sgn in (-1.0, 1.0):
        nx, ny = local_to_world_2d(gx, gy, 0.0, sgn * 1.18, rot)
        add_box_vc(bm, col_layer, nx, ny, z_clear + 0.55, z_clear + 1.18, 3.8, 0.06, c_white, c_white, rot_rad=rot)
        add_box_vc(bm, col_layer, nx, ny, z_clear + 0.72, z_clear + 0.98, 3.3, 0.08, c_dark, c_dark, rot_rad=rot)

    # Central pitched ceremonial portal crest & golden bronze medallion spire
    add_box_vc(
        bm, col_layer, gx, gy, z_clear + 1.72, z_clear + 2.45,
        2.1, 1.25, c_white, c_cream, rot_rad=rot,
    )
    add_hipped_roof_vc(
        bm, col_layer, gx, gy, z_clear + 2.42, z_clear + 3.65,
        2.35, 1.45, c_tile, rot_rad=rot, gable_rgba=c_gold,
    )
    # Keep unused z0 lint clean
    _ = z0


def append_pool_complex_hero(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
    pool_pts: list[tuple[float, float]],
    deck_flat_z: float | None,
    water_flat_z: float | None,
) -> None:
    """Build Pool-1-photo-accurate terracotta deck trim, toddler pool, starting blocks, bleachers & pool-house pavilion."""
    if len(pool_pts) < 4:
        return
    # Identify pool long/short axes cleanly
    edges = [(math.hypot(pool_pts[(i + 1) % 4][0] - pool_pts[i][0], pool_pts[(i + 1) % 4][1] - pool_pts[i][1]), i) for i in range(4)]
    edges.sort(reverse=True)
    i0 = edges[0][1]
    p0, p1 = pool_pts[i0], pool_pts[(i0 + 1) % 4]
    pcx = sum(p[0] for p in pool_pts) / 4.0
    pcy = sum(p[1] for p in pool_pts) / 4.0
    long_ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    # Normalize long axis so local +X runs approximately North (+Y) or East (+X) consistently
    if math.sin(long_ang) < 0:
        long_ang += math.pi
    ca, sa = math.cos(long_ang), math.sin(long_ang)  # along pool length (~North)
    px_perp, py_perp = sa, -ca  # across pool width (~East)

    z_deck = deck_flat_z if deck_flat_z is not None else terrain.sample(pcx, pcy) + 0.30
    z_water = water_flat_z if water_flat_z is not None else z_deck + 0.08

    c_red_deck = srgb_hex_to_linear_rgba(HERO_PALETTE["pool_deck_red"])
    c_ochre = srgb_hex_to_linear_rgba(HERO_PALETTE["pool_deck_ochre"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_toddler = srgb_hex_to_linear_rgba(HERO_PALETTE["pool_toddler_water"])
    c_blue = srgb_hex_to_linear_rgba(HERO_PALETTE["pool_starting_blue"])
    c_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_stair = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_portal"])

    # 1. Terracotta-maroon wet deck perimeter apron strips (z_deck + 0.08 > Draco quant step, zero overlap!)
    half_len = edges[0][0] * 0.5
    half_wid = edges[-1][0] * 0.5
    for side in (-1.0, 1.0):
        # East & West long wet-deck aprons fit strictly between North & South aprons (no corner coplanar z-fight)
        wx, wy = pcx + side * px_perp * (half_wid + 2.3), pcy + side * py_perp * (half_wid + 2.3)
        add_box_vc(bm, col_layer, wx, wy, z_deck - 0.08, z_deck + 0.08, half_len - 0.08, 2.2, c_red_deck, c_red_deck, rot_rad=long_ang)

    # North wet-deck end apron
    nax, nay = pcx + ca * (half_len + 2.65), pcy + sa * (half_len + 2.65)
    add_box_vc(bm, col_layer, nax, nay, z_deck - 0.08, z_deck + 0.08, 2.55, half_wid + 4.5, c_red_deck, c_red_deck, rot_rad=long_ang)

    # South wet-deck apron partitioned into strictly non-overlapping alternating red + ochre runner strips (no XY overlap!)
    sax, say = pcx - ca * (half_len + 2.65), pcy - sa * (half_len + 2.65)
    apron_hw = half_wid + 4.5
    south_strips = [
        (-apron_hw, -6.75, c_red_deck),
        (-6.75, -4.05, c_ochre),
        (-4.05, -1.35, c_red_deck),
        (-1.35, 1.35, c_ochre),
        (1.35, 4.05, c_red_deck),
        (4.05, 6.75, c_ochre),
        (6.75, apron_hw, c_red_deck),
    ]
    for s0, s1, strip_col in south_strips:
        smid = 0.5 * (s0 + s1)
        shw = max(0.2, 0.5 * (s1 - s0) - 0.015)
        sx = sax + px_perp * smid
        sy = say + py_perp * smid
        add_box_vc(bm, col_layer, sx, sy, z_deck - 0.08, z_deck + 0.08, 2.55, shw, strip_col, strip_col, rot_rad=long_ang)

    # 2. Toddler / Warm-up Pool cleanly on wide south-east pool deck apron (-173.5, 371.5), non-overlapping curb bars + water
    t_cx = pcx - ca * (half_len + 8.4) + px_perp * 6.2
    t_cy = pcy - sa * (half_len + 8.4) + py_perp * 6.2
    add_box_vc(bm, col_layer, t_cx, t_cy, z_deck - 0.02, z_deck + 0.14, 2.74, 4.84, c_toddler, c_toddler, rot_rad=long_ang)
    for end_sign in (-1.0, 1.0):
        cx_bar = t_cx + end_sign * ca * 3.025
        cy_bar = t_cy + end_sign * sa * 3.025
        add_box_vc(bm, col_layer, cx_bar, cy_bar, z_deck - 0.02, z_deck + 0.26, 0.27, 5.4, c_white, c_white, rot_rad=long_ang)
    for side_sign in (-1.0, 1.0):
        cx_bar = t_cx + side_sign * px_perp * 5.125
        cy_bar = t_cy + side_sign * py_perp * 5.125
        add_box_vc(bm, col_layer, cx_bar, cy_bar, z_deck - 0.02, z_deck + 0.26, 2.74, 0.27, c_white, c_white, rot_rad=long_ang)

    # 3. 14 Blue-topped competition starting blocks (7 lanes at North wall + 7 at South wall)
    for end_s in (-1.0, 1.0):
        for lane in range(-3, 4):
            off = lane * 2.85
            bx = pcx + end_s * ca * (half_len + 0.65) + px_perp * off
            by = pcy + end_s * sa * (half_len + 0.65) + py_perp * off
            add_box_vc(bm, col_layer, bx, by, z_water + 0.02, z_water + 0.56, 0.36, 0.34, c_white, c_blue, rot_rad=long_ang)

    # 4. East & West 3-tier white spectator pool bleachers with terracotta stairways (inside HERO_POOL_DECK_ID)
    for side in (-1.0, 1.0):
        dist = half_wid + 6.4
        bx = pcx + side * px_perp * dist
        by = pcy + side * py_perp * dist
        for tier in range(3):
            tx = bx + side * px_perp * (tier * 0.85)
            ty = by + side * py_perp * (tier * 0.85)
            add_box_vc(
                bm, col_layer, tx, ty, z_deck - 0.2, z_deck + 0.45 + tier * 0.45,
                21.0, 0.46, c_white, c_white, rot_rad=long_ang,
            )
        # Central red stair aisle on each side bleacher
        for tier in range(3):
            sx = bx + side * px_perp * (tier * 0.85)
            sy = by + side * py_perp * (tier * 0.85)
            add_box_vc(
                bm, col_layer, sx, sy, z_deck - 0.2, z_deck + 0.49 + tier * 0.45,
                1.1, 0.48, c_stair, c_stair, rot_rad=long_ang,
            )

    # 5. Pool-House Changing Pavilion along wide North deck apron (white walls + overhanging terracotta gable roof)
    pav_cx = pcx + ca * (half_len + 13.5)
    pav_cy = pcy + sa * (half_len + 13.5)
    add_box_vc(bm, col_layer, pav_cx, pav_cy, z_deck - 0.2, z_deck + 3.4, 3.2, 19.5, c_cream, c_white, rot_rad=long_ang)
    add_box_vc(
        bm, col_layer, pav_cx - ca * 3.5, pav_cy - sa * 3.5, z_deck + 2.95, z_deck + 3.35,
        1.1, 19.8, c_white, c_tile, rot_rad=long_ang, emit_bottom=True,
    )
    add_gabled_roof_vc(
        bm, col_layer, pav_cx, pav_cy, z_deck + 3.35, z_deck + 5.15,
        4.4, 20.3, c_tile, c_white, rot_rad=long_ang, ridge_along_x=False, soffit_rgba=c_white,
    )
    for px_off in (-14.0, -7.0, 0.0, 7.0, 14.0):
        cx_p = pav_cx - ca * 4.2 + px_perp * px_off
        cy_p = pav_cy - sa * 4.2 + py_perp * px_off
        add_box_vc(bm, col_layer, cx_p, cy_p, z_deck - 0.1, z_deck + 3.0, 0.22, 0.22, c_dark, c_white, rot_rad=long_ang)
