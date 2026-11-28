"""Modular hero: concrete basketball court against the east wall of Vasishta Bhavanam.

Esri imagery shows a pale paved slab (~27 x 33 m) right beside Vasishta's east wing, which the owner
confirmed on site is the hostel's basketball court, painted in bright acrylic colours. Google Open Buildings mis-detected the slab's markings
as three thin buildings (`overture/c9c97b2d-b78`, `overture/eceeb6b9-115`, `overture/f83e0027-dd0`, listed
in `overrides.json` `exclude_ids`); this module draws the court in their place: a level concrete slab on a
low retaining skirt, finished as a colourful acrylic court: green surround, blue play area, red keys and
centre circle, white FIBA markings (28 x 15 m) and two hoops. It is caged in a ~4.5 m dark-green
chain-link fence with a gate on the north side. Per the owner, a long covered cycle stand (sheet roof
on slim posts, rack and parked bicycles) runs in front of Vasishta's north front from just east of the
east entrance porch (leaving the entrance open) past the building's east end, between the building and
the road and ~11 m north of the court. Its sheet roof had been mis-detected by Google
Open Buildings as a one-storey building (`overture/4b86a690-38f`, also in `exclude_ids`). Drawing helpers and
FIBA specs are shared with `yagnavalkya_courts.py`.

Opaque geometry is merged into the existing `STATIC_HeroAccents` mesh, and the see-through chain-link
panels into the tennis courts' `GROUND_TennisFence` mesh (same alpha material, no shadow), so no draw
call is added.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from hero_models.geom_helpers import add_box_vc, add_quad_vc, add_tri_vc, srgb_hex_to_linear_rgba

from .yagnavalkya_courts import (
    C_LINE,
    C_SKIRT,
    _basketball,
    _flat_quad,
    _Frame,
    _grid_surface,
    _make_vcol_material,
    _hash01,
    _rect,
    _shade,
    _skirt,
)

REPLACED_IDS: tuple[str, ...] = ("overture/c9c97b2d-b78", "overture/eceeb6b9-115", "overture/f83e0027-dd0")
# Slab traced from Esri imagery: centre (lat, lon), size E-W x N-S (m), CCW rotation (deg, matches Vasishta)
STRIP_CENTER = (10.90175, 76.896885)
STRIP_W, STRIP_L = 24.0, 33.0
STRIP_ROT_DEG = 2.7
C_SURROUND = "#3E9B5A"  # green acrylic run-off
C_PLAY = "#2F6FB8"  # blue acrylic play area
C_KEY = "#D2483A"  # red keys and centre circle
C_POST = "#2A5A36"  # dark-green cage posts and rails (matches the tennis cage)
CAGE_H = 4.5
CAGE_INSET = 0.4
POST_STEP = 3.3
GATE_W = 2.4
# Cycle stand in Vasishta's building frame (u east along the facade, v north): starts 3 m east of the east
# entrance porch (u <= 106), north of the stair block (v <= 53), south of the road kerb (v >= 74 here) and
# north of the court (v <= 49); built in level sections
STAND_U = (109.0, 181.0)
STAND_V = (60.0, 65.0)
STAND_SECTIONS = 6
STAND_Z_LOW, STAND_Z_HIGH = 2.3, 2.9
C_STAND_ROOF = "#4F7FA6"  # blue-painted metal sheet
C_STAND_POST = "#5E656B"
C_BIKE_FRAMES = ("#B33A2E", "#2E5FA3", "#2B2B2B", "#3C8A4A", "#C9A227")
C_TYRE = "#1F2226"


def _surround(u: float, v: float) -> tuple[float, float, float, float]:
    """Green acrylic with a faint sheen so it reads as a painted surface, not grass."""
    base = srgb_hex_to_linear_rgba(C_SURROUND)
    broad = 0.5 + 0.5 * math.sin(u * 0.37 + 0.4) * math.cos(v * 0.29 - 1.1)
    return _shade(base, 0.96 + 0.03 * _hash01(u, v) + 0.03 * broad)


def _disc(bm: bmesh.types.BMesh, col: Any, fr: _Frame, r: float, z: float, rgba: Any, segs: int = 16) -> None:
    """Filled circle (triangle fan) in the court frame."""
    centre = bm.verts.new((*fr.w(0.0, 0.0), z))
    ring = [bm.verts.new((*fr.w(r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs)), z))
            for i in range(segs)]
    for i in range(segs):
        add_tri_vc(bm, col, (centre, ring[i], ring[(i + 1) % segs]), rgba)


def build_hero(context: dict[str, Any]) -> None:
    import bpy

    terrain = context["terrain"]
    config = context["config"]

    x, z = config.latlon_to_local_xz(*STRIP_CENTER)
    fr = _Frame(x, -z, math.radians(STRIP_ROT_DEG))
    hw, hl = STRIP_W * 0.5, STRIP_L * 0.5

    host = bpy.data.objects.get("STATIC_HeroAccents")
    bm = bmesh.new()
    if host is not None:
        bm.from_mesh(host.data)
        col = bm.loops.layers.color.get("Color") or bm.loops.layers.color.new("Color")
    else:
        col = bm.loops.layers.color.new("Color")

    zs = [terrain.sample(*fr.w(-hw + 2 * hw * i / 4, -hl + 2 * hl * j / 6)) for i in range(5) for j in range(7)]
    z_top = max(zs) + 0.12
    ring = _rect(fr, hw, hl)
    _grid_surface(bm, col, fr, hw, hl, z_top, _surround)
    _skirt(bm, col, ring, z_top, min(zs) - 1.2, srgb_hex_to_linear_rgba(C_SKIRT))
    _flat_quad(bm, col, _rect(fr, 7.5, 14.0), z_top + 0.006, srgb_hex_to_linear_rgba(C_PLAY))
    _disc(bm, col, fr, 1.8, z_top + 0.012, srgb_hex_to_linear_rgba(C_KEY))
    _basketball(bm, col, fr, 7.5, 14.0, z_top, srgb_hex_to_linear_rgba(C_LINE),
                key_fill=srgb_hex_to_linear_rgba(C_KEY))

    _cage_posts(bm, col, fr, hw - CAGE_INSET, hl - CAGE_INSET, z_top)
    _cycle_stand(bm, col, terrain)

    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    context["solid_colliders"].append(((min(xs) - 1.0, min(ys) - 1.0, max(xs) + 1.0, max(ys) + 1.0), [ring]))
    print(f"  Vasishta basketball court: terrain spread {max(zs) - min(zs):.2f} m")

    bm.normal_update()
    if host is not None:
        bm.to_mesh(host.data)
        host.data.update()
        bm.free()
    else:
        mesh = bpy.data.meshes.new("GROUND_VasishtaCourt")
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(context.get("mat_hero_accents") or _make_vcol_material("MAT_VasishtaCourt"))
        obj = bpy.data.objects.new("GROUND_VasishtaCourt", mesh)
        bpy.context.scene.collection.objects.link(obj)
    _chainlink(fr, hw - CAGE_INSET, hl - CAGE_INSET, z_top)


def _cage_runs(hw: float, hl: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Fence runs (court frame) around the court, leaving a gate gap in the middle of the north side."""
    g = GATE_W / 2.0
    return [((-hw, -hl), (hw, -hl)), ((hw, -hl), (hw, hl)), ((hw, hl), (g, hl)),
            ((-g, hl), (-hw, hl)), ((-hw, hl), (-hw, -hl))]


def _cage_posts(bm: bmesh.types.BMesh, col: Any, fr: _Frame, hw: float, hl: float, z0: float) -> None:
    """Dark-green posts every few metres, a top rail and a low kick rail on each run."""
    post = srgb_hex_to_linear_rgba(C_POST)
    for (u0, v0), (u1, v1) in _cage_runs(hw, hl):
        n = max(1, round(math.hypot(u1 - u0, v1 - v0) / POST_STEP))
        for k in range(n + 1):
            f = k / n
            x, y = fr.w(u0 + (u1 - u0) * f, v0 + (v1 - v0) * f)
            add_box_vc(bm, col, x, y, z0, z0 + CAGE_H, 0.05, 0.05, post, post, rot_rad=fr.rot)
        a, b = fr.w(u0, v0), fr.w(u1, v1)
        for za, zb in ((z0 + CAGE_H - 0.12, z0 + CAGE_H), (z0 + 0.25, z0 + 0.35)):
            v = [bm.verts.new((a[0], a[1], za)), bm.verts.new((b[0], b[1], za)),
                 bm.verts.new((b[0], b[1], zb)), bm.verts.new((a[0], a[1], zb))]
            add_quad_vc(bm, col, v[0], v[1], v[2], v[3], post)
            add_quad_vc(bm, col, v[3], v[2], v[1], v[0], post)


def _chainlink(fr: _Frame, hw: float, hl: float, z0: float) -> None:
    """See-through mesh panels, appended to the tennis cage's alpha-blended fence object."""
    import bpy

    host = bpy.data.objects.get("GROUND_TennisFence")
    if host is None:
        return  # tennis cage absent: skip the mesh rather than add a draw call
    fbm = bmesh.new()
    fbm.from_mesh(host.data)
    new_faces = []
    for (u0, v0), (u1, v1) in _cage_runs(hw, hl):
        a, b = fr.w(u0, v0), fr.w(u1, v1)
        new_faces.append(fbm.faces.new([fbm.verts.new((a[0], a[1], z0 + 0.35)), fbm.verts.new((b[0], b[1], z0 + 0.35)),
                                        fbm.verts.new((b[0], b[1], z0 + CAGE_H - 0.12)),
                                        fbm.verts.new((a[0], a[1], z0 + CAGE_H - 0.12))]))
    bmesh.ops.triangulate(fbm, faces=new_faces)
    fbm.to_mesh(host.data)
    host.data.update()
    fbm.free()


def _cycle_stand(bm: bmesh.types.BMesh, col: Any, terrain: Any) -> None:
    """Long open shed in front of Vasishta, stepping with the ground in level sections."""
    from hero_models import vasishta_hero as vh

    fr = _Frame(*vh.to_xy(0.0, 0.0), vh.ROTATION_RAD)  # Vasishta's own (u, v) frame
    (su0, su1), (v0, v1) = STAND_U, STAND_V
    step = (su1 - su0) / STAND_SECTIONS
    post = srgb_hex_to_linear_rgba(C_STAND_POST)
    roof = srgb_hex_to_linear_rgba(C_STAND_ROOF)
    pad = srgb_hex_to_linear_rgba("#B9B3A8")
    tyre = srgb_hex_to_linear_rgba(C_TYRE)
    vm = (v0 + v1) / 2
    bike_i = 0
    for k in range(STAND_SECTIONS):
        u0, u1 = su0 + k * step, su0 + (k + 1) * step
        zs = [terrain.sample(*fr.w(u, v)) for u in (u0, (u0 + u1) / 2, u1) for v in (v0, v1)]
        z0 = max(zs)
        add_box_vc(bm, col, *fr.w((u0 + u1) / 2, vm), min(zs) - 0.4, z0 + 0.08,
                   step / 2, (v1 - v0) / 2 + 0.3, pad, rot_rad=fr.rot)
        for u in (u0 + 0.2, (u0 + u1) / 2, u1 - 0.2):
            for v, zt in ((v0 + 0.2, STAND_Z_LOW), (v1 - 0.2, STAND_Z_HIGH)):
                add_box_vc(bm, col, *fr.w(u, v), z0, z0 + zt, 0.05, 0.05, post, post, rot_rad=fr.rot)
        # mono-pitch sheet roof, low edge toward the building, high edge toward the road
        pts = [(*fr.w(u0, v0 - 0.4), z0 + STAND_Z_LOW), (*fr.w(u1, v0 - 0.4), z0 + STAND_Z_LOW),
               (*fr.w(u1, v1 + 0.4), z0 + STAND_Z_HIGH), (*fr.w(u0, v1 + 0.4), z0 + STAND_Z_HIGH)]
        rv = [bm.verts.new(p) for p in pts]
        add_quad_vc(bm, col, rv[0], rv[1], rv[2], rv[3], roof)
        add_quad_vc(bm, col, rv[3], rv[2], rv[1], rv[0], _shade(roof, 0.7))
        add_box_vc(bm, col, *fr.w((u0 + u1) / 2, vm), z0 + 0.45, z0 + 0.55, step / 2 - 0.3, 0.03, post, post,
                   rot_rad=fr.rot)
        n = int((step - 1.0) // 1.5)
        for i in range(n):
            bike_i += 1
            if (bike_i * 7) % 10 < 3:
                continue  # roughly a third of the slots empty
            u = u0 + 0.8 + i * 1.5
            frame = srgb_hex_to_linear_rgba(C_BIKE_FRAMES[bike_i % len(C_BIKE_FRAMES)])
            for dv in (-0.55, 0.55):
                _wheel(bm, col, fr, u, vm + dv, z0, tyre)
            rear, front, seat = (vm - 0.55, 0.34), (vm + 0.55, 0.34), (vm - 0.2, 0.92)
            fv = [bm.verts.new((*fr.w(u, vv), z0 + zz)) for vv, zz in (rear, front, seat)]
            add_tri_vc(bm, col, (fv[0], fv[1], fv[2]), frame)
            add_tri_vc(bm, col, (fv[0], fv[2], fv[1]), frame)
            add_box_vc(bm, col, *fr.w(u, vm + 0.45), z0 + 0.34, z0 + 1.0, 0.25, 0.025, tyre, tyre, rot_rad=fr.rot)
            add_box_vc(bm, col, *fr.w(u, vm - 0.2), z0 + 0.92, z0 + 0.98, 0.07, 0.12, tyre, tyre, rot_rad=fr.rot)


def _wheel(bm: bmesh.types.BMesh, col: Any, fr: _Frame, u: float, v: float, z0: float, rgba: Any, r: float = 0.34) -> None:
    """Six-sided double-sided wheel disc standing in the bike's plane (the court's v axis)."""
    c = bm.verts.new((*fr.w(u, v), z0 + r))
    ring = [bm.verts.new((*fr.w(u, v + r * math.cos(a)), z0 + r + r * math.sin(a)))
            for a in (k * math.pi / 3 for k in range(6))]
    for k in range(6):
        add_tri_vc(bm, col, (c, ring[k], ring[(k + 1) % 6]), rgba)
        add_tri_vc(bm, col, (c, ring[(k + 1) % 6], ring[k]), rgba)
