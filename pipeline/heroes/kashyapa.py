"""Photo-informed connectivity and facade cues for Kashyapa Bhavan.

The OSM footprints in this area are incomplete.  The override layer supplies the
individual roof masses; this module adds the covered circulation that visibly
joins them, plus a restrained set of peach structural bands and ventilation
screens observed in the supplied ground photographs.  Geometry is intentionally
low-poly: it improves the landmark silhouette without consuming the scene budget
with repeated window meshes.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy

from hero_models.geom_helpers import add_box_vc, srgb_hex_to_linear_rgba


CREAM = srgb_hex_to_linear_rgba("#F2ECE0")
PEACH = srgb_hex_to_linear_rgba("#D18A78")
VENT_BRICK = srgb_hex_to_linear_rgba("#A95443")
DARK_ROOF = srgb_hex_to_linear_rgba("#46505C")
GLASS = srgb_hex_to_linear_rgba("#263744")


def _xy(config: Any, point: list[float]) -> tuple[float, float]:
    x_east, z_south = config.latlon_to_local_xz(point[0], point[1])
    return x_east, -z_south


def _centre(config: Any, ring: list[list[float]]) -> tuple[float, float]:
    pts = [_xy(config, p) for p in ring[:-1]]
    return (
        sum(p[0] for p in pts) / len(pts),
        sum(p[1] for p in pts) / len(pts),
    )


def _span(
    bm: bmesh.types.BMesh,
    col: Any,
    terrain: Any,
    a: tuple[float, float],
    b: tuple[float, float],
    width: float,
    name: str,
) -> list[tuple[float, float]]:
    """Add a shallow roofed circulation link and return its plan ring."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 2.0:
        return []
    rot = math.atan2(dy, dx)
    cx, cy = (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5
    z0 = max(terrain.sample(a[0], a[1]), terrain.sample(b[0], b[1])) + 0.05
    # Cream lower arcade and peach coping echo the actual hostel; the roof is
    # light concrete with a distinct solar strip, as seen in the satellite view.
    add_box_vc(bm, col, cx, cy, z0, z0 + 5.65, length * 0.5, width * 0.5, CREAM, CREAM, rot)
    add_box_vc(bm, col, cx, cy, z0 + 2.84, z0 + 3.08, length * 0.5 + 0.12, width * 0.5 + 0.12, PEACH, PEACH, rot)
    add_box_vc(bm, col, cx, cy, z0 + 5.65, z0 + 5.94, length * 0.5 + 0.22, width * 0.5 + 0.22, PEACH, PEACH, rot)
    add_box_vc(bm, col, cx, cy, z0 + 5.94, z0 + 6.10, length * 0.5 + 0.30, width * 0.5 + 0.30, CREAM, CREAM, rot)
    add_box_vc(bm, col, cx, cy, z0 + 6.11, z0 + 6.15, length * 0.43, min(0.85, width * 0.19), DARK_ROOF, DARK_ROOF, rot)
    # A small number of red perforated-screen panels makes the links readable at
    # pedestrian camera heights without modelling thousands of holes.
    panel_count = max(1, min(5, int(length / 20.0)))
    for i in range(panel_count):
        t = (i + 0.5) / panel_count - 0.5
        px = cx + math.cos(rot) * length * t
        py = cy + math.sin(rot) * length * t
        add_box_vc(bm, col, px, py, z0 + 3.65, z0 + 4.55, 2.0, width * 0.5 + 0.035, VENT_BRICK, VENT_BRICK, rot)
    nx, ny = -math.sin(rot) * width * 0.5, math.cos(rot) * width * 0.5
    return [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]


def _facade_bands(
    bm: bmesh.types.BMesh,
    col: Any,
    terrain: Any,
    ring: list[list[float]],
    floors: int,
    config: Any,
) -> None:
    """Add very thin peach bands/pilasters to the longest facade edge."""
    pts = [_xy(config, p) for p in ring[:-1]]
    edges = list(zip(pts, pts[1:] + pts[:1]))
    a, b = max(edges, key=lambda edge: math.dist(*edge))
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 14.0:
        return
    rot = math.atan2(dy, dx)
    cx, cy = (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5
    base = terrain.sample(cx, cy) + 0.08
    depth = 0.50
    # Belt courses and spaced vertical posts reproduce the cream-and-peach grid
    # visible at the annexe and main entrance.
    # Put the bands a little proud of both faces so they cannot z-fight with
    # the base building shell and remain visible from either approach road.
    normal = (-math.sin(rot), math.cos(rot))
    for face_sign in (-1.0, 1.0):
        fx, fy = cx + normal[0] * depth * face_sign, cy + normal[1] * depth * face_sign
        for level in range(1, max(2, floors)):
            add_box_vc(bm, col, fx, fy, base + level * 3.05 - 0.17, base + level * 3.05 + 0.17, length * 0.5 + 0.25, depth, PEACH, PEACH, rot)
        # Two restrained terracotta ventilation screens, positioned at the top
        # of the facade like the perforated bands in the supplied photos.
        for fraction in (-0.22, 0.22):
            px = fx + math.cos(rot) * length * fraction
            py = fy + math.sin(rot) * length * fraction
            add_box_vc(bm, col, px, py, base + floors * 3.05 - 1.35, base + floors * 3.05 - 0.35, 3.4, depth + 0.04, VENT_BRICK, VENT_BRICK, rot)
    post_count = max(3, min(9, int(length / 12.0)))
    for i in range(post_count):
        t = -0.5 + i / (post_count - 1)
        for face_sign in (-1.0, 1.0):
            px = cx + math.cos(rot) * length * t + normal[0] * depth * face_sign
            py = cy + math.sin(rot) * length * t + normal[1] * depth * face_sign
            add_box_vc(bm, col, px, py, base, base + floors * 3.05, 0.13, depth + 0.05, PEACH, PEACH, rot)


def build_hero(context: dict[str, Any]) -> None:
    config = context["config"]
    terrain = context["terrain"]
    buildings = [
        b for b in context["overrides"].get("custom_buildings", [])
        if b.get("id", "").startswith("custom/kashyapa-")
    ]
    by_id = {b["id"]: b for b in buildings}
    if len(by_id) < 8:
        return

    bm = bmesh.new()
    col = bm.loops.layers.color.new("Color")

    # These three connectors follow the hand-marked circulation route: a north
    # cross-link, a central north-south link, and the southern entry turn.  They
    # bridge the apparent gaps while retaining the real courtyard voids.
    links = [
        ((10.903315, 76.905020), (10.903315, 76.906700), 6.8),
        ((10.903370, 76.905965), (10.902565, 76.905965), 6.8),
        ((10.902620, 76.905710), (10.902620, 76.906120), 6.8),
    ]
    connector_rings: list[list[tuple[float, float]]] = []
    for latlon_a, latlon_b, width in links:
        connector_rings.append(_span(bm, col, terrain, _xy(config, list(latlon_a)), _xy(config, list(latlon_b)), width, "Kashyapa circulation"))

    # Facade bands belong only on the major residence volumes, not the lower
    # Annexe service spine.
    for building in buildings:
        if "annexe" not in building["id"]:
            _facade_bands(bm, col, terrain, building["footprint"], int(building.get("floors", 4)), config)

    if not bm.verts:
        bm.free()
        return
    mesh = bpy.data.meshes.new("HERO_Kashyapa_Bhavan_Connections")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(context["mat_hero_accents"])
    obj = bpy.data.objects.new("HERO Kashyapa Bhavan — connected corridors", mesh)
    bpy.context.scene.collection.objects.link(obj)

    for ring in connector_rings:
        if ring:
            xs, ys = zip(*ring)
            context["solid_colliders"].append(((min(xs), min(ys), max(xs), max(ys)), [ring]))
