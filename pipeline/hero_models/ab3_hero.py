"""Academic Block 3 (AB-3): top-view-traced footprint (court, light wells, notches), photo-matched East front,
side elevations & roofscape,
plus Amrita Playground stepped bleachers + goalposts."""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import (
    HERO_PALETTE,
    add_box_vc,
    add_cylinder_vc,
    add_hipped_roof_vc,
    add_quad_vc,
    add_tri_vc,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# AB-3 local frame: origin = centre of the East (entrance) wall, +lx runs S->N along that wall,
# +ly runs West into the building, -ly faces outward East toward the access road.
# Traced from Esri World Imagery (pipeline/refs/ab3_sat.jpg): the OSM way/380829415 outline is ~6.2 m too far
# South, so the frame centre sits 6.2 m North of the old OSM-derived East wall centre (-275.84, 395.86).
AB3_EAST_ROT = 1.6413  # +94.04 deg
AB3_EAST_CX = -276.28
AB3_EAST_CY = 402.04

# Plan traced from the annotated Google top view (pipeline/refs/ab3_top_marked.webp / ab3_top_clean.webp), which
# agrees with Esri on overall size. East block spans lx -28.75..28.75 for ly 0..54; the central band + West block are
# ~1.85 m narrower on the South side (lx -26.9..28.75) for ly 54..121.5.
AB3_HALF_LEN = 28.75  # East facade length 57.5 m
AB3_EAST_BLOCK_DEPTH = 54.0
AB3_WEST_SOUTH_LX = -26.9
AB3_DEPTH = 121.5
# Two U-shaped notches open to the West (back) edge (red "U" marks): (lx0, lx1, ly0) running out to AB3_DEPTH
AB3_WEST_NOTCHES = ((-12.1, -5.7, 114.0), (5.7, 12.1, 114.0))
# Eight small open light wells (red dotted marks), 2x2 per block: (lx0, lx1, ly0, ly1)
AB3_LIGHT_WELLS = (
    (-13.0, -6.4, 14.7, 25.5), (6.4, 13.0, 14.7, 25.5),
    (-13.2, -6.2, 31.9, 49.1), (6.2, 13.2, 31.9, 49.1),
    (-12.6, -6.0, 77.1, 95.1), (6.0, 12.6, 77.1, 95.1),
    (-12.4, -5.8, 98.4, 107.1), (5.8, 12.4, 98.4, 107.1),
)
# Big central open court (green mark), CCW in local (lx, ly): includes the block jutting in from the North wall
# (lx 9..18, ly 61..68) and the small South-West corner block (lx -10..-4.5, ly 66..72.5)
AB3_CENTRAL_COURT = (
    (-10.0, 55.5), (18.0, 55.5), (18.0, 61.0), (9.0, 61.0), (9.0, 68.0), (18.0, 68.0),
    (18.0, 72.5), (-4.5, 72.5), (-4.5, 66.0), (-10.0, 66.0),
)
# Rooftop solar arrays read from the top view: (lx0, lx1, ly0, ly1, columns)
AB3_SOLAR_ARRAYS = (
    (-26.3, -16.0, 11.6, 50.9, 3), (15.7, 26.0, 11.4, 52.8, 3), (-3.9, 5.1, 28.8, 52.8, 3),
    (-24.5, -13.0, 73.0, 111.0, 4), (15.4, 26.9, 74.8, 111.7, 4), (-3.3, 5.1, 77.3, 95.1, 3),
    (-24.5, -13.0, 114.7, 118.4, 4), (15.4, 26.9, 114.7, 118.4, 4),
)
# Raised skylight box on the West block roof between the upper light wells: (lx0, lx1, ly0, ly1)
AB3_WEST_SKYLIGHT = (-1.5, 7.6, 104.3, 111.0)


# Photo-matched East front layout (left = South, right = North when facing the building)
AB3_TOWER_HX = 5.5
AB3_TOWER_FRONT = -2.6
AB3_PORCH_LX = 14.5
AB3_PORCH_HX = 3.2
AB3_END_LX0 = 20.0
AB3_END_FRONT = -1.4
AB3_GARDEN_LY = -6.6


def _ab3_world(lx: float, ly: float) -> tuple[float, float]:
    return local_to_world_2d(AB3_EAST_CX, AB3_EAST_CY, lx, ly, AB3_EAST_ROT)


def _ab3_ring_world(local: list[tuple[float, float]], ccw: bool) -> list[tuple[float, float]]:
    ring = [_ab3_world(lx, ly) for lx, ly in local]
    area2 = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))
    if (area2 > 0.0) != ccw:
        ring.reverse()
    return ring


def _ab3_outer_local() -> list[tuple[float, float]]:
    h, d, ws = AB3_HALF_LEN, AB3_DEPTH, AB3_WEST_SOUTH_LX
    pts: list[tuple[float, float]] = [(-h, 0.0), (h, 0.0), (h, d)]
    for lx0, lx1, ly0 in sorted(AB3_WEST_NOTCHES, key=lambda n: -n[1]):
        pts += [(lx1, d), (lx1, ly0), (lx0, ly0), (lx0, d)]
    pts += [(ws, d), (ws, AB3_EAST_BLOCK_DEPTH), (-h, AB3_EAST_BLOCK_DEPTH)]
    return pts


def _ab3_holes_local() -> list[list[tuple[float, float]]]:
    holes = [list(AB3_CENTRAL_COURT)]
    holes += [[(x0, y0), (x1, y0), (x1, y1), (x0, y1)] for x0, x1, y0, y1 in AB3_LIGHT_WELLS]
    return holes


def normalize_ab3_footprint_rings(
    outer_ring: list[tuple[float, float]],
) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]]]:
    """Replace the mis-registered OSM AB-3 polygon with the plan traced from the annotated top view:
    outer ring with two West notches, the big central court (rings[1]) and eight light wells (rings[2:]).
    Returns ([outer_ccw, *holes_cw], holes_ccw)."""
    del outer_ring
    outer = _ab3_ring_world(_ab3_outer_local(), ccw=True)
    holes_ccw = [_ab3_ring_world(h, ccw=True) for h in _ab3_holes_local()]
    return ([outer] + [list(reversed(h)) for h in holes_ccw], holes_ccw)


def ab3_forecourt_rect() -> tuple[float, float, float, float, float]:
    """World (cx, cy, hx, hy, rot) of the paved sandstone forecourt under both porches and the garden island."""
    cx, cy = _ab3_world(-1.0, -3.8)
    return (cx, cy, 18.0, 2.6, AB3_EAST_ROT)


def ab3_front_clear_discs() -> list[tuple[float, float, float]]:
    """World (x, y, r^2) discs keeping random scatter trees off the AB-3 garden island & twin porches."""
    discs = [(*_ab3_world(0.0, -6.0), 8.0 * 8.0)]
    for side in (-1.0, 1.0):
        discs.append((*_ab3_world(side * AB3_PORCH_LX, -3.5), 5.5 * 5.5))
    return discs


def ab3_front_tree_spots() -> list[tuple[float, float, int, tuple[float, float]]]:
    """World (x, y, tree_type, scale_range) for the hand-placed AB-3 front garden (0 = palm, 1 = canopy)."""
    local_spots = (
        (-3.4, AB3_GARDEN_LY, 0, (0.80, 0.92)),
        (3.4, AB3_GARDEN_LY, 0, (0.84, 0.96)),
        (0.0, AB3_GARDEN_LY - 0.7, 1, (0.50, 0.60)),
        (-8.6, -4.4, 0, (0.98, 1.10)),
        (8.6, -4.4, 0, (0.98, 1.10)),
        (-19.4, -4.2, 0, (0.95, 1.08)),
        (-25.0, -4.6, 1, (0.80, 0.95)),
    )
    return [(*_ab3_world(lx, ly), t, sc) for lx, ly, t, sc in local_spots]


def append_ab3_hero_details(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
    z_plinth: float,
    z_eave: float,
    z_top: float,
) -> None:
    """Append the photo-matched AB-3 East front & satellite-matched roofscape."""
    del win_lit_bm, win_dark_bm
    rot = AB3_EAST_ROT
    ox, oy, oz = offset_xyz
    c_cream = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_cream"])
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])
    c_orange = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_orange"])
    c_tile = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_roof_tile"])
    c_panel = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_rust_panel"])
    c_glass = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_glass_blue"])
    c_recess = srgb_hex_to_linear_rgba(HERO_PALETTE["portico_dark"])
    c_baluster = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_baluster_shadow"])
    c_step = srgb_hex_to_linear_rgba(HERO_PALETTE["sandstone_plinth"])
    c_stone = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_garden_stone"])
    c_lawn = srgb_hex_to_linear_rgba(HERO_PALETTE["lawn_green"])
    c_hedge = srgb_hex_to_linear_rgba(HERO_PALETTE["ab3_hedge_green"])
    c_maroon = srgb_hex_to_linear_rgba(HERO_PALETTE["amrita_maroon"])
    c_solar = srgb_hex_to_linear_rgba(HERO_PALETTE["solar_panel"])

    n_floors = 4
    step_h = max(2.6, (z_eave - z_plinth) / n_floors)

    def _ground(lx: float, ly: float) -> float:
        return terrain.sample(*_ab3_world(lx, ly))

    def _box(
        lx: float, ly: float, z0: float, z1: float, hx: float, hy: float,
        wall: tuple[float, float, float, float], cap: tuple[float, float, float, float] | None = None,
        emit_bottom: bool = False,
    ) -> None:
        wx, wy = _ab3_world(lx, ly)
        add_box_vc(bm, col_layer, wx, wy, z0, z1, hx, hy, wall, cap, rot_rad=rot, emit_bottom=emit_bottom, offset_xyz=offset_xyz)

    def _v(lx: float, ly: float, z: float) -> bmesh.types.BMVert:
        wx, wy = _ab3_world(lx, ly)
        return bm.verts.new((wx - ox, wy - oy, z - oz))

    def _lean_to(lx0: float, lx1: float, ly_wall: float, depth: float, z_hi: float, drop: float) -> None:
        """Sloped orange Mangalore-tile sunshade/eave leaning off a wall, with fascia & soffit."""
        ly_out = ly_wall - depth
        z_lo = z_hi - drop
        add_quad_vc(bm, col_layer, _v(lx0, ly_out, z_lo), _v(lx1, ly_out, z_lo), _v(lx1, ly_wall, z_hi), _v(lx0, ly_wall, z_hi), c_orange)
        add_quad_vc(bm, col_layer, _v(lx0, ly_out, z_lo - 0.16), _v(lx1, ly_out, z_lo - 0.16), _v(lx1, ly_out, z_lo), _v(lx0, ly_out, z_lo), c_orange)
        add_quad_vc(bm, col_layer, _v(lx0, ly_wall, z_lo - 0.16), _v(lx1, ly_wall, z_lo - 0.16), _v(lx1, ly_out, z_lo - 0.16), _v(lx0, ly_out, z_lo - 0.16), c_white)

    def _balustrade(lx: float, ly: float, z0: float, hx: float, hy: float, h: float = 1.0) -> None:
        """White parapet balustrade with a recessed band of baluster openings."""
        _box(lx, ly, z0, z0 + h, hx, hy, c_white)
        _box(lx, ly - hy - 0.02, z0 + h * 0.25, z0 + h * 0.72, max(0.2, hx - 0.25), 0.03, c_baluster)

    # ---------------------------------------------------------------- 1. Central arched blue-glass tower (G+4)
    tf, thy = AB3_TOWER_FRONT, 1.6
    tly = tf + thy
    z_tower = z_eave + step_h + 0.3
    _box(0.0, tly, _ground(0.0, tf) - 2.2, z_tower, AB3_TOWER_HX, thy, c_cream)
    for side in (-1.0, 1.0):
        _box(side * (AB3_TOWER_HX - 0.55), tly - 0.12, _ground(side * 5.0, tf) - 2.2, z_tower + 0.25, 0.6, thy + 0.12, c_orange)
    _box(0.0, tly, z_tower - 0.35, z_tower, AB3_TOWER_HX + 0.3, thy + 0.3, c_orange)
    _balustrade(0.0, tly, z_tower, AB3_TOWER_HX + 0.05, thy + 0.05, 0.9)
    # Small square blue windows flanking the glass on every floor
    for side in (-1.0, 1.0):
        for fl in range(5):
            z0 = z_plinth + fl * step_h + step_h * 0.38
            _box(side * 3.55, tf - 0.04, z0, z0 + step_h * 0.32, 0.45, 0.06, c_glass)
    # Tall arched curtain-wall window framed in orange (floors 1-4, semicircular head)
    g_hx = 2.0
    g_z0 = z_plinth + step_h * 1.05
    g_spring = z_eave + 0.2
    for side in (-1.0, 1.0):
        _box(side * (g_hx + 0.3), tf - 0.06, g_z0 - 0.3, g_spring, 0.3, 0.08, c_orange)
    _box(0.0, tf - 0.06, g_z0 - 0.35, g_z0, g_hx + 0.6, 0.08, c_orange)
    _box(0.0, tf - 0.05, g_z0, g_spring, g_hx, 0.06, c_glass)
    # Smooth semicircular glass head (triangle fan) + orange arch ring, both facing outward East (-ly)
    arch_segs = 12
    g_face, ring_face = tf - 0.12, tf - 0.16
    r_in, r_out = g_hx, g_hx + 0.6
    centre = _v(0.0, g_face, g_spring)
    for i in range(arch_segs):
        a0, a1 = math.pi * i / arch_segs, math.pi * (i + 1) / arch_segs
        add_tri_vc(
            bm, col_layer,
            (centre, _v(r_in * math.cos(a0), g_face, g_spring + r_in * math.sin(a0)),
             _v(r_in * math.cos(a1), g_face, g_spring + r_in * math.sin(a1))),
            c_glass,
        )
        add_quad_vc(
            bm, col_layer,
            _v(r_in * math.cos(a0), ring_face, g_spring + r_in * math.sin(a0)),
            _v(r_out * math.cos(a0), ring_face, g_spring + r_out * math.sin(a0)),
            _v(r_out * math.cos(a1), ring_face, g_spring + r_out * math.sin(a1)),
            _v(r_in * math.cos(a1), ring_face, g_spring + r_in * math.sin(a1)),
            c_orange,
        )
    for fl in range(2, 5):
        zf = z_plinth + fl * step_h
        if zf < g_spring - 0.3:
            _box(0.0, tf - 0.12, zf - 0.07, zf + 0.07, g_hx, 0.04, c_white)
    # Ground-floor entrance recess under the glass
    _box(0.0, tf - 0.05, z_plinth, z_plinth + step_h * 0.82, 1.6, 0.08, c_recess)

    # ---------------------------------------------------------------- 2. Stepped wings: per-floor tile sunshades
    for side in (-1.0, 1.0):
        lx0, lx1 = sorted((side * AB3_TOWER_HX, side * AB3_END_LX0))
        for fl in range(1, n_floors):
            _lean_to(lx0, lx1, 0.0, 1.3, z_plinth + fl * step_h + 0.15, 0.6)
        _lean_to(lx0, lx1, 0.0, 1.35, z_top + 0.15, 0.62)
        _balustrade(side * (AB3_TOWER_HX + AB3_END_LX0) * 0.5, 0.15, z_top + 0.1, (AB3_END_LX0 - AB3_TOWER_HX) * 0.5, 0.14)
        # Recessed upper-floor setback pavilion beside the tower (stepped silhouette in the photos)
        px = side * 9.8
        _box(px, 4.6, z_top - 0.1, z_top + 3.0, 3.6, 2.6, c_cream, c_white)
        _lean_to(px - 3.8, px + 3.8, 2.0, 0.9, z_top + 3.05, 0.45)
        _balustrade(px, 4.6, z_top + 3.0, 3.6, 2.6, 0.75)
        for dx in (-1.9, 0.0, 1.9):
            _box(px + dx, 1.97, z_top + 0.8, z_top + 2.1, 0.55, 0.04, c_glass)

    # ---------------------------------------------------------------- 3. Projecting end blocks with rust panel grid
    end_hx = (AB3_HALF_LEN - AB3_END_LX0) * 0.5
    end_cx = AB3_END_LX0 + end_hx
    end_hy = -AB3_END_FRONT * 0.5 + 0.2
    end_ly = AB3_END_FRONT + end_hy
    for side in (-1.0, 1.0):
        ex = side * end_cx
        _box(ex, end_ly, _ground(ex, AB3_END_FRONT) - 2.2, z_eave + 0.2, end_hx, end_hy, c_cream)
        for fl in range(n_floors):
            z0 = z_plinth + fl * step_h + step_h * 0.3
            for col in (-2.9, 0.0, 2.9):
                _box(ex + col, AB3_END_FRONT - 0.05, z0, z0 + step_h * 0.42, 0.95, 0.06, c_panel)
            if fl > 0:
                _box(ex, AB3_END_FRONT - 0.08, z_plinth + fl * step_h - 0.08, z_plinth + fl * step_h + 0.08, end_hx, 0.06, c_orange)
        _lean_to(ex - end_hx - 0.2, ex + end_hx + 0.2, AB3_END_FRONT + 0.2, 1.0, z_eave + 0.7, 0.45)
        _box(ex, end_ly, z_eave + 0.2, z_eave + 0.7, end_hx, end_hy, c_cream, c_white)
        _balustrade(ex, end_ly, z_eave + 0.7, end_hx, end_hy, 1.0)

    # ---------------------------------------------------------------- 4. Twin entrance porches (G) + white bay above
    z_porch = z_plinth + step_h * 0.98
    for side in (-1.0, 1.0):
        px = side * AB3_PORCH_LX
        g = _ground(px, -2.7)
        _box(px, -2.7, g - 0.6, g + 0.22, AB3_PORCH_HX, 2.6, c_step)
        _box(px, -0.06, z_plinth, z_plinth + step_h * 0.8, 1.9, 0.08, c_recess)
        for dx in (-AB3_PORCH_HX + 0.45, AB3_PORCH_HX - 0.45):
            for pl_y in (-4.7, -0.9):
                _box(px + dx, pl_y, _ground(px + dx, pl_y) - 1.0, z_porch, 0.28, 0.28, c_white)
        _box(px, -2.75, z_porch, z_porch + 0.34, AB3_PORCH_HX + 0.15, 2.3, c_white, emit_bottom=True)
        rwx, rwy = _ab3_world(px, -2.85)
        add_hipped_roof_vc(
            bm, col_layer, rwx, rwy, z_porch + 0.34, z_porch + 1.45, AB3_PORCH_HX + 0.5, 2.6,
            c_tile, rot_rad=rot, soffit_rgba=c_white, offset_xyz=offset_xyz,
        )
        # White projecting bay over the porch (floor 1) with its own tile sunshade
        _box(px, -0.75, z_plinth + step_h, z_plinth + step_h * 2.0, 2.4, 0.75, c_white)
        _box(px, -1.52, z_plinth + step_h * 1.3, z_plinth + step_h * 1.75, 1.9, 0.04, c_glass)
        _lean_to(px - 2.7, px + 2.7, -1.5, 0.8, z_plinth + step_h * 2.0 + 0.3, 0.38)
    # Maroon "Amrita School of Computing" fascia sign on the South porch
    sx = -AB3_PORCH_LX
    _box(sx, -5.12, z_porch - 0.55, z_porch + 0.3, 1.9, 0.07, c_maroon)
    _box(sx, -5.2, z_porch - 0.3, z_porch + 0.05, 1.4, 0.02, c_white)

    # ---------------------------------------------------------------- 5. Raised stone-edged garden island
    g_hx, g_hy = 5.5, 2.2
    g_samples = [_ground(sx2 * g_hx, AB3_GARDEN_LY + sy * g_hy) for sx2 in (-1, 1) for sy in (-1, 1)]
    g_z0, g_z1 = min(g_samples) - 0.8, max(g_samples) + 0.55
    _box(0.0, AB3_GARDEN_LY, g_z0, g_z1, g_hx, g_hy, c_stone, c_lawn)
    _box(0.0, AB3_GARDEN_LY - g_hy + 0.3, g_z1, g_z1 + 0.5, g_hx - 0.5, 0.22, c_hedge)
    for sx2, sy in ((-4.5, 1.2), (4.5, 1.2), (-1.7, 0.9), (1.7, 0.9)):
        swx, swy = _ab3_world(sx2, AB3_GARDEN_LY + sy)
        add_cylinder_vc(bm, col_layer, swx, swy, g_z1 - 0.05, g_z1 + 0.85, 0.85, 0.32, 6, c_hedge, c_hedge, offset_xyz=offset_xyz)

    # ---------------------------------------------------------------- 6. Side elevations & roofscape (top view)
    def _lean_edge(
        a: tuple[float, float], b: tuple[float, float], n: tuple[float, float],
        depth: float, z_hi: float, drop: float, color: tuple[float, float, float, float] = c_orange,
    ) -> None:
        """Sloped tile sunshade leaning off the wall edge a->b toward unit normal n (local frame)."""
        (ax, ay), (bx, by) = a, b
        if (bx - ax) * n[1] - (by - ay) * n[0] > 0:
            (ax, ay), (bx, by) = (bx, by), (ax, ay)
        z_lo = z_hi - drop
        oax, oay = ax + n[0] * depth, ay + n[1] * depth
        obx, oby = bx + n[0] * depth, by + n[1] * depth
        add_quad_vc(bm, col_layer, _v(oax, oay, z_lo), _v(obx, oby, z_lo), _v(bx, by, z_hi), _v(ax, ay, z_hi), color)
        add_quad_vc(bm, col_layer, _v(oax, oay, z_lo - 0.16), _v(obx, oby, z_lo - 0.16), _v(obx, oby, z_lo), _v(oax, oay, z_lo), color)
        add_quad_vc(bm, col_layer, _v(ax, ay, z_lo - 0.16), _v(bx, by, z_lo - 0.16), _v(obx, oby, z_lo - 0.16), _v(oax, oay, z_lo - 0.16), c_white)

    def _parapet(a: tuple[float, float], b: tuple[float, float], n: tuple[float, float], z0: float, h: float = 1.0) -> None:
        """White roof-edge balustrade on an axis-aligned edge, baluster band facing outward n."""
        (ax, ay), (bx, by) = a, b
        t = 0.14
        if abs(ax - bx) < 1e-6:
            half = abs(by - ay) * 0.5
            cy_ = (ay + by) * 0.5
            _box(ax - n[0] * t, cy_, z0, z0 + h, t, half, c_white)
            _box(ax + n[0] * 0.02, cy_, z0 + h * 0.25, z0 + h * 0.72, 0.03, max(0.2, half - 0.25), c_baluster)
        else:
            half = abs(bx - ax) * 0.5
            cx_ = (ax + bx) * 0.5
            _box(cx_, ay - n[1] * t, z0, z0 + h, half, t, c_white)
            _box(cx_, ay + n[1] * 0.02, z0 + h * 0.25, z0 + h * 0.72, max(0.2, half - 0.25), 0.03, c_baluster)

    # Long North & South sides and the West (back) elevation: tile sunshade per floor + eave + balustrade
    h, d, ws = AB3_HALF_LEN, AB3_DEPTH, AB3_WEST_SOUTH_LX
    side_edges: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]] = [
        ((h, 0.3), (h, d), (1.0, 0.0)),
        ((-h, 0.3), (-h, AB3_EAST_BLOCK_DEPTH), (-1.0, 0.0)),
        ((ws, AB3_EAST_BLOCK_DEPTH), (ws, d), (-1.0, 0.0)),
    ]
    west_breaks = sorted(x for n_ in AB3_WEST_NOTCHES for x in n_[:2])
    west_xs = [ws, *west_breaks, h]
    for i in range(0, len(west_xs) - 1, 2):
        side_edges.append(((west_xs[i], d), (west_xs[i + 1], d), (0.0, 1.0)))
    for a_, b_, n_ in side_edges:
        for fl in range(1, n_floors):
            _lean_edge(a_, b_, n_, 1.1, z_plinth + fl * step_h + 0.15, 0.5)
        _lean_edge(a_, b_, n_, 1.2, z_top + 0.15, 0.55)
        _parapet(a_, b_, n_, z_top + 0.15)
    _parapet((-h, AB3_EAST_BLOCK_DEPTH), (ws, AB3_EAST_BLOCK_DEPTH), (0.0, 1.0), z_top + 0.15)
    for lx0, lx1, ly0 in AB3_WEST_NOTCHES:
        for a_, b_, n_ in (((lx0, ly0), (lx1, ly0), (0.0, 1.0)), ((lx0, ly0), (lx0, d), (1.0, 0.0)), ((lx1, ly0), (lx1, d), (-1.0, 0.0))):
            for fl in range(1, n_floors):
                _lean_edge(a_, b_, n_, 0.8, z_plinth + fl * step_h + 0.15, 0.4)
            _lean_edge(a_, b_, n_, 0.9, z_top + 0.15, 0.45)
        _parapet((lx0, ly0), (lx1, ly0), (0.0, 1.0), z_top + 0.15)
        _parapet((lx0, ly0), (lx0, d), (1.0, 0.0), z_top + 0.15)
        _parapet((lx1, ly0), (lx1, d), (-1.0, 0.0), z_top + 0.15)

    # Light wells: orange tile rims around each opening (seen as orange frames from above)
    for x0, x1, y0, y1 in AB3_LIGHT_WELLS:
        for a_, b_, n_ in (
            ((x0, y0), (x1, y0), (0.0, 1.0)), ((x0, y1), (x1, y1), (0.0, -1.0)),
            ((x0, y0), (x0, y1), (1.0, 0.0)), ((x1, y0), (x1, y1), (-1.0, 0.0)),
        ):
            _lean_edge(a_, b_, n_, 0.75, z_top + 0.2, 0.42)

    # Central court: broad tile roofs along both long edges, narrow tile rims elsewhere
    court = AB3_CENTRAL_COURT
    for i in range(len(court)):
        (ax, ay), (bx, by) = court[i], court[(i + 1) % len(court)]
        ln = math.hypot(bx - ax, by - ay)
        n_in = (-(by - ay) / ln, (bx - ax) / ln)
        is_long = abs(ay - by) < 1e-6 and ln > 20.0
        _lean_edge((ax, ay), (bx, by), n_in, 3.0 if is_long else 0.75, z_top + 0.25, 1.1 if is_long else 0.42)

    # Solar arrays in columns
    for x0, x1, y0, y1, cols in AB3_SOLAR_ARRAYS:
        gap = 0.7
        w = (x1 - x0 - gap * (cols - 1)) / cols
        for c in range(cols):
            cx_ = x0 + w * 0.5 + c * (w + gap)
            _box(cx_, (y0 + y1) * 0.5, z_top - 0.05, z_top + 0.5, w * 0.5, (y1 - y0) * 0.5, c_solar)

    # Raised skylight box on the West block
    sx0, sx1, sy0, sy1 = AB3_WEST_SKYLIGHT
    _box((sx0 + sx1) * 0.5, (sy0 + sy1) * 0.5, z_top - 0.1, z_top + 1.4, (sx1 - sx0) * 0.5, (sy1 - sy0) * 0.5, c_white)
    _box((sx0 + sx1) * 0.5, (sy0 + sy1) * 0.5, z_top + 1.4, z_top + 1.55, (sx1 - sx0) * 0.5 - 0.9, (sy1 - sy0) * 0.5 - 0.9, c_baluster)


def append_playground_bleachers_and_goals(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: Any,
    gcx: float,
    gcy: float,
    pitch_ang_rad: float,
    pg_flat_z: float | None,
) -> None:
    """Build Photo-3-accurate 6-tier white bleachers with terracotta stair aisles, charcoal track wall & football goals."""
    c_white = srgb_hex_to_linear_rgba(HERO_PALETTE["bleacher_white"])
    c_stair = srgb_hex_to_linear_rgba(HERO_PALETTE["terracotta_portal"])
    c_wall = srgb_hex_to_linear_rgba(HERO_PALETTE["charcoal_wall"])
    c_goal = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_white"])

    # Placed north of way/531088132 (ends at y=-29.8) & strictly west of athletics track oval (x>=181)
    stand_cx, stand_cy = 171.8, 16.0
    stand_rot = -0.108
    pg_z = pg_flat_z if pg_flat_z is not None else terrain.sample(stand_cx, stand_cy)
    base_z = pg_z - 1.2

    # 1. Long dark-charcoal perimeter retaining wall with white coping overlooking pitch (foreground of Photo 3)
    wx_wall, wy_wall = local_to_world_2d(stand_cx, stand_cy, 5.6, 0.0, stand_rot)
    add_box_vc(bm, col_layer, wx_wall, wy_wall, base_z, pg_z + 1.35, 0.48, 29.0, c_wall, c_white, rot_rad=stand_rot)
    add_box_vc(bm, col_layer, wx_wall, wy_wall, pg_z + 1.35, pg_z + 1.56, 0.56, 29.2, c_white, c_white, rot_rad=stand_rot)

    # 2. 6-tier stepped white concrete bleachers with 3 terracotta-orange stair aisles
    for tier in range(6):
        lx = 3.2 - tier * 1.15
        z1 = pg_z + 0.55 + tier * 0.58
        tx, ty = local_to_world_2d(stand_cx, stand_cy, lx, 0.0, stand_rot)
        add_box_vc(bm, col_layer, tx, ty, base_z, z1, 0.62, 28.0, c_white, c_white, rot_rad=stand_rot)

    for stair_ly in (-18.0, 0.0, 18.0):
        for tier in range(6):
            lx = 3.25 - tier * 1.15
            z1 = pg_z + 0.61 + tier * 0.58
            sx, sy = local_to_world_2d(stand_cx, stand_cy, lx, stair_ly, stand_rot)
            add_box_vc(bm, col_layer, sx, sy, base_z, z1, 0.64, 1.15, c_stair, c_stair, rot_rad=stand_rot)

    # 3. Twin white football goalposts at both ends of central soccer pitch
    ca, sa = math.cos(pitch_ang_rad), math.sin(pitch_ang_rad)
    goal_z = pg_z - 0.1
    goal_h = 2.6
    goal_hw = 3.7
    nx, ny = -sa, ca
    for end_sign in (-1.0, 1.0):
        gx = gcx + end_sign * ca * 48.0
        gy = gcy + end_sign * sa * 48.0
        for p_sign in (-1.0, 1.0):
            px, py = gx + p_sign * nx * goal_hw, gy + p_sign * ny * goal_hw
            add_cylinder_vc(bm, col_layer, px, py, goal_z, pg_z + goal_h, 0.11, 0.11, 6, c_goal, c_goal)
        add_box_vc(
            bm, col_layer, gx, gy, pg_z + goal_h - 0.14, pg_z + goal_h + 0.04,
            0.11, goal_hw + 0.11, c_goal, c_goal, rot_rad=pitch_ang_rad, emit_bottom=True,
        )
