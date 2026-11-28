"""Amriteshwari Hall (way/380925370): auditorium block over Ganga Mess / Staff Mess (ground floor), Amrita Coimbatore.

References (Esri crop: pipeline/refs/amriteshwari_sat.png; aerial: pipeline/refs/ab1_irl_aerial_far.png):
  - Google Maps satellite, imagery (c) 2026 Airbus/Maxar: flat roof, solar field over the East two-thirds, stair/lift
    tower at the NW corner, tiled rooftop room at the SW corner, rounded West corners, NE water tank.
  - Esri World Imagery (georeferenced): roof outline x 328.8..370.5, y -248.8..-227.4; roofs lean ~(-4.0, +3.5) m at
    this height, so the ground footprint is x 332..375.5, y -251.5..-231 (43.5 x 20.5 m, axis-aligned). The Google Maps
    pin for the hall (343.9, -241.3) sits exactly mid-depth. Stair tower against the North face.
  - Aerial photo from the South-West (refs/ab1_irl_aerial_far.png): long white G+3 block, deep white spandrel bands with
    ~13 punched windows per floor, rooftop rooms at the West end, solar on the East part, tank at the NE corner.
  - Google Maps contributor photos of Ganga Mess (2022, not stored in the repo): white walls with orange-peach string bands and plinth, upper floors
    cantilevered over a ground-floor walkway on round white columns, open twin staircase with dark railings and a green
    painted mural wall at the entrance.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_hipped_roof_vc,
    add_quad_vc,
    add_tri_vc,
    srgb_hex_to_linear_rgba,
)

AMH_X0, AMH_X1 = 332.0, 375.5
AMH_Y0, AMH_Y1 = -251.5, -231.0  # South / North faces
AMH_CORNER_R = 3.5  # rounded West corners (satellite + entrance photo)
AMH_ORANGE = "#E08A5E"
AMH_ROOF = "#B9B4AA"


def normalize_amriteshwari_rings() -> list[list[tuple[float, float]]]:
    """CCW outer ring: rectangle with the two West corners rounded."""
    x0, x1, y0, y1, r = AMH_X0, AMH_X1, AMH_Y0, AMH_Y1, AMH_CORNER_R
    ring: list[tuple[float, float]] = [(x1, y0), (x1, y1)]
    for cx, cy, a0 in ((x0 + r, y1 - r, 90.0), (x0 + r, y0 + r, 180.0)):
        for i in range(5):
            a = math.radians(a0 + i * 22.5)
            ring.append((round(cx + r * math.cos(a), 2), round(cy + r * math.sin(a), 2)))
    return [ring]


def append_amriteshwari_hero_details(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_eave: float,
    z_top: float,
) -> None:
    """Cantilevered South walkway on round columns, entrance stair + mural, North stair tower and the rooftop."""
    del win_lit_bm
    x0, x1, y0, y1, r = AMH_X0, AMH_X1, AMH_Y0, AMH_Y1, AMH_CORNER_R
    step = max(2.6, (z_eave - z_plinth) / 4.0)

    def fl(k: int) -> float:
        return z_plinth + k * step

    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_orange = srgb_hex_to_linear_rgba(AMH_ORANGE)
    c_recess = srgb_hex_to_linear_rgba("#3A3F46")
    c_rail = srgb_hex_to_linear_rgba("#2B2D31")
    c_mural = srgb_hex_to_linear_rgba("#58A84B")
    c_mural_fig = srgb_hex_to_linear_rgba("#E2B83C")
    c_roof = srgb_hex_to_linear_rgba(AMH_ROOF)
    c_tile = srgb_hex_to_linear_rgba("#C8694B")
    c_solar = srgb_hex_to_linear_rgba("#273A55")
    c_solar_frame = srgb_hex_to_linear_rgba("#8C949C")
    c_tank = srgb_hex_to_linear_rgba("#3F6FA6")

    def box(cx: float, cy: float, za: float, zb: float, hx: float, hy: float, wall: Any, cap: Any = None,
            bottom: bool = False) -> None:
        add_box_vc(bm, col_layer, cx, cy, za, zb, hx, hy, wall, cap, emit_bottom=bottom, offset_xyz=offset_xyz)

    # 1) First-floor slab cantilevered 1.3 m over the South walkway (orange edge + soffit), on round white columns
    sx0, sx1 = x0 + r, x1 - 0.2
    scx, shx = 0.5 * (sx0 + sx1), 0.5 * (sx1 - sx0)
    box(scx, y0 - 0.65, fl(1) - 0.38, fl(1) + 0.08, shx, 0.65, c_orange, c_white, bottom=True)
    n_cols = 9
    for i in range(n_cols):
        cx = sx0 + 2.6 + i * (sx1 - sx0 - 5.2) / (n_cols - 1)
        g = terrain.sample(cx, y0 - 1.0)
        add_cylinder_vc(bm, col_layer, cx, y0 - 1.0, g - 1.2, fl(1) - 0.36, 0.26, 0.24, 8, c_white, None,
                        offset_xyz=offset_xyz)
    box(scx, y0 - 0.06, z_plinth - 0.4, z_plinth + 0.55, shx, 0.08, c_orange)  # orange plinth band under the walkway

    # 1b) Deep white spandrel bands projecting from the South face at Floors 2-3 and the roof parapet (aerial photo)
    for zb in (fl(2), fl(3), z_eave - 0.05):
        box(scx, y0 - 0.32, zb - 0.12, zb + 0.78, shx, 0.32, c_white, c_white, bottom=True)
        box(scx, y0 - 0.65, zb - 0.12, zb + 0.02, shx, 0.02, c_orange)

    # 2) Entrance at the South-West: open double-height stair hall (dark), twin stair flights, green mural wall
    ex = x0 + r + 3.4
    g_e = terrain.sample(ex, y0 - 0.5)
    box(ex, y0 - 0.05, g_e - 0.3, fl(1) - 0.4, 3.0, 0.06, c_recess)
    for i in range(4):  # stepped stair flight rising to the West, with dark railing
        box(ex + 1.6 - i * 0.75, y0 - 0.25, g_e, g_e + 0.45 + i * 0.45, 0.38, 0.22, c_white)
    box(ex - 0.6, y0 - 0.38, g_e + 1.0, g_e + 2.9, 2.0, 0.03, c_rail)
    box(ex + 4.2, y0 - 0.08, g_e - 0.3, g_e + 2.0, 1.2, 0.07, c_mural)
    for fx_ in (-0.5, 0.3):
        box(ex + 4.2 + fx_, y0 - 0.16, g_e + 0.5, g_e + 1.3, 0.18, 0.03, c_mural_fig)

    # 2b) West FRONT (faces AB-1). Campus-tour video frames (refs/amriteshwari_yt_*.png, YouTube ptMO2l2Tn2o @ 8:16-8:24):
    #     open ground floor (dark stair hall behind square white piers, stair flight with dark railing, green mural),
    #     solid white Floor 1, continuous dark glass ribbon with black mullions on Floor 2 wrapping the rounded
    #     corner onto the South face, thin curved slabs cantilevered round the West end at Floor 3 and the roof.
    #     Single-sided quads keep it inside the triangle budget; the orange stringcourses come from the base mass.
    ox, oy, oz = offset_xyz
    west_run: list[tuple[float, float, float, float]] = []  # (x, y, nx, ny) North -> South round the West end
    for cx, cy, a0 in ((x0 + r, y1 - r, 90.0), (x0 + r, y0 + r, 180.0)):
        for i in range(5):
            a = math.radians(a0 + i * 22.5)
            west_run.append((cx + r * math.cos(a), cy + r * math.sin(a), math.cos(a), math.sin(a)))

    def vtx(x: float, y: float, z: float) -> Any:
        return bm.verts.new((x - ox, y - oy, z - oz))

    def face(pts: list[Any], rgba: Any) -> None:
        add_quad_vc(bm, col_layer, pts[0], pts[1], pts[2], pts[3], rgba)

    def skin(run: list[tuple[float, float, float, float]], za: float, zb: float, off: float, rgba: Any) -> None:
        """Outward-facing strip hugging the wall polyline (one quad per segment)."""
        for (ax, ay, anx, any_), (bx, by, bnx, bny) in zip(run, run[1:]):
            a = (ax + anx * off, ay + any_ * off)
            b = (bx + bnx * off, by + bny * off)
            face([vtx(a[0], a[1], za), vtx(b[0], b[1], za), vtx(b[0], b[1], zb), vtx(a[0], a[1], zb)], rgba)

    def curved_slab(zb: float, depth: float, thick: float, edge: Any) -> None:
        """Thin slab cantilevered `depth` m round the West end: white top + soffit, orange edge, end caps."""
        za = zb - thick
        for (ax, ay, anx, any_), (bx, by, bnx, bny) in zip(west_run, west_run[1:]):
            qa = (ax + anx * depth, ay + any_ * depth)
            qb = (bx + bnx * depth, by + bny * depth)
            face([vtx(ax, ay, zb), vtx(qa[0], qa[1], zb), vtx(qb[0], qb[1], zb), vtx(bx, by, zb)], c_white)
            face([vtx(bx, by, za), vtx(qb[0], qb[1], za), vtx(qa[0], qa[1], za), vtx(ax, ay, za)], c_white)
            face([vtx(qa[0], qa[1], za), vtx(qb[0], qb[1], za), vtx(qb[0], qb[1], zb), vtx(qa[0], qa[1], zb)], edge)
        for (px, py, nx_, ny_), sgn in ((west_run[0], 1.0), (west_run[-1], -1.0)):
            q = (px + nx_ * depth, py + ny_ * depth)
            p_, q_ = ((px, py), q) if sgn > 0 else (q, (px, py))
            face([vtx(p_[0], p_[1], za), vtx(q_[0], q_[1], za), vtx(q_[0], q_[1], zb), vtx(p_[0], p_[1], zb)], c_white)

    g_w = min(terrain.sample(x0, y0 + r), terrain.sample(x0, y1 - r)) - 0.3
    # Ground floor: dark open stair hall round the whole West end, square piers on the flat front
    skin(west_run, g_w, fl(1) - 0.32, 0.04, c_recess)
    for k in range(4):
        py = y0 + r + 1.3 + k * (y1 - y0 - 2 * r - 2.6) / 3.0
        box(x0 - 0.3, py, g_w, fl(1) - 0.3, 0.26, 0.26, c_white)
    # Stair flight rising North inside the hall (white stringer + dark railing) and the green mural beside it
    sy0, sy1 = y0 + r + 2.2, y0 + r + 6.4
    face([vtx(x0 - 0.07, sy0, g_w + 0.3), vtx(x0 - 0.07, sy1, fl(1) - 0.9),
          vtx(x0 - 0.07, sy1, fl(1) - 0.55), vtx(x0 - 0.07, sy0, g_w + 0.75)][::-1], c_cream)
    face([vtx(x0 - 0.08, sy0, g_w + 1.35), vtx(x0 - 0.08, sy1, fl(1) + 0.05 - 0.55),
          vtx(x0 - 0.08, sy1, fl(1) - 0.35), vtx(x0 - 0.08, sy0, g_w + 1.55)][::-1], c_rail)
    my0, my1 = y1 - r - 5.2, y1 - r - 1.6
    face([vtx(x0 - 0.07, my1, g_w + 0.3), vtx(x0 - 0.07, my0, g_w + 0.3),
          vtx(x0 - 0.07, my0, fl(1) - 0.6), vtx(x0 - 0.07, my1, fl(1) - 0.6)], c_mural)
    face([vtx(x0 - 0.09, my1 - 1.0, g_w + 1.0), vtx(x0 - 0.09, my0 + 1.0, g_w + 1.0),
          vtx(x0 - 0.09, my0 + 1.0, fl(1) - 1.1), vtx(x0 - 0.09, my1 - 1.0, fl(1) - 1.1)], c_mural_fig)
    # Floor 2: flush dark glass ribbon (light grey frames) round the West end and ~9 m along the South face
    c_glass = srgb_hex_to_linear_rgba("#26303A")
    c_frame = srgb_hex_to_linear_rgba("#C9CED2")
    gz0, gz1 = fl(2) + 0.5, fl(3) - 0.36

    def frames(pts: list[tuple[float, float, float, float]], off: float, za: float, zb: float) -> None:
        for mx, my, mnx, mny in pts:
            tx, ty = -mny, mnx  # wall tangent (North -> South along the run)
            a = (mx + mnx * off - tx * 0.06, my + mny * off - ty * 0.06)
            b = (mx + mnx * off + tx * 0.06, my + mny * off + ty * 0.06)
            face([vtx(a[0], a[1], za), vtx(b[0], b[1], za), vtx(b[0], b[1], zb), vtx(a[0], a[1], zb)], c_frame)

    yc = 0.5 * (y0 + y1)
    bay_hw, bay_d = 4.0, 2.4  # curved bay: 8 m chord on the West face, bulging 2.4 m (user-marked screenshots)
    glass_run = west_run + [(x0 + r + 9.0, y0, 0.0, -1.0)]
    skin(glass_run, gz0, gz1, 0.09, c_glass)
    ribbon_frames = [p for p in west_run[1:-1]]
    ribbon_frames += [(x0, yy, -1.0, 0.0) for yy in (y1 - r - 0.9, y1 - r - 2.2, y0 + r + 2.2, y0 + r + 0.9)
                      if abs(yy - yc) > bay_hw]
    ribbon_frames += [(x0 + r + k * 2.25, y0, 0.0, -1.0) for k in range(1, 4)]
    frames(ribbon_frames, 0.12, gz0, gz1)

    # Central curved bay on the West front (the "bump" in refs/amriteshwari_front_bump_marked.webp and the
    # video frame): a circular-segment volume from the Floor-1 soffit to the parapet, standing on two piers over
    # the open ground-floor hall; white walls, orange stringcourses, dark glass band in light frames on Floor 2.
    bay_r = (bay_hw ** 2 + bay_d ** 2) / (2.0 * bay_d)
    bay_cx = x0 - bay_d + bay_r
    half_a = math.asin(bay_hw / bay_r)
    bay: list[tuple[float, float, float, float]] = []  # North -> South, radial outward normals
    for k in range(7):
        a = math.pi - half_a + k * (2.0 * half_a / 6.0)
        bay.append((bay_cx + bay_r * math.cos(a), yc + bay_r * math.sin(a), math.cos(a), math.sin(a)))
    zs = fl(1) - 0.32
    for za, zb, col in (
        (zs, fl(2) - 0.28, c_white), (fl(2) - 0.28, fl(2), c_orange), (fl(2), gz0, c_white),
        (gz0, gz1, c_glass), (gz1, fl(3) - 0.04, c_orange), (fl(3) - 0.04, z_top - 0.24, c_white),
        (z_top - 0.24, z_top, c_orange),
    ):
        skin(bay, za, zb, 0.0, col)
    skin(bay, gz1 - 0.62, gz1 - 0.55, 0.02, c_frame)  # transom
    frames(bay[1:-1], 0.03, gz0, gz1)
    for k in range(1, 6):  # flat roof cap (up) and soffit (down) as fans over the circular segment
        p0, pa, pb = bay[0], bay[k], bay[k + 1]
        add_tri_vc(bm, col_layer, (vtx(p0[0], p0[1], z_top), vtx(pa[0], pa[1], z_top), vtx(pb[0], pb[1], z_top)),
                   c_roof)
        add_tri_vc(bm, col_layer, (vtx(p0[0], p0[1], zs), vtx(pb[0], pb[1], zs), vtx(pa[0], pa[1], zs)), c_white)
    for k in (2, 4):  # piers under the bay front
        px, py, pnx, pny = bay[k]
        box(px - pnx * 0.3, py - pny * 0.3, g_w, zs, 0.24, 0.24, c_white)

    # Roof: thin curved slab cantilevered round the West end (orange edge)
    curved_slab(z_eave + 0.05, 0.9, 0.26, c_orange)

    # 3) Vertical recessed stair slot on the East end face (aerial photo)
    box(x1 + 0.05, 0.5 * (y0 + y1) + 3.0, z_plinth + 0.6, z_eave - 0.4, 0.07, 1.1, c_recess)

    # 4) Stair tower against the North face (bright block north of the roof in the satellite), rising above the roof
    tx0, tx1, ty0, ty1 = 345.5, 351.5, -231.2, -228.2
    g_t = terrain.sample(0.5 * (tx0 + tx1), 0.5 * (ty0 + ty1))
    box(0.5 * (tx0 + tx1), 0.5 * (ty0 + ty1), g_t - 1.5, z_top + 1.2, 0.5 * (tx1 - tx0), 0.5 * (ty1 - ty0), c_white, c_roof)
    box(0.5 * (tx0 + tx1), ty1 + 0.06, z_plinth + 0.8, z_top - 0.6, 0.6, 0.06, c_recess)  # tall stair window slot

    # 5) Rooftop: solar field over the East two-thirds (7 rows), NW stair/lift tower, long rooftop room,
    #    SW tiled rooftop room and the blue water tank at the NE corner
    box(359.5, -239.0, z_top - 0.05, z_top + 0.22, 11.6, 6.75, c_solar_frame)  # one racking block ...
    for i in range(7):  # ... with the 7 panel rows as top quads (saves triangles for the West front)
        yc = -233.0 - i * 2.0
        face([vtx(347.9, yc - 0.66, z_top + 0.24), vtx(371.1, yc - 0.66, z_top + 0.24),
              vtx(371.1, yc + 0.66, z_top + 0.24), vtx(347.9, yc + 0.66, z_top + 0.24)], c_solar)
    box(336.6, -233.4, z_top - 0.05, z_top + 3.2, 2.85, 2.2, c_white, c_roof)
    box(336.6, -235.65, z_top + 2.9, z_top + 3.2, 2.9, 0.05, c_orange)
    box(346.5, -233.8, z_top - 0.05, z_top + 2.8, 5.5, 2.3, c_cream, c_roof)
    box(336.5, -246.0, z_top - 0.05, z_top + 2.5, 2.0, 3.4, c_white)
    add_hipped_roof_vc(bm, col_layer, 336.5, -246.0, z_top + 2.45, z_top + 3.6, 2.3, 3.7, c_tile,
                       offset_xyz=offset_xyz)
    add_cylinder_vc(bm, col_layer, 373.2, -233.2, z_top - 0.05, z_top + 1.5, 0.8, 0.8, 8, c_tank, c_tank,
                    offset_xyz=offset_xyz)
