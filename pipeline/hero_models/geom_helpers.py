"""Shared low-poly bmesh geometry & Amrita architectural palette helpers."""

from __future__ import annotations

import math
from typing import Any

import bmesh

# Photo-verified Amrita Vishwa Vidyapeetham, Coimbatore architectural colors (sRGB hex)
HERO_PALETTE: dict[str, str] = {
    "stucco_cream": "#F2ECE0",
    "stucco_white": "#F6F4EE",
    "sandstone_plinth": "#D6CAB8",
    "stone_masonry": "#9B8D7B",
    "ab1_tile_roof": "#C77456",
    "terracotta_tile": "#B54E34",
    "terracotta_portal": "#C9603B",
    "ab3_brick": "#A54E37",
    "asb_slate_tile": "#727B85",
    "amrita_maroon": "#8E1B3E",
    "portico_dark": "#343940",
    "recess_shadow": "#242A32",
    "bronze_gold": "#D4A13E",
    "fountain_water": "#1F7482",
    "pool_deck_red": "#9E3743",
    "pool_deck_ochre": "#D48863",
    "pool_toddler_water": "#6EE0EE",
    "pool_starting_blue": "#2274A5",
    "solar_panel": "#1E3A5F",
    "lawn_green": "#56A14A",
    "bleacher_white": "#F2F0EA",
    "charcoal_wall": "#3D4249",
    # AB-3 East front (photo-matched): cream stucco, bright orange eaves/pilasters, rust panels, blue curtain glass
    "ab3_cream": "#F5EFE3",
    "ab3_orange": "#EA8540",
    "ab3_rust_panel": "#CC5A33",
    "ab3_glass_blue": "#5E87B8",
    "ab3_garden_stone": "#A69886",
    "ab3_hedge_green": "#3F8A3A",
    "ab3_roof_tile": "#D9774A",
    "ab3_baluster_shadow": "#B9B3A8",
    # AB-2 & Central Library (sampled from Google Maps ground photos and satellite views)
    "ab2_salmon": "#CF7A55",
    "roof_concrete": "#8D8984",
    "verandah_shadow": "#4A3A33",
    "timber_post": "#3B2E28",
    "walkway_red": "#A8553F",
    "channel_water": "#2F5F66",
    "skylight_vault": "#DCE3E4",
    "skylight_glass": "#6F7C80",
    "library_tile": "#D2866A",
    "ab2_tile": "#CC7F5E",
    "porch_tile": "#C98E76",
    "path_stone": "#CDBFAE",
    "sign_red": "#B4252C",
    "granite_dark": "#55585C",
    "granite_light": "#8B8D8F",
    "bronze_patina": "#2F5C52",
    # IT Canteen (Google Maps photos)
    "canteen_wall": "#EEE9DA",
    "canteen_tile": "#C4705A",
    "rock_brown": "#5E554B",
    "table_red": "#B4533E",
    # Courtyard hostel (Google satellite)
    "hostel_white": "#EDEAE1",
    "hostel_roof": "#E2DDD0",
    "hostel_trim": "#CFC7B6",
    # Vasishta Bhavanam (owner's ground photo): salmon-pink pilasters/bands, salmon Mangalore tiles, blue name board
    "vasishta_pink": "#E9A48F",
    "vasishta_tile": "#D47D60",
    "vasishta_sign": "#1F4FA8",
    "vasishta_earth": "#C98B6E",
    "vasishta_roof": "#ADA79D",
    # Academic Block 4 (Google satellite; walls from the owner's photos across the sports ground)
    "ab4_wall": "#EFE9DC",
    "ab4_roof": "#DEDAD0",
    "ab4_trim": "#C9BEA8",
    "ab4_brick": "#A9604C",
    "ab4_glass": "#252C33",
    "ab4_concrete": "#A8A49C",
    # Pandal: open-sided metal shed (satellite roof colours, campus-tour video walls)
    "pandal_roof": "#ECE9E1",
    "pandal_ridge": "#D5D2CA",
    "pandal_metal": "#A7ABAE",
    "pandal_red": "#B0503F",
    "pandal_band": "#E2DED4",
    "pandal_pillar": "#EDE7D8",
    "pandal_shadow": "#4A403A",
    "pandal_paving": "#A65E50",
    # MBA (ASB) canteen (Google Maps photo and campus-tour video)
    "mba_stone": "#BDAA9E",
    "mba_stone_dark": "#A08D83",
    "mba_stripe": "#D07A52",
    "mba_white": "#F1ECE2",
    "mba_coping": "#B05F45",
    "mba_roof": "#9B968E",
    "mba_rock": "#8A7D72",
    "mba_graffiti": "#C9663A",
    "mba_door": "#2B2624",
    # Amrita School of Business (Google Maps photos)
    "asb_wall": "#EFB398",
    "asb_pilaster": "#C46A47",
    "asb_cream": "#F3E7D0",
    "asb_verandah": "#8A6255",
    "asb_roof_old": "#9C8678",
    "asb_roof": "#D8CBB2",
    "asb_porch_tile": "#B34A35",
    "asb_column": "#4A3830",
    "asb_sign": "#A32231",
    "asb_hedge": "#B7C84A",
    "asb_flower": "#D9584B",
    # Corporate and Industry Relations (Google Maps photos)
    "cir_pink": "#EDB3AC",
    "cir_line": "#C6706A",
    "cir_wood": "#7A4A2C",
    "cir_roof": "#C6BAA6",
    "cir_vault": "#8C99A2",
    "cir_vault_rib": "#C3CBD0",
    "cir_sign": "#2B5DAA",
    "cir_paving": "#B25C4C",
    "cir_ac": "#D3D5D6",
}


def srgb_hex_to_linear_rgba(hex_color: str, scale: float = 1.0) -> tuple[float, float, float, float]:
    """Convert an sRGB hex string to Blender linear-space RGBA."""
    c = hex_color.strip().lstrip("#")
    if len(c) != 6:
        return (0.7, 0.7, 0.7, 1.0)
    r, g, b = (int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0)

    def _to_lin(u: float) -> float:
        u = max(0.0, min(1.0, u * scale))
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

    return (_to_lin(r), _to_lin(g), _to_lin(b), 1.0)


def local_to_world_2d(
    cx: float,
    cy: float,
    lx: float,
    ly: float,
    rot_rad: float = 0.0,
) -> tuple[float, float]:
    """Rotate local (lx, ly) by rot_rad around (cx, cy) and return world 2D XY."""
    ca, sa = math.cos(rot_rad), math.sin(rot_rad)
    return (cx + lx * ca - ly * sa, cy + lx * sa + ly * ca)


def add_tri_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    verts: tuple[bmesh.types.BMVert, bmesh.types.BMVert, bmesh.types.BMVert],
    rgba: tuple[float, float, float, float],
    mat_idx: int = 0,
) -> None:
    try:
        f = bm.faces.new(verts)
        f.smooth = False
        f.material_index = mat_idx
        for loop in f.loops:
            loop[col_layer] = rgba
    except ValueError:
        pass


def add_quad_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    v0: bmesh.types.BMVert,
    v1: bmesh.types.BMVert,
    v2: bmesh.types.BMVert,
    v3: bmesh.types.BMVert,
    rgba: tuple[float, float, float, float],
    mat_idx: int = 0,
) -> None:
    add_tri_vc(bm, col_layer, (v0, v1, v2), rgba, mat_idx)
    add_tri_vc(bm, col_layer, (v0, v2, v3), rgba, mat_idx)


def add_box_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    hx: float,
    hy: float,
    wall_rgba: tuple[float, float, float, float],
    cap_rgba: tuple[float, float, float, float] | None = None,
    rot_rad: float = 0.0,
    emit_bottom: bool = False,
    offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Emit a watertight or open-bottom rotated box in world coordinates minus offset_xyz."""
    ox, oy, oz = offset_xyz
    top_col = cap_rgba if cap_rgba is not None else wall_rgba
    ca, sa = math.cos(rot_rad), math.sin(rot_rad)
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    pts = [(cx + lx * ca - ly * sa - ox, cy + lx * sa + ly * ca - oy) for lx, ly in corners]
    b = [bm.verts.new((px, py, z0 - oz)) for px, py in pts]
    t = [bm.verts.new((px, py, z1 - oz)) for px, py in pts]
    for i in range(4):
        j = (i + 1) % 4
        add_quad_vc(bm, col_layer, b[i], b[j], t[j], t[i], wall_rgba)
    add_quad_vc(bm, col_layer, t[0], t[1], t[2], t[3], top_col)
    if emit_bottom:
        add_quad_vc(bm, col_layer, b[3], b[2], b[1], b[0], wall_rgba)


def add_cylinder_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    r0: float,
    r1: float,
    segments: int,
    side_rgba: tuple[float, float, float, float],
    cap_rgba: tuple[float, float, float, float] | None = None,
    rot_rad: float = 0.0,
    offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
    emit_bottom: bool = False,
) -> None:
    """Emit a tapered cylinder/octagonal drum with clean outward normals."""
    ox, oy, oz = offset_xyz
    b_ring: list[bmesh.types.BMVert] = []
    t_ring: list[bmesh.types.BMVert] = []
    for i in range(segments):
        ang = rot_rad + (2.0 * math.pi * i) / segments
        ca, sa = math.cos(ang), math.sin(ang)
        b_ring.append(bm.verts.new((cx + r0 * ca - ox, cy + r0 * sa - oy, z0 - oz)))
        t_ring.append(bm.verts.new((cx + r1 * ca - ox, cy + r1 * sa - oy, z1 - oz)))
    for i in range(segments):
        j = (i + 1) % segments
        add_quad_vc(bm, col_layer, b_ring[i], b_ring[j], t_ring[j], t_ring[i], side_rgba)
    if cap_rgba is not None and r1 > 0.04:
        c_top = bm.verts.new((cx - ox, cy - oy, z1 - oz))
        for i in range(segments):
            j = (i + 1) % segments
            add_tri_vc(bm, col_layer, (t_ring[i], t_ring[j], c_top), cap_rgba)
    if emit_bottom and r0 > 0.04:
        c_bot = bm.verts.new((cx - ox, cy - oy, z0 - oz))
        for i in range(segments):
            j = (i + 1) % segments
            add_tri_vc(bm, col_layer, (b_ring[j], b_ring[i], c_bot), side_rgba)


def add_hipped_roof_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z_eave: float,
    z_peak: float,
    hx: float,
    hy: float,
    roof_rgba: tuple[float, float, float, float],
    rot_rad: float = 0.0,
    gable_rgba: tuple[float, float, float, float] | None = None,
    soffit_rgba: tuple[float, float, float, float] | None = None,
    offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Emit a rotated 4-sided pitched hipped roof with optional soffit & south gable pediment."""
    ox, oy, oz = offset_xyz
    ca, sa = math.cos(rot_rad), math.sin(rot_rad)

    def _pt(lx: float, ly: float, wz: float) -> bmesh.types.BMVert:
        return bm.verts.new((cx + lx * ca - ly * sa - ox, cy + lx * sa + ly * ca - oy, wz - oz))

    c = [_pt(-hx, -hy, z_eave), _pt(hx, -hy, z_eave), _pt(hx, hy, z_eave), _pt(-hx, hy, z_eave)]
    if hx >= hy:
        ridge_hx = max(0.35, hx - hy * 0.72)
        r0 = _pt(-ridge_hx, 0.0, z_peak)
        r1 = _pt(ridge_hx, 0.0, z_peak)
        add_quad_vc(bm, col_layer, c[0], c[1], r1, r0, roof_rgba)
        add_tri_vc(bm, col_layer, (c[1], c[2], r1), roof_rgba)
        add_quad_vc(bm, col_layer, c[2], c[3], r0, r1, roof_rgba)
        add_tri_vc(bm, col_layer, (c[3], c[0], r0), roof_rgba)
    else:
        ridge_hy = max(0.35, hy - hx * 0.72)
        r0 = _pt(0.0, -ridge_hy, z_peak)
        r1 = _pt(0.0, ridge_hy, z_peak)
        add_tri_vc(bm, col_layer, (c[0], c[1], r0), roof_rgba)
        add_quad_vc(bm, col_layer, c[1], c[2], r1, r0, roof_rgba)
        add_tri_vc(bm, col_layer, (c[2], c[3], r1), roof_rgba)
        add_quad_vc(bm, col_layer, c[3], c[0], r0, r1, roof_rgba)

    if soffit_rgba is not None:
        add_quad_vc(bm, col_layer, c[3], c[2], c[1], c[0], soffit_rgba)

    if gable_rgba is not None:
        gw = min(4.2, hx * 0.44)
        gh = min(2.3, (z_peak - z_eave) * 0.62)
        gl = _pt(-gw, -hy - 0.14, z_eave + 0.08)
        gr = _pt(gw, -hy - 0.14, z_eave + 0.08)
        gt = _pt(0.0, -hy + min(1.3, hy * 0.22), z_eave + gh)
        gb_l = _pt(-gw * 0.85, -hy - 0.02, z_eave + 0.08)
        gb_r = _pt(gw * 0.85, -hy - 0.02, z_eave + 0.08)
        add_tri_vc(bm, col_layer, (gl, gr, gt), gable_rgba)
        add_quad_vc(bm, col_layer, gb_l, gb_r, gr, gl, roof_rgba)


def add_gabled_roof_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z_eave: float,
    z_peak: float,
    hx: float,
    hy: float,
    roof_rgba: tuple[float, float, float, float],
    gable_wall_rgba: tuple[float, float, float, float],
    rot_rad: float = 0.0,
    ridge_along_x: bool = True,
    soffit_rgba: tuple[float, float, float, float] | None = None,
    offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Emit a clean pitched gable roof rotated by rot_rad."""
    ox, oy, oz = offset_xyz
    ca, sa = math.cos(rot_rad), math.sin(rot_rad)

    def _pt(lx: float, ly: float, wz: float) -> bmesh.types.BMVert:
        return bm.verts.new((cx + lx * ca - ly * sa - ox, cy + lx * sa + ly * ca - oy, wz - oz))

    c = [_pt(-hx, -hy, z_eave), _pt(hx, -hy, z_eave), _pt(hx, hy, z_eave), _pt(-hx, hy, z_eave)]
    if ridge_along_x:
        rl = _pt(-hx, 0.0, z_peak)
        rr = _pt(hx, 0.0, z_peak)
        add_quad_vc(bm, col_layer, c[0], c[1], rr, rl, roof_rgba)
        add_quad_vc(bm, col_layer, c[2], c[3], rl, rr, roof_rgba)
        add_tri_vc(bm, col_layer, (c[1], c[2], rr), gable_wall_rgba)
        add_tri_vc(bm, col_layer, (c[3], c[0], rl), gable_wall_rgba)
    else:
        rs = _pt(0.0, -hy, z_peak)
        rn = _pt(0.0, hy, z_peak)
        add_quad_vc(bm, col_layer, c[1], c[2], rn, rs, roof_rgba)
        add_quad_vc(bm, col_layer, c[3], c[0], rs, rn, roof_rgba)
        add_tri_vc(bm, col_layer, (c[0], c[1], rs), gable_wall_rgba)
        add_tri_vc(bm, col_layer, (c[2], c[3], rn), gable_wall_rgba)

    if soffit_rgba is not None:
        add_quad_vc(bm, col_layer, c[3], c[2], c[1], c[0], soffit_rgba)


def add_glass_panel(
    win_bm: bmesh.types.BMesh | None,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    half_width: float,
    local_y: float,
    rot_rad: float = 0.0,
    facing_south: bool = True,
) -> None:
    """Emit an outward-facing glass quad in WORLD Blender coordinates (never offset) for night glow."""
    if win_bm is None or z1 - z0 < 0.15 or half_width < 0.15:
        return
    ca, sa = math.cos(rot_rad), math.sin(rot_rad)
    p0x, p0y = cx + (-half_width) * ca - local_y * sa, cy + (-half_width) * sa + local_y * ca
    p1x, p1y = cx + (+half_width) * ca - local_y * sa, cy + (+half_width) * sa + local_y * ca
    if not facing_south:
        p0x, p1x = p1x, p0x
        p0y, p1y = p1y, p0y
    v0 = win_bm.verts.new((p0x, p0y, z0))
    v1 = win_bm.verts.new((p1x, p1y, z0))
    v2 = win_bm.verts.new((p1x, p1y, z1))
    v3 = win_bm.verts.new((p0x, p0y, z1))
    try:
        win_bm.faces.new((v0, v1, v2)).smooth = False
        win_bm.faces.new((v0, v2, v3)).smooth = False
    except ValueError:
        pass


def add_tiered_vimana_roof(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z_base: float,
    hx: float,
    hy: float,
    roof_rgba: tuple[float, float, float, float],
    trim_rgba: tuple[float, float, float, float],
    gold_rgba: tuple[float, float, float, float],
    rot_rad: float = 0.0,
    offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Emit a 2-tiered South Indian / Kerala pyramidal temple vimana roof + golden kalasha finial."""
    # Tier 1 skirt
    add_hipped_roof_vc(
        bm, col_layer, cx, cy, z_base, z_base + 2.35, hx + 0.65, hy + 0.65,
        roof_rgba, rot_rad=rot_rad, soffit_rgba=trim_rgba, offset_xyz=offset_xyz,
    )
    # Upper neck drum
    add_box_vc(
        bm, col_layer, cx, cy, z_base + 1.55, z_base + 2.45, hx * 0.56, hy * 0.56,
        trim_rgba, trim_rgba, rot_rad=rot_rad, offset_xyz=offset_xyz,
    )
    # Tier 2 upper pyramidal cap
    add_hipped_roof_vc(
        bm, col_layer, cx, cy, z_base + 2.40, z_base + 4.35, hx * 0.72, hy * 0.72,
        roof_rgba, rot_rad=rot_rad, soffit_rgba=trim_rgba, offset_xyz=offset_xyz,
    )
    # Golden kalasha finial
    add_cylinder_vc(
        bm, col_layer, cx, cy, z_base + 4.15, z_base + 4.95, 0.24, 0.04, 8,
        gold_rgba, gold_rgba, offset_xyz=offset_xyz,
    )
