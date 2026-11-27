"""Modular hero: outdoor courts along Yagnavalkiya Bhavanam Road (between Yagnavalkya & Amriteshwari Hall).

Traced from `pipeline/refs/yagnavalkya_courts_sat.png` (Google satellite, registered to OSM, ~2 m accuracy).
Replaces the generic orange OSM pitch slabs (`way/380926242`, `way/531088166`, `way/380926245`,
`way/380926247`, listed in `overrides.json` `exclude_ids`) with what the imagery actually shows:

South of the road (west -> east):
  1. Teal acrylic basketball court with a red surround, white FIBA-style lines and two hoops.
  2. Bare red-earth dirt court (no markings visible).
  3. Green artificial-turf football pitch with white lines and two goals
     (missing entirely before: the OSM "volleyball" polygon straddled this pitch and the dirt court).
North of the road, west of the terracotta court hall:
  4. Renovated red-clay volleyball court (9 x 18 m lines, net + posts) in a clay yard.
  5. Grey earth basketball court (lines + two hoops) filling the rest of the yard.

All geometry is merged into the existing `STATIC_HeroAccents` mesh so no draw call is added.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from hero_models.geom_helpers import add_box_vc, add_quad_vc, srgb_hex_to_linear_rgba

REPLACED_OSM_SPORTS_IDS: tuple[str, ...] = (
    "way/380926242",
    "way/531088166",
    "way/380926245",
    "way/380926247",
)

# Courts as oriented rectangles: center (lat, lon), width (E-W m), length (N-S m), CCW rotation (deg)
COURT_ROT_DEG = 1.3
COURTS: dict[str, dict[str, Any]] = {
    "teal_basketball": {"center": (10.900774, 76.904064), "w": 17.3, "l": 34.5, "hex": "#B5675A", "group": "south"},
    "dirt_court": {"center": (10.900793, 76.904236), "w": 19.9, "l": 32.0, "hex": "#B98A62", "group": "south"},
    "turf_pitch": {"center": (10.900788, 76.904422), "w": 20.1, "l": 37.0, "hex": "#4A8C48", "group": "south"},
    "clay_volleyball_yard": {"center": (10.901524, 76.904054), "w": 30.6, "l": 23.0, "hex": "#B4714F", "group": "north"},
    "earth_basketball_yard": {"center": (10.90123, 76.904057), "w": 30.1, "l": 42.5, "hex": "#A99A86", "group": "north"},
}
VOLLEYBALL_LINES_CENTER = (10.90153, 76.90399)  # OSM way/380926247 centroid
NORTH_BASKETBALL_LINES_CENTER = (10.90123, 76.904005)  # OSM way/380926245 centroid

C_LINE = "#F4F1EA"
C_TEAL = "#4F9A8C"
C_SKIRT = "#CFC6B8"
C_POLE = "#5B6168"
C_BOARD = "#F2F0EA"
C_NET = "#2F343A"

LINE_W = 0.12


class _Frame:
    """Local court frame: u = across (east), v = along (north), rotated by COURT_ROT_DEG."""

    def __init__(self, cx: float, cy: float, rot_rad: float) -> None:
        self.cx, self.cy = cx, cy
        self.ca, self.sa = math.cos(rot_rad), math.sin(rot_rad)
        self.rot = rot_rad

    def w(self, u: float, v: float) -> tuple[float, float]:
        return (self.cx + u * self.ca - v * self.sa, self.cy + u * self.sa + v * self.ca)


def _rect(frame: _Frame, hw: float, hl: float) -> list[tuple[float, float]]:
    return [frame.w(-hw, -hl), frame.w(hw, -hl), frame.w(hw, hl), frame.w(-hw, hl)]


def _flat_quad(bm: bmesh.types.BMesh, col: Any, pts: list[tuple[float, float]], z: float, rgba: Any) -> None:
    v = [bm.verts.new((x, y, z)) for x, y in pts]
    add_quad_vc(bm, col, v[0], v[1], v[2], v[3], rgba)


def _slab(bm: bmesh.types.BMesh, col: Any, ring: list[tuple[float, float]], z_top: float, z_bot: float, top: Any, skirt: Any) -> None:
    """Flat terrace slab: CCW top quad + 4 retaining skirt walls."""
    t = [bm.verts.new((x, y, z_top)) for x, y in ring]
    b = [bm.verts.new((x, y, z_bot)) for x, y in ring]
    add_quad_vc(bm, col, t[0], t[1], t[2], t[3], top)
    for i in range(4):
        j = (i + 1) % 4
        add_quad_vc(bm, col, b[i], b[j], t[j], t[i], skirt)


def _line(bm: bmesh.types.BMesh, col: Any, fr: _Frame, u0: float, v0: float, u1: float, v1: float, z: float, rgba: Any) -> None:
    du, dv = u1 - u0, v1 - v0
    ln = math.hypot(du, dv)
    if ln < 1e-4:
        return
    nu, nv = -dv / ln * LINE_W * 0.5, du / ln * LINE_W * 0.5
    pts = [fr.w(u0 - nu, v0 - nv), fr.w(u1 - nu, v1 - nv), fr.w(u1 + nu, v1 + nv), fr.w(u0 + nu, v0 + nv)]
    _flat_quad(bm, col, pts, z, rgba)


def _arc(bm: bmesh.types.BMesh, col: Any, fr: _Frame, cu: float, cv: float, r: float, a0: float, a1: float, segs: int, z: float, rgba: Any) -> None:
    for i in range(segs):
        t0 = a0 + (a1 - a0) * i / segs
        t1 = a0 + (a1 - a0) * (i + 1) / segs
        _line(bm, col, fr, cu + r * math.cos(t0), cv + r * math.sin(t0), cu + r * math.cos(t1), cv + r * math.sin(t1), z, rgba)


def _outline(bm: bmesh.types.BMesh, col: Any, fr: _Frame, hw: float, hl: float, z: float, rgba: Any) -> None:
    _line(bm, col, fr, -hw, -hl, hw, -hl, z, rgba)
    _line(bm, col, fr, hw, -hl, hw, hl, z, rgba)
    _line(bm, col, fr, hw, hl, -hw, hl, z, rgba)
    _line(bm, col, fr, -hw, hl, -hw, -hl, z, rgba)


def _basketball(bm: bmesh.types.BMesh, col: Any, fr: _Frame, hw: float, hl: float, z_surf: float, c_line: Any, c_pole: Any, c_board: Any) -> None:
    z = z_surf + 0.02
    _outline(bm, col, fr, hw, hl, z, c_line)
    _line(bm, col, fr, -hw, 0.0, hw, 0.0, z, c_line)
    _arc(bm, col, fr, 0.0, 0.0, 1.8, 0.0, 2 * math.pi, 10, z, c_line)
    key_hw, key_d, three_r = 2.45, 5.8, min(6.75, hw - 0.6)
    for sgn in (-1.0, 1.0):
        base = sgn * hl
        ft = sgn * (hl - key_d)
        _line(bm, col, fr, -key_hw, base, -key_hw, ft, z, c_line)
        _line(bm, col, fr, key_hw, base, key_hw, ft, z, c_line)
        _line(bm, col, fr, -key_hw, ft, key_hw, ft, z, c_line)
        hoop_v = sgn * (hl - 1.575)
        a_mid = -sgn * math.pi / 2
        _arc(bm, col, fr, 0.0, hoop_v, three_r, a_mid - 1.25, a_mid + 1.25, 7, z, c_line)
        # Pole behind the baseline + backboard
        pu, pv = fr.w(0.0, sgn * (hl + 1.0))
        add_box_vc(bm, col, pu, pv, z_surf, z_surf + 3.05, 0.09, 0.09, c_pole, c_pole, rot_rad=fr.rot)
        bu, bv = fr.w(0.0, sgn * (hl - 1.2))
        add_box_vc(bm, col, bu, bv, z_surf + 2.9, z_surf + 3.95, 0.9, 0.04, c_board, c_board, rot_rad=fr.rot)


def _make_vcol_material(name: str) -> Any:
    import bpy

    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name=name)
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None) or nt.nodes.new("ShaderNodeBsdfPrincipled")
    vcol = nt.nodes.new(type="ShaderNodeVertexColor")
    vcol.layer_name = "Color"
    nt.links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.84
    return mat


def build_hero(context: dict[str, Any]) -> None:
    import bpy

    terrain = context["terrain"]
    config = context["config"]
    solid_colliders = context["solid_colliders"]

    def ll2xy(lat: float, lon: float) -> tuple[float, float]:
        x, z = config.latlon_to_local_xz(lat, lon)
        return (x, -z)

    host = bpy.data.objects.get("STATIC_HeroAccents")
    bm = bmesh.new()
    if host is not None:
        bm.from_mesh(host.data)
        col = bm.loops.layers.color.get("Color") or bm.loops.layers.color.new("Color")
    else:
        col = bm.loops.layers.color.new("Color")

    rot = math.radians(COURT_ROT_DEG)
    frames: dict[str, _Frame] = {}
    rings: dict[str, list[tuple[float, float]]] = {}
    for key, spec in COURTS.items():
        cx, cy = ll2xy(*spec["center"])
        frames[key] = _Frame(cx, cy, rot)
        rings[key] = _rect(frames[key], spec["w"] * 0.5, spec["l"] * 0.5)

    # One level per court group so adjacent courts meet without steps
    group_z: dict[str, tuple[float, float]] = {}
    for grp in {s["group"] for s in COURTS.values()}:
        zs = []
        for key, spec in COURTS.items():
            if spec["group"] != grp:
                continue
            fr = frames[key]
            hw, hl = spec["w"] * 0.5, spec["l"] * 0.5
            for i in range(5):
                for j in range(5):
                    zs.append(terrain.sample(*fr.w(-hw + 2 * hw * i / 4, -hl + 2 * hl * j / 4)))
        group_z[grp] = (max(zs) + 0.22, min(zs) - 1.8)
        print(f"  Yagnavalkya courts [{grp}]: terrain spread {max(zs) - min(zs):.2f} m")

    c_line = srgb_hex_to_linear_rgba(C_LINE)
    c_skirt = srgb_hex_to_linear_rgba(C_SKIRT)
    c_pole = srgb_hex_to_linear_rgba(C_POLE)
    c_board = srgb_hex_to_linear_rgba(C_BOARD)
    for key, spec in COURTS.items():
        z_top, z_bot = group_z[spec["group"]]
        _slab(bm, col, rings[key], z_top, z_bot, srgb_hex_to_linear_rgba(spec["hex"]), c_skirt)
        xs, ys = [p[0] for p in rings[key]], [p[1] for p in rings[key]]
        solid_colliders.append(((min(xs) - 1.0, min(ys) - 1.0, max(xs) + 1.0, max(ys) + 1.0), [rings[key]]))

    # 1. Teal basketball court inside its red surround
    fr = frames["teal_basketball"]
    z_s = group_z["south"][0]
    _flat_quad(bm, col, _rect(fr, 7.65, 15.75), z_s + 0.012, srgb_hex_to_linear_rgba(C_TEAL))
    _basketball(bm, col, fr, 7.1, 13.0, z_s + 0.012, c_line, c_pole, c_board)

    # 3. Turf football pitch lines + goals
    fr = frames["turf_pitch"]
    z = z_s + 0.02
    hw, hl = 9.2, 17.6
    _outline(bm, col, fr, hw, hl, z, c_line)
    _line(bm, col, fr, -hw, 0.0, hw, 0.0, z, c_line)
    _arc(bm, col, fr, 0.0, 0.0, 3.0, 0.0, 2 * math.pi, 12, z, c_line)
    for sgn in (-1.0, 1.0):
        box_d = sgn * (hl - 5.0)
        _line(bm, col, fr, -5.0, sgn * hl, -5.0, box_d, z, c_line)
        _line(bm, col, fr, 5.0, sgn * hl, 5.0, box_d, z, c_line)
        _line(bm, col, fr, -5.0, box_d, 5.0, box_d, z, c_line)
        for gu in (-1.5, 1.5):
            pu, pv = fr.w(gu, sgn * (hl + 0.15))
            add_box_vc(bm, col, pu, pv, z_s, z_s + 2.0, 0.06, 0.06, c_board, c_board, rot_rad=fr.rot)
        bu, bv = fr.w(0.0, sgn * (hl + 0.15))
        add_box_vc(bm, col, bu, bv, z_s + 1.94, z_s + 2.06, 1.56, 0.06, c_board, c_board, rot_rad=fr.rot)

    # 4. Renovated volleyball court (lines centred on the OSM court), net + posts
    z_n = group_z["north"][0]
    vcx, vcy = ll2xy(*VOLLEYBALL_LINES_CENTER)
    fr = _Frame(vcx, vcy, rot)
    _outline(bm, col, fr, 4.5, 9.0, z_n + 0.02, c_line)
    for su in (-1.0, 1.0):
        pu, pv = fr.w(su * 5.0, 0.0)
        add_box_vc(bm, col, pu, pv, z_n, z_n + 2.45, 0.07, 0.07, c_pole, c_pole, rot_rad=fr.rot)
    nu0, nv0 = fr.w(-5.0, 0.0)
    nu1, nv1 = fr.w(5.0, 0.0)
    c_net = srgb_hex_to_linear_rgba(C_NET)
    nv = [
        bm.verts.new((nu0, nv0, z_n + 1.43)),
        bm.verts.new((nu1, nv1, z_n + 1.43)),
        bm.verts.new((nu1, nv1, z_n + 2.43)),
        bm.verts.new((nu0, nv0, z_n + 2.43)),
    ]
    add_quad_vc(bm, col, nv[0], nv[1], nv[2], nv[3], c_net)
    add_quad_vc(bm, col, nv[3], nv[2], nv[1], nv[0], c_net)

    # 5. Earth basketball court (lines centred on the OSM court)
    bcx, bcy = ll2xy(*NORTH_BASKETBALL_LINES_CENTER)
    _basketball(bm, col, _Frame(bcx, bcy, rot), 7.5, 14.0, z_n, c_line, c_pole, c_board)

    bm.normal_update()
    if host is not None:
        bm.to_mesh(host.data)
        host.data.update()
        bm.free()
    else:
        mesh = bpy.data.meshes.new("GROUND_YagnavalkyaCourts")
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(context.get("mat_hero_accents") or _make_vcol_material("MAT_YagnavalkyaCourts"))
        obj = bpy.data.objects.new("GROUND_YagnavalkyaCourts", mesh)
        bpy.context.scene.collection.objects.link(obj)
