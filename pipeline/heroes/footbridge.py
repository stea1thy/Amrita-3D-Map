"""Raised, roofed footbridges with stair flights at both ends (`overrides.json` -> `footbridges`).

The AB-2 / IT Canteen shortcut follows the owner's sketch: stairs up from the AB-2 side, a high
covered deck on piers over the road, then a turn and stairs down facing the canteen, clear of the road.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy

import footbridges
from hero_models.geom_helpers import add_box_vc, add_quad_vc, add_tri_vc, srgb_hex_to_linear_rgba

DECK_THICKNESS_M = 0.35
RAIL_HEIGHTS_M = (0.55, 1.1)
RAIL_DEPTH_M = 0.12
STEP_RUN_M = 0.55
ROOF_POST_SPACING_M = 5.0
ROOF_HEIGHT_M = 2.6
ROOF_RISE_M = 0.85
PIER_SPACING_M = 11.5
# Piers are kept off the road that the raised span crosses: (distance along the bridge, from, to)
PIER_FREE_M: tuple[tuple[float, float], ...] = ((38.0, 47.5),)


def build_hero(context: dict[str, Any]) -> None:
    for bridge in footbridges.load_footbridges(context["overrides"]):
        _BridgeBuilder(context, bridge).build()


class _BridgeBuilder:
    def __init__(self, context: dict[str, Any], bridge: footbridges.Footbridge) -> None:
        self.context, self.bridge = context, bridge
        self.terrain = context["terrain"]
        self.half = bridge.width / 2.0
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new("Color")
        cx, cy, _, _ = bridge.point_at(0.5)
        self.offset = (cx, cy, bridge.deck_height(0.5, self.terrain.sample))
        self.deck = srgb_hex_to_linear_rgba("#BBA78F")
        self.edge = srgb_hex_to_linear_rgba("#8E8578")
        self.steel = srgb_hex_to_linear_rgba("#C3C9CD")
        self.concrete = srgb_hex_to_linear_rgba("#CDC6B8")
        self.tile = srgb_hex_to_linear_rgba("#CC7F5E")
        self.fascia = srgb_hex_to_linear_rgba("#EDE7D8")

    # -- primitives ---------------------------------------------------------
    def quad(self, pts: list[tuple[float, float, float]], rgba) -> None:
        ox, oy, oz = self.offset
        verts = [self.bm.verts.new((x - ox, y - oy, z - oz)) for x, y, z in pts]
        add_quad_vc(self.bm, self.col, verts[0], verts[1], verts[2], verts[3], rgba)

    def tri(self, pts: list[tuple[float, float, float]], rgba) -> None:
        ox, oy, oz = self.offset
        verts = [self.bm.verts.new((x - ox, y - oy, z - oz)) for x, y, z in pts]
        add_tri_vc(self.bm, self.col, (verts[0], verts[1], verts[2]), rgba)

    def post(self, x: float, y: float, z0: float, z1: float, half: float, rgba, rot: float = 0.0) -> None:
        add_box_vc(self.bm, self.col, x, y, z0, z1, half, half, rgba, rot_rad=rot, offset_xyz=self.offset)

    @staticmethod
    def sides(p: tuple[float, float], tx: float, ty: float, half: float):
        """(right edge, left edge) points either side of the centre line."""
        return (p[0] + ty * half, p[1] - tx * half), (p[0] - ty * half, p[1] + tx * half)

    def slab(self, ea, eb, za: float, zb: float) -> None:
        """Deck or stringer slab between two (right, left) edge pairs with sloping top and underside."""
        (r0, l0), (r1, l1) = ea, eb
        ba, bb = za - DECK_THICKNESS_M, zb - DECK_THICKNESS_M
        self.quad([(*r0, za), (*r1, zb), (*l1, zb), (*l0, za)], self.deck)
        self.quad([(*l0, ba), (*l1, bb), (*r1, bb), (*r0, ba)], self.edge)
        self.quad([(*r0, ba), (*r1, bb), (*r1, zb), (*r0, za)], self.edge)
        self.quad([(*l1, bb), (*l0, ba), (*l0, za), (*l1, zb)], self.edge)

    def railings(self, ea, eb, za: float, zb: float) -> None:
        for p0, p1 in zip(ea, eb):
            for h in RAIL_HEIGHTS_M:
                lo0, lo1 = za + h - RAIL_DEPTH_M, zb + h - RAIL_DEPTH_M
                self.quad([(*p0, lo0), (*p1, lo1), (*p1, zb + h), (*p0, za + h)], self.steel)
                self.quad([(*p1, lo1), (*p0, lo0), (*p0, za + h), (*p1, zb + h)], self.steel)
            posts = max(1, int(math.dist(p0, p1) // 2.4))
            for i in range(posts + 1):
                f = i / posts
                z = za + (zb - za) * f
                self.post(p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f,
                          z - 0.05, z + RAIL_HEIGHTS_M[-1], 0.06, self.steel)

    # -- spans --------------------------------------------------------------
    def stairs(self, a, b, za: float, zb: float) -> None:
        """Flight of block steps from a to b over a sloping stringer."""
        length = math.dist(a, b)
        tx, ty = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        count = max(2, int(round(length / STEP_RUN_M)))
        ea, eb = self.sides(a, tx, ty, self.half), self.sides(b, tx, ty, self.half)
        self.slab(ea, eb, za - 0.12, zb - 0.12)
        for i in range(count):
            f0, f1 = i / count, (i + 1) / count
            p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
            p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
            z = za + (zb - za) * (f1 if zb > za else f0)
            r0, l0 = self.sides(p0, tx, ty, self.half - 0.08)
            r1, l1 = self.sides(p1, tx, ty, self.half - 0.08)
            self.quad([(*r0, z), (*r1, z), (*l1, z), (*l0, z)], self.deck if i % 2 else self.concrete)
            low = z - abs(zb - za) / count
            edge_r, edge_l = (r0, l0) if zb > za else (r1, l1)
            if zb > za:
                self.quad([(*edge_l, low), (*edge_r, low), (*edge_r, z), (*edge_l, z)], self.edge)
            else:
                self.quad([(*edge_r, low), (*edge_l, low), (*edge_l, z), (*edge_r, z)], self.edge)
        self.railings(ea, eb, za, zb)
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        self.pier(mid, tx, ty, (za + zb) / 2.0 - DECK_THICKNESS_M - 0.1)

    def level_span(self, index: int, z: float) -> None:
        """Flat deck from points[index] to the next point, mitred into its neighbours at turns."""
        ea = self.bridge.vertex_sides(index, self.half)
        eb = self.bridge.vertex_sides(index + 1, self.half)
        self.slab(ea, eb, z, z)
        self.railings(ea, eb, z, z)
        if self.bridge.roof:
            self.roof(index, z)

    def roof(self, index: int, z: float) -> None:
        """Pitched tile canopy on slim posts; gabled at both ends of the raised span, mitred at turns."""
        a, b = self.bridge.points[index], self.bridge.points[index + 1]
        length = math.dist(a, b)
        tx, ty = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        first, last = index == 1, index + 1 == len(self.bridge.points) - 2
        bays = max(1, int(round(length / ROOF_POST_SPACING_M)))
        eave = z + ROOF_HEIGHT_M
        for i in range(0 if first else 1, bays + 1):
            f = i / bays
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            if i in (0, bays):
                sides = self.bridge.vertex_sides(index + (i == bays), self.half - 0.05)
            else:
                sides = self.sides(p, tx, ty, self.half - 0.05)
            for side in sides:
                self.post(*side, z, eave, 0.1, self.fascia, rot=math.atan2(ty, tx))
        eave_half = self.half + 0.55
        if first:
            a = (a[0] - tx * 0.5, a[1] - ty * 0.5)
            r0, l0 = self.sides(a, tx, ty, eave_half)
        else:
            r0, l0 = self.bridge.vertex_sides(index, eave_half)
        if last:
            b = (b[0] + tx * 0.5, b[1] + ty * 0.5)
            r1, l1 = self.sides(b, tx, ty, eave_half)
        else:
            r1, l1 = self.bridge.vertex_sides(index + 1, eave_half)
        ridge0, ridge1 = (*a, eave + ROOF_RISE_M), (*b, eave + ROOF_RISE_M)
        self.quad([(*r0, eave), (*r1, eave), ridge1, ridge0], self.tile)
        self.quad([(*l1, eave), (*l0, eave), ridge0, ridge1], self.tile)
        self.quad([(*l0, eave), (*l1, eave), (*r1, eave), (*r0, eave)], self.fascia)
        if first:
            self.tri([(*l0, eave), (*r0, eave), ridge0], self.fascia)
        if last:
            self.tri([(*r1, eave), (*l1, eave), ridge1], self.fascia)

    def pier(self, p: tuple[float, float], tx: float, ty: float, z_top: float) -> None:
        z_ground = self.terrain.sample(*p) - 1.2
        if z_top - z_ground < 1.8:
            return
        add_box_vc(self.bm, self.col, p[0], p[1], z_ground, z_top, 0.3, self.half * 0.78, self.concrete,
                   rot_rad=math.atan2(ty, tx), offset_xyz=self.offset)

    def raised_piers(self, level: float) -> None:
        fractions = self.bridge.vertex_fractions()
        start, end = fractions[1] * self.bridge.length, fractions[-2] * self.bridge.length
        bays = max(1, int(math.ceil((end - start) / PIER_SPACING_M)))
        for i in range(bays + 1):
            s = start + (end - start) * i / bays
            for lo, hi in PIER_FREE_M:
                if lo < s < hi:
                    s = lo if s - lo < hi - s else hi
            x, y, tx, ty = self.bridge.point_at(s / self.bridge.length)
            self.pier((x, y), tx, ty, level - DECK_THICKNESS_M)

    # -- assembly -----------------------------------------------------------
    def build(self) -> None:
        bridge, points = self.bridge, self.bridge.points
        level = bridge.deck_level(self.terrain.sample)
        z_start = bridge.deck_height(0.0, self.terrain.sample)
        z_end = bridge.deck_height(1.0, self.terrain.sample)
        self.stairs(points[0], points[1], z_start, level)
        for index in range(1, len(points) - 2):
            self.level_span(index, level)
        self.stairs(points[-2], points[-1], level, z_end)
        self.raised_piers(level)
        self._register(level)

    def _register(self, level: float) -> None:
        bridge, config = self.bridge, self.context["config"]
        self.bm.normal_update()
        mesh_name = "BRIDGE_" + bridge.id.replace("/", "_").replace("-", "_")
        mesh = bpy.data.meshes.new(mesh_name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(self.context["mat_body"])
        obj = bpy.data.objects.new(mesh_name, mesh)
        obj.location = self.offset
        bpy.context.scene.collection.objects.link(obj)

        edges = [bridge.vertex_sides(i, self.half) for i in range(len(bridge.points))]
        ring = [r for r, _ in edges] + [l for _, l in edges][::-1]
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        self.context["solid_colliders"].append(
            ((min(xs) - 2.6, min(ys) - 2.6, max(xs) + 2.6, max(ys) + 2.6), [ring])
        )
        cx, cy, cz = self.offset
        self.context["inspectables"].append({
            "id": bridge.id,
            "meshName": mesh_name,
            "kind": "bridge",
            "name": bridge.name,
            "subtitle": "Covered high-level shortcut with stairs",
            "isNamed": True,
            "category": "landmark",
            "floors": 1,
            "heightM": round(level - self.terrain.sample(*bridge.points[0]), 2),
            "center": [round(cx, 3), round(cz, 3), round(-cy, 3)],
            "latLon": list(config.local_xz_to_latlon(cx, -cy)),
            "boundsXZ": [round(min(xs), 1), round(-max(ys), 1), round(max(xs), 1), round(-min(ys), 1)],
            "footprintXZ": [[round(x, 1), round(-y, 1)] for x, y in ring],
            "rawTags": {"bridge": "yes", "highway": "footway"},
            "tags": ["bridge", "footbridge", "shortcut", "it canteen", "stairs"],
            "departments": [],
            "boundingRadius": round(bridge.length / 2.0 + 1.0, 2),
        })
