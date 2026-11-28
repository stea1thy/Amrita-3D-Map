"""Modular Hero generator for Amrita Coimbatore Main Gate, Security Office & Parking Zone.

Replaces the undersized arch overlapping the railway corridor and generic cubes with:
1. `GROUND_MainGateSite`: railway level-crossing shoulders, campus compound wall, the crossing-side
   brick piers / AMRITA signage wings, and the white-piered
   iron-grille fence along the south verge of the approach road.
2. `BLDG_hero_main_gate` (`hero/main-gate`): the Kerala-style timber gatehouse over `way/128964701`
   (`refs/main_gate_irl_user.jpg`) -- 2-storey tower with tiled skirt roof and road balcony, one long
   terracotta hipped roof spanning the road onto timber posts with a west `mukhappu` gable, and a small
   tiled security cabin on the south kerb.
3. `BLDG_hero_security_office` (`hero/security-office`): the white mural-panelled visitor / security
   check shelter on the north kerb west of the gatehouse, with kerb railing and drop-off cone line.
4. `BLDG_hero_students_parking` (`hero/students-parking`): two open-sided covered two-wheeler sheds
   with slim steel pillars and light corrugated gable canopies (NO enclosed window boxes).
5. `BLDG_hero_visitor_parking` (`hero/visitor-parking`): paved Visitor / Car Parking lot with white
   parking bay lines, connector driveway, and minimal low-poly parked cars.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy

from hero_models.geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_gabled_roof_vc,
    add_hipped_roof_vc,
    add_quad_vc,
    add_tri_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# Perimeter compound wall runs ~12.3m north of north rail (-55.4, -408.3), tilted +2.15 deg E-W
WALL_ANCHOR_X = -55.5
WALL_ANCHOR_Y = -396.0
WALL_SLOPE = 0.0375  # dy/dx parallel to northern railway line
WALL_ROT_RAD = math.atan(WALL_SLOPE)

# Landmark coordinates calibrated directly from `pipeline/refs/main_gate_sat.jpg`
GATE_CX = -55.5
GATE_CY = -395.2

SEC_CX = -18.6
SEC_CY = -382.2

EAST_SHED_CX = -26.8
EAST_SHED_CY = -336.1
EAST_SHED_ROT = 0.24

WEST_SHED_CX = -42.8
WEST_SHED_CY = -320.0
WEST_SHED_ROT = 0.144

CAR_LOT_CX = 11.1
CAR_LOT_CY = -327.1
CAR_LOT_ROT = 0.20


def _wall_y(x: float) -> float:
    return WALL_ANCHOR_Y + (x - WALL_ANCHOR_X) * WALL_SLOPE


def _blender_to_gltf_xyz(x: float, y: float, z: float) -> list[float]:
    return [round(float(x), 2), round(float(z), 2), round(float(-y), 2)]


def _make_vcol_material(name: str, roughness: float = 0.80) -> bpy.types.Material:
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


def _link_bmesh_object(
    mesh_name: str,
    bm: bmesh.types.BMesh,
    mat: bpy.types.Material,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    bm.normal_update()
    mesh = bpy.data.meshes.new(name=mesh_name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(mesh_name, mesh)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _add_ground_quad_offset(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    hx: float,
    hy: float,
    z_top: float,
    rgba: tuple[float, float, float, float],
    rot_rad: float = 0.0,
    offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    ox, oy, oz = offset_xyz
    ca, sa = math.cos(rot_rad), math.sin(rot_rad)
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    verts = [
        bm.verts.new((cx + lx * ca - ly * sa - ox, cy + lx * sa + ly * ca - oy, z_top - oz))
        for lx, ly in corners
    ]
    add_quad_vc(bm, col_layer, verts[0], verts[1], verts[2], verts[3], rgba)


def _add_boom_barrier(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    ped_x: float,
    ped_y: float,
    arm_dir_rad: float,
    arm_len: float,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> None:
    """Emit a checkpoint pedestal and horizontal red-and-white striped boom barrier."""
    c_post = srgb_hex_to_linear_rgba("#D69E2E")
    c_base = srgb_hex_to_linear_rgba("#2D333B")
    c_red = srgb_hex_to_linear_rgba("#D63333")
    c_white = srgb_hex_to_linear_rgba("#F6F4EE")

    pz = terrain.sample(ped_x, ped_y)
    add_box_vc(
        bm, col_layer, ped_x, ped_y, pz - 0.5, pz + 0.16,
        0.34, 0.34, c_base, c_base, rot_rad=arm_dir_rad, offset_xyz=offset_xyz,
    )
    add_box_vc(
        bm, col_layer, ped_x, ped_y, pz + 0.16, pz + 1.08,
        0.20, 0.20, c_post, c_base, rot_rad=arm_dir_rad, offset_xyz=offset_xyz,
    )
    # 5 alternating red/white arm segments
    segs = 5
    seg_len = arm_len / segs
    for i in range(segs):
        dist = 0.25 + (i + 0.5) * seg_len
        sx = ped_x + dist * math.cos(arm_dir_rad)
        sy = ped_y + dist * math.sin(arm_dir_rad)
        col = c_red if i % 2 == 0 else c_white
        add_box_vc(
            bm, col_layer, sx, sy, pz + 0.88, pz + 1.00,
            seg_len * 0.49, 0.06, col, col, rot_rad=arm_dir_rad, emit_bottom=True, offset_xyz=offset_xyz,
        )


# OSM `way/128964701` south of the level crossing, towards the Coimbatore-Palakkad highway
SOUTH_ROAD_PTS = [(-55.7, -417.2), (-54.9, -454.2), (-54.3, -562.7), (-51.3, -568.2)]
SOUTH_ROAD_START_Y = -417.7   # just south of the concrete crossing plate
SOUTH_ROAD_MAX_LEN = 160.0


def _quad_facing(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    pts: list[tuple[float, float, float]],
    out_dir: tuple[float, float, float],
    rgba: tuple[float, float, float, float],
) -> None:
    """Emit a quad from 4 ordered world points, flipped if needed so its normal points along out_dir."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts[0], pts[1], pts[2]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    if nx * out_dir[0] + ny * out_dir[1] + nz * out_dir[2] < 0:
        pts = list(reversed(pts))
    v = [bm.verts.new(p) for p in pts]
    add_quad_vc(bm, col_layer, v[0], v[1], v[2], v[3], rgba)


def _add_beam(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    half_w: float,
    rgba: tuple[float, float, float, float],
) -> None:
    """Square-section beam between two world points (4 sides + far end cap)."""
    dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    dx, dy, dz = dx / length, dy / length, dz / length
    sx, sy, sz = dy, -dx, 0.0                     # horizontal side vector
    sl = math.hypot(sx, sy) or 1.0
    sx, sy = sx / sl, sy / sl
    ux, uy, uz = sy * dz - sz * dy, sz * dx - sx * dz, sx * dy - sy * dx
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]

    def c(p: tuple[float, float, float], a: int, b: int) -> tuple[float, float, float]:
        return (p[0] + (sx * a + ux * b) * half_w, p[1] + (sy * a + uy * b) * half_w, p[2] + (sz * a + uz * b) * half_w)

    for i in range(4):
        a0, b0 = corners[i]
        a1, b1 = corners[(i + 1) % 4]
        out = (sx * (a0 + a1) + ux * (b0 + b1), sy * (a0 + a1) + uy * (b0 + b1), sz * (a0 + a1) + uz * (b0 + b1))
        _quad_facing(bm, col_layer, [c(p0, a0, b0), c(p0, a1, b1), c(p1, a1, b1), c(p1, a0, b0)], out, rgba)
    _quad_facing(bm, col_layer, [c(p1, a, b) for a, b in corners], (dx, dy, dz), rgba)


def _add_level_crossing_gate(
    bm: bmesh.types.BMesh, col_layer: Any, terrain: Any, px: float, py: float, span_dir: float,
) -> None:
    """Indian Railways lifting-barrier gate: striped pedestal with counterweight and a red/white boom.

    The boom is shown raised (open, ~78 deg) over the carriageway it closes, with a rest post opposite.
    """
    c_yellow = srgb_hex_to_linear_rgba("#E5C544")
    c_black = srgb_hex_to_linear_rgba("#2C3035")
    c_red = srgb_hex_to_linear_rgba("#D63333")
    c_white = srgb_hex_to_linear_rgba("#F6F4EE")
    c_lamp = srgb_hex_to_linear_rgba("#E04A3A")

    pz = terrain.sample(px, py)
    add_box_vc(bm, col_layer, px, py, pz - 0.5, pz + 0.25, 0.42, 0.42, c_black, c_black)
    add_box_vc(bm, col_layer, px, py, pz + 0.25, pz + 0.75, 0.26, 0.26, c_yellow, c_yellow)
    add_box_vc(bm, col_layer, px, py, pz + 0.75, pz + 1.25, 0.26, 0.26, c_black, c_black)
    add_box_vc(bm, col_layer, px, py, pz + 1.25, pz + 1.45, 0.26, 0.26, c_yellow, c_black)

    pivot = (px, py, pz + 1.35)
    ang = math.radians(78.0)
    arm_len, segs = 6.6, 6
    dir3 = (span_dir * math.cos(ang), 0.0, math.sin(ang))
    for i in range(segs):
        a = 0.3 + i * arm_len / segs
        b = 0.3 + (i + 1) * arm_len / segs
        p0 = (pivot[0] + dir3[0] * a, pivot[1], pivot[2] + dir3[2] * a)
        p1 = (pivot[0] + dir3[0] * b, pivot[1], pivot[2] + dir3[2] * b)
        _add_beam(bm, col_layer, p0, p1, 0.07, c_red if i % 2 == 0 else c_white)
    # Counterweight stub behind the pivot
    _add_beam(bm, col_layer, pivot, (pivot[0] - dir3[0] * 0.9, pivot[1], pivot[2] - dir3[2] * 0.9), 0.16, c_black)
    # Rest post on the far kerb and a red warning lamp head on the pedestal side
    rx = px + span_dir * 7.3
    rz = terrain.sample(rx, py)
    add_box_vc(bm, col_layer, rx, py, rz - 0.4, rz + 0.95, 0.09, 0.09, c_black, c_yellow)
    add_box_vc(bm, col_layer, px - span_dir * 0.6, py, pz - 0.3, pz + 2.6, 0.06, 0.06, c_black, c_black)
    add_box_vc(bm, col_layer, px - span_dir * 0.6, py, pz + 2.35, pz + 2.65, 0.16, 0.12, c_lamp, c_black)


def _append_south_approach_road(bm: bmesh.types.BMesh, col_layer: Any, terrain: Any) -> None:
    """Asphalt carriageway + black/yellow kerb dashes continuing `way/128964701` south of the rails."""
    c_asphalt = srgb_hex_to_linear_rgba("#9EA4AB")
    c_kerbs = (srgb_hex_to_linear_rgba("#2C3035"), srgb_hex_to_linear_rgba("#E5C544"))
    half_w, kerb_w = 2.4, 0.42
    z_road, z_kerb = 0.275, 0.305  # sits just above the campus road's rounded end cap & kerb (0.23 / 0.265)

    end_y = max(SOUTH_ROAD_START_Y - SOUTH_ROAD_MAX_LEN, terrain.core_min_y + 2.0)
    # Resample the centreline every ~4 m from the start point down to end_y
    poly = [(SOUTH_ROAD_PTS[0][0], SOUTH_ROAD_START_Y)] + list(SOUTH_ROAD_PTS[1:])
    samples: list[tuple[float, float]] = [poly[0]]
    for (ax, ay), (bx, by) in zip(poly[:-1], poly[1:]):
        n = max(1, int(math.ceil(math.hypot(bx - ax, by - ay) / 4.0)))
        done = False
        for k in range(1, n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            if y <= end_y:
                t = (ay - end_y) / (ay - by)
                samples.append((ax + (bx - ax) * t, end_y))
                done = True
                break
            samples.append((x, y))
        if done:
            break

    def normal(i: int) -> tuple[float, float]:
        a = samples[max(0, i - 1)]
        b = samples[min(len(samples) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        return (dy / d, -dx / d)  # right-hand side when heading south (-y) is west (-x)

    def pt(i: int, off: float, dz: float) -> tuple[float, float, float]:
        x, y = samples[i]
        nx, ny = normal(i)
        wx, wy = x + nx * off, y + ny * off
        return (wx, wy, terrain.sample(wx, wy) + dz)

    for i in range(len(samples) - 1):
        _quad_facing(bm, col_layer, [pt(i, -half_w, z_road), pt(i, half_w, z_road), pt(i + 1, half_w, z_road),
                                      pt(i + 1, -half_w, z_road)], (0.0, 0.0, 1.0), c_asphalt)
        col = c_kerbs[i % 2]
        for side in (-1.0, 1.0):
            a_in, a_out = side * half_w, side * (half_w + kerb_w)
            _quad_facing(bm, col_layer, [pt(i, a_in, z_kerb), pt(i, a_out, z_kerb), pt(i + 1, a_out, z_kerb),
                                          pt(i + 1, a_in, z_kerb)], (0.0, 0.0, 1.0), col)
            nx, ny = normal(i)
            skirt = (col[0] * 0.72, col[1] * 0.72, col[2] * 0.72, 1.0)
            q0, q1 = pt(i, a_out, z_kerb), pt(i + 1, a_out, z_kerb)
            _quad_facing(bm, col_layer, [(q0[0], q0[1], q0[2] - 0.45), (q1[0], q1[1], q1[2] - 0.45), q1, q0],
                         (nx * side, ny * side, 0.0), skirt)



def _build_site_crossing_and_wall(terrain: Any, mat: bpy.types.Material) -> None:
    """Build railway level-crossing road apron/shoulders and campus brick-and-cream perimeter compound wall."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    c_stripe = srgb_hex_to_linear_rgba("#E8D24A")
    c_dark = srgb_hex_to_linear_rgba("#25292E")
    c_brick = srgb_hex_to_linear_rgba("#A65E44")
    c_cream = srgb_hex_to_linear_rgba("#EFE8DC")
    c_coping = srgb_hex_to_linear_rgba("#9E5B42")

    # 1. Railway level crossing (rails at y -408.3 / -417.2): warning posts, lifting-barrier gates on both
    #    approaches, and the approach road extended south of the tracks (campus roads stop at the rails)
    _append_south_approach_road(bm, col_layer, terrain)
    _add_level_crossing_gate(bm, col_layer, terrain, -51.85, -403.0, -1.0)  # north approach, arm spans west
    _add_level_crossing_gate(bm, col_layer, terrain, -59.35, -422.4, 1.0)   # south approach, arm spans east
    for lx, ly in ((-55.55, -420.5), (-55.55, -404.2)):
        for side in (-1.0, 1.0):
            bx, by = lx + side * 4.4, ly
            bz = terrain.sample(bx, by)
            add_box_vc(bm, col_layer, bx, by, bz - 0.4, bz + 0.9, 0.16, 0.16, c_dark, c_stripe)
            add_box_vc(bm, col_layer, bx, by, bz + 0.9, bz + 1.45, 0.18, 0.18, c_stripe, c_dark)

    # 2. Continuous Campus Compound Wall parallel to the northern railway tracks (gap [-63.2 .. -47.8] at Main Gate)
    for x0, x1 in ((-165.0, -63.2), (-47.8, 122.0)):
        span = x1 - x0
        steps = max(2, int(round(span / 14.0)))
        dx_step = span / steps
        for i in range(steps):
            xa = x0 + i * dx_step
            xb = x0 + (i + 1) * dx_step
            xm = 0.5 * (xa + xb)
            ym = _wall_y(xm)
            zm = terrain.sample(xm, ym)
            half_seg = math.hypot(xb - xa, _wall_y(xb) - _wall_y(xa)) * 0.5
            # Lower brick plinth + cream wall body + terracotta coping
            add_box_vc(
                bm, col_layer, xm, ym, zm - 1.5, zm + 0.70,
                half_seg, 0.22, c_brick, c_brick, rot_rad=WALL_ROT_RAD,
            )
            add_box_vc(
                bm, col_layer, xm, ym, zm + 0.70, zm + 2.05,
                half_seg, 0.19, c_cream, c_cream, rot_rad=WALL_ROT_RAD,
            )
            add_box_vc(
                bm, col_layer, xm, ym, zm + 2.05, zm + 2.24,
                half_seg + 0.04, 0.25, c_coping, c_coping, rot_rad=WALL_ROT_RAD,
            )

        # Brick masonry pilasters every ~14m along the compound wall
        for i in range(steps + 1):
            px = x0 + i * dx_step
            py = _wall_y(px)
            pz = terrain.sample(px, py)
            add_box_vc(
                bm, col_layer, px, py, pz - 1.5, pz + 2.48,
                0.34, 0.34, c_brick, c_coping, rot_rad=WALL_ROT_RAD,
            )

    _append_crossing_gate(bm, col_layer, terrain)
    _append_south_kerb_fence(bm, col_layer, terrain)

    _link_bmesh_object("GROUND_MainGateSite", bm, mat)


def _append_crossing_gate(bm: bmesh.types.BMesh, col_layer: Any, terrain: Any) -> None:
    """Railway-crossing entry: brick piers with lantern caps and AMRITA signage wing walls (no booth/barrier/canopy)."""
    offset_xyz = (0.0, 0.0, 0.0)

    c_brick = srgb_hex_to_linear_rgba("#A65E44")
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_maroon = srgb_hex_to_linear_rgba(HERO_PALETTE["amrita_maroon"])
    c_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_glass = srgb_hex_to_linear_rgba("#384958")

    # 1. Twin tall terracotta-brick square entrance piers with cream cornice & modern lantern caps (main_gate_arch.jpg)
    for side in (-1.0, 1.0):
        px = GATE_CX + side * 6.2
        py = _wall_y(px)
        pz = terrain.sample(px, py)
        add_box_vc(bm, col_layer, px, py, pz - 1.5, pz + 0.65, 0.85, 0.85, c_cream, c_brick, rot_rad=WALL_ROT_RAD, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, px, py, pz + 0.65, pz + 4.35, 0.74, 0.74, c_brick, c_white, rot_rad=WALL_ROT_RAD, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, px, py, pz + 4.35, pz + 4.65, 0.84, 0.84, c_cream, c_brick, rot_rad=WALL_ROT_RAD, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, px, py, pz + 4.65, pz + 5.28, 0.44, 0.44, c_glass, c_dark, rot_rad=WALL_ROT_RAD, offset_xyz=offset_xyz)

        # Flanking wing walls with carved AMRITA signage marquee on south (approach) face
        wx = px + side * 3.8
        wy = _wall_y(wx)
        wz = terrain.sample(wx, wy)
        add_box_vc(bm, col_layer, wx, wy, wz - 1.5, wz + 2.65, 2.95, 0.28, c_brick, c_cream, rot_rad=WALL_ROT_RAD, offset_xyz=offset_xyz)
        sx, sy = local_to_world_2d(wx, wy, 0.0, -0.31, WALL_ROT_RAD)
        add_box_vc(bm, col_layer, sx, sy, wz + 1.15, wz + 2.15, 2.35, 0.05, c_maroon, c_maroon, rot_rad=WALL_ROT_RAD, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, sx, sy - 0.03, wz + 1.45, wz + 1.88, 1.95, 0.04, c_white, c_white, rot_rad=WALL_ROT_RAD, offset_xyz=offset_xyz)


def _road_cy(x: float) -> float:
    """Centreline Y of `way/128964701` on its straight run from the bend (-48.1) to the gatehouse (0.9)."""
    if x <= -28.2:
        return -384.2 + (x + 48.1) * (1.3 / 19.9)
    return -382.9 + (x + 28.2) * (0.6 / 29.1)


def _wall_quad(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    a: tuple[float, float],
    b: tuple[float, float],
    z0: float,
    z1: float,
    rgba: tuple[float, float, float, float],
    offset_xyz: tuple[float, float, float],
) -> None:
    """Vertical quad from a to b; its face points to the right of a->b (outward on a CCW ring)."""
    ox, oy, oz = offset_xyz
    v = [
        bm.verts.new((a[0] - ox, a[1] - oy, z0 - oz)),
        bm.verts.new((b[0] - ox, b[1] - oy, z0 - oz)),
        bm.verts.new((b[0] - ox, b[1] - oy, z1 - oz)),
        bm.verts.new((a[0] - ox, a[1] - oy, z1 - oz)),
    ]
    add_quad_vc(bm, col_layer, v[0], v[1], v[2], v[3], rgba)


def _framed_window(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    a: tuple[float, float],
    b: tuple[float, float],
    z0: float,
    z1: float,
    out_n: tuple[float, float],
    frame_rgba: tuple[float, float, float, float],
    glass_rgba: tuple[float, float, float, float],
    offset_xyz: tuple[float, float, float],
) -> None:
    """Light timber frame quad with an inset dark glass pane, both proud of the wall along out_n."""
    nx, ny = out_n
    ux, uy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(ux, uy)
    ux, uy = ux / length, uy / length
    f = 0.10
    _wall_quad(
        bm, col_layer, (a[0] + nx * 0.03, a[1] + ny * 0.03), (b[0] + nx * 0.03, b[1] + ny * 0.03),
        z0, z1, frame_rgba, offset_xyz,
    )
    _wall_quad(
        bm, col_layer,
        (a[0] + ux * f + nx * 0.05, a[1] + uy * f + ny * 0.05),
        (b[0] - ux * f + nx * 0.05, b[1] - uy * f + ny * 0.05),
        z0 + f, z1 - f, glass_rgba, offset_xyz,
    )


def _build_gatehouse_object(terrain: Any, mat: bpy.types.Material) -> list[tuple[float, float, float]]:
    """Kerala-style timber gatehouse over `way/128964701` (`refs/main_gate_irl_user.jpg`).

    North of the road: a 2-storey timber tower (`way/546394580`) with a tiled skirt roof, upper-floor
    windows and a road-facing balcony. One long terracotta hipped roof (satellite: x -23.3..-13.7,
    y -368.7..-387.1) spans the road onto two timber posts and carries a gabled `mukhappu` on its
    west slope. South of the road: a small timber security cabin with its own tiled roof (`way/546394581`).
    """
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    zr = terrain.sample(-18.5, -382.7)
    offset_xyz = (-18.5, -378.0, zr)

    c_plinth = srgb_hex_to_linear_rgba(HERO_PALETTE["sandstone_plinth"])
    c_timber = srgb_hex_to_linear_rgba("#A8693B")
    c_timber_up = srgb_hex_to_linear_rgba("#B37243")
    c_timber_dk = srgb_hex_to_linear_rgba("#5C3A24")
    c_soffit = srgb_hex_to_linear_rgba("#6E472C")
    c_frame = srgb_hex_to_linear_rgba("#E6D6B8")
    c_glass = srgb_hex_to_linear_rgba("#2B3138")
    c_tile = srgb_hex_to_linear_rgba("#BE6440")
    c_tile_dk = srgb_hex_to_linear_rgba("#A9553A")
    c_gable_in = srgb_hex_to_linear_rgba("#3A2416")

    # Tower plan (OSM way/546394580, trimmed clear of the 5.6 m carriageway edge at y -379.9)
    tx0, tx1 = -22.2, -14.8
    ty0, ty1 = -379.2, -371.6
    tcx, tcy = 0.5 * (tx0 + tx1), 0.5 * (ty0 + ty1)
    thx, thy = 0.5 * (tx1 - tx0), 0.5 * (ty1 - ty0)

    z_g = zr + 0.35      # ground floor level
    z_skirt = zr + 3.05  # skirt-roof eave
    z_up = zr + 3.9      # upper floor level
    z_eave = zr + 7.0    # main roof eave
    z_ridge = zr + 9.7

    # 1. Tower: laterite plinth, timber ground storey, tiled skirt roof, timber upper storey
    add_box_vc(bm, col_layer, tcx, tcy, zr - 1.0, z_g, thx + 0.12, thy + 0.12, c_plinth, c_plinth, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, tcx, tcy, z_g, z_skirt + 0.2, thx, thy, c_timber, c_timber, offset_xyz=offset_xyz)
    # Ground-storey windows: two on the west (approach) face, one beside the door on the road face
    for wy in (-377.4, -373.6):
        _framed_window(bm, col_layer, (tx0, wy + 0.7), (tx0, wy - 0.7), z_g + 0.9, z_g + 2.2,
                       (-1.0, 0.0), c_frame, c_glass, offset_xyz)
    _framed_window(bm, col_layer, (tx0 + 1.0, ty0), (tx0 + 2.4, ty0), z_g + 0.9, z_g + 2.2,
                   (0.0, -1.0), c_frame, c_glass, offset_xyz)
    _framed_window(bm, col_layer, (tx1 - 2.6, ty0), (tx1 - 1.4, ty0), z_g, z_g + 2.3,
                   (0.0, -1.0), c_timber_dk, c_glass, offset_xyz)
    # Skirt roof: a sloped tile ring, eaves 0.9 m out, rising 0.8 m to the wall line (tucked under the balcony
    # on the road side), with a flat timber soffit underneath
    ox, oy, oz = offset_xyz
    ring_out = [(tx0 - 0.9, ty0 - 0.9), (tx1 + 0.9, ty0 - 0.9), (tx1 + 0.9, ty1 + 0.9), (tx0 - 0.9, ty1 + 0.9)]
    ring_in = [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)]
    o_v = [bm.verts.new((x - ox, y - oy, z_skirt - oz)) for x, y in ring_out]
    i_v = [bm.verts.new((x - ox, y - oy, z_skirt + 0.8 - oz)) for x, y in ring_in]
    s_v = [bm.verts.new((x - ox, y - oy, z_skirt - oz)) for x, y in ring_in]
    for i in range(4):
        j = (i + 1) % 4
        add_quad_vc(bm, col_layer, o_v[i], o_v[j], i_v[j], i_v[i], c_tile)
        add_quad_vc(bm, col_layer, s_v[i], s_v[j], o_v[j], o_v[i], c_soffit)

    # Upper storey: enclosed rooms on the north, balcony facing the road on the south
    uy0 = -377.8
    add_box_vc(bm, col_layer, tcx, 0.5 * (uy0 + ty1), z_up - 0.1, z_eave, thx, 0.5 * (ty1 - uy0),
               c_timber_up, c_timber_up, offset_xyz=offset_xyz)
    for wy in (-376.6, -374.7, -372.8):
        _framed_window(bm, col_layer, (tx0, wy + 0.62), (tx0, wy - 0.62), z_up + 0.75, z_up + 2.35,
                       (-1.0, 0.0), c_frame, c_glass, offset_xyz)
        _framed_window(bm, col_layer, (tx1, wy - 0.62), (tx1, wy + 0.62), z_up + 0.75, z_up + 2.35,
                       (1.0, 0.0), c_frame, c_glass, offset_xyz)
    for wx in (-20.4, -16.6):
        _framed_window(bm, col_layer, (wx + 0.7, ty1), (wx - 0.7, ty1), z_up + 0.75, z_up + 2.35,
                       (0.0, 1.0), c_frame, c_glass, offset_xyz)
    # Balcony doors onto the road-facing balcony
    for wx in (-20.2, -16.8):
        _framed_window(bm, col_layer, (wx - 0.8, uy0), (wx + 0.8, uy0), z_up, z_up + 2.4,
                       (0.0, -1.0), c_frame, c_glass, offset_xyz)
    by0 = -379.6
    add_box_vc(bm, col_layer, tcx, 0.5 * (by0 + uy0), z_up - 0.2, z_up, thx + 0.1, 0.5 * (uy0 - by0),
               c_timber_dk, c_timber_dk, emit_bottom=True, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, tcx, by0 + 0.05, z_up, z_up + 1.0, thx + 0.05, 0.05,
               c_timber_dk, c_frame, offset_xyz=offset_xyz)
    for px in (tx0 + 0.12, tx1 - 0.12):
        add_box_vc(bm, col_layer, px, by0 + 0.12, z_up, z_eave, 0.12, 0.12,
                   c_timber_dk, c_timber_dk, offset_xyz=offset_xyz)

    # 2. Road span: two timber posts on stone bases, tie beams back to the tower
    sy = -386.3
    for px in (-22.6, -14.4):
        pz = terrain.sample(px, sy)
        add_box_vc(bm, col_layer, px, sy, pz - 0.6, pz + 0.55, 0.34, 0.34, c_plinth, c_plinth, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, px, sy, pz + 0.55, z_eave, 0.21, 0.21, c_timber_dk, c_timber_dk, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, px, 0.5 * (sy + ty0), z_eave - 0.42, z_eave, 0.16, 0.5 * (ty0 - sy),
                   c_timber_dk, c_timber_dk, emit_bottom=True, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, -18.5, sy, z_eave - 0.48, z_eave, 4.3, 0.17,
               c_timber_dk, c_timber_dk, emit_bottom=True, offset_xyz=offset_xyz)

    # 3. Main terracotta hipped roof across the road (fascia slab doubles as the timber soffit)
    rcx, rcy, rhx, rhy = -18.5, -378.3, 4.85, 8.85
    add_box_vc(bm, col_layer, rcx, rcy, z_eave - 0.22, z_eave, rhx, rhy, c_soffit, c_soffit,
               emit_bottom=True, offset_xyz=offset_xyz)
    add_hipped_roof_vc(bm, col_layer, rcx, rcy, z_eave, z_ridge, rhx, rhy, c_tile, offset_xyz=offset_xyz)

    # 4. Kerala `mukhappu` gable on the west slope, centred over the tower/road junction
    slope = (z_ridge - z_eave) / rhx
    gx0 = rcx - rhx + 1.45          # front face of the gable
    gz_roof = z_eave + 1.45 * slope  # main-roof surface under that face
    g_eave, g_peak, g_hy = gz_roof + 0.32, z_ridge - 0.22, 1.55
    gcx, ghx = 0.5 * (gx0 + rcx), 0.5 * (rcx - gx0)
    add_gabled_roof_vc(bm, col_layer, gcx, rcy, g_eave, g_peak, ghx, g_hy + 0.18,
                       c_tile_dk, c_timber, ridge_along_x=True, offset_xyz=offset_xyz)
    _wall_quad(bm, col_layer, (gx0, rcy + g_hy + 0.18), (gx0, rcy - g_hy - 0.18), gz_roof - 0.05, g_eave,
               c_timber_dk, offset_xyz)
    gi = [
        bm.verts.new((gx0 - 0.04 - ox, rcy + g_hy * 0.62 - oy, g_eave + 0.12 - oz)),
        bm.verts.new((gx0 - 0.04 - ox, rcy - g_hy * 0.62 - oy, g_eave + 0.12 - oz)),
        bm.verts.new((gx0 - 0.04 - ox, rcy - oy, g_peak - 0.32 - oz)),
    ]
    add_tri_vc(bm, col_layer, (gi[0], gi[1], gi[2]), c_gable_in)

    # 5. Toll gate under the span: staggered entry/exit boom barriers with face-scan posts on each kerb
    c_scan = srgb_hex_to_linear_rgba("#2F353C")
    c_screen = srgb_hex_to_linear_rgba("#7FB3D9")
    for bx, by, arm_dir in ((-20.6, -380.1, -0.5 * math.pi), (-16.4, -385.3, 0.5 * math.pi)):
        _add_boom_barrier(bm, col_layer, bx, by, arm_dir, 2.3, terrain, offset_xyz)
        sx = bx + (1.0 if by > -382.7 else -1.0)
        sz = terrain.sample(sx, by)
        add_box_vc(bm, col_layer, sx, by, sz - 0.3, sz + 1.45, 0.13, 0.13, c_scan, c_scan, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, sx, by, sz + 1.2, sz + 1.55, 0.17, 0.05, c_screen, c_scan, offset_xyz=offset_xyz)

    # 6. Security cabin on the south verge just in front of the west span post, under the big shade tree
    #    (`refs/main_gate_irl_user.jpg`), between the kerb (-385.6) and the white-pier fence (-389.1)
    kcx, kcy, khx, khy = -26.2, -387.4, 2.2, 1.35
    kz = terrain.sample(kcx, kcy)
    add_box_vc(bm, col_layer, kcx, kcy, kz - 0.8, kz + 0.3, khx + 0.1, khy + 0.1, c_plinth, c_plinth, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, kcx, kcy, kz + 0.3, kz + 2.8, khx, khy, c_timber, c_timber, offset_xyz=offset_xyz)
    _framed_window(bm, col_layer, (kcx + 0.6, kcy + khy), (kcx - 1.8, kcy + khy), kz + 1.1, kz + 2.25,
                   (0.0, 1.0), c_frame, c_glass, offset_xyz)
    _framed_window(bm, col_layer, (kcx - khx, kcy + 0.8), (kcx - khx, kcy - 0.8), kz + 1.1, kz + 2.25,
                   (-1.0, 0.0), c_frame, c_glass, offset_xyz)
    add_hipped_roof_vc(bm, col_layer, kcx, kcy, kz + 2.75, kz + 4.35, khx + 0.6, khy + 0.6,
                       c_tile, soffit_rgba=c_soffit, offset_xyz=offset_xyz)

    _link_bmesh_object("BLDG_hero_main_gate", bm, mat, location=offset_xyz)
    return [
        (kcx - khx - 0.6, rcy - rhy - 2.0, zr),
        (rcx + rhx, rcy - rhy - 2.0, zr),
        (rcx + rhx, rcy + rhy, z_ridge),
        (kcx - khx - 0.6, rcy + rhy, z_ridge),
    ]


def _build_visitor_shelter_object(terrain: Any, mat: bpy.types.Material) -> list[tuple[float, float, float]]:
    """White mural-panelled visitor & security-check shelter on the north kerb west of the gatehouse.

    `refs/main_gate_irl_user.jpg`: a flat-roofed white pavilion parallel to the road, its road side
    made of mural panels ("discover") with open bays between, a steel railing along the kerb and a
    line of traffic cones marking the visitor drop-off lane.
    """
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    rot = math.atan2(1.3, 19.9)  # parallel to the bend->gatehouse road segment
    lcx = -36.8
    lcy = _road_cy(lcx) + 7.0
    zs = terrain.sample(lcx, lcy) + 0.55  # raised walkway level
    offset_xyz = (lcx, lcy, zs)
    hx, hy = 9.0, 2.7

    c_slab = srgb_hex_to_linear_rgba("#B9B6AE")
    c_white = srgb_hex_to_linear_rgba("#F3F3F0")
    c_steel = srgb_hex_to_linear_rgba("#C4C9CE")
    c_dark = srgb_hex_to_linear_rgba("#3A3F46")
    c_cone = srgb_hex_to_linear_rgba("#EE5A1E")
    murals = [srgb_hex_to_linear_rgba(h) for h in ("#6F9AD8", "#5FB8A6", "#EE9A62", "#9C7FC8", "#E07A92", "#6F9AD8")]

    def at(lx: float, ly: float) -> tuple[float, float]:
        return local_to_world_2d(lcx, lcy, lx, ly, rot)

    def box(lx: float, ly: float, z0: float, z1: float, bhx: float, bhy: float, wall, cap=None, bottom=False) -> None:
        wx, wy = at(lx, ly)
        add_box_vc(bm, col_layer, wx, wy, z0, z1, bhx, bhy, wall, cap, rot_rad=rot, emit_bottom=bottom, offset_xyz=offset_xyz)

    # Floor slab and flat white roof with a light underside
    box(0.0, 0.0, zs - 0.7, zs, hx + 0.2, hy + 0.2, c_slab)
    box(0.0, 0.0, zs + 3.0, zs + 3.32, hx + 0.15, hy + 0.15, c_white, c_white, bottom=True)

    # Road-side mural panels with open bays between them, plus closed mural end walls
    panel_hw = 1.55
    for i, lx in enumerate((-6.75, -2.25, 2.25, 6.75)):
        box(lx, -hy, zs, zs + 3.0, panel_hw, 0.06, c_white)
        a = at(lx - panel_hw * 0.8, -hy - 0.07)
        b = at(lx + panel_hw * 0.8, -hy - 0.07)
        z_lo = zs + (0.7 if i % 2 == 0 else 1.25)
        _wall_quad(bm, col_layer, a, b, z_lo, z_lo + 0.85, murals[i], offset_xyz)
    for side, mural in ((-1.0, murals[4]), (1.0, murals[5])):
        box(side * hx, 0.0, zs, zs + 3.0, 0.06, hy, c_white)
        a = at(side * (hx + 0.07), -side * hy * 0.75)
        b = at(side * (hx + 0.07), side * hy * 0.75)
        _wall_quad(bm, col_layer, a, b, zs + 1.0, zs + 1.9, mural, offset_xyz)
    # Face-scan pedestals in the open bays between the mural panels
    for lx in (-4.5, 0.0, 4.5):
        box(lx, -hy + 0.5, zs, zs + 1.45, 0.14, 0.14, c_dark)
        box(lx, -hy + 0.5, zs + 1.2, zs + 1.55, 0.2, 0.05, srgb_hex_to_linear_rgba("#7FB3D9"), c_dark)
    # Slim back columns (open rear) and two long benches
    for lx in (-4.5, 0.0, 4.5):
        box(lx, hy - 0.1, zs, zs + 3.0, 0.08, 0.08, c_white)
    for lx in (-4.5, 4.5):
        box(lx, 0.9, zs, zs + 0.45, 3.2, 0.25, c_dark)

    # Raised walkway along the kerb (the shelter floor level) with a steel grille railing on its road edge,
    # an access step at the gate end, and the cone line marking the drop-off lane
    rail_y = -hy - 1.25
    box(0.0, -hy - 0.7, zs - 0.95, zs, hx + 0.6, 0.65, c_slab)
    box(hx + 1.0, -hy - 0.7, zs - 0.95, zs - 0.27, 0.4, 0.65, c_slab)
    box(0.0, rail_y, zs + 0.95, zs + 1.02, hx + 0.55, 0.03, c_steel, bottom=True)
    box(0.0, rail_y, zs + 0.1, zs + 0.15, hx + 0.55, 0.025, c_steel, bottom=True)
    n_bal = 17
    for k in range(n_bal):
        lx = -hx - 0.5 + k * (2 * hx + 1.0) / (n_bal - 1)
        box(lx, rail_y, zs, zs + 1.02, 0.025, 0.025, c_steel)
    for k in range(6):
        lx = -7.5 + k * 3.0
        cx_c, cy_c = at(lx, -hy - 2.6)
        cz = terrain.sample(cx_c, cy_c)
        add_cylinder_vc(bm, col_layer, cx_c, cy_c, cz - 0.05, cz + 0.72, 0.2, 0.03, 4, c_cone,
                        rot_rad=rot + math.pi / 4, offset_xyz=offset_xyz)

    _link_bmesh_object("BLDG_hero_security_office", bm, mat, location=offset_xyz)
    pts = [at(-hx - 0.6, -hy - 2.9), at(hx + 0.6, -hy - 2.9), at(hx + 0.2, hy + 0.2), at(-hx - 0.2, hy + 0.2)]
    return [(px, py, zs + (3.3 if i >= 2 else -0.2)) for i, (px, py) in enumerate(pts)]


def _append_south_kerb_fence(bm: bmesh.types.BMesh, col_layer: Any, terrain: Any) -> None:
    """White-piered compound fence with dark iron grille along the south verge, bend -> security cabin."""
    c_white = srgb_hex_to_linear_rgba("#F1EFEA")
    c_grille = srgb_hex_to_linear_rgba("#454B53")
    rot = math.atan2(1.3, 19.9)
    xs = [-46.0 + i * 3.75 for i in range(7)]  # -46.0 .. -23.5
    piers = [(x, _road_cy(x) - 6.3) for x in xs]
    for (xa, ya), (xb, yb) in zip(piers[:-1], piers[1:]):
        xm, ym = 0.5 * (xa + xb), 0.5 * (ya + yb)
        zm = terrain.sample(xm, ym)
        half = 0.5 * math.hypot(xb - xa, yb - ya)
        add_box_vc(bm, col_layer, xm, ym, zm - 0.5, zm + 0.6, half, 0.13, c_white, c_white, rot_rad=rot)
        add_box_vc(bm, col_layer, xm, ym, zm + 0.6, zm + 1.85, half, 0.025, c_grille, c_grille, rot_rad=rot)
    for px, py in piers:
        pz = terrain.sample(px, py)
        add_box_vc(bm, col_layer, px, py, pz - 0.5, pz + 2.1, 0.24, 0.24, c_white, c_white, rot_rad=rot)
        add_box_vc(bm, col_layer, px, py, pz + 2.1, pz + 2.3, 0.31, 0.31, c_white, c_white, rot_rad=rot)


def _build_students_parking_object(terrain: Any, mat: bpy.types.Material) -> list[tuple[float, float, float]]:
    """Build two open-sided corrugated-roof two-wheeler sheds matching `main_gate_sat.jpg` (zero walls/windows)."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    cx_b = 0.5 * (EAST_SHED_CX + WEST_SHED_CX)
    cy_b = 0.5 * (EAST_SHED_CY + WEST_SHED_CY)
    cz_b = terrain.sample(cx_b, cy_b) + 1.8
    offset_xyz = (cx_b, cy_b, cz_b)

    c_slab = srgb_hex_to_linear_rgba("#B6B4AD")
    c_curb = srgb_hex_to_linear_rgba("#8F8D86")
    c_steel = srgb_hex_to_linear_rgba("#383E46")
    c_roof_top = srgb_hex_to_linear_rgba("#DCE0E5")
    c_roof_rib = srgb_hex_to_linear_rgba("#B9C0C8")
    c_roof_under = srgb_hex_to_linear_rgba("#9CA2AA")

    sheds = (
        (EAST_SHED_CX, EAST_SHED_CY, 4.0, 13.75, EAST_SHED_ROT),
        (WEST_SHED_CX, WEST_SHED_CY, 4.2, 15.25, WEST_SHED_ROT),
    )
    for scx, scy, hx, hy, srot in sheds:
        zs = [
            terrain.sample(*local_to_world_2d(scx, scy, lx, ly, srot))
            for lx in (-hx, hx)
            for ly in (-hy, 0.0, hy)
        ]
        z_pad = max(zs) + 0.14
        z_bot = min(zs) - 1.5
        # Concrete floor apron
        add_box_vc(bm, col_layer, scx, scy, z_bot, z_pad, hx, hy, c_curb, c_slab, rot_rad=srot, offset_xyz=offset_xyz)

        # Open perimeter dark steel columns (6 bays along length, ZERO side walls)
        n_bays = 5
        for i in range(n_bays + 1):
            ly = -hy + 0.8 + (2.0 * hy - 1.6) * (i / n_bays)
            for lx in (-hx + 0.45, hx - 0.45):
                px, py = local_to_world_2d(scx, scy, lx, ly, srot)
                add_cylinder_vc(
                    bm, col_layer, px, py, z_pad - 0.05, z_pad + 2.95,
                    0.10, 0.10, 5, c_steel, c_steel, offset_xyz=offset_xyz,
                )

        # Lightweight pitched corrugated metal canopy & subtle purlin ribs
        z_eave = z_pad + 2.92
        z_peak = z_pad + 3.95
        add_gabled_roof_vc(
            bm, col_layer, scx, scy, z_eave, z_peak,
            hx + 0.55, hy + 0.45, c_roof_top, c_roof_under,
            rot_rad=srot, ridge_along_x=False, soffit_rgba=c_roof_under, offset_xyz=offset_xyz,
        )
        # Raised roof ridge cap so shed roof reads crisply from top & 3/4 views
        add_box_vc(
            bm, col_layer, scx, scy, z_peak - 0.05, z_peak + 0.10,
            0.22, hy + 0.46, c_roof_rib, c_roof_rib, rot_rad=srot, offset_xyz=offset_xyz,
        )

    # Paved concrete apron linking East & West sheds smoothly
    ax, ay = -34.2, -330.0
    az = terrain.sample(ax, ay)
    add_box_vc(bm, col_layer, ax, ay, az - 1.5, az + 0.12, 4.5, 6.0, c_curb, c_slab, rot_rad=0.20, offset_xyz=offset_xyz)

    _link_bmesh_object("BLDG_hero_students_parking", bm, mat, location=offset_xyz)
    return [
        (-48.5, -350.0, cz_b - 2.0),
        (-22.0, -350.0, cz_b + 4.5),
        (-22.0, -304.0, cz_b + 4.5),
        (-48.5, -304.0, cz_b - 2.0),
    ]


def _build_visitor_parking_object(terrain: Any, mat: bpy.types.Material) -> list[tuple[float, float, float]]:
    """Build sloped-to-grade Visitor / Car Parking lot, short NW-road connector driveway & low-poly parked cars."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    cx_b, cy_b = CAR_LOT_CX, CAR_LOT_CY
    hx, hy, rot = 26.8, 11.4, CAR_LOT_ROT

    # Fit an exact planar slope to terrain across the lot so edges stay ~0.16-0.35m above grade (no cliff)
    z_sw = terrain.sample(*local_to_world_2d(cx_b, cy_b, -hx, -hy, rot))
    z_se = terrain.sample(*local_to_world_2d(cx_b, cy_b, hx, -hy, rot))
    z_nw = terrain.sample(*local_to_world_2d(cx_b, cy_b, -hx, hy, rot))
    z_ne = terrain.sample(*local_to_world_2d(cx_b, cy_b, hx, hy, rot))
    z0 = 0.25 * (z_sw + z_se + z_nw + z_ne)
    dz_dlx = ((z_ne + z_se) - (z_nw + z_sw)) / (4.0 * hx)
    dz_dly = ((z_ne + z_nw) - (z_se + z_sw)) / (4.0 * hy)

    max_err = -1e9
    for ix in range(5):
        lx = -hx + (2.0 * hx) * (ix / 4.0)
        for iy in range(5):
            ly = -hy + (2.0 * hy) * (iy / 4.0)
            wx, wy = local_to_world_2d(cx_b, cy_b, lx, ly, rot)
            tz = terrain.sample(wx, wy) + 0.16
            pz = z0 + dz_dlx * lx + dz_dly * ly
            max_err = max(max_err, tz - pz)
    z0 += max(0.0, max_err)

    def _z_lot(lx: float, ly: float) -> float:
        return z0 + dz_dlx * lx + dz_dly * ly

    cz_b = z0 + 0.7
    offset_xyz = (cx_b, cy_b, cz_b)
    ox, oy, oz = offset_xyz

    c_lot = srgb_hex_to_linear_rgba("#ACA89F")
    c_curb = srgb_hex_to_linear_rgba("#87857F")
    c_line = srgb_hex_to_linear_rgba("#ECEAE4")
    c_glass = srgb_hex_to_linear_rgba("#27313C")
    car_colors = (
        srgb_hex_to_linear_rgba("#F2F1ED"),
        srgb_hex_to_linear_rgba("#9AA3AD"),
        srgb_hex_to_linear_rgba("#4E5863"),
        srgb_hex_to_linear_rgba("#2E4460"),
        srgb_hex_to_linear_rgba("#7C343A"),
        srgb_hex_to_linear_rgba("#D3CBB8"),
    )

    # 1. Planar terrain-matched parking terrace + grounded perimeter retaining skirt
    lot_corners_local = ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))
    top_v: list[bmesh.types.BMVert] = []
    bot_v: list[bmesh.types.BMVert] = []
    for lx, ly in lot_corners_local:
        wx, wy = local_to_world_2d(cx_b, cy_b, lx, ly, rot)
        top_v.append(bm.verts.new((wx - ox, wy - oy, _z_lot(lx, ly) - oz)))
        bot_v.append(bm.verts.new((wx - ox, wy - oy, terrain.sample(wx, wy) - 1.5 - oz)))
    add_quad_vc(bm, col_layer, top_v[0], top_v[1], top_v[2], top_v[3], c_lot)
    for i in range(4):
        j = (i + 1) % 4
        add_quad_vc(bm, col_layer, bot_v[i], bot_v[j], top_v[j], top_v[i], c_curb)

    # 1B. Short terrain-draped connector driveway from SW lot edge (-9.5, -342.4) to NW branch road (-11.2, -361.8)
    # Stops cleanly north of the NW branch road (never crosses it or touches Security Office)
    n_seg = 6
    x_start, y_start = local_to_world_2d(cx_b, cy_b, -hx + 6.8, -hy, rot)
    z_start = _z_lot(-hx + 6.8, -hy)
    x_end, y_end = -11.2, -361.8
    z_end = terrain.sample(x_end, y_end) + 0.14
    seg_dx, seg_dy = x_end - x_start, y_end - y_start
    seg_len = math.hypot(seg_dx, seg_dy)
    nx_d, ny_d = (-seg_dy / seg_len) * 3.4, (seg_dx / seg_len) * 3.4
    prev_l = prev_r = prev_bl = prev_br = None
    for si in range(n_seg + 1):
        t = si / n_seg
        cx_s = x_start + seg_dx * t
        cy_s = y_start + seg_dy * t
        lx_s, ly_s = cx_s - nx_d, cy_s - ny_d
        rx_s, ry_s = cx_s + nx_d, cy_s + ny_d
        if si == 0:
            zl = _z_lot(-hx + 3.4, -hy)
            zr = _z_lot(-hx + 10.2, -hy)
        elif si == n_seg:
            zl = terrain.sample(lx_s, ly_s) + 0.14
            zr = terrain.sample(rx_s, ry_s) + 0.14
        else:
            z_lin = z_start * (1.0 - t) + z_end * t
            zl = max(z_lin, terrain.sample(lx_s, ly_s) + 0.14)
            zr = max(z_lin, terrain.sample(rx_s, ry_s) + 0.14)
        vl = bm.verts.new((lx_s - ox, ly_s - oy, zl - oz))
        vr = bm.verts.new((rx_s - ox, ry_s - oy, zr - oz))
        vbl = bm.verts.new((lx_s - ox, ly_s - oy, terrain.sample(lx_s, ly_s) - 0.8 - oz))
        vbr = bm.verts.new((rx_s - ox, ry_s - oy, terrain.sample(rx_s, ry_s) - 0.8 - oz))
        if prev_l is not None:
            add_quad_vc(bm, col_layer, prev_l, prev_r, vr, vl, c_lot)
            add_quad_vc(bm, col_layer, prev_bl, prev_l, vl, vbl, c_curb)
            add_quad_vc(bm, col_layer, prev_r, prev_br, vbr, vr, c_curb)
        prev_l, prev_r, prev_bl, prev_br = vl, vr, vbl, vbr

    # 2. Crisp white parking bay lines lying flush on the tilted lot plane
    bay_w = 2.85
    for row_sign, row_ly in ((1.0, hy - 3.2), (-1.0, -hy + 3.2)):
        for bay_idx in range(15):
            lx = -hx + 4.2 + bay_idx * bay_w
            if row_sign < 0 and lx < -hx + 11.5:
                continue  # leave SW entrance apron clear
            line_verts = []
            for dlx, dly in ((-0.08, -2.45), (0.08, -2.45), (0.08, 2.45), (-0.08, 2.45)):
                wx, wy = local_to_world_2d(cx_b, cy_b, lx + dlx, row_ly + dly, rot)
                line_verts.append(bm.verts.new((wx - ox, wy - oy, _z_lot(lx + dlx, row_ly + dly) + 0.035 - oz)))
            add_quad_vc(bm, col_layer, line_verts[0], line_verts[1], line_verts[2], line_verts[3], c_line)

    # 3. 11 minimal low-poly parked cars resting cleanly on the sloped lot surface
    car_slots = (
        (1, 0), (1, 1), (1, 3), (1, 5), (1, 8), (1, 10), (1, 12),
        (-1, 5), (-1, 6), (-1, 9), (-1, 12),
    )
    for idx, (row_sign, bay_idx) in enumerate(car_slots):
        lx = -hx + 4.2 + (bay_idx + 0.5) * bay_w
        ly = (hy - 3.2) if row_sign > 0 else (-hy + 3.2)
        px, py = local_to_world_2d(cx_b, cy_b, lx, ly, rot)
        z_car_base = min(
            _z_lot(lx - 0.88, ly - 2.05),
            _z_lot(lx + 0.88, ly - 2.05),
            _z_lot(lx - 0.88, ly + 2.05),
            _z_lot(lx + 0.88, ly + 2.05),
        ) - 0.02
        z_car_mid = _z_lot(lx, ly) + 0.72
        z_car_top = _z_lot(lx, ly) + 1.28
        body_col = car_colors[idx % len(car_colors)]
        add_box_vc(
            bm, col_layer, px, py, z_car_base, z_car_mid,
            0.88, 2.05, body_col, body_col, rot_rad=rot, offset_xyz=offset_xyz,
        )
        add_box_vc(
            bm, col_layer, px, py, z_car_mid, z_car_top,
            0.76, 1.08, c_glass, body_col, rot_rad=rot, offset_xyz=offset_xyz,
        )

    _link_bmesh_object("BLDG_hero_visitor_parking", bm, mat, location=offset_xyz)
    return [
        (-17.8, -344.5, _z_lot(-hx, -hy)),
        (40.5, -333.0, _z_lot(hx, -hy)),
        (34.0, -309.5, _z_lot(hx, hy) + 1.5),
        (-18.0, -322.0, _z_lot(-hx, hy) + 1.5),
    ]


def _register_building_meta(
    context: dict[str, Any],
    fid: str,
    mesh_name: str,
    default_name: str,
    default_category: str,
    default_floors: int,
    default_tags: list[str],
    height_m: float,
    footprint_pts: list[tuple[float, float, float]],
) -> None:
    """Append modular hero landmark to `meta_buildings` and `inspectables` using overrides metadata."""
    overrides = context["overrides"]
    config = context["config"]
    ov_entry = (overrides.get("rename_or_retag") or {}).get(fid) or {}

    xs = [p[0] for p in footprint_pts]
    ys = [p[1] for p in footprint_pts]
    zs = [p[2] for p in footprint_pts]
    cx_b = 0.5 * (min(xs) + max(xs))
    cy_b = 0.5 * (min(ys) + max(ys))
    cz_b = 0.5 * (min(zs) + max(zs))
    radius = max(8.0, max(math.hypot(px - cx_b, py - cy_b) for px, py, _ in footprint_pts))

    lat, lon = config.local_xz_to_latlon(cx_b, -cy_b)
    bounds_xz = [round(min(xs), 2), round(-max(ys), 2), round(max(xs), 2), round(-min(ys), 2)]
    footprint_xz = [[round(px, 2), round(-py, 2)] for px, py, _ in footprint_pts]

    tags_list = list(ov_entry.get("tags") or default_tags)
    entry: dict[str, Any] = {
        "id": fid,
        "meshName": mesh_name,
        "name": str(ov_entry.get("name") or default_name),
        "source": "hero",
        "isNamed": True,
        "category": str(ov_entry.get("category") or default_category),
        "tags": tags_list,
        "departments": list(ov_entry.get("departments") or []),
        "floors": int(ov_entry.get("floors") or default_floors),
        "heightM": round(float(height_m), 2),
        "center": _blender_to_gltf_xyz(cx_b, cy_b, cz_b),
        "boundingRadius": round(float(radius), 2),
        "latLon": [round(lat, 6), round(lon, 6)],
        "rawTags": {"hero": fid},
    }
    if ov_entry.get("subtitle"):
        entry["subtitle"] = str(ov_entry["subtitle"])

    context["meta_buildings"].append(entry)
    context["inspectables"].append(
        {
            **entry,
            "kind": "building",
            "boundsXZ": bounds_xz,
            "footprintXZ": footprint_xz,
        }
    )


def get_main_gate_feature_trees() -> list[tuple[float, float, int, float]]:
    """Hand-placed (x, y, type, scale) shade trees from `refs/main_gate_irl_user.jpg` (type 1 = broadleaf).

    The big flowering tree whose canopy covers the security cabin on the south verge, a row of shade trees
    along the verge between the kerb and the white-pier fence, and trees behind the visitor shelter.
    """
    return [
        (-30.0, -387.0, 1, 1.85),  # big canopy over the security cabin
        (-37.5, -388.0, 1, 1.45),
        (-44.5, -388.6, 1, 1.35),
        (-43.0, -369.0, 1, 1.4),
        (-35.0, -369.0, 1, 1.3),
        (-27.5, -369.5, 1, 1.45),
    ]


def get_main_gate_shade_tree_belts() -> list[tuple[float, float, float, float, float]]:
    """Return rectangular (x0, y0, x1, y1, step) regions for natural shade trees around parking & gate perimeter."""
    return [
        (-86.0, -390.0, -67.0, -342.0, 9.0),  # West woodland buffer north of gate wall
        (-62.0, -304.0, 38.0, -288.0, 9.0),   # North shade belt behind sheds & Car Parking
        (43.0, -356.0, 62.0, -308.0, 9.0),    # East shade belt framing Car Parking lot
        (-6.0, -392.0, 56.0, -366.0, 10.0),   # South-East garden belt north of boundary wall
    ]


def build_hero(context: dict[str, Any]) -> None:
    """Build Main Gate site crossing, compound wall, entrance arch, Security Office & parking facilities."""
    terrain = context["terrain"]
    mat_body = context["mat_body"]
    mat_site = _make_vcol_material("MAT_MainGate", roughness=0.84)
    solid_colliders = context["solid_colliders"]

    _build_site_crossing_and_wall(terrain, mat_site)

    gate_pts = _build_gatehouse_object(terrain, mat_body)
    sec_pts = _build_visitor_shelter_object(terrain, mat_body)
    shed_pts = _build_students_parking_object(terrain, mat_body)
    lot_pts = _build_visitor_parking_object(terrain, mat_body)

    _register_building_meta(
        context, "hero/main-gate", "BLDG_hero_main_gate",
        "Main Gate", "landmark", 2, ["main gate", "gate", "entrance", "gatehouse"], 9.7, gate_pts,
    )
    _register_building_meta(
        context, "hero/security-office", "BLDG_hero_security_office",
        "Security Office", "admin", 1, ["security", "security office", "visitor pass"], 3.3, sec_pts,
    )
    _register_building_meta(
        context, "hero/students-parking", "BLDG_hero_students_parking",
        "Student's Parking", "landmark", 1, ["parking", "student parking", "sheds"], 4.0, shed_pts,
    )
    _register_building_meta(
        context, "hero/visitor-parking", "BLDG_hero_visitor_parking",
        "Visitor / Car Parking", "landmark", 1, ["parking", "car parking", "visitor parking"], 2.0, lot_pts,
    )

    # Register strict tree-exclusion colliders for sheds, car lot, gate, security & compound wall
    extra_colliders = [
        [(-166.0, -402.5), (124.0, -392.0), (124.0, -386.5), (-166.0, -397.0)],  # Tilted compound wall
        [(-67.0, -398.5), (-44.0, -398.5), (-44.0, -393.0), (-67.0, -393.0)],    # Crossing piers & wing walls
        [(-47.0, -380.5), (-26.5, -380.5), (-26.5, -372.0), (-47.0, -372.0)],    # Visitor shelter (Security Office)
        [(-47.0, -391.5), (-23.0, -391.5), (-23.0, -389.0), (-47.0, -389.0)],    # South kerb fence
        [(-29.0, -392.0), (-12.5, -392.0), (-12.5, -368.5), (-29.0, -368.5)],    # Gatehouse + cabin (Main Gate)
        [(-50.5, -352.0), (-20.0, -352.0), (-20.0, -302.5), (-50.5, -302.5)],    # Student's Parking sheds
        [(-19.5, -346.5), (42.5, -346.5), (42.5, -307.5), (-19.5, -307.5)],      # Car Parking lot
        [(-15.5, -362.5), (-4.5, -362.5), (-4.5, -340.0), (-15.5, -340.0)],      # Short sloped lot driveway
    ]
    for ring in extra_colliders:
        x0, y0 = min(p[0] for p in ring), min(p[1] for p in ring)
        x1, y1 = max(p[0] for p in ring), max(p[1] for p in ring)
        solid_colliders.append(((x0, y0, x1, y1), [ring]))
