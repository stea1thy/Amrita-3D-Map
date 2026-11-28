"""Site paving around Academic Block 4: Play Ground Road, the west entrance path and its parking.

Play Ground Road past the block is missing from the OSM extract. Everything is drawn as plain draped
paving: the merged road network's kerb dashes would not fit the triangle budget. Routing uses the
matching `custom_roads` entries (marked `render: false`). The path follows the owner's mark-up.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy

import config
from hero_models.ab4_hero import to_xy
from hero_models.geom_helpers import add_box_vc, add_quad_vc, srgb_hex_to_linear_rgba

ROAD_ID = "road/ab4-play-ground-road"
ENTRY_ID = "road/ab4-entrance"
ROAD_HALF_M = 2.6
PATH_HALF_M = 2.5
SEGMENT_M = 3.5  # short enough to follow the terrain without it showing through
ASPHALT_HEX = "#9EA4AB"
PAVING_HEX = "#B7B0A4"
PARKING_HEX = "#868C94"
LINE_HEX = "#F4F2EC"
# West-side parking in the AB-4 frame: straight west edge, east edge slanting along the entrance path
PARKING_WEST_U = -33.0
PARKING_V = (-35.0, -11.0)
PARKING_EAST_U = (-22.0, -19.2)  # at PARKING_V[0] and PARKING_V[1]
BAY_COUNT = 8
BAY_DEPTH_M = 5.0
# (u, v, body colour) of parked cars, nose towards the west edge
CARS: tuple[tuple[float, float, str], ...] = (
    (-30.4, -33.5, "#D9DCE0"), (-30.4, -24.5, "#8E2F2B"), (-30.4, -18.5, "#2E4A6B"),
)


def _resample(points: list[tuple[float, float]], step: float) -> list[tuple[float, float]]:
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        count = max(1, math.ceil(math.dist(a, b) / step))
        out.extend((a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count) for i in range(1, count + 1))
    return out


def _edges(points: list[tuple[float, float]], index: int, half: float):
    """(right, left) edge points, square to the local direction of travel."""
    a, b = points[max(index - 1, 0)], points[min(index + 1, len(points) - 1)]
    length = math.dist(a, b)
    nx, ny = (b[1] - a[1]) / length * half, (a[0] - b[0]) / length * half
    x, y = points[index]
    return (x + nx, y + ny), (x - nx, y - ny)


class _Paving:
    def __init__(self, context: dict[str, Any]) -> None:
        self.terrain = context["terrain"]
        self.colliders = context["solid_colliders"]
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new("Color")

    def vert(self, p: tuple[float, float], lift: float):
        return self.bm.verts.new((p[0], p[1], self.terrain.sample(*p) + lift))

    def quad(self, pts, lift: float, hex_colour: str) -> None:
        """Draped quad from four ground points, counter-clockwise seen from above."""
        v = [self.vert(p, lift) for p in pts]
        add_quad_vc(self.bm, self.col, v[0], v[1], v[2], v[3], srgb_hex_to_linear_rgba(hex_colour))

    def keep_clear(self, ring: list[tuple[float, float]], margin: float) -> None:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        self.colliders.append(((min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin), [ring]))

    def ribbon(self, line: list[tuple[float, float]], half: float, lift: float, hex_colour: str) -> None:
        line = _resample(line, SEGMENT_M)
        sections = [_edges(line, i, half) for i in range(len(line))]
        for (r0, l0), (r1, l1) in zip(sections, sections[1:]):
            self.quad((r0, r1, l1, l0), lift, hex_colour)
        # one collider per stretch, so trees keep off the paving without clearing its whole bounding box
        for i in range(len(line) - 1):
            wide0, wide1 = _edges(line, i, half + 1.2), _edges(line, i + 1, half + 1.2)
            self.keep_clear([wide0[0], wide1[0], wide1[1], wide0[1]], 0.0)

    def rect(self, u0: float, u1: float, v0: float, v1: float, lift: float, hex_colour: str, nu: int, nv: int) -> None:
        for i in range(nu):
            for j in range(nv):
                a, b = u0 + (u1 - u0) * i / nu, u0 + (u1 - u0) * (i + 1) / nu
                c, d = v0 + (v1 - v0) * j / nv, v0 + (v1 - v0) * (j + 1) / nv
                self.quad((to_xy(a, c), to_xy(b, c), to_xy(b, d), to_xy(a, d)), lift, hex_colour)

    def parking_surface(self) -> None:
        (v0, v1), (east0, east1) = PARKING_V, PARKING_EAST_U
        cols, rows = 4, 7

        def point(i: int, j: int) -> tuple[float, float]:
            t = j / rows
            east = east0 + (east1 - east0) * t
            return to_xy(PARKING_WEST_U + (east - PARKING_WEST_U) * i / cols, v0 + (v1 - v0) * t)

        for i in range(cols):
            for j in range(rows):
                self.quad((point(i, j), point(i + 1, j), point(i + 1, j + 1), point(i, j + 1)), 0.15, PARKING_HEX)
        self.keep_clear([point(0, 0), point(cols, 0), point(cols, rows), point(0, rows)], 1.5)

    def car(self, u: float, v: float, hex_colour: str) -> None:
        x, y = to_xy(u, v)
        z = self.terrain.sample(x, y)
        body, glass = srgb_hex_to_linear_rgba(hex_colour), srgb_hex_to_linear_rgba("#2B333B")
        add_box_vc(self.bm, self.col, x, y, z + 0.35, z + 0.95, 2.1, 0.9, body, rot_rad=0.12)
        add_box_vc(self.bm, self.col, x + 0.2, y, z + 0.95, z + 1.5, 1.15, 0.82, glass, rot_rad=0.12)

    def finish(self, context: dict[str, Any]) -> None:
        self.bm.normal_update()
        mesh = bpy.data.meshes.new("ROAD_ab4_site")
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(context["mat_body"])
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(mesh.name, mesh))


def _line_of(context: dict[str, Any], road_id: str) -> list[tuple[float, float]] | None:
    road = next((r for r in context["overrides"].get("custom_roads") or [] if r.get("id") == road_id), None)
    if road is None:
        return None
    out = []
    for lat, lon in road["points"]:
        x, z = config.latlon_to_local_xz(float(lat), float(lon))
        out.append((x, -z))
    return out


def build_hero(context: dict[str, Any]) -> None:
    road, entry = _line_of(context, ROAD_ID), _line_of(context, ENTRY_ID)
    if road is None or entry is None:
        return
    paving = _Paving(context)
    paving.ribbon(road, ROAD_HALF_M, 0.14, ASPHALT_HEX)
    # the routing line starts on the road centre to join the walking graph; the paving starts at the kerb
    paving.ribbon(entry[1:], PATH_HALF_M, 0.17, PAVING_HEX)

    paving.parking_surface()
    v0, v1 = PARKING_V
    for i in range(BAY_COUNT + 1):
        v = v0 + i * (v1 - v0) / BAY_COUNT
        paving.rect(PARKING_WEST_U, PARKING_WEST_U + BAY_DEPTH_M, v - 0.08, v + 0.08, 0.2, LINE_HEX, 1, 1)
    for u, v, hex_colour in CARS:
        paving.car(u, v, hex_colour)
    paving.finish(context)
