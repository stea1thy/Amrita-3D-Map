"""Modular hero: outdoor courts along Yagnavalkiya Bhavanam Road (between Yagnavalkya & Amriteshwari Hall).

Layout traced from `pipeline/refs/yagnavalkya_courts_sat.png` (Google satellite, registered to OSM, ~2 m accuracy).
Replaces the generic orange OSM pitch slabs (`way/380926242`, `way/531088166`, `way/380926245`,
`way/380926247`, listed in `overrides.json` `exclude_ids`).

South of the road (west -> east):
  1. Acrylic basketball court: teal play area, red apron and red painted keys, FIBA markings, two hoops.
  2. Bare red-earth dirt court (no markings visible in imagery).
  3. Artificial-turf futsal pitch (~18.5 x 35 m inside a 20 x 37 m turf) with mowing stripes, futsal markings
     and 3 x 2 m goals.
North of the road, west of the terracotta court hall:
  4. Renovated red-clay volleyball court (9 x 18 m, attack lines, mesh net with white band, posts).
  5. Grey earth basketball court (FIBA lines, two hoops) filling the rest of the yard.

Surfaces are subdivided grids with per-vertex colour variation (mottled earth/clay, striped turf, faint acrylic
sheen) so they read as textured materials while staying a single vertex-coloured mesh.

Marking specs: FIBA court 28 x 15 m, 3-point line 6.75 m (0.9 m from the sideline in the corners), key 4.9 x 5.8 m,
restricted-area arc 1.25 m, centre / free-throw circles 1.8 m radius, basket 1.575 m in from the baseline.
Futsal (Laws of the Game, Law 1): 6 m quarter circles centred on each goalpost joined by a 3.16 m line, penalty
marks at 6 m and 10 m, 3 m centre circle, 3 x 2 m goals. Volleyball: 9 x 18 m court with 3 m attack lines.

All geometry is merged into the existing `STATIC_HeroAccents` mesh so no draw call is added.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import bmesh

from hero_models.geom_helpers import add_box_vc, add_quad_vc, srgb_hex_to_linear_rgba

REPLACED_OSM_SPORTS_IDS: tuple[str, ...] = (
    "way/380926242",
    "way/531088166",
    "way/380926245",
    "way/380926247",
)

# Courts as oriented rectangles: center (lat, lon), width (E-W m), length (N-S m); CCW rotation (deg)
COURT_ROT_DEG = 1.3
COURTS: dict[str, dict[str, Any]] = {
    "teal_basketball": {"center": (10.900774, 76.904064), "w": 17.3, "l": 34.5, "surface": "acrylic"},
    "dirt_court": {"center": (10.900793, 76.904236), "w": 19.9, "l": 32.0, "surface": "dirt"},
    "turf_pitch": {"center": (10.900788, 76.904422), "w": 20.1, "l": 37.0, "surface": "turf"},
    "clay_volleyball_yard": {"center": (10.901524, 76.904054), "w": 30.6, "l": 23.0, "surface": "clay"},
    "earth_basketball_yard": {"center": (10.90123, 76.904057), "w": 30.1, "l": 42.5, "surface": "earth"},
}
VOLLEYBALL_LINES_CENTER = (10.90153, 76.90399)  # OSM way/380926247 centroid
NORTH_BASKETBALL_LINES_CENTER = (10.90123, 76.904005)  # OSM way/380926245 centroid

C_LINE = "#F4F1EA"
C_LINE_FAINT = "#E2DACB"
C_ACRYLIC_TEAL = "#3D8C84"
C_ACRYLIC_RED = "#A9534A"
C_TURF_A = "#4F9545"
C_TURF_B = "#44873C"
C_DIRT = "#B37C52"
C_CLAY = "#B8673F"
C_EARTH = "#A59682"
C_SKIRT = "#B8B2A6"
C_POLE = "#4E555C"
C_BOARD = "#F2F0EA"
C_RIM = "#E0662A"
C_NET = "#C9CCC8"
C_NET_BAND = "#F7F6F2"
C_GOAL = "#F6F4EE"

LINE_W = 0.10
GRID_CELL_M = 2.2


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


def _hash01(x: float, y: float) -> float:
    """Deterministic per-vertex value noise in [0, 1)."""
    s = math.sin(x * 12.9898 + y * 78.233) * 43758.5453
    return s - math.floor(s)


def _shade(rgba: Any, k: float) -> tuple[float, float, float, float]:
    return (min(1.0, rgba[0] * k), min(1.0, rgba[1] * k), min(1.0, rgba[2] * k), 1.0)


def _face_vc(bm: bmesh.types.BMesh, col: Any, verts: list[Any], cols: list[Any]) -> None:
    try:
        f = bm.faces.new(verts)
    except ValueError:
        return
    f.smooth = False
    for loop, rgba in zip(f.loops, cols):
        loop[col] = rgba


def _flat_quad(bm: bmesh.types.BMesh, col: Any, pts: list[tuple[float, float]], z: float, rgba: Any) -> None:
    v = [bm.verts.new((x, y, z)) for x, y in pts]
    add_quad_vc(bm, col, v[0], v[1], v[2], v[3], rgba)


def _grid_surface(
    bm: bmesh.types.BMesh,
    col: Any,
    fr: _Frame,
    hw: float,
    hl: float,
    z: float,
    color_fn: Callable[[float, float], tuple[float, float, float, float]],
) -> None:
    """Subdivided flat surface with per-vertex colours (the 'texture')."""
    nu = max(2, int(round(2 * hw / GRID_CELL_M)))
    nv = max(2, int(round(2 * hl / GRID_CELL_M)))
    verts: list[list[Any]] = []
    cols: list[list[Any]] = []
    for j in range(nv + 1):
        v = -hl + 2 * hl * j / nv
        row_v, row_c = [], []
        for i in range(nu + 1):
            u = -hw + 2 * hw * i / nu
            row_v.append(bm.verts.new((*fr.w(u, v), z)))
            row_c.append(color_fn(u, v))
        verts.append(row_v)
        cols.append(row_c)
    for j in range(nv):
        for i in range(nu):
            _face_vc(
                bm, col,
                [verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]],
                [cols[j][i], cols[j][i + 1], cols[j + 1][i + 1], cols[j + 1][i]],
            )


def _skirt(bm: bmesh.types.BMesh, col: Any, ring: list[tuple[float, float]], z_top: float, z_bot: float, rgba: Any) -> None:
    """Retaining skirt walls around a CCW ring (court terraces are level; terrain falls away)."""
    t = [bm.verts.new((x, y, z_top)) for x, y in ring]
    b = [bm.verts.new((x, y, z_bot)) for x, y in ring]
    for i in range(len(ring)):
        j = (i + 1) % len(ring)
        add_quad_vc(bm, col, b[i], b[j], t[j], t[i], rgba)


def _line(bm: bmesh.types.BMesh, col: Any, fr: _Frame, u0: float, v0: float, u1: float, v1: float, z: float, rgba: Any, width: float = LINE_W) -> None:
    du, dv = u1 - u0, v1 - v0
    ln = math.hypot(du, dv)
    if ln < 1e-4:
        return
    nu, nv = -dv / ln * width * 0.5, du / ln * width * 0.5
    pts = [fr.w(u0 - nu, v0 - nv), fr.w(u1 - nu, v1 - nv), fr.w(u1 + nu, v1 + nv), fr.w(u0 + nu, v0 + nv)]
    _flat_quad(bm, col, pts, z, rgba)


def _arc(bm: bmesh.types.BMesh, col: Any, fr: _Frame, cu: float, cv: float, r: float, a0: float, a1: float, segs: int, z: float, rgba: Any, width: float = LINE_W) -> None:
    for i in range(segs):
        t0 = a0 + (a1 - a0) * i / segs
        t1 = a0 + (a1 - a0) * (i + 1) / segs
        _line(bm, col, fr, cu + r * math.cos(t0), cv + r * math.sin(t0), cu + r * math.cos(t1), cv + r * math.sin(t1), z, rgba, width)


def _outline(bm: bmesh.types.BMesh, col: Any, fr: _Frame, hw: float, hl: float, z: float, rgba: Any) -> None:
    _line(bm, col, fr, -hw, -hl, hw, -hl, z, rgba)
    _line(bm, col, fr, hw, -hl, hw, hl, z, rgba)
    _line(bm, col, fr, hw, hl, -hw, hl, z, rgba)
    _line(bm, col, fr, -hw, hl, -hw, -hl, z, rgba)


def _spot(bm: bmesh.types.BMesh, col: Any, fr: _Frame, u: float, v: float, z: float, rgba: Any, r: float = 0.12) -> None:
    _flat_quad(bm, col, [fr.w(u - r, v - r), fr.w(u + r, v - r), fr.w(u + r, v + r), fr.w(u - r, v + r)], z, rgba)


def _hoop(bm: bmesh.types.BMesh, col: Any, fr: _Frame, sgn: float, hl: float, z0: float) -> None:
    """Pole behind the baseline, overhanging arm, white backboard and an orange rim (FIBA heights)."""
    c_pole = srgb_hex_to_linear_rgba(C_POLE)
    c_board = srgb_hex_to_linear_rgba(C_BOARD)
    c_rim = srgb_hex_to_linear_rgba(C_RIM)
    pu, pv = fr.w(0.0, sgn * (hl + 1.0))
    add_box_vc(bm, col, pu, pv, z0, z0 + 3.45, 0.10, 0.10, c_pole, c_pole, rot_rad=fr.rot)
    au, av = fr.w(0.0, sgn * (hl - 0.05))
    add_box_vc(bm, col, au, av, z0 + 3.25, z0 + 3.40, 0.06, 1.05, c_pole, c_pole, rot_rad=fr.rot)
    bu, bv = fr.w(0.0, sgn * (hl - 1.2))
    add_box_vc(bm, col, bu, bv, z0 + 2.90, z0 + 3.95, 0.90, 0.03, c_board, c_board, rot_rad=fr.rot)
    _arc(bm, col, fr, 0.0, sgn * (hl - 1.575), 0.225, 0.0, 2 * math.pi, 8, z0 + 3.05, c_rim, width=0.05)


def _basketball(bm: bmesh.types.BMesh, col: Any, fr: _Frame, hw: float, hl: float, z_surf: float, rgba: Any, key_fill: Any | None) -> None:
    """FIBA markings and two hoops."""
    z = z_surf + 0.02
    _outline(bm, col, fr, hw, hl, z, rgba)
    _line(bm, col, fr, -hw, 0.0, hw, 0.0, z, rgba)
    _arc(bm, col, fr, 0.0, 0.0, 1.8, 0.0, 2 * math.pi, 16, z, rgba)
    key_hw, key_d = 2.45, 5.8
    corner_u = hw - 0.9
    three_r = 6.75
    for sgn in (-1.0, 1.0):
        base = sgn * hl
        ft = sgn * (hl - key_d)
        hoop_v = sgn * (hl - 1.575)
        a_in = -sgn * math.pi / 2  # direction from the basket toward mid-court
        if key_fill is not None:
            _flat_quad(bm, col, [fr.w(-key_hw, base), fr.w(key_hw, base), fr.w(key_hw, ft), fr.w(-key_hw, ft)], z_surf + 0.01, key_fill)
        _line(bm, col, fr, -key_hw, base, -key_hw, ft, z, rgba)
        _line(bm, col, fr, key_hw, base, key_hw, ft, z, rgba)
        _line(bm, col, fr, -key_hw, ft, key_hw, ft, z, rgba)
        _arc(bm, col, fr, 0.0, ft, 1.8, a_in - math.pi / 2, a_in + math.pi / 2, 10, z, rgba)  # free-throw semicircle
        _arc(bm, col, fr, 0.0, hoop_v, 1.25, a_in - math.pi / 2, a_in + math.pi / 2, 8, z, rgba)  # restricted area
        # 3-point line: straight corner segments 0.9 m inside the sidelines, joined by the 6.75 m arc
        if corner_u < three_r:
            dv = math.sqrt(three_r * three_r - corner_u * corner_u)
            v_meet = hoop_v - sgn * dv
            for su in (-1.0, 1.0):
                _line(bm, col, fr, su * corner_u, base, su * corner_u, v_meet, z, rgba)
            half_ang = math.atan2(dv, corner_u)
            span = math.pi / 2 - half_ang
            _arc(bm, col, fr, 0.0, hoop_v, three_r, a_in - span, a_in + span, 18, z, rgba)
        _hoop(bm, col, fr, sgn, hl, z_surf)


def _futsal(bm: bmesh.types.BMesh, col: Any, fr: _Frame, hw: float, hl: float, z_surf: float, rgba: Any) -> None:
    z = z_surf + 0.02
    _outline(bm, col, fr, hw, hl, z, rgba)
    _line(bm, col, fr, -hw, 0.0, hw, 0.0, z, rgba)
    _arc(bm, col, fr, 0.0, 0.0, 3.0, 0.0, 2 * math.pi, 20, z, rgba)
    _spot(bm, col, fr, 0.0, 0.0, z, rgba)
    c_goal = srgb_hex_to_linear_rgba(C_GOAL)
    post_u = 1.58  # outside of each 3 m goal's posts (incl. 8 cm posts)
    for sgn in (-1.0, 1.0):
        gl = sgn * hl
        # 6 m quarter circles centred on the outside of each goalpost, joined by a 3.16 m line parallel to goal line
        left = (math.pi, 1.5 * math.pi) if sgn > 0 else (0.5 * math.pi, math.pi)
        right = (1.5 * math.pi, 2.0 * math.pi) if sgn > 0 else (0.0, 0.5 * math.pi)
        _arc(bm, col, fr, -post_u, gl, 6.0, left[0], left[1], 8, z, rgba)
        _arc(bm, col, fr, post_u, gl, 6.0, right[0], right[1], 8, z, rgba)
        _line(bm, col, fr, -post_u, gl - sgn * 6.0, post_u, gl - sgn * 6.0, z, rgba)
        _spot(bm, col, fr, 0.0, gl - sgn * 6.0, z, rgba)  # penalty mark
        _spot(bm, col, fr, 0.0, gl - sgn * 10.0, z, rgba)  # second penalty mark
        # 3 x 2 m goal: posts, crossbar and a shallow back frame
        for gu in (-1.5, 1.5):
            pu, pv = fr.w(gu, gl + sgn * 0.04)
            add_box_vc(bm, col, pu, pv, z_surf, z_surf + 2.0, 0.04, 0.04, c_goal, c_goal, rot_rad=fr.rot)
            ru, rv = fr.w(gu, gl + sgn * 0.9)
            add_box_vc(bm, col, ru, rv, z_surf, z_surf + 0.9, 0.03, 0.03, c_goal, c_goal, rot_rad=fr.rot)
        cu, cv = fr.w(0.0, gl + sgn * 0.04)
        add_box_vc(bm, col, cu, cv, z_surf + 1.96, z_surf + 2.04, 1.54, 0.04, c_goal, c_goal, rot_rad=fr.rot)
        bu, bv = fr.w(0.0, gl + sgn * 0.9)
        add_box_vc(bm, col, bu, bv, z_surf + 0.87, z_surf + 0.93, 1.53, 0.03, c_goal, c_goal, rot_rad=fr.rot)


def _volleyball(bm: bmesh.types.BMesh, col: Any, fr: _Frame, z_surf: float, rgba: Any) -> None:
    z = z_surf + 0.02
    _outline(bm, col, fr, 4.5, 9.0, z, rgba)
    _line(bm, col, fr, -4.5, 0.0, 4.5, 0.0, z, rgba)
    for sgn in (-1.0, 1.0):
        _line(bm, col, fr, -4.5, sgn * 3.0, 4.5, sgn * 3.0, z, rgba)  # attack lines
    c_pole = srgb_hex_to_linear_rgba(C_POLE)
    c_net = srgb_hex_to_linear_rgba(C_NET)
    c_band = srgb_hex_to_linear_rgba(C_NET_BAND)
    for su in (-1.0, 1.0):
        pu, pv = fr.w(su * 5.0, 0.0)
        add_box_vc(bm, col, pu, pv, z_surf, z_surf + 2.55, 0.05, 0.05, c_pole, c_pole, rot_rad=fr.rot)
    nu, nv = fr.w(0.0, 0.0)
    add_box_vc(bm, col, nu, nv, z_surf + 1.43, z_surf + 2.37, 4.95, 0.01, c_net, c_net, rot_rad=fr.rot)
    add_box_vc(bm, col, nu, nv, z_surf + 2.37, z_surf + 2.43, 4.95, 0.015, c_band, c_band, rot_rad=fr.rot)


def _surface_fn(kind: str, hl: float) -> Callable[[float, float], tuple[float, float, float, float]]:
    """Per-vertex colour 'texture' for each surface material."""
    if kind == "acrylic":
        red = srgb_hex_to_linear_rgba(C_ACRYLIC_RED)

        def acrylic(u: float, v: float) -> tuple[float, float, float, float]:
            return _shade(red, 0.97 + 0.06 * _hash01(u, v))  # red apron; crisp teal play area drawn on top
        return acrylic
    if kind == "turf":
        a = srgb_hex_to_linear_rgba(C_TURF_A)
        b = srgb_hex_to_linear_rgba(C_TURF_B)

        def turf(u: float, v: float) -> tuple[float, float, float, float]:
            stripe = int(math.floor((v + hl) / 4.4)) % 2  # mowing-pattern bands across the pitch
            return _shade(a if stripe else b, 0.97 + 0.05 * _hash01(u, v))
        return turf
    base = srgb_hex_to_linear_rgba({"dirt": C_DIRT, "clay": C_CLAY, "earth": C_EARTH}[kind])
    amp = 0.16 if kind != "clay" else 0.10

    def earth(u: float, v: float) -> tuple[float, float, float, float]:
        # mottled earth: fine grain + broad patches, slightly darker where play concentrates
        broad = 0.5 + 0.5 * math.sin(u * 0.41 + 1.3) * math.cos(v * 0.33 - 0.7)
        worn = math.exp(-((u / 6.0) ** 2 + (v / 9.0) ** 2))
        k = 1.0 - amp * 0.5 + amp * (0.55 * _hash01(u, v) + 0.45 * broad) - 0.07 * worn
        return _shade(base, k)
    return earth


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
    c_skirt = srgb_hex_to_linear_rgba(C_SKIRT)
    c_line = srgb_hex_to_linear_rgba(C_LINE)
    c_faint = srgb_hex_to_linear_rgba(C_LINE_FAINT)
    frames: dict[str, _Frame] = {}
    levels: dict[str, float] = {}
    for key, spec in COURTS.items():
        cx, cy = ll2xy(*spec["center"])
        fr = _Frame(cx, cy, rot)
        frames[key] = fr
        hw, hl = spec["w"] * 0.5, spec["l"] * 0.5
        zs = [terrain.sample(*fr.w(-hw + 2 * hw * i / 4, -hl + 2 * hl * j / 4)) for i in range(5) for j in range(5)]
        z_top = max(zs) + 0.12  # each court is its own level terrace -> low retaining skirts
        levels[key] = z_top
        ring = _rect(fr, hw, hl)
        _grid_surface(bm, col, fr, hw, hl, z_top, _surface_fn(spec["surface"], hl))
        _skirt(bm, col, ring, z_top, min(zs) - 1.2, c_skirt)
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        solid_colliders.append(((min(xs) - 1.0, min(ys) - 1.0, max(xs) + 1.0, max(ys) + 1.0), [ring]))
        print(f"  Yagnavalkya court {key}: terrain spread {max(zs) - min(zs):.2f} m")

    # 1. Acrylic basketball court: crisp teal play area over the red apron, red painted keys
    _flat_quad(
        bm, col, _rect(frames["teal_basketball"], 7.65, 15.75), levels["teal_basketball"] + 0.006,
        srgb_hex_to_linear_rgba(C_ACRYLIC_TEAL),
    )
    _basketball(
        bm, col, frames["teal_basketball"], 7.5, 14.0, levels["teal_basketball"], c_line,
        key_fill=srgb_hex_to_linear_rgba(C_ACRYLIC_RED),
    )
    # 3. Futsal turf
    _futsal(bm, col, frames["turf_pitch"], 9.25, 17.7, levels["turf_pitch"], c_line)
    # 4. Renovated clay volleyball court (lines centred on the OSM court)
    vcx, vcy = ll2xy(*VOLLEYBALL_LINES_CENTER)
    _volleyball(bm, col, _Frame(vcx, vcy, rot), levels["clay_volleyball_yard"], c_line)
    # 5. Earth basketball court (faint lime lines, no painted key)
    bcx, bcy = ll2xy(*NORTH_BASKETBALL_LINES_CENTER)
    _basketball(bm, col, _Frame(bcx, bcy, rot), 7.5, 14.0, levels["earth_basketball_yard"], c_faint, key_fill=None)

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
