"""Arched steel-railed footbridges (`overrides.json` -> `footbridges`).

Modelled on the AB-2 / IT Canteen shortcut bridge: paved deck, galvanised pipe railings, concrete piers.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy

import footbridges
from hero_models.geom_helpers import add_box_vc, add_quad_vc, srgb_hex_to_linear_rgba

DECK_SEGMENTS = 16
DECK_THICKNESS_M = 0.32
RAIL_HEIGHTS_M = (0.55, 1.1)
RAIL_DEPTH_M = 0.12
PIER_FRACTIONS = (0.28, 0.5, 0.72)


def build_hero(context: dict[str, Any]) -> None:
    for bridge in footbridges.load_footbridges(context["overrides"]):
        _build_bridge(context, bridge)


def _build_bridge(context: dict[str, Any], bridge: footbridges.Footbridge) -> None:
    terrain, config = context["terrain"], context["config"]
    bm = bmesh.new()
    col = bm.loops.layers.color.new("Color")
    deck = srgb_hex_to_linear_rgba("#BBA78F")
    edge = srgb_hex_to_linear_rgba("#8E8578")
    steel = srgb_hex_to_linear_rgba("#C3C9CD")
    concrete = srgb_hex_to_linear_rgba("#A8A197")

    cx, cy, _, _ = bridge.point_at(0.5)
    cz = bridge.deck_height(0.5, terrain.sample)
    offset = (cx, cy, cz)
    half = bridge.width / 2.0

    def quad(pts: list[tuple[float, float, float]], rgba) -> None:
        verts = [bm.verts.new((x - cx, y - cy, z - cz)) for x, y, z in pts]
        add_quad_vc(bm, col, verts[0], verts[1], verts[2], verts[3], rgba)

    def station(i: int) -> tuple[tuple[float, float], tuple[float, float], float]:
        """(right edge, left edge, deck height) at deck station i."""
        t = i / DECK_SEGMENTS
        x, y, tx, ty = bridge.point_at(t)
        return ((x + ty * half, y - tx * half), (x - ty * half, y + tx * half),
                bridge.deck_height(t, terrain.sample))

    stations = [station(i) for i in range(DECK_SEGMENTS + 1)]
    for (r0, l0, z0), (r1, l1, z1) in zip(stations, stations[1:]):
        b0, b1 = z0 - DECK_THICKNESS_M, z1 - DECK_THICKNESS_M
        quad([(*r0, z0), (*r1, z1), (*l1, z1), (*l0, z0)], deck)
        quad([(*l0, b0), (*l1, b1), (*r1, b1), (*r0, b0)], edge)
        quad([(*r0, b0), (*r1, b1), (*r1, z1), (*r0, z0)], edge)
        quad([(*l1, b1), (*l0, b0), (*l0, z0), (*l1, z1)], edge)
        for p0, p1 in ((r0, r1), (l0, l1)):
            for h in RAIL_HEIGHTS_M:
                lo0, lo1, hi0, hi1 = z0 + h - RAIL_DEPTH_M, z1 + h - RAIL_DEPTH_M, z0 + h, z1 + h
                quad([(*p0, lo0), (*p1, lo1), (*p1, hi1), (*p0, hi0)], steel)
                quad([(*p1, lo1), (*p0, lo0), (*p0, hi0), (*p1, hi1)], steel)

    for r, l, z in stations[::2]:
        for px, py in (r, l):
            add_box_vc(bm, col, px, py, z - 0.05, z + RAIL_HEIGHTS_M[-1], 0.07, 0.07, steel,
                       offset_xyz=offset)

    for t in PIER_FRACTIONS:
        x, y, tx, ty = bridge.point_at(t)
        z_top = bridge.deck_height(t, terrain.sample) - DECK_THICKNESS_M
        add_box_vc(bm, col, x, y, terrain.sample(x, y) - 1.5, z_top, 0.28, half * 0.8, concrete,
                   rot_rad=math.atan2(ty, tx), offset_xyz=offset)

    bm.normal_update()
    mesh_name = "BRIDGE_" + bridge.id.replace("/", "_").replace("-", "_")
    mesh = bpy.data.meshes.new(mesh_name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(context["mat_body"])
    obj = bpy.data.objects.new(mesh_name, mesh)
    obj.location = offset
    bpy.context.scene.collection.objects.link(obj)

    ring = [s[0] for s in stations] + [s[1] for s in reversed(stations)]
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    context["solid_colliders"].append(((min(xs) - 2.6, min(ys) - 2.6, max(xs) + 2.6, max(ys) + 2.6), [ring]))

    context["inspectables"].append({
        "id": bridge.id,
        "meshName": mesh_name,
        "kind": "bridge",
        "name": bridge.name,
        "subtitle": "Arched shortcut footbridge",
        "isNamed": True,
        "category": "landmark",
        "floors": 1,
        "heightM": round(bridge.rise, 2),
        "center": [round(cx, 3), round(cz, 3), round(-cy, 3)],
        "latLon": list(config.local_xz_to_latlon(cx, -cy)),
        "boundsXZ": [round(min(xs), 1), round(-max(ys), 1), round(max(xs), 1), round(-min(ys), 1)],
        "footprintXZ": [[round(x, 1), round(-y, 1)] for x, y in ring],
        "rawTags": {"bridge": "yes", "highway": "footway"},
        "tags": ["bridge", "footbridge", "shortcut", "it canteen"],
        "departments": [],
        "boundingRadius": round(bridge.length / 2.0 + 1.0, 2),
    })
