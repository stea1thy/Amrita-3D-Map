"""Modular hero: concrete basketball court against the east wall of Vasishta Bhavanam.

Esri imagery shows a pale paved slab (~27 x 33 m) right beside Vasishta's east wing, which the owner
confirmed on site is the hostel's basketball court, painted in bright acrylic colours. Google Open Buildings mis-detected the slab's markings
as three thin buildings (`overture/c9c97b2d-b78`, `overture/eceeb6b9-115`, `overture/f83e0027-dd0`, listed
in `overrides.json` `exclude_ids`); this module draws the court in their place: a level concrete slab on a
low retaining skirt, finished as a colourful acrylic court: green surround, blue play area, red keys and
centre circle, white FIBA markings (28 x 15 m) and two hoops. Drawing helpers and
FIBA specs are shared with `yagnavalkya_courts.py`.

All geometry is merged into the existing `STATIC_HeroAccents` mesh so no draw call is added.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from hero_models.geom_helpers import add_tri_vc, srgb_hex_to_linear_rgba

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
