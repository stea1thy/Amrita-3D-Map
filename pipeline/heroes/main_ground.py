"""Modular Hero landmark for Amrita Main Sports Ground (`way/528938316`).

Generates:
1. Natural sunlit mowed grass apron (`#78A852` with warmer earthy infield pitch variation).
   - Zero seating on the LEFT (west) side — clean open grass transitioning to west trees.
2. Signature red-clay / terracotta oval athletics track (`#C7704A`, ~9m wide, +0.045m)
   with 3 subtle white concentric lane markings.
3. Minimal football pitch markings & twin low-poly white football goalposts along long axis.
4. Stepped light-grey concrete spectator gallery on the RIGHT (east) side (7 tiers,
   `#C9C8C3` treads / `#A8A7A2` risers, 5 concrete stair aisles, central projecting bastion).
5. Low weathered concrete perimeter boundary wall along the far (north) edge.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from hero_models.geom_helpers import (
    add_box_vc,
    add_cylinder_vc,
    add_quad_vc,
    add_tri_vc,
    srgb_hex_to_linear_rgba,
)

HERO_PLAYGROUND_ID = "way/528938316"

# Satellite-calibrated oval track & east concrete gallery geometry (Blender XY meters)
TRACK_CENTER_X = 303.0
TRACK_CENTER_Y = 11.0
TRACK_ROT_RAD = 0.125  # ~7.16 deg CCW (matches East ground straightaway SE->NE)
TRACK_HALF_STRAIGHT = 40.0
TRACK_INNER_RADIUS = 38.65
TRACK_WIDTH = 9.0
TRACK_OUTER_RADIUS = TRACK_INNER_RADIUS + TRACK_WIDTH  # 47.65m

GALLERY_FRONT_U = TRACK_OUTER_RADIUS + 3.2  # 50.85m east of track center
GALLERY_TIERS = 7
GALLERY_TREAD_D = 0.96
GALLERY_RISER_H = 0.48
GALLERY_HALF_LEN = 43.0  # 86m long along East straightaway


def _local_to_world(u: float, v: float) -> tuple[float, float]:
    """Map local ground coordinates (u=East across width, v=North along straightaway) to Blender XY."""
    ca, sa = math.cos(TRACK_ROT_RAD), math.sin(TRACK_ROT_RAD)
    return (TRACK_CENTER_X + u * ca - v * sa, TRACK_CENTER_Y + u * sa + v * ca)


def _world_to_local(wx: float, wy: float) -> tuple[float, float]:
    """Inverse transform from Blender XY into (u=East, v=North) track frame."""
    dx, dy = wx - TRACK_CENTER_X, wy - TRACK_CENTER_Y
    ca, sa = math.cos(TRACK_ROT_RAD), math.sin(TRACK_ROT_RAD)
    return (dx * ca + dy * sa, -dx * sa + dy * ca)


def _stadium_curve_points(radius: float, arc_segs: int = 22) -> list[tuple[float, float]]:
    """Return CCW local (u, v) points tracing a stadium oval (long axis along v)."""
    pts: list[tuple[float, float]] = []
    # Top semicircle centered at (0, +TRACK_HALF_STRAIGHT): angle 0 -> pi
    for i in range(arc_segs + 1):
        ang = math.pi * i / arc_segs
        pts.append((radius * math.cos(ang), TRACK_HALF_STRAIGHT + radius * math.sin(ang)))
    # Bottom semicircle centered at (0, -TRACK_HALF_STRAIGHT): angle pi -> 2*pi
    for i in range(arc_segs + 1):
        ang = math.pi + math.pi * i / arc_segs
        pts.append((radius * math.cos(ang), -TRACK_HALF_STRAIGHT + radius * math.sin(ang)))
    return pts


def _signed_area_2d(ring: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1]
        for i in range(len(ring))
    )


def _make_vertex_color_material(name: str, roughness: float = 0.88) -> Any:
    import bpy

    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    mat = bpy.data.materials.new(name=name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new(type="ShaderNodeBsdfPrincipled")
    vcol = nt.nodes.new(type="ShaderNodeVertexColor")
    vcol.layer_name = "Color"
    nt.links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _extract_ground_polygon(raw_osm: dict[str, Any], config: Any) -> list[tuple[float, float]]:
    feat = next(
        (
            f
            for f in raw_osm.get("features", [])
            if str(f.get("id") or f.get("properties", {}).get("osm_id") or "") == HERO_PLAYGROUND_ID
        ),
        None,
    )
    if feat is None:
        return [
            (175.72, -107.01),
            (364.53, -78.28),
            (341.66, 116.41),
            (154.02, 93.53),
        ]
    ring = feat["geometry"]["coordinates"][0][:-1]
    pts: list[tuple[float, float]] = []
    for lon, lat in ring:
        lx, lz = config.latlon_to_local_xz(float(lat), float(lon))
        pts.append((lx, -lz))
    if _signed_area_2d(pts) < 0:
        pts.reverse()
    return pts


def _lerp_rgba(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    t: float,
) -> tuple[float, float, float, float]:
    t = max(0.0, min(1.0, t))
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
        1.0,
    )


def _grass_color_at(wx: float, wy: float) -> tuple[float, float, float, float]:
    """Smooth sunlit mowed grass (#78A852) with subtle continuous earthy infield variation."""
    c_apron = srgb_hex_to_linear_rgba("#78A852")
    c_apron_warm = srgb_hex_to_linear_rgba("#82AB56")
    c_apron_deep = srgb_hex_to_linear_rgba("#6E9E4B")
    c_infield = srgb_hex_to_linear_rgba("#86AA59")
    c_infield_earth = srgb_hex_to_linear_rgba("#95A95D")

    # Gentle organic variation across the outer lawn
    wave = 0.5 + 0.5 * math.sin(wx * 0.045 + 0.6) * math.cos(wy * 0.042 - 0.3)
    col = _lerp_rgba(c_apron_deep, c_apron_warm, wave)
    col = _lerp_rgba(col, c_apron, 0.35)

    # Smooth transition into warmer earthy mowed infield inside the oval
    u, v = _world_to_local(wx, wy)
    clamped_v = max(-TRACK_HALF_STRAIGHT, min(TRACK_HALF_STRAIGHT, v))
    d_oval = math.hypot(u, v - clamped_v)
    if d_oval < TRACK_INNER_RADIUS:
        in_t = max(0.0, min(1.0, (TRACK_INNER_RADIUS - d_oval) / 10.0))
        mow_band = 0.5 + 0.5 * math.sin(v * 0.24)
        pitch_col = _lerp_rgba(c_infield, c_infield_earth, 0.45 * mow_band)
        col = _lerp_rgba(col, pitch_col, in_t * 0.85)
    return col


def _add_smooth_quad_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    v0: bmesh.types.BMVert,
    v1: bmesh.types.BMVert,
    v2: bmesh.types.BMVert,
    v3: bmesh.types.BMVert,
    c0: tuple[float, float, float, float],
    c1: tuple[float, float, float, float],
    c2: tuple[float, float, float, float],
    c3: tuple[float, float, float, float],
) -> None:
    for tri_verts, tri_cols in (((v0, v1, v2), (c0, c1, c2)), ((v0, v2, v3), (c0, c2, c3))):
        try:
            f = bm.faces.new(tri_verts)
            f.smooth = False
            f.material_index = 0
            for loop, rgba in zip(f.loops, tri_cols):
                loop[col_layer] = rgba
        except ValueError:
            pass


def _add_stadium_strip(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    r_inner: float,
    r_outer: float,
    z_top: float,
    rgba: tuple[float, float, float, float],
    skirt_z: float | None = None,
    skirt_rgba: tuple[float, float, float, float] | None = None,
    arc_segs: int = 22,
) -> None:
    """Emit a watertight oval stadium ribbon (plus optional thin bevel skirts to skirt_z)."""
    in_pts = _stadium_curve_points(r_inner, arc_segs=arc_segs)
    out_pts = _stadium_curve_points(r_outer, arc_segs=arc_segs)
    n = len(in_pts)
    in_v = [bm.verts.new((*_local_to_world(u, v), z_top)) for u, v in in_pts]
    out_v = [bm.verts.new((*_local_to_world(u, v), z_top)) for u, v in out_pts]
    for i in range(n):
        j = (i + 1) % n
        # Top face upward (+Z)
        add_quad_vc(bm, col_layer, in_v[i], out_v[i], out_v[j], in_v[j], rgba)

    if skirt_z is not None:
        scol = skirt_rgba if skirt_rgba is not None else rgba
        in_b = [bm.verts.new((*_local_to_world(u, v), skirt_z)) for u, v in in_pts]
        out_b = [bm.verts.new((*_local_to_world(u, v), skirt_z)) for u, v in out_pts]
        for i in range(n):
            j = (i + 1) % n
            add_quad_vc(bm, col_layer, out_b[i], out_b[j], out_v[j], out_v[i], scol)
            add_quad_vc(bm, col_layer, in_v[i], in_v[j], in_b[j], in_b[i], scol)


def _add_thin_line_local(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    u0: float,
    v0: float,
    u1: float,
    v1: float,
    width: float,
    z_top: float,
    rgba: tuple[float, float, float, float],
) -> None:
    """Emit a flat chalk/paint line strip in local (u, v) coordinates."""
    du, dv = u1 - u0, v1 - v0
    seg_len = math.hypot(du, dv)
    if seg_len < 1e-4:
        return
    nu, nv = (-dv / seg_len) * (width * 0.5), (du / seg_len) * (width * 0.5)
    c0 = _local_to_world(u0 - nu, v0 - nv)
    c1 = _local_to_world(u1 - nu, v1 - nv)
    c2 = _local_to_world(u1 + nu, v1 + nv)
    c3 = _local_to_world(u0 + nu, v0 + nv)
    verts = [bm.verts.new((px, py, z_top)) for px, py in (c0, c1, c2, c3)]
    add_quad_vc(bm, col_layer, verts[0], verts[1], verts[2], verts[3], rgba)


def _add_goalpost(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    v_pos: float,
    facing_sign: float,
    z_ground: float,
    c_goal: tuple[float, float, float, float],
) -> None:
    """Build a crisp low-poly white football goalpost centered at u=0, v=v_pos."""
    goal_hw = 3.66  # regulation 7.32m width
    goal_h = 2.44
    net_d = 1.6
    r_post = 0.085
    z0 = z_ground - 0.06
    z_top = z_ground + goal_h

    # Left and right front uprights
    for u_sign in (-1.0, 1.0):
        px, py = _local_to_world(u_sign * goal_hw, v_pos)
        add_cylinder_vc(bm, col_layer, px, py, z0, z_top, r_post, r_post, 6, c_goal, c_goal)
        # Rear ground bar & top support rail
        bx, by = _local_to_world(u_sign * goal_hw, v_pos - facing_sign * (net_d * 0.5))
        add_box_vc(
            bm, col_layer, bx, by, z_ground, z_ground + 0.09,
            0.06, net_d * 0.5, c_goal, c_goal, rot_rad=TRACK_ROT_RAD,
        )
        # Rear corner vertical support
        rx, ry = _local_to_world(u_sign * goal_hw, v_pos - facing_sign * net_d)
        add_cylinder_vc(bm, col_layer, rx, ry, z0, z_top - 0.25, 0.055, 0.055, 5, c_goal, c_goal)

    # Top front crossbar & rear top brace
    cx, cy = _local_to_world(0.0, v_pos)
    add_box_vc(
        bm, col_layer, cx, cy, z_top - 0.08, z_top + 0.08,
        goal_hw + r_post, r_post, c_goal, c_goal, rot_rad=TRACK_ROT_RAD, emit_bottom=True,
    )
    rx_mid, ry_mid = _local_to_world(0.0, v_pos - facing_sign * net_d)
    add_box_vc(
        bm, col_layer, rx_mid, ry_mid, z_ground, z_ground + 0.09,
        goal_hw + 0.05, 0.06, c_goal, c_goal, rot_rad=TRACK_ROT_RAD,
    )


def _build_east_concrete_gallery(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    z_top: float,
    z_skirt: float,
) -> None:
    """Build the 7-tier concrete spectator gallery along the RIGHT (east) side of the track."""
    c_tread = srgb_hex_to_linear_rgba("#C9C8C3")
    c_riser = srgb_hex_to_linear_rgba("#A8A7A2")
    c_stair = srgb_hex_to_linear_rgba("#B3B2AC")
    c_wall_top = srgb_hex_to_linear_rgba("#D2D1CC")
    c_dark_rec = srgb_hex_to_linear_rgba("#8D8C87")

    u_front = GALLERY_FRONT_U
    u_back = u_front + GALLERY_TIERS * GALLERY_TREAD_D
    z_base = z_skirt

    # Front concrete apron curb wall separating track perimeter grass from seating gallery
    wx, wy = _local_to_world(u_front - 0.30, 0.0)
    add_box_vc(
        bm, col_layer, wx, wy, z_base, z_top + 0.72,
        0.30, GALLERY_HALF_LEN + 0.8, c_riser, c_tread, rot_rad=TRACK_ROT_RAD,
    )

    # Central projecting concrete bastion / VIP viewing box on the gallery's front face
    bastion_hw = 3.8
    bastion_depth = 2.4
    bx, by = _local_to_world(u_front - 0.6 - bastion_depth * 0.5, 0.0)
    add_box_vc(
        bm, col_layer, bx, by, z_base, z_top + 1.55,
        bastion_depth * 0.5, bastion_hw, c_riser, c_tread, rot_rad=TRACK_ROT_RAD,
    )
    # Bastion concrete parapet rim (raised front/side parapet)
    for side in (-1.0, 1.0):
        spx, spy = _local_to_world(u_front - 0.6 - bastion_depth * 0.5, side * (bastion_hw - 0.18))
        add_box_vc(
            bm, col_layer, spx, spy, z_top + 1.55, z_top + 2.15,
            bastion_depth * 0.5, 0.18, c_riser, c_wall_top, rot_rad=TRACK_ROT_RAD,
        )
    fpx, fpy = _local_to_world(u_front - 0.6 - bastion_depth + 0.18, 0.0)
    add_box_vc(
        bm, col_layer, fpx, fpy, z_top + 1.55, z_top + 2.20,
        0.18, bastion_hw, c_riser, c_wall_top, rot_rad=TRACK_ROT_RAD,
    )

    # 5 evenly spaced stair aisle coordinates cutting through the 7 concrete tiers
    stair_vs = (-32.0, -16.0, 0.0, 16.0, 32.0)
    stair_hw = 0.82  # 1.64m wide stair aisles

    # Build seating tier segments between the stair aisles (so stair cutouts have zero z-fighting)
    boundaries = [-GALLERY_HALF_LEN]
    for sv in stair_vs:
        boundaries.append(sv - stair_hw)
        boundaries.append(sv + stair_hw)
    boundaries.append(GALLERY_HALF_LEN)

    seating_spans: list[tuple[float, float]] = []
    for k in range(0, len(boundaries), 2):
        v0, v1 = boundaries[k], boundaries[k + 1]
        if v1 - v0 > 0.25:
            seating_spans.append((v0, v1))

    for tier in range(GALLERY_TIERS):
        u_t_mid = u_front + (tier + 0.5) * GALLERY_TREAD_D
        z_tread = z_top + (tier + 1) * GALLERY_RISER_H
        for v0, v1 in seating_spans:
            vc = 0.5 * (v0 + v1)
            vh = 0.5 * (v1 - v0)
            tx, ty = _local_to_world(u_t_mid, vc)
            add_box_vc(
                bm, col_layer, tx, ty, z_base, z_tread,
                GALLERY_TREAD_D * 0.5, vh, c_riser, c_tread, rot_rad=TRACK_ROT_RAD,
            )

        # Two half-height stair steps per tier inside each stair aisle
        for sv in stair_vs:
            for half_idx in (0, 1):
                u_s_mid = u_front + (tier + 0.25 + 0.5 * half_idx) * GALLERY_TREAD_D
                z_step = z_top + (tier + 0.5 + 0.5 * half_idx) * GALLERY_RISER_H + 0.03
                sx, sy = _local_to_world(u_s_mid, sv)
                add_box_vc(
                    bm, col_layer, sx, sy, z_base, z_step,
                    GALLERY_TREAD_D * 0.25, stair_hw, c_dark_rec, c_stair, rot_rad=TRACK_ROT_RAD,
                )

    # Elevated rear press/VIP concrete gallery deck behind central bastion
    bx_rear, by_rear = _local_to_world(u_back - 1.4, 0.0)
    add_box_vc(
        bm, col_layer, bx_rear, by_rear, z_top + GALLERY_TIERS * GALLERY_RISER_H,
        z_top + GALLERY_TIERS * GALLERY_RISER_H + 1.1,
        1.4, bastion_hw + 0.4, c_riser, c_wall_top, rot_rad=TRACK_ROT_RAD,
    )

    # Rear retaining wall & north/south stepped side end walls framing the gallery cleanly
    rx, ry = _local_to_world(u_back + 0.25, 0.0)
    z_rear_top = z_top + GALLERY_TIERS * GALLERY_RISER_H + 0.85
    add_box_vc(
        bm, col_layer, rx, ry, z_base, z_rear_top,
        0.26, GALLERY_HALF_LEN + 0.8, c_riser, c_wall_top, rot_rad=TRACK_ROT_RAD,
    )
    for end_s in (-1.0, 1.0):
        ex, ey = _local_to_world(0.5 * (u_front + u_back), end_s * (GALLERY_HALF_LEN + 0.35))
        add_box_vc(
            bm, col_layer, ex, ey, z_base, z_rear_top - 0.35,
            (u_back - u_front) * 0.5 + 0.28, 0.35, c_riser, c_wall_top, rot_rad=TRACK_ROT_RAD,
        )


def _build_north_perimeter_wall(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    nw_pt: tuple[float, float],
    ne_pt: tuple[float, float],
    terrain: Any,
    z_top: float,
) -> None:
    """Build low weathered concrete perimeter boundary wall with pilasters along the far (north) edge."""
    c_wall = srgb_hex_to_linear_rgba("#BCB9B1")
    c_coping = srgb_hex_to_linear_rgba("#9F9D96")

    dx, dy = ne_pt[0] - nw_pt[0], ne_pt[1] - nw_pt[1]
    length = math.hypot(dx, dy)
    if length < 10.0:
        return
    ang = math.atan2(dy, dx)
    nx, ny = dy / length, -dx / length  # inward south normal of NW -> NE edge

    inset = 1.6
    start_x, start_y = nw_pt[0] + nx * inset + (dx / length) * 3.0, nw_pt[1] + ny * inset + (dy / length) * 3.0
    end_x, end_y = ne_pt[0] + nx * inset - (dx / length) * 3.0, ne_pt[1] + ny * inset - (dy / length) * 3.0
    mid_x, mid_y = 0.5 * (start_x + end_x), 0.5 * (start_y + end_y)
    wall_hlen = math.hypot(end_x - start_x, end_y - start_y) * 0.5

    z_wall_base = min(z_top, terrain.sample(mid_x, mid_y)) - 1.5
    z_wall_top = z_top + 1.65
    add_box_vc(
        bm, col_layer, mid_x, mid_y, z_wall_base, z_wall_top,
        wall_hlen, 0.20, c_wall, c_coping, rot_rad=ang,
    )
    add_box_vc(
        bm, col_layer, mid_x, mid_y, z_wall_top, z_wall_top + 0.14,
        wall_hlen + 0.08, 0.26, c_coping, c_coping, rot_rad=ang,
    )

    num_pilasters = max(4, int(wall_hlen * 2.0 / 18.0))
    for i in range(num_pilasters + 1):
        t = i / num_pilasters
        px = start_x + t * (end_x - start_x)
        py = start_y + t * (end_y - start_y)
        pz_b = min(z_top, terrain.sample(px, py)) - 1.5
        add_box_vc(
            bm, col_layer, px, py, pz_b, z_wall_top + 0.30,
            0.34, 0.34, c_wall, c_coping, rot_rad=ang,
        )


def get_main_ground_collider_ring() -> list[tuple[float, float]]:
    """Return tight CCW polygon covering ground + oval + east gallery + north wall to exclude trees."""
    u_min = -142.0
    u_max = GALLERY_FRONT_U + GALLERY_TIERS * GALLERY_TREAD_D + 0.6
    v_min = -102.5
    v_max = 101.2
    return [
        _local_to_world(u_min, v_min),
        _local_to_world(u_max, v_min),
        _local_to_world(u_max, v_max),
        _local_to_world(u_min, v_max),
    ]


def get_main_ground_tree_belts() -> list[tuple[str, float, float, float, float, float]]:
    """Return local (belt_name, u0, u1, v0, v1, spacing) strips for dense perimeter tree belts."""
    u_back = GALLERY_FRONT_U + GALLERY_TIERS * GALLERY_TREAD_D
    return [
        # Thick woodland screen immediately behind (east of) the East concrete gallery, west of East road
        ("east_gallery_screen", u_back + 2.8, u_back + 11.8, -76.0, 96.0, 5.0),
        # North perimeter canopy belt outside the north boundary wall & north of the north road
        ("north_perimeter", -142.0, u_back + 12.0, 103.5, 140.0, 6.2),
        # West / NW perimeter canopy grove outside the open left-side grass apron
        ("west_perimeter", -212.0, -148.0, -28.0, 130.0, 6.4),
    ]


def belt_local_to_world(u: float, v: float) -> tuple[float, float]:
    """Public wrapper converting (u, v) belt coordinate to Blender XY."""
    return _local_to_world(u, v)


def build_hero(context: dict[str, Any]) -> None:
    """Build modular `GROUND_MainSports` hero object and register its collider."""
    import bpy

    terrain = context["terrain"]
    raw_osm = context["raw_osm"]
    flat_pad_heights: dict[str, float] = context["flat_pad_heights"]
    solid_colliders = context["solid_colliders"]
    config = context["config"]

    poly = _extract_ground_polygon(raw_osm, config)
    if len(poly) < 4:
        return

    # Sample field elevations consistently with build_ground_features_object
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    max_z = -1e9
    min_edge_z = 1e9
    for p in poly:
        ez = terrain.sample(p[0], p[1])
        min_edge_z = min(min_edge_z, ez)
        max_z = max(max_z, ez)
    for ix in range(9):
        fx = min(xs) + (max(xs) - min(xs)) * (ix / 8.0)
        for iy in range(9):
            fy = min(ys) + (max(ys) - min(ys)) * (iy / 8.0)
            max_z = max(max_z, terrain.sample(fx, fy))

    z_top = flat_pad_heights.get(HERO_PLAYGROUND_ID, max_z + 0.26)
    flat_pad_heights[HERO_PLAYGROUND_ID] = z_top
    z_skirt = min_edge_z - 3.0

    # Identify NE / NW corners cleanly by projecting onto local ground axes (u, v)
    by_v_top = sorted(poly, key=lambda p: _world_to_local(p[0], p[1])[1], reverse=True)[:2]
    nw_pt, ne_pt = sorted(by_v_top, key=lambda p: _world_to_local(p[0], p[1])[0])
    by_v_bot = sorted(poly, key=lambda p: _world_to_local(p[0], p[1])[1])[:2]
    sw_pt, se_pt = sorted(by_v_bot, key=lambda p: _world_to_local(p[0], p[1])[0])

    # Expand East apron edge slightly out to behind gallery back wall so gallery rests solidly on terrace
    u_gallery_back = GALLERY_FRONT_U + GALLERY_TIERS * GALLERY_TREAD_D + 1.2
    se_u, se_v = _world_to_local(*se_pt)
    ne_u, ne_v = _world_to_local(*ne_pt)
    se_ext = _local_to_world(max(se_u, u_gallery_back), se_v)
    ne_ext = _local_to_world(max(ne_u, u_gallery_back), ne_v)
    slab_ring = [sw_pt, se_ext, ne_ext, nw_pt]  # CCW

    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    c_skirt = srgb_hex_to_linear_rgba("#989389")
    c_track = srgb_hex_to_linear_rgba("#C7704A")
    c_track_edge = srgb_hex_to_linear_rgba("#AE5E3C")
    c_lane = srgb_hex_to_linear_rgba("#EDEBE4")
    c_pitch_line = srgb_hex_to_linear_rgba("#E4E6DC")
    c_goal = srgb_hex_to_linear_rgba("#F6F4EE")

    # 1. Subdivided 18x18 smooth vertex-colored sunlit mowed grass slab (zero blocky tiles)
    grid_n = 18
    verts_grid: list[list[bmesh.types.BMVert]] = []
    cols_grid: list[list[tuple[float, float, float, float]]] = []
    for iy in range(grid_n + 1):
        ty = iy / grid_n
        row_v: list[bmesh.types.BMVert] = []
        row_c: list[tuple[float, float, float, float]] = []
        lx0 = sw_pt[0] * (1.0 - ty) + nw_pt[0] * ty
        ly0 = sw_pt[1] * (1.0 - ty) + nw_pt[1] * ty
        rx0 = se_ext[0] * (1.0 - ty) + ne_ext[0] * ty
        ry0 = se_ext[1] * (1.0 - ty) + ne_ext[1] * ty
        for ix in range(grid_n + 1):
            tx = ix / grid_n
            wx = lx0 * (1.0 - tx) + rx0 * tx
            wy = ly0 * (1.0 - tx) + ry0 * tx
            row_v.append(bm.verts.new((wx, wy, z_top)))
            row_c.append(_grass_color_at(wx, wy))
        verts_grid.append(row_v)
        cols_grid.append(row_c)

    for iy in range(grid_n):
        for ix in range(grid_n):
            v00 = verts_grid[iy][ix]
            v10 = verts_grid[iy][ix + 1]
            v11 = verts_grid[iy + 1][ix + 1]
            v01 = verts_grid[iy + 1][ix]
            _add_smooth_quad_vc(
                bm, col_layer,
                v00, v10, v11, v01,
                cols_grid[iy][ix],
                cols_grid[iy][ix + 1],
                cols_grid[iy + 1][ix + 1],
                cols_grid[iy + 1][ix],
            )

    # Perimeter vertical retaining skirt down to z_skirt (watertight terrain grounding)
    perimeter_top: list[bmesh.types.BMVert] = []
    for ix in range(grid_n):
        perimeter_top.append(verts_grid[0][ix])
    for iy in range(grid_n):
        perimeter_top.append(verts_grid[iy][grid_n])
    for ix in range(grid_n, 0, -1):
        perimeter_top.append(verts_grid[grid_n][ix])
    for iy in range(grid_n, 0, -1):
        perimeter_top.append(verts_grid[iy][0])
    perimeter_bot = [bm.verts.new((v.co.x, v.co.y, z_skirt)) for v in perimeter_top]
    pn = len(perimeter_top)
    for i in range(pn):
        j = (i + 1) % pn
        add_quad_vc(
            bm, col_layer,
            perimeter_bot[i], perimeter_bot[j], perimeter_top[j], perimeter_top[i],
            c_skirt,
        )

    # 2. Red-clay oval athletics track (+0.045m above grass) + 3 subtle white concentric lane lines
    z_track = z_top + 0.045
    _add_stadium_strip(
        bm, col_layer,
        TRACK_INNER_RADIUS, TRACK_OUTER_RADIUS, z_track, c_track,
        skirt_z=z_top + 0.005, skirt_rgba=c_track_edge, arc_segs=20,
    )
    z_lane = z_track + 0.018
    for lane_r in (
        TRACK_INNER_RADIUS + 0.35,
        TRACK_INNER_RADIUS + TRACK_WIDTH * 0.50,
        TRACK_OUTER_RADIUS - 0.35,
    ):
        _add_stadium_strip(bm, col_layer, lane_r - 0.08, lane_r + 0.08, z_lane, c_lane, arc_segs=20)

    # 3. Minimal faint white football pitch outline inside oval + twin white goalposts
    pitch_hw = 28.0
    pitch_hl = 48.0
    z_pitch = z_top + 0.028
    _add_thin_line_local(bm, col_layer, -pitch_hw, -pitch_hl, pitch_hw, -pitch_hl, 0.24, z_pitch, c_pitch_line)
    _add_thin_line_local(bm, col_layer, -pitch_hw, pitch_hl, pitch_hw, pitch_hl, 0.24, z_pitch, c_pitch_line)
    _add_thin_line_local(bm, col_layer, -pitch_hw, -pitch_hl, -pitch_hw, pitch_hl, 0.24, z_pitch, c_pitch_line)
    _add_thin_line_local(bm, col_layer, pitch_hw, -pitch_hl, pitch_hw, pitch_hl, 0.24, z_pitch, c_pitch_line)
    _add_thin_line_local(bm, col_layer, -pitch_hw, 0.0, pitch_hw, 0.0, 0.20, z_pitch, c_pitch_line)
    # Subtle penalty boxes at both goal ends
    for end_s in (-1.0, 1.0):
        gv = end_s * pitch_hl
        bv = end_s * (pitch_hl - 12.0)
        _add_thin_line_local(bm, col_layer, -14.0, bv, 14.0, bv, 0.20, z_pitch, c_pitch_line)
        _add_thin_line_local(bm, col_layer, -14.0, bv, -14.0, gv, 0.20, z_pitch, c_pitch_line)
        _add_thin_line_local(bm, col_layer, 14.0, bv, 14.0, gv, 0.20, z_pitch, c_pitch_line)

    _add_goalpost(bm, col_layer, v_pos=-pitch_hl, facing_sign=1.0, z_ground=z_top, c_goal=c_goal)
    _add_goalpost(bm, col_layer, v_pos=+pitch_hl, facing_sign=-1.0, z_ground=z_top, c_goal=c_goal)

    # 4. East concrete spectator gallery (7 tiers, 5 stair aisles, central projecting bastion)
    _build_east_concrete_gallery(bm, col_layer, z_top, z_skirt)

    # 5. Low weathered concrete perimeter boundary wall along far (north) edge
    _build_north_perimeter_wall(bm, col_layer, nw_pt, ne_ext, terrain, z_top)

    bm.normal_update()
    mat = _make_vertex_color_material("MAT_MainGround", roughness=0.88)
    mesh = bpy.data.meshes.new(name="GROUND_MainSports")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new("GROUND_MainSports", mesh)
    bpy.context.scene.collection.objects.link(obj)

    # Register extended ground + gallery + north wall collider so no random trees clip inside
    c_ring = get_main_ground_collider_ring()
    cx0, cy0 = min(p[0] for p in c_ring), min(p[1] for p in c_ring)
    cx1, cy1 = max(p[0] for p in c_ring), max(p[1] for p in c_ring)
    solid_colliders.append(((cx0, cy0, cx1, cy1), [c_ring]))

    # Keep unused helper reference clean
    _ = (add_tri_vc, slab_ring)
