"""Academic Block 1 (AB-1, Amrita School of Engineering): top-view-traced X/diamond plan with two triangular courts,
photo-matched South entrance tower (twin column pairs, glass top floor, terracotta hipped roof + front gable),
drive-through porte-cochere with roof terrace, rooftop solar rows / stair rooms, plus the scalloped front plaza,
Lotus fountain roundabout and the West parking lot."""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .saraswati_statue import append_saraswati_statue
from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_gabled_roof_vc,
    add_glass_panel,
    add_hipped_roof_vc,
    add_quad_vc,
    add_tri_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# ---------------------------------------------------------------------------------------------------------------
# Plan. Traced from the Google top view (pipeline/refs/ab1_top_google.webp), registered to world metres on the
# fountain centre + Esri imagery (ground features agree with the OSM path network). Both images lean: roofs read
# ~(-5.5 m, +4.0 m) away from their bases (east-end and south facades are visible), so the roof trace was shifted
# by (+5.5, -4.0) to get the ground footprint. The building is axis-aligned (spine N-S, W/E arms E-W).
#
#   - W arm (long) and E arm (shorter, ~12 m further North) run E-W.
#   - NW and NE arms meet at the North hub; two diagonal wings drop from the hub to the W/E arms and two more run
#     from the W/E arms down to the entrance tower, forming a diamond split by the N-S spine into two courts.
#   - Front (marked top view pipeline/refs/ab1_top_marked_front.webp, red line): the SW and SE wings end in
#     square-cut faces with pointed corners at (222.7,-271.4) / (271.2,-267.5); each end face runs back to the tower,
#     leaving ~6 m of the tower's side walls exposed. Tower 28.4 m wide, side-bay front y=-268.4, central block a
#     further 2.6 m forward (y=-271.0); porte-cochere from the central block to y=-285.3.
# ---------------------------------------------------------------------------------------------------------------
AB1_OUTER: tuple[tuple[float, float], ...] = (
    (261.0, -268.4), (232.6, -268.4), (232.6, -262.0), (222.7, -271.4), (202.1, -255.3), (178.5, -255.3),
    (178.5, -242.6), (200.5, -242.6), (222.2, -214.6), (211.3, -204.7), (220.5, -194.5), (239.7, -211.7),
    (260.2, -191.2), (269.8, -200.8), (257.9, -212.7), (283.6, -230.8), (309.8, -230.8), (309.8, -243.5),
    (292.5, -243.5), (282.9, -253.2), (271.2, -267.5), (261.0, -262.4),
)
AB1_COURTS: tuple[tuple[tuple[float, float], ...], ...] = (
    ((232.5, -223.8), (214.0, -247.8), (228.3, -258.0), (235.3, -258.0), (235.3, -226.3)),  # West court
    ((253.0, -225.4), (253.0, -258.0), (273.0, -239.5)),  # East court
)

# Entrance axis: tower, porte-cochere, fountain and entry road line up (front photo)
AB1_AXIS_X = 246.8
AB1_TOWER_FRONT_Y = -268.4  # side-bay front / twin-column line
AB1_TOWER_HX = 14.2
AB1_TOWER_SIDE_BACK_Y = (-262.0, -262.4)  # where the SW / SE wing end faces meet the tower's West / East walls
AB1_CENTRAL_HX = 6.0
AB1_CENTRAL_FRONT_Y = -271.0

# Porte-cochere (drive-under canopy with roof terrace), ground-level extents
AB1_PORTE_HX = 8.6
AB1_PORTE_Y0 = AB1_CENTRAL_FRONT_Y  # attaches to the tower's projecting central block
AB1_PORTE_Y1 = -285.3
AB1_PORTE_WHITE_Y = -277.0  # top view: grey terrace behind, white roof slab in front of this line

# Lotus fountain roundabout centre (Google + Esri agree to ~0.6 m)
AB1_FOUNTAIN_CX = 249.5
AB1_FOUNTAIN_CY = -302.7

# Terrain-hugging paved parking lot west of AB-1 NW wing (replacing 2 stray Overture sheds)
AB1_PARKING_CX = 184.5
AB1_PARKING_CY = -210.5
AB1_PARKING_HX = 15.0
AB1_PARKING_HY = 17.5
AB1_PARKING_ROT = 0.082  # +4.7 deg parallel to Ettimadai Road

# Wing centrelines (ground coords) used to lay rooftop solar rows along the diagonal wings
_NW_ARM = ((215.9, -199.6), (242.0, -223.0))
_NE_ARM = ((265.0, -196.0), (240.0, -221.0))
_L_DIAG = ((203.5, -250.0), (234.5, -210.0))
_SW_WING = ((204.5, -249.0), (239.5, -274.0))
_SE_WING_ROT = math.atan2(0.678, 0.735)


def _signed_area(ring: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring))
    )


def _oriented(ring: tuple[tuple[float, float], ...], ccw: bool) -> list[tuple[float, float]]:
    pts = list(ring)
    if (_signed_area(pts) > 0.0) != ccw:
        pts.reverse()
    return pts


def normalize_ab1_footprint_rings(
    outer_ring: list[tuple[float, float]],
) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]]]:
    """Replace the coarse OSM AB-1 outline with the traced plan: CCW outer ring + the two open triangular courts.
    Returns ([outer_ccw, *holes_cw], holes_ccw)."""
    del outer_ring
    outer = _oriented(AB1_OUTER, ccw=True)
    holes_ccw = [_oriented(c, ccw=True) for c in AB1_COURTS]
    return ([outer] + [list(reversed(h)) for h in holes_ccw], holes_ccw)


def get_ab1_plaza_ring() -> list[tuple[float, float]]:
    """CCW polygon of AB-1's scalloped asphalt forecourt + straight South entry road, traced from the top view. The two
    approaches either side of the porte-cochere run right up to the tower front and the wing-end corners (green areas
    on the marked top view)."""
    return [
        (246.0, -367.0),
        (253.0, -367.0),
        (253.3, -318.8),
        (264.0, -318.5),
        (269.5, -318.0),
        (274.4, -309.2),
        (265.4, -299.0),
        (266.5, -291.0),
        (270.5, -284.5),  # East approach (green, marked top view) flaring up to the SE wing corner
        (272.0, -278.5),
        (268.5, -271.2),
        (261.5, -268.9),
        (246.8, -268.9),
        (232.0, -268.9),
        (225.5, -273.6),  # West approach flaring up to the SW wing corner
        (222.0, -279.5),
        (223.5, -286.5),
        (228.5, -293.5),
        (232.2, -297.5),
        (232.5, -305.0),
        (223.5, -312.0),
        (232.5, -323.5),
        (238.5, -321.0),
        (245.5, -320.0),
    ]


def _lerp(p0: tuple[float, float], p1: tuple[float, float], t: float) -> tuple[float, float]:
    return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)


def _append_sign_text(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    text: str,
    size: float,
    cx: float,
    y_front: float,
    zc: float,
    rgba: tuple[float, float, float, float],
    offset_xyz: tuple[float, float, float],
) -> None:
    """Real lettering for the porte fascia: Blender text curve -> mesh, stood up on the South-facing fascia."""
    import bpy

    ox, oy, oz = offset_xyz
    cu = bpy.data.curves.new("ab1_sign_tmp", "FONT")
    cu.body = text
    cu.size = size
    cu.resolution_u = 2
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_word = 1.6
    ob = bpy.data.objects.new("ab1_sign_tmp", cu)
    bpy.context.scene.collection.objects.link(ob)
    try:
        ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        me.calc_loop_triangles()
        # text space (x right, y up, normal +z) -> world (x, -z, y): proper rotation, normal faces South (-Y)
        vmap = [bm.verts.new((cx + v.co.x - ox, y_front - v.co.z - oy, zc + v.co.y - oz)) for v in me.vertices]
        for lt in me.loop_triangles:
            i0, i1, i2 = lt.vertices
            if lt.normal.z < 0.0:
                i1, i2 = i2, i1
            add_tri_vc(bm, col_layer, (vmap[i0], vmap[i1], vmap[i2]), rgba)
        ev.to_mesh_clear()
    finally:
        bpy.data.objects.remove(ob)
        bpy.data.curves.remove(cu)


def ab1_front_tree_spots() -> list[tuple[float, float, int, tuple[float, float]]]:
    """World (x, y, tree_type, scale_range) for AB-1's hand-placed front landscaping (0 = palm, 1 = canopy/shrub),
    read from the aerial photos: palms framing the fountain, the round lime-green bush of the East garden and the
    tall tree in front of the SE wing. Low shrubs are modelled in `heroes/ab1_garden.py`."""
    return [
        (235.8, -326.5, 0, (0.95, 1.05)),  # palms just in front of the fountain, either side of the entry road
        (263.0, -326.0, 0, (0.95, 1.05)),
        (278.0, -287.5, 1, (0.62, 0.70)),  # big round bush, East garden
        (277.0, -279.0, 1, (0.55, 0.62)),  # tall tree in front of the SE wing next to the tower
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
    """Photo-matched entrance tower + porte-cochere, rooftop solar rows, stair rooms, tanks and roof membrane."""
    ox, oy, oz = offset_xyz
    ax, fy = AB1_AXIS_X, AB1_TOWER_FRONT_Y
    step = max(2.6, (z_eave - z_plinth) / 4.0)

    def fl(k: int) -> float:
        return z_plinth + k * step

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_recess = srgb_hex_to_linear_rgba("#353A41")
    c_glass = srgb_hex_to_linear_rgba("#2C3946")
    c_glass_blue = srgb_hex_to_linear_rgba("#4D6E8E")
    c_window_brown = srgb_hex_to_linear_rgba("#5B4A3E")
    c_pillar = srgb_hex_to_linear_rgba("#2B2826")
    c_soffit = srgb_hex_to_linear_rgba("#2F3135")
    c_terrace = srgb_hex_to_linear_rgba("#8F8C86")
    c_roof_white = srgb_hex_to_linear_rgba("#DAD6CD")
    c_letter = srgb_hex_to_linear_rgba("#454950")
    c_step = srgb_hex_to_linear_rgba("#B9B2A6")
    c_tile = srgb_hex_to_linear_rgba("#CF7350")
    c_emblem = srgb_hex_to_linear_rgba("#7A5C46")
    c_band = srgb_hex_to_linear_rgba("#C8714E")
    c_hedge = srgb_hex_to_linear_rgba("#3E7231")
    c_hedge_top = srgb_hex_to_linear_rgba("#5E8A3A")
    c_solar = srgb_hex_to_linear_rgba("#273A55")
    c_solar_frame = srgb_hex_to_linear_rgba("#8C949C")
    c_membrane = srgb_hex_to_linear_rgba("#767A80")
    c_tank = srgb_hex_to_linear_rgba("#E6E3DC")
    c_hatch = srgb_hex_to_linear_rgba("#8A5B45")

    def box(cx: float, cy: float, z0: float, z1: float, hx: float, hy: float, wall: Any, cap: Any = None,
            rot: float = 0.0, bottom: bool = False) -> None:
        add_box_vc(bm, col_layer, cx, cy, z0, z1, hx, hy, wall, cap, rot_rad=rot, emit_bottom=bottom,
                   offset_xyz=offset_xyz)

    def column(cx: float, cy: float, z1: float) -> None:
        """Round white column on a square pedestal (front photo: twin round columns with plinth blocks)."""
        g = terrain.sample(cx, cy)
        box(cx, cy, g - 1.5, max(g + 0.9, z_plinth + 0.5), 0.40, 0.40, c_white)
        add_cylinder_vc(bm, col_layer, cx, cy, g + 0.8, z1, 0.29, 0.29, 10, c_white, None, offset_xyz=offset_xyz)

    def balustrade(p0: tuple[float, float], p1: tuple[float, float], z0: float, n: tuple[float, float],
                   h: float = 0.95, spacing: float = 0.42) -> None:
        """White balustrade: plinth, handrail and outward-facing balusters (seen against the dark veranda)."""
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        ln = math.hypot(dx, dy)
        rot = math.atan2(dy, dx)
        mx, my = 0.5 * (p0[0] + p1[0]), 0.5 * (p0[1] + p1[1])
        box(mx, my, z0, z0 + 0.16, 0.5 * ln, 0.10, c_white, rot=rot)
        box(mx, my, z0 + h - 0.12, z0 + h, 0.5 * ln + 0.03, 0.12, c_white, rot=rot)
        rx, ry = -n[1], n[0]
        cnt = max(2, int(ln / spacing))
        for i in range(cnt):
            d = (i + 0.5) * ln / cnt
            bx, by = p0[0] + dx / ln * d, p0[1] + dy / ln * d
            pl = (bx - rx * 0.06 - ox, by - ry * 0.06 - oy)
            pr = (bx + rx * 0.06 - ox, by + ry * 0.06 - oy)
            za, zb = z0 + 0.16 - oz, z0 + h - 0.12 - oz
            add_quad_vc(bm, col_layer, bm.verts.new((*pl, za)), bm.verts.new((*pr, za)),
                        bm.verts.new((*pr, zb)), bm.verts.new((*pl, zb)), c_white)

    # ---------------- Entrance tower (marked top view: side bays at fy, central block 2.6 m further) --------------
    hw = AB1_TOWER_HX
    chx = AB1_CENTRAL_HX
    cb = AB1_CENTRAL_FRONT_Y  # central block front face
    pair_c = hw - 0.70  # centre of each twin-column pair
    bay_c, bay_h = 0.5 * (chx + pair_c - 0.45), 0.5 * (pair_c - 0.45 - chx)

    # a) Twin round columns at both front corners + a round column at the back of each exposed side wall
    for s, back_y in ((-1.0, AB1_TOWER_SIDE_BACK_Y[0]), (1.0, AB1_TOWER_SIDE_BACK_Y[1])):
        for cxo in (pair_c - 0.45, pair_c + 0.45):
            column(ax + s * cxo, fy - 0.45, z_eave + 0.05)
        for k in (1, 2, 3):
            box(ax + s * pair_c, fy - 0.45, fl(k) - 0.22, fl(k) + 0.10, 0.86, 0.40, c_white)
        box(ax + s * pair_c, fy - 0.45, z_eave - 0.55, z_eave - 0.20, 0.92, 0.46, c_white)
        column(ax + s * (hw - 0.25), back_y - 0.55, z_eave + 0.05)

    # b) Front side bays: deep shaded verandas, floor slab edges and baluster railings on Floors 1-3
    for s in (-1.0, 1.0):
        bx = ax + s * bay_c
        box(bx, fy - 0.07, z_plinth + 0.3, z_eave - 0.12, bay_h, 0.08, c_recess)
        for k in (1, 2, 3):
            box(bx, fy - 0.22, fl(k) - 0.24, fl(k), bay_h + 0.05, 0.22, c_white)
            balustrade((ax + s * (chx + 0.2), fy - 0.36), (ax + s * (pair_c - 0.55), fy - 0.36), fl(k), (0.0, -1.0))

    # c) Exposed tower side walls between the wing end faces and the front: verandas + railings per floor
    for s, back_y in ((-1.0, AB1_TOWER_SIDE_BACK_Y[0]), (1.0, AB1_TOWER_SIDE_BACK_Y[1])):
        xf = ax + s * hw
        side_cy, side_hy = 0.5 * (back_y + fy), 0.5 * (back_y - fy)
        box(xf + s * 0.07, side_cy, z_plinth + 0.3, z_eave - 0.12, 0.08, side_hy - 0.95, c_recess)
        for k in (1, 2, 3):
            box(xf + s * 0.20, side_cy, fl(k) - 0.24, fl(k), 0.20, side_hy, c_white)
            balustrade((xf + s * 0.34, back_y - 1.05), (xf + s * 0.34, fy - 0.95), fl(k), (s, 0.0))

    # d) Projecting central block: Floor 3 glass wall, Floor 2 wide 2-pane window, Floor 1 blue gridded window above the
    #    porte terrace, ground-floor glazed lobby behind the dark pillars, balcony slabs across the bays
    box(ax, 0.5 * (fy + cb), z_plinth, z_eave, chx, 0.5 * (fy - cb), c_white)
    for s in (-1.0, 1.0):  # shaded side openings of the projecting block
        box(ax + s * (chx + 0.06), 0.5 * (fy + cb), z_plinth + 0.3, z_eave - 0.12, 0.07, 0.5 * (fy - cb) - 0.45, c_recess)
    g3_z0, g3_z1 = fl(3) + 0.28, z_eave - 0.32
    box(ax, cb - 0.03, g3_z0, g3_z1, chx - 0.5, 0.05, c_glass)
    add_glass_panel(win_lit_bm, ax, cb - 0.10, g3_z0 + 0.05, g3_z1 - 0.05, chx - 0.6, 0.0, facing_south=True)
    for mx in (-3.67, -1.83, 0.0, 1.83, 3.67):
        box(ax + mx, cb - 0.11, g3_z0, g3_z1, 0.07, 0.07, c_white)
    z_tr = g3_z0 + 0.62 * (g3_z1 - g3_z0)
    box(ax, cb - 0.11, z_tr - 0.06, z_tr + 0.06, chx - 0.5, 0.07, c_white)

    w2_z0, w2_z1 = fl(2) + 1.0, fl(2) + 2.55
    box(ax, cb - 0.03, w2_z0, w2_z1, 2.85, 0.05, c_window_brown)
    add_glass_panel(win_dark_bm, ax, cb - 0.10, w2_z0 + 0.05, w2_z1 - 0.05, 2.75, 0.0, facing_south=True)
    box(ax, cb - 0.11, w2_z0, w2_z1, 0.08, 0.07, c_white)
    box(ax, cb - 0.08, w2_z0 - 0.16, w2_z0, 3.0, 0.10, c_white)

    slab_front = cb - 0.3
    for k in (2, 3):
        box(ax, 0.5 * (fy + slab_front), fl(k) - 0.45, fl(k) + 0.05, 8.6, 0.5 * (fy - slab_front), c_white, bottom=True)
        for s in (-1.0, 1.0):  # railings on the balcony parts of the slabs either side of the central block
            balustrade((ax + s * (chx + 0.15), slab_front + 0.12), (ax + s * 8.5, slab_front + 0.12), fl(k) + 0.05,
                       (0.0, -1.0), spacing=0.5)

    # ---------------- Porte-cochere (sign fascia, dark soffit + brackets, two pairs of dark pillars) ----------------
    py0, py1 = AB1_PORTE_Y0, AB1_PORTE_Y1
    py_c, py_h = 0.5 * (py0 + py1), 0.5 * (py0 - py1)
    g_p = terrain.sample(ax, py1 + 1.0)
    pz0, pz1 = g_p + 4.4, g_p + 5.8

    w1_z0, w1_z1 = max(fl(1) + 0.5, pz1 + 0.95), fl(2) - 0.45
    if w1_z1 - w1_z0 > 0.6:
        box(ax, cb - 0.03, w1_z0, w1_z1, 2.45, 0.05, c_glass_blue)
        add_glass_panel(win_lit_bm, ax, cb - 0.10, w1_z0 + 0.05, w1_z1 - 0.05, 2.35, 0.0, facing_south=True)
        for mx in (-1.22, 0.0, 1.22):
            box(ax + mx, cb - 0.11, w1_z0, w1_z1, 0.06, 0.06, c_white)
        zm = 0.5 * (w1_z0 + w1_z1)
        box(ax, cb - 0.11, zm - 0.05, zm + 0.05, 2.45, 0.06, c_white)
        box(ax, cb - 0.10, w1_z0 - 0.14, w1_z0, 2.6, 0.12, c_white)

    lob_z1 = min(pz0 - 0.5, z_plinth + 3.2)
    lob_g = terrain.sample(ax, cb - 1.0)
    box(ax, cb - 0.03, lob_g - 0.3, lob_z1, 4.6, 0.05, c_glass)
    add_glass_panel(win_lit_bm, ax, cb - 0.10, lob_g + 0.1, lob_z1 - 0.05, 4.5, 0.0, facing_south=True)
    for mx in (-2.3, -0.9, 0.9, 2.3):
        box(ax + mx, cb - 0.11, lob_g - 0.3, lob_z1, 0.07, 0.07, c_pillar)

    box(ax, py_c, pz0, pz1, AB1_PORTE_HX, py_h, c_white, c_terrace)
    wy0 = AB1_PORTE_WHITE_Y
    box(ax, 0.5 * (wy0 + py1) - 0.15, pz1, pz1 + 0.04, AB1_PORTE_HX - 0.3, 0.5 * (wy0 - py1) - 0.3, c_roof_white)
    box(ax, py_c, pz0 - 0.05, pz0, AB1_PORTE_HX - 0.15, py_h - 0.10, c_soffit, bottom=True)
    box(ax, py1 + 0.05, pz1 - 0.22, pz1 + 0.03, AB1_PORTE_HX + 0.12, 0.18, c_white)  # top cornice
    box(ax, py1 + 0.15, pz1, pz1 + 0.80, AB1_PORTE_HX, 0.15, c_white)  # terrace parapet
    for s in (-1.0, 1.0):
        box(ax + s * (AB1_PORTE_HX - 0.15), py_c, pz1, pz1 + 0.80, 0.15, py_h, c_white)
    box(ax, py1 + 0.55, pz0 - 0.55, pz0, AB1_PORTE_HX - 0.3, 0.28, c_soffit)  # dark lintel under the fascia
    for bxo in (-4.5, -1.5, 1.5, 4.5):
        box(ax + bxo, py_c, pz0 - 0.40, pz0, 0.16, py_h - 0.3, c_soffit)  # ceiling beams
    for i in range(9):
        box(ax - 4.8 + i * 1.2, py1 + 0.35, pz0 - 0.78, pz0 - 0.55, 0.11, 0.12, c_soffit)  # bracket row
    for s in (-1.0, 1.0):
        for cxo in (5.4, 6.45):
            px = ax + s * cxo
            for pyy in (py1 + 0.9, py0 - 5.2):  # front pair row (photo) + a mid row carrying the 14 m deep canopy
                g = terrain.sample(px, pyy)
                box(px, pyy, g - 1.5, pz0 - 0.5, 0.36, 0.36, c_pillar)
    _append_sign_text(bm, col_layer, "AMRITA VISHWA VIDYAPEETHAM", 0.5, ax, py1 - 0.025, 0.5 * (pz0 + pz1) - 0.05,
                      c_letter, offset_xyz)
    box(ax, cb - 0.9, g_p - 0.8, g_p + 0.32, 4.8, 0.9, c_step)  # entrance steps under the canopy

    # e) Terracotta full-height band on the SE wing end face where it meets the tower (front + aerial photos)
    jx, jy = ax + hw, AB1_TOWER_SIDE_BACK_Y[1]
    dxe, dye = 271.2 - jx, -267.5 - jy
    de = math.hypot(dxe, dye)
    tx_e, ty_e = dxe / de, dye / de
    bx_e, by_e = jx + tx_e * 0.75 + ty_e * 0.10, jy + ty_e * 0.75 - tx_e * 0.10  # offset outward (away from the wing)
    box(bx_e, by_e, terrain.sample(bx_e, by_e) - 0.5, z_eave, 0.6, 0.09, c_band, rot=math.atan2(ty_e, tx_e))

    # f) Low hedge/flower planters at the tower base either side of the porte (aerial photo)
    for s in (-1.0, 1.0):
        hx_c = ax + s * 10.4
        g = terrain.sample(hx_c, fy - 1.1)
        box(hx_c, fy - 1.1, g - 0.5, g + 0.55, 1.6, 0.5, c_hedge, c_hedge_top)

    # g) Terracotta hipped roof over the whole (projecting) tower + front gable over the central block with emblem
    roof_y0, roof_y1 = -256.0, fy - 0.8
    roof_cy, roof_hy = 0.5 * (roof_y0 + roof_y1), 0.5 * (roof_y0 - roof_y1)
    box(ax, roof_cy, z_top - 0.55, z_top, hw + 0.5, roof_hy - 0.2, c_white)
    add_hipped_roof_vc(
        bm, col_layer, ax, roof_cy, z_top - 0.05, z_top + 4.6, hw + 0.8, roof_hy, c_tile,
        soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )
    gable_y0, gable_y1 = -262.0, cb - 0.8
    add_gabled_roof_vc(
        bm, col_layer, ax, 0.5 * (gable_y0 + gable_y1), z_top - 0.05, z_top + 4.3, chx + 1.0, 0.5 * (gable_y0 - gable_y1),
        c_tile, c_white, ridge_along_x=False, soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )
    ey = gable_y1 - 0.06
    e0 = bm.verts.new((ax - 1.05 - ox, ey - oy, z_top + 0.95 - oz))
    e1 = bm.verts.new((ax + 1.05 - ox, ey - oy, z_top + 0.95 - oz))
    e2 = bm.verts.new((ax - ox, ey - oy, z_top + 2.25 - oz))
    add_tri_vc(bm, col_layer, (e0, e1, e2), c_emblem)

    # ---------------- Rooftop solar rows (layout read from the top view) ----------------
    z_s0, z_s1 = z_top - 0.05, z_top + 0.32

    def solar_row(cx: float, cy: float, hx: float, hy: float = 0.68) -> None:
        box(cx, cy, z_s0, z_s1, hx, hy, c_solar_frame, c_solar)

    for ry in (-244.6, -246.5, -248.4, -250.3, -252.2):  # W arm
        solar_row(193.5, ry, 12.0)
    for ry in (-233.0, -234.9, -236.8, -238.7, -240.6):  # E arm
        solar_row(297.5, ry, 11.0)
    for i in range(8):  # Spine: large field split into 8 blocks
        solar_row(244.2, -220.2 - i * 4.9, 7.0, 2.2)
    for ry in (-214.4, -216.4):  # Spine head at the North hub
        solar_row(245.0, ry, 5.3)
    # Diagonal wings: E-W rows stepping along the wing like a staircase (top view)
    for (p0, p1), t0, t1, hx in (
        (_NW_ARM, 0.30, 0.76, 3.7),
        (_NE_ARM, 0.36, 0.56, 3.7),
        (_L_DIAG, 0.26, 0.74, 3.5),
        (_SW_WING, 0.20, 0.58, 3.5),
    ):
        seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        n_rows = max(2, int((t1 - t0) * seg_len / 2.45) + 1)
        for i in range(n_rows):
            solar_row(*_lerp(p0, p1, t0 + (t1 - t0) * i / (n_rows - 1)), hx, 0.82)

    # ---------------- Rooftop structures ----------------
    nw_rot = math.atan2(_NW_ARM[1][1] - _NW_ARM[0][1], _NW_ARM[1][0] - _NW_ARM[0][0])
    box(216.6, -202.6, z_top - 0.05, z_top + 2.6, 2.0, 1.7, c_cream, c_terrace, rot=nw_rot)  # NW arm stair room
    for tx, ty in ((253.2, -198.6), (255.6, -201.4), (259.0, -201.6)):  # NE arm tip tanks / vents
        add_cylinder_vc(bm, col_layer, tx, ty, z_top - 0.05, z_top + 1.1, 0.65, 0.65, 6, c_tank, c_terrace,
                        offset_xyz=offset_xyz)
    box(256.3, -218.6, z_top - 0.05, z_top + 2.3, 2.2, 1.6, c_cream, c_terrace)  # Hub lift/stair room
    for tx in (254.6, 258.0):
        add_cylinder_vc(bm, col_layer, tx, -216.2, z_top + 2.3, z_top + 3.4, 0.7, 0.7, 6, c_tank, c_tank,
                        offset_xyz=offset_xyz)
    box(251.4, -220.4, z_top - 0.05, z_top + 2.0, 1.3, 1.3, c_cream)  # Small tiled stair cabin beside the spine
    add_hipped_roof_vc(bm, col_layer, 251.4, -220.4, z_top + 2.0, z_top + 2.9, 1.55, 1.55, c_tile,
                       offset_xyz=offset_xyz)
    for hx_c, hy_c in ((277.0, -230.6), (269.6, -230.2)):  # Right diagonal roof hatches
        box(hx_c, hy_c, z_top - 0.05, z_top + 0.6, 0.8, 0.8, c_hatch)
    box(276.4, -248.2, z_top - 0.05, z_top + 0.06, 5.8, 4.2, c_membrane, rot=_SE_WING_ROT)  # SE wing dark membrane


def append_ab1_fountain_plaza(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
) -> None:
    """Curved flowerbed borders, lane dashes and the twin-ring fountain with the marble Saraswati of the AB-1 roundabout."""
    fx, fy = AB1_FOUNTAIN_CX, AB1_FOUNTAIN_CY

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_water = srgb_hex_to_linear_rgba("#8CD2E0")  # pale pool blue (owner's photo from the AB-1 roof)
    c_lawn = srgb_hex_to_linear_rgba("#86C03E")
    c_garden = srgb_hex_to_linear_rgba("#74B238")
    c_curb_stone = srgb_hex_to_linear_rgba("#DCD6CA")
    c_shrub = srgb_hex_to_linear_rgba("#5C9C30")

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
        del seed_base
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


    # 1. Flowerbed borders hugging the scalloped plaza edges (West: porte corner -> lobe -> entry road; East mirrored)
    ring = get_ab1_plaza_ring()
    west_edge = ring[14:] + [ring[0]]  # SW wing corner -> West lobe -> entry road
    east_edge = ring[1:11]  # entry road -> East lobe -> SE wing corner
    _build_flower_border(west_edge, outward_sign=1.0, seed_base=1)
    _build_flower_border(east_edge, outward_sign=1.0, seed_base=5)

    # 2. Dashed white lane markings: entry road centre line, roundabout ring and the two straight porte lanes
    def _emit_dash(dcx: float, dcy: float, hl: float, hw: float, drot: float) -> None:
        ca, sa = math.cos(drot), math.sin(drot)
        pts = [(dcx + lx * ca - ly * sa, dcy + lx * sa + ly * ca) for lx, ly in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]
        vs = [bm.verts.new((px, py, terrain.sample(px, py) + 0.27)) for px, py in pts]
        add_quad_vc(bm, col_layer, vs[0], vs[1], vs[2], vs[3], c_white)

    entry_ang = math.atan2(43.0, -0.6)
    for k in range(7):
        t = k / 6.0
        _emit_dash(251.0 * (1.0 - t) + 250.4 * t, -362.0 * (1.0 - t) + -322.0 * t, 1.3, 0.13, entry_ang)

    ring_r = 13.4
    for k in range(18):
        ang = (2.0 * math.pi * k) / 18.0
        if math.sin(ang) > 0.62:  # leave the porte side open (lanes run straight up to the canopy there)
            continue
        _emit_dash(fx + ring_r * math.cos(ang), fy + ring_r * math.sin(ang), 1.05, 0.12, ang + 0.5 * math.pi)
    for lane_x in (235.4, 260.4):  # lane lines either side of the porte-cochere (marked top view)
        for step_y in (-274.5, -279.5, -284.5, -289.5, -294.5):
            _emit_dash(lane_x, step_y, 1.05, 0.12, 0.5 * math.pi)

    # 3. Fountain: outer white rim wall, lawn ring, inner white rim, water basin, Saraswati statue on a lotus.
    #    The forecourt falls ~1.7 m North->South across the fountain (9 %), like the draped asphalt, so the fountain
    #    is set on the best-fit plane of the ground: the rim wall then stands ~1 m above the drive all the way round.
    samples: list[tuple[float, float, float]] = [(0.0, 0.0, terrain.sample(fx, fy))]
    for i in range(16):
        ang = (2.0 * math.pi * i) / 16.0
        dx_s, dy_s = 9.3 * math.cos(ang), 9.3 * math.sin(ang)
        samples.append((dx_s, dy_s, terrain.sample(fx + dx_s, fy + dy_s)))
    n_s = len(samples)
    z_mean = sum(z for _, _, z in samples) / n_s
    sxx = sum(dx_s * dx_s for dx_s, _, _ in samples) or 1.0
    syy = sum(dy_s * dy_s for _, dy_s, _ in samples) or 1.0
    slope_x = sum(dx_s * (z - z_mean) for dx_s, _, z in samples) / sxx
    slope_y = sum(dy_s * (z - z_mean) for _, dy_s, z in samples) / syy
    z_mean += 0.06

    def pz(x: float, y: float, dz: float) -> float:
        return z_mean + slope_x * (x - fx) + slope_y * (y - fy) + dz

    segs = 24

    def _ring_wall(r_in: float, r_out: float, d_in0: float, d_out0: float | None, d_top: float,
                   rgba: tuple[float, float, float, float], emit_inner: bool = True) -> None:
        for i in range(segs):
            a0 = (2.0 * math.pi * i) / segs
            a1 = (2.0 * math.pi * (i + 1)) / segs
            p_in0 = (fx + r_in * math.cos(a0), fy + r_in * math.sin(a0))
            p_in1 = (fx + r_in * math.cos(a1), fy + r_in * math.sin(a1))
            p_ou0 = (fx + r_out * math.cos(a0), fy + r_out * math.sin(a0))
            p_ou1 = (fx + r_out * math.cos(a1), fy + r_out * math.sin(a1))
            if d_out0 is None:  # outer face runs down into the terrain
                zb0, zb1 = terrain.sample(*p_ou0) - 0.45, terrain.sample(*p_ou1) - 0.45
            else:
                zb0, zb1 = pz(*p_ou0, d_out0), pz(*p_ou1, d_out0)
            vo0, vo1 = bm.verts.new((*p_ou0, zb0)), bm.verts.new((*p_ou1, zb1))
            ti0, ti1 = bm.verts.new((*p_in0, pz(*p_in0, d_top))), bm.verts.new((*p_in1, pz(*p_in1, d_top)))
            to0, to1 = bm.verts.new((*p_ou0, pz(*p_ou0, d_top))), bm.verts.new((*p_ou1, pz(*p_ou1, d_top)))
            add_quad_vc(bm, col_layer, vo0, vo1, to1, to0, rgba)
            add_quad_vc(bm, col_layer, to0, to1, ti1, ti0, rgba)
            if emit_inner:
                vi0, vi1 = bm.verts.new((*p_in0, pz(*p_in0, d_in0))), bm.verts.new((*p_in1, pz(*p_in1, d_in0)))
                add_quad_vc(bm, col_layer, vi1, vi0, ti0, ti1, rgba)

    _ring_wall(8.5, 9.3, 0.35, None, 1.05, c_white)  # outer rim wall (~1 m above the drive, close-up photo)
    _ring_wall(9.2, 9.42, 0.95, 0.95, 1.12, c_curb_stone, emit_inner=False)  # thin coping lip
    _ring_wall(7.4, 8.5, 0.40, 0.40, 0.62, c_lawn, emit_inner=False)
    _ring_wall(6.9, 7.4, 0.25, 0.62, 0.90, c_white)
    w_c = bm.verts.new((fx, fy, pz(fx, fy, 0.42)))
    w_ring = [
        bm.verts.new((fx + 6.95 * math.cos(2 * math.pi * i / segs), fy + 6.95 * math.sin(2 * math.pi * i / segs),
                      pz(fx + 6.95 * math.cos(2 * math.pi * i / segs), fy + 6.95 * math.sin(2 * math.pi * i / segs), 0.42)))
        for i in range(segs)
    ]
    for i in range(segs):
        add_tri_vc(bm, col_layer, (w_c, w_ring[i], w_ring[(i + 1) % segs]), c_water)

    # Small clipped shrubs on the lawn ring (seen just above the rim wall in the close-up photo)
    for i in range(12):
        a = (2.0 * math.pi * (i + 0.5)) / 12.0
        sx, sy = fx + 7.95 * math.cos(a), fy + 7.95 * math.sin(a)
        add_cylinder_vc(bm, col_layer, sx, sy, pz(sx, sy, 0.55), pz(sx, sy, 1.12), 0.38, 0.30, 5, c_shrub, c_garden)

    # Terracotta pots with arching spider plants ringing the base of the rim wall on the drive (close-up photo)
    c_pot = srgb_hex_to_linear_rgba("#7C4130")
    c_leaf = srgb_hex_to_linear_rgba("#8FB03C")
    c_leaf_back = srgb_hex_to_linear_rgba("#6F9330")
    for i in range(28):
        a = (2.0 * math.pi * i) / 28.0
        px, py = fx + 9.85 * math.cos(a), fy + 9.85 * math.sin(a)
        gz = terrain.sample(px, py) + 0.22
        add_cylinder_vc(bm, col_layer, px, py, gz - 0.12, gz + 0.48, 0.18, 0.25, 5, c_pot, None, rot_rad=a)
        for b in range(5):  # five leaf blades fanning up and out (front + back faces)
            ba = a + 0.4 + b * (2.0 * math.pi / 5.0)
            ca_, sa_ = math.cos(ba), math.sin(ba)
            q0 = bm.verts.new((px - 0.07 * sa_, py + 0.07 * ca_, gz + 0.45))
            q1 = bm.verts.new((px + 0.07 * sa_, py - 0.07 * ca_, gz + 0.45))
            tip = bm.verts.new((px + 0.52 * ca_, py + 0.52 * sa_, gz + 0.98 - 0.12 * (b % 2)))
            add_tri_vc(bm, col_layer, (q0, q1, tip), c_leaf)
            add_tri_vc(bm, col_layer, (q1, q0, tip), c_leaf_back)

    # Pedestal in the basin + white marble Saraswati on her lotus, facing the entry road
    z_stat = pz(fx, fy, 0.95)
    add_cylinder_vc(bm, col_layer, fx, fy, pz(fx, fy, -0.3), z_stat, 1.55, 1.50, 12, c_white, c_white)
    append_saraswati_statue(
        bm, col_layer, (fx, fy, z_stat),
        marble=srgb_hex_to_linear_rgba("#F3F1EC"),
        marble_shade=srgb_hex_to_linear_rgba("#DEDCD6"),
        scale=1.15,
    )


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
