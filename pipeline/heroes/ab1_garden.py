"""Front garden of AB-1, after the owner's photo from the AB-1 roof.

Bright striped lawns, rounded clipped hedges and painted kerbs along the drive, rows of topiary balls,
planted beds, a red-earth path, a ring of large trees (instanced, so they cost no model triangles) and
the white flag on the entrance canopy. The fountain and paving come from `hero_models/ab1_hero.py`.
Foliage colours are deliberately light: the camera usually sees the shaded side.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from hero_models.ab1_hero import AB1_AXIS_X, AB1_PORTE_Y1, get_ab1_plaza_ring
from hero_models.geom_helpers import add_box_vc, add_quad_vc, add_tri_vc, srgb_hex_to_linear_rgba

Point = tuple[float, float]

# Lawns reach from just behind the paving's flower border out to these limits
LAWN_WEST_X, LAWN_EAST_X = 203.0, 295.0
LAWN_NORTH_Y = -273.0
# The road south of the garden runs at a slant; nothing planted goes below this line (x0, y0, rise per metre)
SOUTH_EDGE: tuple[float, float, float] = (202.0, -367.1, 0.0798)
LAWN_OFFSET_M = 2.0
LAWN_MAX_EDGE_M = 6.0
LAWN_STRIPE_M = 6.5
LAWN_SHADES = ("#8DC63F", "#7AB534")

# Rounded hedge cross-section: (distance beyond the paving edge, height)
HEDGE_PROFILE: tuple[tuple[float, float], ...] = ((2.15, -0.2), (2.15, 0.45), (2.65, 0.72), (3.15, 0.45), (3.15, -0.2))
HEDGE_SHADES = ("#5F9E2C", "#8CC845", "#7DBB3B", "#5F9E2C")
HEDGE_SEGMENT_M = 4.5
KERB_DASH_M = 2.0

# Topiary rows follow these stretches of paving edge (indices into the plaza ring), set back on the lawn
TOPIARY_EDGES: tuple[tuple[int, int], ...] = ((3, 6), (17, 21))
TOPIARY_SETBACK_M = 5.6
TOPIARY_SPACING_M = 3.6
# x positions of the row of balls along the south road
SOUTH_ROW_X: tuple[float, ...] = (210.0, 215.0, 220.0, 225.0, 230.0, 235.0, 262.5, 267.5, 272.5, 277.5, 282.5, 287.5)
# (x, y, radius) of the other clipped balls
TOPIARY: tuple[tuple[float, float, float], ...] = (
    (262.0, -327.0, 1.25), (264.8, -329.2, 0.9), (236.5, -330.0, 1.25), (233.8, -332.4, 0.9),
    (287.0, -283.0, 1.1), (213.0, -283.0, 1.1),
)
# Planted beds: (centre x, centre y, half length, half width, angle degrees, flower colour)
BEDS: tuple[tuple[float, float, float, float, float, str], ...] = (
    (270.0, -321.8, 4.2, 1.7, 8.0, "#E5453C"), (284.5, -337.0, 4.6, 2.1, 70.0, "#F2A52B"),
    (266.0, -355.0, 3.8, 1.8, -15.0, "#E95C9C"), (229.0, -322.5, 3.4, 1.6, -35.0, "#F5D436"),
    (213.0, -333.0, 4.4, 2.0, 80.0, "#E5453C"), (232.0, -354.5, 4.0, 1.8, 12.0, "#F2A52B"),
)
# Winding red-earth paths across the lawns
PATHS: tuple[tuple[Point, ...], ...] = (
    ((294.0, -313.0), (285.0, -326.0), (275.0, -330.5), (268.0, -338.0), (269.0, -346.0), (278.0, -354.0), (294.0, -356.0)),
    ((204.0, -318.0), (214.0, -324.0), (222.0, -333.0), (234.0, -337.0), (239.5, -347.0)),
)
PATH_HALF_M = 0.45
# (x, y, tree type, scale range, shade): 4 and 5 are the light garden greens in the web viewer
TREE_SPOTS: tuple[tuple[float, float, int, tuple[float, float], int], ...] = (
    # large trees closing in both sides of the garden
    *((x + (3.0 if i % 2 else 0.0), y, 1, (1.15, 1.5), 4 if i % 3 else 1)
      for x in (204.0, 292.0) for i, y in enumerate((-290.0, -299.0, -308.0, -317.0, -326.0, -335.0, -344.0, -353.0))),
    # smaller ornamental trees on the lawns
    (214.0, -352.0, 1, (0.55, 0.65), 5), (236.0, -362.0, 1, (0.5, 0.6), 5), (216.0, -315.0, 1, (0.55, 0.65), 5),
    (283.0, -318.0, 1, (0.55, 0.65), 5), (276.0, -342.0, 1, (0.6, 0.7), 5), (264.0, -347.0, 1, (0.45, 0.55), 5),
    # royal palms deepening the avenue
    (241.0, -324.5, 0, (1.25, 1.4), 5), (258.5, -324.5, 0, (1.25, 1.4), 5),
    (241.5, -357.5, 0, (1.3, 1.5), 4), (258.0, -357.5, 0, (1.3, 1.5), 4),
)
# Clear ground (off roads and buildings) behind and beside the lawns, planted as a dense belt like the photo's
BELT_SPOTS: tuple[Point, ...] = (
    (186.0, -359.6), (192.9, -359.8), (182.6, -354.5), (196.8, -354.1), (194.6, -347.1), (196.9, -341.6),
    (186.8, -333.0), (184.4, -328.0), (196.6, -328.5), (188.0, -321.4), (193.8, -320.9), (183.9, -315.4),
    (197.2, -314.6), (187.5, -307.2), (195.1, -309.1), (190.7, -301.2), (196.9, -302.0), (185.9, -295.1),
    (185.2, -289.8), (198.3, -289.3), (302.6, -352.3), (309.8, -354.0), (300.1, -345.6), (306.1, -347.0),
    (297.2, -339.2), (310.3, -340.7), (299.9, -332.8), (308.9, -335.1), (296.0, -328.5), (303.1, -327.6),
    (311.3, -328.4), (298.8, -321.5), (307.0, -321.0), (304.0, -314.4), (311.6, -316.2), (301.7, -307.5),
    (308.6, -307.4), (302.7, -301.6), (299.5, -296.7), (306.9, -297.0), (309.5, -288.0), (300.8, -283.9),
    (306.6, -283.3), (185.6, -403.2), (194.1, -400.4), (199.9, -402.1), (205.7, -403.3), (213.5, -402.8),
    (222.1, -403.1), (226.5, -400.6), (235.1, -403.1), (189.5, -397.1), (196.5, -394.1), (204.6, -395.0),
    (209.6, -396.0), (216.3, -394.7), (224.5, -394.7), (230.9, -396.5), (187.0, -387.6), (194.1, -388.2),
    (201.0, -388.4), (206.1, -389.1), (213.5, -390.7), (219.5, -389.9), (227.2, -388.6), (236.5, -389.4),
    (190.8, -381.2), (197.9, -383.2), (202.5, -383.7), (209.4, -383.7), (217.8, -381.5), (225.5, -382.9),
    (231.9, -381.8), (222.5, -376.7), (235.7, -377.5), (261.1, -400.6), (267.8, -400.8), (276.0, -402.9),
    (281.2, -402.7), (288.2, -401.7), (295.2, -402.3), (301.8, -400.7), (309.5, -402.1), (264.7, -394.3),
    (271.1, -394.3), (278.4, -395.5), (285.5, -397.1), (292.2, -396.6), (297.8, -394.6), (305.4, -395.7),
    (314.1, -395.4), (260.4, -389.1), (268.2, -388.3), (273.7, -389.0), (281.2, -389.9), (296.2, -388.4),
    (304.3, -389.4), (310.4, -389.2), (264.4, -382.2), (271.2, -382.7), (278.3, -381.4), (286.0, -381.6),
    (293.8, -383.6), (299.6, -381.4), (307.5, -384.0), (312.2, -383.0), (259.6, -377.2), (266.6, -375.9),
    (275.9, -375.1), (280.9, -375.7), (289.5, -377.5), (297.2, -374.9), (302.1, -375.0), (309.7, -376.4),
    (299.6, -370.2), (304.9, -370.5), (313.8, -370.0),
)
BELT_SHADES = (4, 1, 4, 2)  # mostly light greens with darker crowns between them for depth
FLAG_EAST_OF_AXIS_M = 7.9
FLAG_POLE_M = 8.5


def build_hero(context: dict[str, Any]) -> None:
    garden = _Garden(context["terrain"])
    ring = get_ab1_plaza_ring()
    # the avenue edges stop short of the south road
    west = ring[14:] + [(ring[0][0], _south_y(ring[0][0]))]
    east = [(ring[1][0], _south_y(ring[1][0])), *ring[2:11]]
    garden.lawn(_clip_south([
        (LAWN_WEST_X, _south_y(LAWN_WEST_X)), *reversed(_offset(west, LAWN_OFFSET_M)), (LAWN_WEST_X, LAWN_NORTH_Y),
    ]))
    garden.lawn(_clip_south([
        *_offset(east, LAWN_OFFSET_M), (LAWN_EAST_X, LAWN_NORTH_Y), (LAWN_EAST_X, _south_y(LAWN_EAST_X)),
    ]))
    for edge in (west, east):
        garden.hedge([_offset(edge, d) for d, _ in HEDGE_PROFILE])
        garden.kerb(edge)
    for first, last in TOPIARY_EDGES:
        row = _offset((ring + ring[:1])[first:last + 1], TOPIARY_SETBACK_M)
        for i, (x, y) in enumerate(_spaced(row, TOPIARY_SPACING_M)):
            garden.ball(x, y, 1.15 if i % 2 else 0.95)
    for x, y, radius in TOPIARY:
        garden.ball(x, y, radius)
    for x in SOUTH_ROW_X:
        garden.ball(x, _south_y(x) + 1.5, 0.8)
    for bed in BEDS:
        garden.bed(*bed)
    for path in PATHS:
        garden.path(list(path))
    garden.flag()
    context["hand_tree_spots"].extend(TREE_SPOTS)
    context["hand_tree_spots"].extend(
        (x, y, 1, (1.2, 1.65), BELT_SHADES[i % len(BELT_SHADES)]) for i, (x, y) in enumerate(BELT_SPOTS)
    )
    garden.finish(context["mat_body"])


def _south_y(x: float) -> float:
    x0, y0, rise = SOUTH_EDGE
    return y0 + (x - x0) * rise


def _clip_south(outline: list[Point]) -> list[Point]:
    """Keep the part of a polygon on the garden side of the south road."""
    out: list[Point] = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        da, db = a[1] - _south_y(a[0]), b[1] - _south_y(b[0])
        if da >= -1e-6:
            out.append(a)
        if (da > 1e-6 and db < -1e-6) or (da < -1e-6 and db > 1e-6):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _flag_material() -> Any:
    material = bpy.data.materials.new("MAT_FlagCloth")
    material.use_nodes = True
    shader = material.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (0.9, 0.9, 0.88, 1.0)
    shader.inputs["Roughness"].default_value = 0.8
    shader.inputs["Emission Color"].default_value = (1.0, 1.0, 0.97, 1.0)
    shader.inputs["Emission Strength"].default_value = 0.35
    return material


def _offset(line: list[Point], distance: float) -> list[Point]:
    """Parallel copy of a polyline, `distance` to the right of travel (off the paving), mitred at corners."""
    out: list[Point] = []
    for i, p in enumerate(line):
        segments = list(zip(line, line[1:]))[max(i - 1, 0):i + 1]
        normals = [((b[1] - a[1]) / math.dist(a, b), (a[0] - b[0]) / math.dist(a, b)) for a, b in segments]
        (ax, ay), (bx, by) = normals[0], normals[-1]
        scale = distance / max(0.35, 1.0 + ax * bx + ay * by)
        out.append((p[0] + (ax + bx) * scale, p[1] + (ay + by) * scale))
    return out


def _spaced(line: list[Point], spacing: float) -> list[Point]:
    """Points every `spacing` metres along a polyline."""
    out, carry = [], spacing / 2.0
    for a, b in zip(line, line[1:]):
        length = math.dist(a, b)
        while carry <= length:
            out.append((a[0] + (b[0] - a[0]) * carry / length, a[1] + (b[1] - a[1]) * carry / length))
            carry += spacing
        carry -= length
    return out


def _smooth(points: list[Point], steps: int = 4) -> list[Point]:
    """Catmull-Rom curve through the points."""
    padded = [points[0], *points, points[-1]]
    out = [points[0]]
    for p0, p1, p2, p3 in zip(padded, padded[1:], padded[2:], padded[3:]):
        for i in range(1, steps + 1):
            t = i / steps
            out.append(tuple(
                0.5 * (2 * p1[k] + (p2[k] - p0[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
                       + (3 * p1[k] - p0[k] - 3 * p2[k] + p3[k]) * t ** 3)
                for k in (0, 1)
            ))
    return out


class _Garden:
    def __init__(self, terrain: Any) -> None:
        self.terrain = terrain
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new("Color")

    def vert(self, x: float, y: float, lift: float):
        return self.bm.verts.new((x, y, self.terrain.sample(x, y) + lift))

    def tri(self, pts, hex_colour: str) -> None:
        """Triangle from (x, y, height above ground) points."""
        add_tri_vc(self.bm, self.col, tuple(self.vert(*p) for p in pts), srgb_hex_to_linear_rgba(hex_colour))

    def quad(self, pts, hex_colour: str) -> None:
        add_quad_vc(self.bm, self.col, *(self.vert(*p) for p in pts), srgb_hex_to_linear_rgba(hex_colour))

    def flat_tri(self, a: Point, b: Point, c: Point, lift: float, hex_colour: str) -> None:
        """Ground triangle in any winding, emitted facing up."""
        if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) < 0.0:
            b, c = c, b
        self.tri([(*a, lift), (*b, lift), (*c, lift)], hex_colour)

    def lawn(self, outline: list[Point]) -> None:
        """Draped lawn, split finely enough to follow the slope and shaded in mown stripes."""

        def split(a: Point, b: Point, c: Point) -> None:
            for p, q, r in ((a, b, c), (b, c, a), (c, a, b)):
                longest = max(math.dist(a, b), math.dist(b, c), math.dist(c, a))
                if longest > LAWN_MAX_EDGE_M and math.dist(p, q) == longest:
                    mid = ((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)
                    split(p, mid, r)
                    split(mid, q, r)
                    return
            cx, cy = (a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0
            shade = LAWN_SHADES[int((cx * 0.45 + cy) // LAWN_STRIPE_M) % 2]
            self.flat_tri(a, b, c, 0.13, shade)

        for i, j, k in tessellate_polygon([[Vector((x, y, 0.0)) for x, y in outline]]):
            split(outline[i], outline[j], outline[k])

    def hedge(self, rails: list[list[Point]]) -> None:
        """Loft the rounded profile along matching polylines, one per profile point."""
        counts = [max(1, math.ceil(math.dist(a, b) / HEDGE_SEGMENT_M)) for a, b in zip(rails[2], rails[2][1:])]
        lines = []
        for rail in rails:
            line = [rail[0]]
            for (a, b), n in zip(zip(rail, rail[1:]), counts):
                line.extend((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1))
            lines.append(line)
        sections = [
            [(*lines[k][i], HEDGE_PROFILE[k][1]) for k in range(len(HEDGE_PROFILE))] for i in range(len(lines[0]))
        ]
        for near, far in zip(sections, sections[1:]):
            for k, shade in enumerate(HEDGE_SHADES):
                self.quad((far[k], near[k], near[k + 1], far[k + 1]), shade)
        first, last = sections[0], sections[-1]
        self.quad((first[4], first[3], first[1], first[0]), HEDGE_SHADES[0])
        self.tri((first[3], first[2], first[1]), HEDGE_SHADES[1])
        self.quad((last[0], last[1], last[3], last[4]), HEDGE_SHADES[0])
        self.tri((last[1], last[2], last[3]), HEDGE_SHADES[1])

    def kerb(self, edge: list[Point]) -> None:
        """Black-and-white painted kerb blocks along the paving edge."""
        points = [edge[0]]
        for a, b in zip(edge, edge[1:]):
            n = max(1, round(math.dist(a, b) / KERB_DASH_M))
            points.extend((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1))
        inner, outer = _offset(points, -0.05), _offset(points, 0.38)
        for i in range(len(points) - 1):
            shade = "#F4F2EC" if i % 2 else "#2C3035"
            self.quad(((*inner[i + 1], 0.34), (*inner[i], 0.34), (*outer[i], 0.34), (*outer[i + 1], 0.34)), shade)

    def ball(self, x: float, y: float, radius: float) -> None:
        """Clipped topiary ball, lighter towards the top."""
        sides = 7
        tiers = ((0.72, 0.0), (1.0, 0.55), (0.74, 1.2))  # (radius factor, height factor)
        angles = [2.0 * math.pi * i / sides for i in range(sides)]
        ground = self.terrain.sample(x, y)
        loops = [
            [self.bm.verts.new((x + radius * r * math.cos(a), y + radius * r * math.sin(a), ground + radius * h))
             for a in angles] for r, h in tiers
        ]
        apex = self.bm.verts.new((x, y, ground + radius * 1.5))
        for i in range(sides):
            j = (i + 1) % sides
            for tier, shade in ((0, "#63A22E"), (1, "#7CBC3A")):
                add_quad_vc(self.bm, self.col, loops[tier][i], loops[tier][j], loops[tier + 1][j], loops[tier + 1][i],
                            srgb_hex_to_linear_rgba(shade))
            add_tri_vc(self.bm, self.col, (loops[2][i], loops[2][j], apex), srgb_hex_to_linear_rgba("#9AD451"))

    def bed(self, cx: float, cy: float, half_len: float, half_wid: float, angle: float, flower: str) -> None:
        """Oval red-earth bed filled with low flowering clumps."""
        ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        to_xy = lambda u, v: (cx + u * ca - v * sa, cy + u * sa + v * ca)
        sides = 12
        rim = [to_xy(half_len * math.cos(2 * math.pi * i / sides), half_wid * math.sin(2 * math.pi * i / sides))
               for i in range(sides)]
        for a, b in zip(rim, rim[1:] + rim[:1]):
            self.flat_tri((cx, cy), a, b, 0.18, "#A8603F")
        clumps = 13
        for k in range(clumps):
            spread = math.sqrt((k + 0.5) / clumps) * 0.82
            turn = k * 2.39996  # golden angle, for an even but irregular fill
            x, y = to_xy(half_len * spread * math.cos(turn), half_wid * spread * math.sin(turn))
            shade = "#78B83A" if k % 4 == 3 else flower
            base = [(x + 0.55 * math.cos(turn + 2 * math.pi * i / 5), y + 0.55 * math.sin(turn + 2 * math.pi * i / 5))
                    for i in range(5)]
            for a, b in zip(base, base[1:] + base[:1]):
                self.tri(((*a, 0.18), (*b, 0.18), (x, y, 0.68)), shade)

    def path(self, points: list[Point]) -> None:
        line = _smooth(points)
        left, right = _offset(line, -PATH_HALF_M), _offset(line, PATH_HALF_M)
        for i in range(len(line) - 1):
            self.quad(((*right[i], 0.17), (*right[i + 1], 0.17), (*left[i + 1], 0.17), (*left[i], 0.17)), "#B99068")

    def flag(self) -> None:
        """Pole on the east end of the entrance canopy roof with a rippling white flag flying east.

        The cloth is its own object with a faint glow, so its shaded side still reads as white.
        """
        x, y = AB1_AXIS_X + FLAG_EAST_OF_AXIS_M, AB1_PORTE_Y1 + 1.6
        roof = self.terrain.sample(AB1_AXIS_X, AB1_PORTE_Y1 + 1.0) + 5.84  # canopy roof height used by `ab1_hero`
        pole = srgb_hex_to_linear_rgba("#E8EAEC")
        add_box_vc(self.bm, self.col, x, y, roof, roof + 0.4, 0.4, 0.4, pole)
        add_box_vc(self.bm, self.col, x, y, roof + 0.4, roof + FLAG_POLE_M, 0.12, 0.12, pole)

        cloth = bmesh.new()
        top = roof + FLAG_POLE_M - 0.1
        folds = ((0.12, 0.0, 0.0), (1.0, 0.16, -0.1), (1.9, -0.12, -0.22), (2.8, 0.14, -0.38), (3.6, 0.0, -0.55))
        for (d0, w0, s0), (d1, w1, s1) in zip(folds, folds[1:]):
            corners = ((x + d1, y + w1, top - 2.1 + s1), (x + d0, y + w0, top - 2.1 + s0),
                       (x + d0, y + w0, top + s0), (x + d1, y + w1, top + s1))
            for ordered, shift in ((corners, 0.0), (corners[::-1], 0.012)):
                cloth.faces.new([cloth.verts.new((px, py + shift, pz)) for px, py, pz in ordered])
        cloth.normal_update()
        mesh = bpy.data.meshes.new("SITE_ab1_flag")
        cloth.to_mesh(mesh)
        cloth.free()
        mesh.materials.append(_flag_material())
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(mesh.name, mesh))

    def finish(self, material: Any) -> None:
        self.bm.normal_update()
        mesh = bpy.data.meshes.new("SITE_ab1_garden")
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(material)
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(mesh.name, mesh))
