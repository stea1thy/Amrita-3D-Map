"""Modular Hero generator for Amrita Coimbatore Main Gate, Security Office & Parking Zone.

Replaces the undersized arch overlapping the railway corridor and generic cubes with:
1. `GROUND_MainGateSite`: clean railway level-crossing road shoulders + campus boundary compound wall
   parallel to the northern railway track.
2. `BLDG_hero_main_gate` (`hero/main-gate`): verified terracotta-brick outer entrance piers with lantern
   caps, AMRITA wing signage, divided entry/exit lanes, red-and-white boom barriers, terracotta-roofed
   guard booth, and open-sided white canopy at the road bend.
3. `BLDG_hero_security_office` (`hero/security-office`): verified 2-story cream & terracotta-roofed
   gatehouse straddling `way/128964701` (`5.2m` clear drive-through height) with flanking approach piers.
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


def _build_site_crossing_and_wall(terrain: Any, mat: bpy.types.Material) -> None:
    """Build railway level-crossing road apron/shoulders and campus brick-and-cream perimeter compound wall."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    c_asphalt = srgb_hex_to_linear_rgba("#484D54")
    c_stripe = srgb_hex_to_linear_rgba("#E8D24A")
    c_dark = srgb_hex_to_linear_rgba("#25292E")
    c_brick = srgb_hex_to_linear_rgba("#A65E44")
    c_cream = srgb_hex_to_linear_rgba("#EFE8DC")
    c_coping = srgb_hex_to_linear_rgba("#9E5B42")

    # 1. Clean railway level-crossing shoulders & warning posts (north & south of rails at -408.3 / -417.2)
    for lx, ly in ((-55.55, -420.5), (-55.55, -404.2)):
        lz = terrain.sample(lx, ly)
        add_box_vc(bm, col_layer, lx, ly, lz - 0.6, lz + 0.20, 4.6, 2.2, c_asphalt, c_asphalt)
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

    _link_bmesh_object("GROUND_MainGateSite", bm, mat)


def _build_main_gate_object(terrain: Any, mat: bpy.types.Material) -> list[tuple[float, float, float]]:
    """Build outer Main Gate brick piers, AMRITA signage wings, boom barriers, guard booth & bend canopy."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    cx_b, cy_b = GATE_CX, GATE_CY
    cz_b = terrain.sample(cx_b, cy_b) + 2.4
    offset_xyz = (cx_b, cy_b, cz_b)

    c_brick = srgb_hex_to_linear_rgba("#A65E44")
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_maroon = srgb_hex_to_linear_rgba(HERO_PALETTE["amrita_maroon"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_glass = srgb_hex_to_linear_rgba("#384958")
    c_canopy = srgb_hex_to_linear_rgba("#E4E7EB")

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

    # 2. Divided Entry / Exit lane median island + slim central checkpoint booth + twin boom barriers
    mx, my = -55.5, -391.4
    mz = terrain.sample(mx, my)
    add_box_vc(bm, col_layer, mx, my, mz - 0.6, mz + 0.26, 0.55, 3.8, c_cream, c_white, rot_rad=0.0, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, mx, my, mz + 0.26, mz + 2.55, 0.52, 1.05, c_cream, c_white, rot_rad=0.0, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, mx, my, mz + 1.25, mz + 2.15, 0.55, 0.90, c_glass, c_dark, rot_rad=0.0, offset_xyz=offset_xyz)
    add_hipped_roof_vc(bm, col_layer, mx, my, mz + 2.52, mz + 3.25, 0.85, 1.35, c_tile, offset_xyz=offset_xyz)

    _add_boom_barrier(bm, col_layer, mx - 0.62, -393.0, math.pi, 4.1, terrain, offset_xyz)
    _add_boom_barrier(bm, col_layer, mx + 0.62, -393.0, 0.0, 4.1, terrain, offset_xyz)

    # 3. Terracotta pyramid-roofed Guard Booth tucked just inside west gate pier (`main_gate_arch.jpg`)
    gx, gy = -62.5, -390.2
    gz = terrain.sample(gx, gy)
    add_box_vc(bm, col_layer, gx, gy, gz - 1.2, gz + 0.85, 1.65, 1.55, c_brick, c_brick, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, gx, gy, gz + 0.85, gz + 2.85, 1.60, 1.50, c_cream, c_white, offset_xyz=offset_xyz)
    add_box_vc(bm, col_layer, gx + 0.05, gy, gz + 1.35, gz + 2.30, 1.63, 1.15, c_glass, c_dark, offset_xyz=offset_xyz)
    add_hipped_roof_vc(bm, col_layer, gx, gy, gz + 2.82, gz + 4.35, 2.25, 2.15, c_tile, soffit_rgba=c_cream, offset_xyz=offset_xyz)

    # 4. Open-sided white steel entry canopy at road bend (`main_gate_sat.jpg` px=(268,285) at -60.2, -377.5)
    can_x, can_y = -60.2, -377.5
    can_z = terrain.sample(can_x, can_y)
    can_hx, can_hy = 5.0, 3.6
    for px_s in (-can_hx + 0.4, 0.0, can_hx - 0.4):
        for py_s in (-can_hy + 0.4, can_hy - 0.4):
            cpx, cpy = local_to_world_2d(can_x, can_y, px_s, py_s, 0.0)
            cpz = terrain.sample(cpx, cpy)
            add_cylinder_vc(bm, col_layer, cpx, cpy, cpz - 0.8, can_z + 4.0, 0.13, 0.13, 6, c_dark, c_dark, offset_xyz=offset_xyz)
    add_box_vc(
        bm, col_layer, can_x, can_y, can_z + 3.96, can_z + 4.30,
        can_hx, can_hy, c_white, c_canopy, emit_bottom=True, offset_xyz=offset_xyz,
    )

    _link_bmesh_object("BLDG_hero_main_gate", bm, mat, location=offset_xyz)
    return [
        (-66.0, -398.0, cz_b - 2.4),
        (-45.0, -398.0, cz_b + 5.5),
        (-45.0, -373.5, cz_b + 5.5),
        (-66.0, -373.5, cz_b - 2.4),
    ]


def _build_security_office_object(terrain: Any, mat: bpy.types.Material) -> list[tuple[float, float, float]]:
    """Build 2-story cream & terracotta Security Office gatehouse straddling way/128964701 (`main_gate_area.jpg`)."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    cx_b, cy_b = SEC_CX, SEC_CY
    cz_b = terrain.sample(cx_b, cy_b) + 4.8
    offset_xyz = (cx_b, cy_b, cz_b)
    rot = 0.045  # aligns cleanly with E-W entrance road way/128964701

    c_plinth = srgb_hex_to_linear_rgba(HERO_PALETTE["sandstone_plinth"])
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_tile"])
    c_maroon = srgb_hex_to_linear_rgba(HERO_PALETTE["amrita_maroon"])
    c_dark = srgb_hex_to_linear_rgba(HERO_PALETTE["recess_shadow"])

    # 1. Twin foreground gate piers seen in `main_gate_area.jpg` along the approach road
    for side in (-1.0, 1.0):
        px, py = local_to_world_2d(-33.5, -382.7, 0.0, side * 5.2, rot)
        pz = terrain.sample(px, py)
        add_box_vc(bm, col_layer, px, py, pz - 1.2, pz + 0.5, 0.52, 0.52, c_plinth, c_cream, rot_rad=rot, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, px, py, pz + 0.5, pz + 3.05, 0.44, 0.44, c_cream, c_white, rot_rad=rot, offset_xyz=offset_xyz)
        add_hipped_roof_vc(bm, col_layer, px, py, pz + 3.05, pz + 3.55, 0.56, 0.56, c_tile, rot_rad=rot, offset_xyz=offset_xyz)

    # 2. North Wing (way/546394580 footprint) & South Wing (way/546394581 footprint), clear of road [-385.8 .. -379.0]
    road_z = terrain.sample(cx_b, cy_b)
    for wing_y, wing_hy in ((-375.5, 3.3), (-388.9, 3.1)):
        wx, wy = cx_b, wing_y
        wz0 = terrain.sample(wx, wy) - 1.5
        z_top_w = road_z + 7.2
        add_box_vc(bm, col_layer, wx, wy, wz0, road_z + 0.45, 4.4, wing_hy, c_plinth, c_plinth, rot_rad=rot, offset_xyz=offset_xyz)
        add_box_vc(bm, col_layer, wx, wy, road_z + 0.45, z_top_w, 4.25, wing_hy - 0.15, c_cream, c_white, rot_rad=rot, offset_xyz=offset_xyz)
        # Subtle mid-floor horizontal cornice band
        add_box_vc(bm, col_layer, wx, wy, road_z + 3.55, road_z + 3.85, 4.35, wing_hy - 0.05, c_white, c_white, rot_rad=rot, offset_xyz=offset_xyz)
        # Spaced dark framed windows on West/East and North/South facades
        for wz_fl in (road_z + 1.5, road_z + 4.7):
            for wy_off in (-1.2, 1.2):
                add_box_vc(bm, col_layer, wx, wy + wy_off, wz_fl, wz_fl + 1.25, 4.30, 0.72, c_dark, c_dark, rot_rad=rot, offset_xyz=offset_xyz)
        add_hipped_roof_vc(
            bm, col_layer, wx, wy, z_top_w - 0.02, z_top_w + 2.15,
            4.85, wing_hy + 0.45, c_tile, rot_rad=rot, soffit_rgba=c_cream, offset_xyz=offset_xyz,
        )

    # 3. 2-Story Gatehouse Archway Span bridging cleanly over road way/128964701 (`main_gate_area.jpg`)
    z_clear = road_z + 5.15
    z_bridge_top = road_z + 7.75
    add_box_vc(
        bm, col_layer, cx_b, cy_b, z_clear, z_bridge_top,
        4.1, 3.8, c_cream, c_white, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_box_vc(
        bm, col_layer, cx_b, cy_b, z_clear + 0.25, z_clear + 1.05,
        4.22, 2.8, c_maroon, c_maroon, rot_rad=rot, emit_bottom=True, offset_xyz=offset_xyz,
    )
    add_box_vc(
        bm, col_layer, cx_b, cy_b, z_clear + 1.45, z_bridge_top - 0.45,
        4.18, 2.3, c_dark, c_dark, rot_rad=rot, offset_xyz=offset_xyz,
    )
    add_hipped_roof_vc(
        bm, col_layer, cx_b, cy_b, z_bridge_top - 0.02, z_bridge_top + 2.45,
        4.65, 4.35, c_tile, rot_rad=rot, soffit_rgba=c_cream, offset_xyz=offset_xyz,
    )

    # Security checkpoint boom barriers right beneath the Security Office approach
    _add_boom_barrier(bm, col_layer, -24.0, -379.6, -math.pi * 0.5, 2.8, terrain, offset_xyz)
    _add_boom_barrier(bm, col_layer, -24.0, -385.4, math.pi * 0.5, 2.8, terrain, offset_xyz)

    _link_bmesh_object("BLDG_hero_security_office", bm, mat, location=offset_xyz)
    return [
        (-25.0, -393.0, cz_b - 4.8),
        (-13.0, -393.0, cz_b + 6.0),
        (-13.0, -371.5, cz_b + 6.0),
        (-25.0, -371.5, cz_b - 4.8),
    ]


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

    gate_pts = _build_main_gate_object(terrain, mat_body)
    sec_pts = _build_security_office_object(terrain, mat_body)
    shed_pts = _build_students_parking_object(terrain, mat_body)
    lot_pts = _build_visitor_parking_object(terrain, mat_body)

    _register_building_meta(
        context, "hero/main-gate", "BLDG_hero_main_gate",
        "Main Gate", "landmark", 1, ["main gate", "gate", "entrance", "checkpoint"], 5.2, gate_pts,
    )
    _register_building_meta(
        context, "hero/security-office", "BLDG_hero_security_office",
        "Security Office", "admin", 2, ["security", "security office", "gatehouse"], 9.5, sec_pts,
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
        [(-67.0, -398.5), (-44.0, -398.5), (-44.0, -372.0), (-67.0, -372.0)],    # Main Gate & bend canopy
        [(-36.5, -389.5), (-30.5, -389.5), (-30.5, -376.0), (-36.5, -376.0)],    # Security approach piers
        [(-26.5, -394.5), (-11.5, -394.5), (-11.5, -370.0), (-26.5, -370.0)],    # Security Office
        [(-50.5, -352.0), (-20.0, -352.0), (-20.0, -302.5), (-50.5, -302.5)],    # Student's Parking sheds
        [(-19.5, -346.5), (42.5, -346.5), (42.5, -307.5), (-19.5, -307.5)],      # Car Parking lot
        [(-15.5, -362.5), (-4.5, -362.5), (-4.5, -340.0), (-15.5, -340.0)],      # Short sloped lot driveway
    ]
    for ring in extra_colliders:
        x0, y0 = min(p[0] for p in ring), min(p[1] for p in ring)
        x1, y1 = max(p[0] for p in ring), max(p[1] for p in ring)
        solid_colliders.append(((x0, y0, x1, y1), [ring]))
