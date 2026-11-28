"""Basketball court beside the Gargi hall (`way/380702793`): blue-grey acrylic court with white lines and two
hoops inside the red surround the OSM pitch slab already draws (Google satellite).

The court follows the OSM pitch outline (same registration as the hall next to it); the inner court
covers the middle of the pitch the way the satellite shows it.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy

from hero_models.facade_kit import Kit
from hero_models.geom_helpers import srgb_hex_to_linear_rgba
from terrain_utils import latlon_to_blender_xy

PITCH_ID = "way/380702793"
INNER_S, INNER_T = (0.21, 0.79), (0.12, 0.88)  # fractions of the pitch (s across, t along)
SLAB_LIFT_M = 0.22  # height of the OSM pitch slab above the highest ground under it
LINE_M = 0.12


def _pitch_corners(raw_osm: dict[str, Any]) -> list[tuple[float, float]] | None:
    feat = next((f for f in raw_osm.get("features", []) if f.get("id") == PITCH_ID), None)
    if not feat:
        return None
    ring = [latlon_to_blender_xy(float(c[1]), float(c[0])) for c in feat["geometry"]["coordinates"][0]]
    if len(ring) > 4 and math.dist(ring[0], ring[-1]) < 1e-3:
        ring = ring[:-1]
    return ring if len(ring) == 4 else None


def build_hero(context: dict[str, Any]) -> None:
    corners = _pitch_corners(context.get("raw_osm") or {})
    if corners is None:
        print(f"[gargi_court] {PITCH_ID} not found; court markings skipped")
        return
    # order: put the short edge first so s runs across the court and t along it
    if math.dist(corners[0], corners[1]) > math.dist(corners[1], corners[2]):
        corners = corners[1:] + corners[:1]
    p00, p10, p11, p01 = corners

    def to_xy(s: float, t: float) -> tuple[float, float]:
        return tuple(  # bilinear over the pitch quad
            (1 - s) * (1 - t) * p00[i] + s * (1 - t) * p10[i] + s * t * p11[i] + (1 - s) * t * p01[i] for i in (0, 1)
        )

    terrain = context["terrain"]
    z = max(terrain.sample(*p) for p in corners) + SLAB_LIFT_M + 0.02
    width = math.dist(p00, p10)
    length = math.dist(p10, p11)
    ls, lt = LINE_M / width, LINE_M / length

    bm = bmesh.new()
    col = bm.loops.layers.color.new("Color")
    kit = Kit(bm, col, None, None, to_xy=to_xy)
    s0, s1 = INNER_S
    t0, t1 = INNER_T
    kit.quad([(s0, t0, z), (s1, t0, z), (s1, t1, z), (s0, t1, z)], srgb_hex_to_linear_rgba("#4C5F78"))
    white = srgb_hex_to_linear_rgba("#F2F2EE")
    zl = z + 0.01
    for a0, a1, b0, b1 in (
        (s0, s1, t0, t0 + lt), (s0, s1, t1 - lt, t1), (s0, s0 + ls, t0, t1), (s1 - ls, s1, t0, t1),
        (s0, s1, 0.5 - lt / 2, 0.5 + lt / 2),
    ):
        kit.quad([(a0, b0, zl), (a1, b0, zl), (a1, b1, zl), (a0, b1, zl)], white)
    # painted keys at both ends
    key = srgb_hex_to_linear_rgba("#B5574A")
    for ta, tb in ((t0, t0 + 0.15), (t1 - 0.15, t1)):
        kit.quad([(0.42, ta, zl - 0.005), (0.58, ta, zl - 0.005), (0.58, tb, zl - 0.005), (0.42, tb, zl - 0.005)], key)
    # hoop poles and backboards at the ends
    pole, board = srgb_hex_to_linear_rgba("#3A3D42"), srgb_hex_to_linear_rgba("#F4F4F0")
    for t, sign in ((t0 - 0.02, 1), (t1 + 0.02, -1)):
        kit.box((0.485, 0.515, t - 0.006, t + 0.006), z, z + 3.0, pole)
        bt = t + sign * 0.03
        kit.box((0.45, 0.55, bt - 0.004, bt + 0.004), z + 2.9, z + 3.9, board)

    bm.normal_update()
    mesh = bpy.data.meshes.new("GROUND_GargiCourt")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(context["mat_hero_accents"])
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("GROUND_GargiCourt", mesh))
