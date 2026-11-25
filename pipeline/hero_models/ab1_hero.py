"""Academic Block 1 (AB-1) Main Block 3-tier pavilion, solar arrays, scalloped front plaza, white lotus fountain & parking lot."""

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
    add_quad_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# Exact OSM south portico center & alignment from way/380925364: (235.4,-287.9)->(251.2,-286.7)
AB1_PORTICO_CX = 243.3
AB1_PORTICO_CY = -282.8
AB1_PORTICO_ROT = 0.0758  # ~4.3 deg

# Properly centered inside wide scalloped asphalt plaza with clear driving clearance to porte-cochere
AB1_FOUNTAIN_CX = 246.0
AB1_FOUNTAIN_CY = -309.5

# Terrain-hugging paved parking lot west of AB-1 NW wing (replacing 2 stray Overture sheds)
AB1_PARKING_CX = 184.5
AB1_PARKING_CY = -210.5
AB1_PARKING_HX = 15.0
AB1_PARKING_HY = 17.5
AB1_PARKING_ROT = 0.082  # +4.7 deg parallel to Ettimadai Road


def normalize_ab1_footprint_rings(
    outer_ring: list[tuple[float, float]],
) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]]]:
    """Add AB-1's two open internal triangular courtyard holes flanking the central north-south spine."""
    west_ccw = [(213.5, -251.5), (233.5, -264.0), (232.0, -231.5)]
    east_ccw = [(251.0, -263.5), (271.0, -246.5), (250.5, -230.0)]
    return ([outer_ring, list(reversed(west_ccw)), list(reversed(east_ccw))], [west_ccw, east_ccw])


def get_ab1_plaza_ring() -> list[tuple[float, float]]:
    """Return CCW polygon for AB-1's flared/scalloped dark asphalt front plaza + straight south entry road."""
    return [
        (244.5, -367.5),
        (253.5, -367.0),
        (253.5, -327.0),
        (260.0, -322.5),
        (266.8, -321.5),
        (272.2, -315.5),
        (273.0, -308.0),
        (268.0, -302.0),
        (263.5, -295.0),
        (263.5, -287.5),
        (266.5, -281.5),
        (256.0, -280.5),
        (243.3, -281.5),
        (229.0, -282.5),
        (219.5, -284.0),
        (223.5, -290.5),
        (225.2, -298.0),
        (224.0, -303.5),
        (218.0, -308.0),
        (217.5, -315.0),
        (224.0, -322.5),
        (233.0, -323.5),
        (241.5, -327.0),
    ]


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
    """Append IRL-accurate 3-tier AB-1 entrance pavilion & rooftop solar arrays."""
    cx, cy, rot = AB1_PORTICO_CX, AB1_PORTICO_CY, AB1_PORTICO_ROT
    pz0 = terrain.sample(cx, cy) - 2.4
    hero_h = max(8.0, z_eave - z_plinth)

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_roof_sand = srgb_hex_to_linear_rgba("#CFB396")
    c_col_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_recess = srgb_hex_to_linear_rgba(HERO_PALETTE["recess_shadow"])
    c_portico_slab = srgb_hex_to_linear_rgba("#6A6861")
    c_solar = srgb_hex_to_linear_rgba("#2A3542")
    c_solar_frame = srgb_hex_to_linear_rgba("#7E8790")
    c_terracotta_trim = srgb_hex_to_linear_rgba("#C27856")

    # a) Wide pale sandy-terracotta hipped roof + front white triangular gable pediment
    roof_wx, roof_wy = local_to_world_2d(cx, cy, 0.0, -1.6, rot)
    add_box_vc(
        bm, col_layer, roof_wx, roof_wy, z_top - 0.30, z_top + 0.08,
        10.4, 7.2, c_white, c_white, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_hipped_roof_vc(
        bm, col_layer, roof_wx, roof_wy, z_top + 0.06, z_top + 4.45,
        10.8, 7.6, c_roof_sand, rot_rad=rot, gable_rgba=c_white, soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )

    # b) Twin paired full-height white square corner pilasters/columns & wing piers
    for side in (-1.0, 1.0):
        wing_wx, wing_wy = local_to_world_2d(cx, cy, side * 8.9, -2.2, rot)
        add_box_vc(
            bm, col_layer, wing_wx, wing_wy, pz0, z_top + 0.06,
            0.85, 3.6, c_cream, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
        for p_off in (8.2, 9.3):
            px_w, py_w = local_to_world_2d(cx, cy, side * p_off, -5.8, rot)
            add_box_vc(
                bm, col_layer, px_w, py_w, pz0, z_top + 0.06,
                0.48, 0.48, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
            )
            for frac in (0.30, 0.52, 0.75):
                mz = z_plinth + hero_h * frac
                add_box_vc(
                    bm, col_layer, px_w, py_w, mz - 0.14, mz + 0.14,
                    0.56, 0.56, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
                )

    # c) Top floor (Floor 4): wide recessed multi-pane dark glass window wall directly beneath hipped roof
    z_pan0 = z_plinth + hero_h * 0.76
    z_pan1 = z_eave - 0.12
    gwall_wx, gwall_wy = local_to_world_2d(cx, cy, 0.0, -5.8, rot)
    add_box_vc(
        bm, col_layer, gwall_wx, gwall_wy, z_pan0, z_pan1,
        6.9, 0.25, c_recess, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    for bay in range(-3, 3):
        bay_cx_local = (bay + 0.5) * 2.2
        bw_x, bw_y = local_to_world_2d(cx, cy, bay_cx_local, 0.0, rot)
        add_glass_panel(win_lit_bm, bw_x, bw_y, z_pan0 + 0.08, z_pan1 - 0.08, 0.96, -6.08, rot_rad=rot, facing_south=True)
    for mx in (-4.4, -2.2, 0.0, 2.2, 4.4):
        mw_x, mw_y = local_to_world_2d(cx, cy, mx, -6.02, rot)
        add_box_vc(
            bm, col_layer, mw_x, mw_y, z_pan0, z_pan1,
            0.11, 0.14, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
    trans_wx, trans_wy = local_to_world_2d(cx, cy, 0.0, -6.02, rot)
    z_mid_pan = 0.5 * (z_pan0 + z_pan1)
    add_box_vc(
        bm, col_layer, trans_wx, trans_wy, z_mid_pan - 0.09, z_mid_pan + 0.09,
        6.85, 0.14, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )

    # d) Middle floors (Floors 2 & 3): two recessed white balcony/veranda levels + centered dark window panel
    rec_wx, rec_wy = local_to_world_2d(cx, cy, 0.0, -3.5, rot)
    add_box_vc(
        bm, col_layer, rec_wx, rec_wy, z_plinth + hero_h * 0.26, z_eave - 0.05,
        7.2, 1.5, c_recess, c_cream, rot_rad=rot, offset_xyz=offset_xyz,
    )
    for frac in (0.50, 0.75):
        tz = z_plinth + hero_h * frac
        bal_wx, bal_wy = local_to_world_2d(cx, cy, 0.0, -4.6, rot)
        add_box_vc(
            bm, col_layer, bal_wx, bal_wy, tz - 0.34, tz,
            7.4, 2.2, c_white, c_white, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
        )
        rail_wx, rail_wy = local_to_world_2d(cx, cy, 0.0, -6.68, rot)
        add_box_vc(
            bm, col_layer, rail_wx, rail_wy, tz, tz + 0.42,
            7.35, 0.12, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
    for bcol_x in (-6.6, -4.6, 4.6, 6.6):
        bc_wx, bc_wy = local_to_world_2d(cx, cy, bcol_x, -6.5, rot)
        add_box_vc(
            bm, col_layer, bc_wx, bc_wy, z_plinth + hero_h * 0.34, z_pan0,
            0.22, 0.22, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
        )
    # White center wall core with centered framed dark window panel on Floor 3
    midwall_wx, midwall_wy = local_to_world_2d(cx, cy, 0.0, -5.6, rot)
    add_box_vc(
        bm, col_layer, midwall_wx, midwall_wy, z_plinth + hero_h * 0.34, z_pan0,
        3.6, 0.28, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    f3_z0 = z_plinth + hero_h * 0.56
    f3_z1 = z_plinth + hero_h * 0.70
    add_glass_panel(win_dark_bm, midwall_wx, midwall_wy, f3_z0, f3_z1, 2.1, -0.32, rot_rad=rot, facing_south=True)

    # e) Ground Porte-Cochere: projecting flat-roofed drive-under portico with dark pillars & white fascia
    p_wx, p_wy = local_to_world_2d(cx, cy, 0.0, -7.8, rot)
    z_can0 = z_plinth + hero_h * 0.25
    z_can1 = z_plinth + hero_h * 0.34
    add_box_vc(
        bm, col_layer, p_wx, p_wy, z_can0, z_can1,
        7.4, 3.2, c_white, c_portico_slab, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    # Nameplate accent centered cleanly on white fascia front
    sign_wx, sign_wy = local_to_world_2d(cx, cy, 0.0, -11.06, rot)
    add_box_vc(
        bm, col_layer, sign_wx, sign_wy, z_can0 + 0.14, z_can1 - 0.14,
        3.6, 0.08, c_col_dark, c_white, rot_rad=rot, offset_xyz=offset_xyz,
    )
    # Paired dark charcoal square pillars on front corners + rear piers (wide clear drive-through middle!)
    for plx, ply in ((-6.5, -10.3), (-5.5, -10.3), (5.5, -10.3), (6.5, -10.3), (-6.5, -5.6), (6.5, -5.6)):
        col_wx, col_wy = local_to_world_2d(cx, cy, plx, ply, rot)
        col_g = terrain.sample(col_wx, col_wy)
        add_box_vc(
            bm, col_layer, col_wx, col_wy, col_g - 1.5, z_can0 + 0.04,
            0.36, 0.36, c_col_dark, c_col_dark, rot_rad=rot, offset_xyz=offset_xyz,
        )
    # Low planter box strip along inner back step
    step_wx, step_wy = local_to_world_2d(cx, cy, 0.0, -5.2, rot)
    step_g = terrain.sample(step_wx, step_wy)
    add_box_vc(
        bm, col_layer, step_wx, step_wy, step_g - 1.2, step_g + 0.42,
        4.6, 0.55, c_terracotta_trim, c_terracotta_trim, rot_rad=rot, offset_xyz=offset_xyz,
    )

    # f) 9 Neat Solar Panel Array Strips across flat wing roofs & central spine
    solar_arrays = (
        (241.5, -246.5, 4.8, 17.5, 0.08),
        (186.5, -254.0, 9.5, 4.2, 0.11),
        (294.5, -244.0, 9.2, 4.2, 0.12),
        (214.0, -235.0, 11.5, 3.6, 0.89),
        (214.0, -265.0, 10.5, 3.4, -0.71),
        (266.0, -231.0, 11.5, 3.6, -0.68),
        (268.0, -261.0, 10.5, 3.4, 0.89),
        (221.0, -214.0, 8.5, 3.4, -0.71),
        (252.5, -212.0, 8.5, 3.4, 0.88),
    )
    for sx, sy, shx, shy, srot in solar_arrays:
        if shy > shx:
            row_hx = max(1.0, 0.5 * shx - 0.35)
            for row_s in (-1.0, 1.0):
                rx, ry = local_to_world_2d(sx, sy, row_s * (row_hx + 0.35), 0.0, srot)
                add_box_vc(
                    bm, col_layer, rx, ry, z_top - 0.05, z_top + 0.18,
                    row_hx, shy, c_solar_frame, c_solar, rot_rad=srot, offset_xyz=offset_xyz,
                )
        else:
            row_hy = max(1.0, 0.5 * shy - 0.35)
            for row_s in (-1.0, 1.0):
                rx, ry = local_to_world_2d(sx, sy, 0.0, row_s * (row_hy + 0.35), srot)
                add_box_vc(
                    bm, col_layer, rx, ry, z_top - 0.05, z_top + 0.18,
                    shx, row_hy, c_solar_frame, c_solar, rot_rad=srot, offset_xyz=offset_xyz,
                )


def append_ab1_fountain_plaza(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
) -> None:
    """Build AB-1's curved garden flowerbeds, white lane guide dashes, and sculptural white Lotus Fountain."""
    fx, fy = AB1_FOUNTAIN_CX, AB1_FOUNTAIN_CY

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_terracotta = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_water = srgb_hex_to_linear_rgba("#1C4B52")
    c_hedge = srgb_hex_to_linear_rgba("#387833")
    c_garden = srgb_hex_to_linear_rgba("#3F7F38")
    c_curb_stone = srgb_hex_to_linear_rgba("#DCD6CA")
    c_shrub = srgb_hex_to_linear_rgba("#2F6A2D")
    c_flowers = (
        srgb_hex_to_linear_rgba("#D64B8A"),
        srgb_hex_to_linear_rgba("#E8B93A"),
        srgb_hex_to_linear_rgba("#E86F9A"),
        c_shrub,
    )

    def _emit_border_strip(
        p0: tuple[float, float],
        n0: tuple[float, float],
        p1: tuple[float, float],
        n1: tuple[float, float],
        off0: float,
        off1: float,
        z_off: float,
        rgba: tuple[float, float, float, float],
    ) -> None:
        a0 = (p0[0] + n0[0] * off0, p0[1] + n0[1] * off0)
        b0 = (p0[0] + n0[0] * off1, p0[1] + n0[1] * off1)
        a1 = (p1[0] + n1[0] * off0, p1[1] + n1[1] * off0)
        b1 = (p1[0] + n1[0] * off1, p1[1] + n1[1] * off1)
        va0 = bm.verts.new((a0[0], a0[1], terrain.sample(a0[0], a0[1]) + z_off))
        vb0 = bm.verts.new((b0[0], b0[1], terrain.sample(b0[0], b0[1]) + z_off))
        va1 = bm.verts.new((a1[0], a1[1], terrain.sample(a1[0], a1[1]) + z_off))
        vb1 = bm.verts.new((b1[0], b1[1], terrain.sample(b1[0], b1[1]) + z_off))
        cross = (b0[0] - a0[0]) * (b1[1] - a0[1]) - (b0[1] - a0[1]) * (b1[0] - a0[0])
        if cross >= 0.0:
            add_quad_vc(bm, col_layer, va0, vb0, vb1, va1, rgba)
        else:
            add_quad_vc(bm, col_layer, va0, va1, vb1, vb0, rgba)

    def _build_flower_border(pts: list[tuple[float, float]], outward_sign: float, seed_base: int) -> None:
        n = len(pts)
        seg_norms: list[tuple[float, float]] = []
        for i in range(n - 1):
            dx = pts[i + 1][0] - pts[i][0]
            dy = pts[i + 1][1] - pts[i][1]
            d = max(1e-5, math.hypot(dx, dy))
            seg_norms.append((outward_sign * dy / d, outward_sign * (-dx) / d))
        v_norms: list[tuple[float, float]] = []
        for i in range(n):
            if i == 0:
                nx, ny = seg_norms[0]
            elif i == n - 1:
                nx, ny = seg_norms[-1]
            else:
                nx = seg_norms[i - 1][0] + seg_norms[i][0]
                ny = seg_norms[i - 1][1] + seg_norms[i][1]
            nl = max(1e-5, math.hypot(nx, ny))
            v_norms.append((nx / nl, ny / nl))

        for i in range(n - 1):
            _emit_border_strip(pts[i], v_norms[i], pts[i + 1], v_norms[i + 1], 0.0, 0.25, 0.275, c_curb_stone)
            _emit_border_strip(pts[i], v_norms[i], pts[i + 1], v_norms[i + 1], 0.22, 2.05, 0.255, c_garden)

            ax, ay = pts[i]
            bx, by = pts[i + 1]
            if max(ay, by) < -330.0:
                continue
            seg_len = math.hypot(bx - ax, by - ay)
            steps = max(1, int(seg_len // 3.0))
            for k in range(steps):
                t = (k + 0.5) / steps
                mx = ax + (bx - ax) * t
                my = ay + (by - ay) * t
                nx = v_norms[i][0] * (1.0 - t) + v_norms[i + 1][0] * t
                ny = v_norms[i][1] * (1.0 - t) + v_norms[i + 1][1] * t
                nl = max(1e-5, math.hypot(nx, ny))
                off = 1.05 + 0.35 * ((i + k) % 2)
                fx_c = mx + (nx / nl) * off
                fy_c = my + (ny / nl) * off
                fz_c = terrain.sample(fx_c, fy_c) + 0.18
                f_col = c_flowers[(seed_base + i * 3 + k) % len(c_flowers)]
                add_box_vc(bm, col_layer, fx_c, fy_c, fz_c, fz_c + 0.28, 0.28, 0.28, f_col, f_col)

    # 1. Curved garden flowerbed borders + low-poly flower clusters flanking both sides of the plaza
    west_edge = [
        (219.5, -284.0), (223.5, -290.5), (225.2, -298.0), (224.0, -303.5),
        (218.0, -308.0), (217.5, -315.0), (224.0, -322.5), (233.0, -323.5),
        (241.5, -327.0), (244.0, -363.5),
    ]
    east_edge = [
        (254.0, -363.5), (253.5, -327.0), (260.0, -322.5), (266.8, -321.5),
        (272.2, -315.5), (273.0, -308.0), (268.0, -302.0), (263.5, -295.0),
        (263.5, -287.5), (266.5, -281.5),
    ]
    _build_flower_border(west_edge, outward_sign=-1.0, seed_base=1)
    _build_flower_border(east_edge, outward_sign=-1.0, seed_base=5)

    # 2. Crisp dashed white lane guide markings along straight entry road & curved roundabout
    def _emit_dash(dcx: float, dcy: float, hl: float, hw: float, drot: float) -> None:
        ca, sa = math.cos(drot), math.sin(drot)
        pts = [(dcx + lx * ca - ly * sa, dcy + lx * sa + ly * ca) for lx, ly in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]
        vs = [bm.verts.new((px, py, terrain.sample(px, py) + 0.27)) for px, py in pts]
        add_quad_vc(bm, col_layer, vs[0], vs[1], vs[2], vs[3], c_white)

    entry_ang = math.atan2(37.0, -1.5)
    for k in range(6):
        t = k / 5.0
        dx_c = 249.0 * (1.0 - t) + 247.5 * t
        dy_c = -362.0 * (1.0 - t) + -326.5 * t
        _emit_dash(dx_c, dy_c, 1.3, 0.13, entry_ang)

    for k in range(18):
        ang = (2.0 * math.pi * k) / 18.0
        mx = fx + 13.4 * math.cos(ang)
        my = fy + 13.4 * math.sin(ang)
        _emit_dash(mx, my, 1.05, 0.12, ang + 0.5 * math.pi)

    for side in (-1.0, 1.0):
        for step_y in (-298.0, -293.0):
            _emit_dash(fx + side * 12.2, step_y, 1.05, 0.12, 0.5 * math.pi + side * 0.12)

    # 3. Centered multi-tiered sculptural white Lotus Fountain
    rim_zs = [terrain.sample(fx, fy)]
    for i in range(12):
        ang = (2.0 * math.pi * i) / 12.0
        rim_zs.append(terrain.sample(fx + 8.45 * math.cos(ang), fy + 8.45 * math.sin(ang)))
    fz = max(rim_zs) + 0.14
    fz_bot = min(rim_zs) - 1.8

    segs = 24
    r_in, r_out = 7.45, 8.45
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs
        a1 = (2.0 * math.pi * (i + 1)) / segs
        p_in0 = (fx + r_in * math.cos(a0), fy + r_in * math.sin(a0))
        p_in1 = (fx + r_in * math.cos(a1), fy + r_in * math.sin(a1))
        p_ou0 = (fx + r_out * math.cos(a0), fy + r_out * math.sin(a0))
        p_ou1 = (fx + r_out * math.cos(a1), fy + r_out * math.sin(a1))
        vi0, vi1 = bm.verts.new((p_in0[0], p_in0[1], fz_bot)), bm.verts.new((p_in1[0], p_in1[1], fz_bot))
        vo0, vo1 = bm.verts.new((p_ou0[0], p_ou0[1], fz_bot)), bm.verts.new((p_ou1[0], p_ou1[1], fz_bot))
        ti0, ti1 = bm.verts.new((p_in0[0], p_in0[1], fz + 0.72)), bm.verts.new((p_in1[0], p_in1[1], fz + 0.72))
        to0, to1 = bm.verts.new((p_ou0[0], p_ou0[1], fz + 0.72)), bm.verts.new((p_ou1[0], p_ou1[1], fz + 0.72))
        add_quad_vc(bm, col_layer, vo0, vo1, to1, to0, c_white)
        add_quad_vc(bm, col_layer, vi1, vi0, ti0, ti1, c_white)
        add_quad_vc(bm, col_layer, to0, to1, ti1, ti0, c_white)

    # Inner circular trimmed dark-green hedge ring + calm deep water basin
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs
        a1 = (2.0 * math.pi * (i + 1)) / segs
        p_in0 = (fx + 6.20 * math.cos(a0), fy + 6.20 * math.sin(a0))
        p_in1 = (fx + 6.20 * math.cos(a1), fy + 6.20 * math.sin(a1))
        p_ou0 = (fx + 7.48 * math.cos(a0), fy + 7.48 * math.sin(a0))
        p_ou1 = (fx + 7.48 * math.cos(a1), fy + 7.48 * math.sin(a1))
        vi0, vi1 = bm.verts.new((p_in0[0], p_in0[1], fz + 0.35)), bm.verts.new((p_in1[0], p_in1[1], fz + 0.35))
        ti0, ti1 = bm.verts.new((p_in0[0], p_in0[1], fz + 0.66)), bm.verts.new((p_in1[0], p_in1[1], fz + 0.66))
        to0, to1 = bm.verts.new((p_ou0[0], p_ou0[1], fz + 0.66)), bm.verts.new((p_ou1[0], p_ou1[1], fz + 0.66))
        add_quad_vc(bm, col_layer, vi1, vi0, ti0, ti1, c_hedge)
        add_quad_vc(bm, col_layer, to0, to1, ti1, ti0, c_hedge)

    add_cylinder_vc(bm, col_layer, fx, fy, fz - 0.5, fz + 0.48, 6.25, 6.25, 24, c_water, c_water)

    # 24 tiny terracotta planter dots spaced around white concrete fountain wall
    for i in range(24):
        ang = (2.0 * math.pi * i) / 24.0
        bx = fx + 7.95 * math.cos(ang)
        by = fy + 7.95 * math.sin(ang)
        add_cylinder_vc(bm, col_layer, bx, by, fz + 0.68, fz + 0.96, 0.22, 0.19, 6, c_terracotta, c_hedge)

    # Multi-tiered white sculptural lotus centerpiece (strictly sculptural white, NO orange cone)
    add_cylinder_vc(bm, col_layer, fx, fy, fz - 0.3, fz + 0.90, 2.60, 2.20, 12, c_white, c_white)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 0.90, fz + 1.65, 1.60, 2.75, 12, c_white, c_water)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 1.65, fz + 2.65, 1.15, 1.95, 12, c_white, c_white)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 2.65, fz + 3.55, 0.95, 0.55, 10, c_white, c_white)
    add_cylinder_vc(bm, col_layer, fx, fy, fz + 3.55, fz + 4.35, 0.42, 0.28, 10, c_white, c_white)


def append_ab1_parking_lot(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
) -> None:
    """Build terrain-hugging AB-1 west parking lot with asphalt deck, perimeter curbs, driveway & painted bays."""
    cx, cy = AB1_PARKING_CX, AB1_PARKING_CY
    hx, hy, rot = AB1_PARKING_HX, AB1_PARKING_HY, AB1_PARKING_ROT

    c_asphalt = srgb_hex_to_linear_rgba("#6E757E")
    c_curb = srgb_hex_to_linear_rgba("#D8D2C6")
    c_line = srgb_hex_to_linear_rgba("#F4F2EC")

    def _draped_grid(
        lx0: float,
        ly0: float,
        lx1: float,
        ly1: float,
        z_off: float,
        rgba: tuple[float, float, float, float],
        nx: int = 1,
        ny: int = 1,
    ) -> None:
        verts: list[list[bmesh.types.BMVert]] = []
        for iy in range(ny + 1):
            ly = ly0 + (ly1 - ly0) * (iy / ny)
            row: list[bmesh.types.BMVert] = []
            for ix in range(nx + 1):
                lx = lx0 + (lx1 - lx0) * (ix / nx)
                wx, wy = local_to_world_2d(cx, cy, lx, ly, rot)
                row.append(bm.verts.new((wx, wy, terrain.sample(wx, wy) + z_off)))
            verts.append(row)
        for iy in range(ny):
            for ix in range(nx):
                add_quad_vc(
                    bm,
                    col_layer,
                    verts[iy][ix],
                    verts[iy][ix + 1],
                    verts[iy + 1][ix + 1],
                    verts[iy + 1][ix],
                    rgba,
                )

    # 1. Sloped asphalt parking deck + West driveway apron connecting smoothly to Ettimadai Road
    _draped_grid(-hx, -hy, hx, hy, 0.16, c_asphalt, nx=6, ny=6)
    _draped_grid(-hx - 5.5, -5.0, -hx + 0.3, 5.0, 0.15, c_asphalt, nx=2, ny=2)

    # 2. Concrete perimeter curb border with 10m driveway entrance gap along West edge
    curb_w = 0.55
    _draped_grid(-hx, hy - curb_w, hx, hy, 0.24, c_curb, nx=6, ny=1)
    _draped_grid(-hx, -hy, hx, -hy + curb_w, 0.24, c_curb, nx=6, ny=1)
    _draped_grid(hx - curb_w, -hy, hx, hy, 0.24, c_curb, nx=1, ny=6)
    _draped_grid(-hx, -hy, -hx + curb_w, -5.0, 0.24, c_curb, nx=1, ny=3)
    _draped_grid(-hx, 5.0, -hx + curb_w, hy, 0.24, c_curb, nx=1, ny=3)

    # 3. Painted white bay lines (West row with driveway gap + East row) & center aisle dashes
    _draped_grid(-13.71, -hy + 1.2, -13.49, -5.2, 0.21, c_line, nx=1, ny=3)
    _draped_grid(-13.71, 5.2, -13.49, hy - 1.2, 0.21, c_line, nx=1, ny=3)
    _draped_grid(13.49, -hy + 1.2, 13.71, hy - 1.2, 0.21, c_line, nx=1, ny=6)

    for bi in range(10):
        ly_line = -15.3 + bi * 3.4
        _draped_grid(7.2, ly_line - 0.11, 13.6, ly_line + 0.11, 0.21, c_line, nx=2, ny=1)
        if abs(ly_line) > 5.2:
            _draped_grid(-13.6, ly_line - 0.11, -7.2, ly_line + 0.11, 0.21, c_line, nx=2, ny=1)

    for di in range(-2, 3):
        yc = di * 6.2
        _draped_grid(-0.11, yc - 1.3, 0.11, yc + 1.3, 0.21, c_line, nx=1, ny=1)
