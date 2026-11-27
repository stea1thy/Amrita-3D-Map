"""IT Canteen garden: lawn, kerbed stone paths, standing boulder, round red tables and shade trees.

Placed from the canteen's emitted footprint, so it moves with the building.
Local frame (see `hero_models.it_canteen_hero`): u = east of the hall centre, v = north.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy

from hero_models import HERO_IT_CANTEEN_ID
from hero_models.facade_kit import Kit, Rect, color
from hero_models.geom_helpers import add_cylinder_vc, add_tri_vc
from hero_models.it_canteen_hero import frame_from_hall_ring

LAWN: Rect = (9.2, 25.0, -17.0, 15.0)
FRONT_WALK: Rect = (9.2, 11.2, -15.0, 13.0)
DOOR_WALK: Rect = (11.2, 25.0, 3.4, 5.6)
SOUTH_WALK: list[tuple[float, float]] = [(11.2, -9.2), (17.0, -10.6), (22.0, -14.0), (25.0, -17.0)]
BOULDER_UV: tuple[float, float] = (17.5, -2.5)
TABLE_UVS: tuple[tuple[float, float], ...] = ((14.0, -14.2), (19.2, -7.2), (22.5, -2.2), (14.2, 10.2))
# (u, v, scale low, scale high): slender shade trees clear of the paths and tables
TREE_SPOTS: tuple[tuple[float, float, float, float], ...] = (
    (13.5, -5.5, 0.62, 0.72), (19.0, 9.5, 0.75, 0.88), (23.0, 13.0, 0.7, 0.82),
    (24.2, -12.0, 0.68, 0.8),(11.5, 17.5, 0.8, 0.95), (3.0, 22.0, 1.0, 1.15), (-6.0, 23.0, 0.95, 1.1),
    (-15.0, 12.0, 1.0, 1.2), (-15.5, 0.0, 0.9, 1.1), (-14.5, -13.0, 1.0, 1.2), (-5.0, -23.5, 0.9, 1.05),
    (6.0, -22.5, 0.85, 1.0), (17.0, -21.0, 0.95, 1.1), (30.0, -15.0, 0.9, 1.05), (28.0, 10.0, 0.95, 1.15),
)


def build_hero(context: dict[str, Any]) -> None:
    item = next((i for i in context["inspectables"] if i["id"] == HERO_IT_CANTEEN_ID), None)
    if item is None:
        raise RuntimeError(f"IT Canteen {HERO_IT_CANTEEN_ID} missing from the scene; garden not built")
    terrain = context["terrain"]
    frame = frame_from_hall_ring([(x, -z) for x, z in item["footprintXZ"]])

    bm = bmesh.new()
    col = bm.loops.layers.color.new("Color")
    kit = Kit(bm, col, None, None, to_xy=frame.to_xy)
    ground = max(terrain.sample(*frame.to_xy(u, v)) for u in (LAWN[0], LAWN[1]) for v in (LAWN[2], LAWN[3]))

    kit.flat(LAWN, ground + 0.12, color("lawn_green"))
    for walk in (FRONT_WALK, DOOR_WALK):
        _kerbed_walk(kit, walk, ground)
    for (u0, v0), (u1, v1) in zip(SOUTH_WALK, SOUTH_WALK[1:]):
        length = math.hypot(u1 - u0, v1 - v0)
        du, dv = -(v1 - v0) / length * 0.8, (u1 - u0) / length * 0.8
        kit.quad([(u0 - du, v0 - dv, ground + 0.17), (u1 - du, v1 - dv, ground + 0.17),
                  (u1 + du, v1 + dv, ground + 0.17), (u0 + du, v0 + dv, ground + 0.17)], color("path_stone"))
    _boulder(bm, col, frame.to_xy(*BOULDER_UV), ground + 0.1)
    for uv in TABLE_UVS:
        _round_table(bm, col, kit, frame.to_xy(*uv), uv, ground + 0.12)

    bm.normal_update()
    mesh = bpy.data.meshes.new("GROUND_ITCanteen")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(context["mat_hero_accents"])
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("GROUND_ITCanteen", mesh))

    ring = frame.ring([(LAWN[0], LAWN[2]), (LAWN[1], LAWN[2]), (LAWN[1], LAWN[3]), (LAWN[0], LAWN[3])])
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    context["solid_colliders"].append(((min(xs) - 2.6, min(ys) - 2.6, max(xs) + 2.6, max(ys) + 2.6), [ring]))
    context["hand_tree_spots"].extend(
        (*frame.to_xy(u, v), 1, (low, high)) for u, v, low, high in TREE_SPOTS
    )


def _kerbed_walk(kit: Kit, rect: Rect, ground: float) -> None:
    u0, u1, v0, v1 = rect
    kit.flat(rect, ground + 0.17, color("path_stone"))
    along_v = (v1 - v0) > (u1 - u0)
    kerbs = (((u1, u1 + 0.25, v0, v1),) if along_v
             else ((u0, u1, v0 - 0.25, v0), (u0, u1, v1, v1 + 0.25)))
    for kerb in kerbs:
        kit.box(kerb, ground, ground + 0.32, color("granite_light"))


def _boulder(bm: bmesh.types.BMesh, col: Any, centre: tuple[float, float], z: float) -> None:
    """Upright weathered rock: two irregular six-point rings closed to an off-centre tip."""
    cx, cy = centre
    rock, rock_top = color("rock_brown"), color("rock_brown", 1.2)
    rings = []
    for height, radii in ((0.0, (1.35, 1.1, 1.25, 1.4, 1.05, 1.2)), (1.5, (1.05, 0.9, 1.15, 0.95, 0.8, 1.0))):
        rings.append([
            bm.verts.new((cx + r * math.cos(math.tau * k / 6), cy + r * 0.75 * math.sin(math.tau * k / 6), z + height))
            for k, r in enumerate(radii)
        ])
    tip = bm.verts.new((cx + 0.25, cy - 0.1, z + 2.7))
    low, high = rings
    for k in range(6):
        j = (k + 1) % 6
        add_tri_vc(bm, col, (low[k], low[j], high[j]), rock)
        add_tri_vc(bm, col, (low[k], high[j], high[k]), rock)
        add_tri_vc(bm, col, (high[k], high[j], tip), rock_top)


def _round_table(
    bm: bmesh.types.BMesh,
    col: Any,
    kit: Kit,
    centre: tuple[float, float],
    uv: tuple[float, float],
    z: float,
) -> None:
    """Red concrete table on a stem, ringed by two bench seats."""
    cx, cy = centre
    red = color("table_red")
    add_cylinder_vc(bm, col, cx, cy, z, z + 0.7, 0.28, 0.28, 6, red, None)
    add_cylinder_vc(bm, col, cx, cy, z + 0.7, z + 0.86, 1.0, 1.0, 10, red, red)
    u, v = uv
    for side in (-1.0, 1.0):
        kit.box((u - 0.8, u + 0.8, v + side * 1.45 - 0.25, v + side * 1.45 + 0.25), z, z + 0.48, red)
