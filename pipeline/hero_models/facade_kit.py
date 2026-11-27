"""Low-triangle facade and roof primitives in a building-aligned (u, v) frame.

The frame defaults to the AB-2 / library one from `campus_frame`; pass `to_xy` for another building.
"""

from __future__ import annotations

from typing import Any, Callable

import bmesh

from campus_frame import uv_to_xy

from .geom_helpers import HERO_PALETTE, add_quad_vc, add_tri_vc, srgb_hex_to_linear_rgba

Rect = tuple[float, float, float, float]  # u0, u1, v0, v1
RGBA = tuple[float, float, float, float]

SIDES: tuple[str, ...] = ("s", "e", "n", "w")
_OUTWARD: dict[str, tuple[float, float]] = {"s": (0.0, -1.0), "e": (1.0, 0.0), "n": (0.0, 1.0), "w": (-1.0, 0.0)}


def color(key: str, scale: float = 1.0) -> RGBA:
    return srgb_hex_to_linear_rgba(HERO_PALETTE[key], scale)


def edge_of(rect: Rect, side: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Edge (a, b) of a rectangle side, ordered so the outward normal is to the right of a->b."""
    u0, u1, v0, v1 = rect
    return {
        "s": ((u0, v0), (u1, v0)),
        "e": ((u1, v0), (u1, v1)),
        "n": ((u1, v1), (u0, v1)),
        "w": ((u0, v1), (u0, v0)),
    }[side]


class Kit:
    """Emits vertex-colored geometry into one building mesh plus the shared window-glass meshes."""

    def __init__(
        self,
        bm: bmesh.types.BMesh,
        col_layer: Any,
        win_lit_bm: bmesh.types.BMesh | None,
        win_dark_bm: bmesh.types.BMesh | None,
        offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
        to_xy: Callable[[float, float], tuple[float, float]] = uv_to_xy,
    ) -> None:
        self.to_xy = to_xy
        self.bm = bm
        self.col = col_layer
        self.win_lit = win_lit_bm
        self.win_dark = win_dark_bm
        self.offset = offset_xyz
        self.world_pts: list[tuple[float, float, float]] = []
        self._win_counter = 0

    # -- raw faces ---------------------------------------------------------
    def vert(self, u: float, v: float, z: float) -> bmesh.types.BMVert:
        x, y = self.to_xy(u, v)
        self.world_pts.append((x, y, z))
        ox, oy, oz = self.offset
        return self.bm.verts.new((x - ox, y - oy, z - oz))

    def quad(self, pts: list[tuple[float, float, float]], rgba: RGBA) -> None:
        """Quad from four (u, v, z) points, counter-clockwise seen from the visible side."""
        v = [self.vert(*p) for p in pts]
        add_quad_vc(self.bm, self.col, v[0], v[1], v[2], v[3], rgba)

    def tri(self, pts: list[tuple[float, float, float]], rgba: RGBA) -> None:
        v = [self.vert(*p) for p in pts]
        add_tri_vc(self.bm, self.col, (v[0], v[1], v[2]), rgba)

    def flat(self, rect: Rect, z: float, rgba: RGBA) -> None:
        """Upward-facing horizontal rectangle."""
        self.quad([(u, v, z) for u, v in _corners(rect)], rgba)

    def box(self, rect: Rect, z0: float, z1: float, wall: RGBA, top: RGBA | None = None) -> None:
        for side in SIDES:
            a, b = edge_of(rect, side)
            self.quad([(*a, z0), (*b, z0), (*b, z1), (*a, z1)], wall)
        self.flat(rect, z1, top or wall)

    # -- wall-relative helpers --------------------------------------------
    def panel(
        self,
        rect: Rect,
        side: str,
        d0: float,
        d1: float,
        z0: float,
        z1: float,
        rgba: RGBA,
        proud: float = 0.0,
    ) -> None:
        """Vertical quad on a wall between distances d0..d1 along the edge, pushed `proud` metres out."""
        p0 = _along(rect, side, d0, proud)
        p1 = _along(rect, side, d1, proud)
        self.quad([(*p0, z0), (*p1, z0), (*p1, z1), (*p0, z1)], rgba)

    def shade(self, rect: Rect, side: str, z_low: float, z_high: float, depth: float, rgba: RGBA) -> None:
        """Sloped tile sunshade running along a wall (outer edge low, wall edge high)."""
        length = side_length(rect, side)
        o0, o1 = _along(rect, side, 0.0, depth), _along(rect, side, length, depth)
        i0, i1 = _along(rect, side, 0.0, 0.0), _along(rect, side, length, 0.0)
        self.quad([(*o0, z_low), (*o1, z_low), (*i1, z_high), (*i0, z_high)], rgba)

    def window(self, rect: Rect, side: str, d0: float, d1: float, z0: float, z1: float, proud: float = 0.07) -> None:
        """Night-glow window quad (about 60 % lit), placed proud of the wall."""
        self._win_counter += 1
        target = self.win_lit if (self._win_counter * 7) % 10 < 6 else self.win_dark
        if target is None or z1 - z0 < 0.15 or d1 - d0 < 0.15:
            return
        p0 = self.to_xy(*_along(rect, side, d0, proud))
        p1 = self.to_xy(*_along(rect, side, d1, proud))
        v = [
            target.verts.new((p0[0], p0[1], z0)),
            target.verts.new((p1[0], p1[1], z0)),
            target.verts.new((p1[0], p1[1], z1)),
            target.verts.new((p0[0], p0[1], z1)),
        ]
        for tri in ((v[0], v[1], v[2]), (v[0], v[2], v[3])):
            target.faces.new(tri).smooth = False

    def window_row(
        self,
        rect: Rect,
        side: str,
        z0: float,
        z1: float,
        pitch: float,
        width: float,
        margin: float = 1.0,
        proud: float = 0.07,
    ) -> None:
        for d in bay_centres(side_length(rect, side), pitch, width, margin):
            self.window(rect, side, d - width / 2.0, d + width / 2.0, z0, z1, proud)

    # -- facade styles -----------------------------------------------------
    def stucco_facade(
        self,
        rect: Rect,
        side: str,
        z_bottom: float,
        z_floor: float,
        floors: int,
        step: float,
        wall: RGBA,
        band: RGBA,
        pitch: float = 4.0,
        win_w: float = 1.8,
    ) -> None:
        """Plinth, per-floor wall + string course, and spaced windows."""
        length = side_length(rect, side)
        if z_floor > z_bottom + 0.05:
            self.panel(rect, side, 0.0, length, z_bottom, z_floor, color("sandstone_plinth"))
        for i in range(floors):
            za = z_floor + i * step
            zb = za + step
            self.panel(rect, side, 0.0, length, za, zb - 0.32, wall)
            self.panel(rect, side, 0.0, length, zb - 0.32, zb, band)
            self.window_row(rect, side, za + 0.95, za + step - 0.85, pitch, win_w)

    def verandah_facade(
        self,
        rect: Rect,
        side: str,
        z_bottom: float,
        z_floor: float,
        floors: int,
        step: float,
        pitch: float = 4.4,
    ) -> None:
        """Open corridor floors: white railing, shaded recess, slab edge, tile sunshades and dark posts."""
        length = side_length(rect, side)
        rail, recess, slab = color("stucco_white"), color("verandah_shadow"), color("stucco_cream")
        tile, post = color("ab2_tile"), color("timber_post")
        if z_floor > z_bottom + 0.05:
            self.panel(rect, side, 0.0, length, z_bottom, z_floor, color("sandstone_plinth"))
        for i in range(floors):
            za = z_floor + i * step
            zb = za + step
            self.panel(rect, side, 0.0, length, za, za + 1.0, rail)
            self.panel(rect, side, 0.0, length, za + 1.0, zb - 0.4, recess)
            self.panel(rect, side, 0.0, length, zb - 0.4, zb, slab)
            if i < floors - 1:
                self.shade(rect, side, zb - 0.45, zb + 0.15, 0.9, tile)
            self.window_row(rect, side, za + 1.15, zb - 0.75, pitch, 1.3, margin=1.6, proud=0.04)
        for d in bay_centres(length, pitch, 0.3, 0.2):
            self.panel(rect, side, d - 0.14, d + 0.14, z_floor, z_floor + floors * step - 0.4, post, proud=0.1)

    # -- roofs -------------------------------------------------------------
    def skirt_roof(
        self,
        rect: Rect,
        z_eave: float,
        widths: dict[str, float],
        rise: float,
        cap: RGBA,
        overhang: float = 0.8,
    ) -> float:
        """Flat concrete roof ringed by sloping tile eaves. A side of width 0 is closed vertically.

        Returns the cap height.
        """
        u0, u1, v0, v1 = rect
        w = {s: widths.get(s, 0.0) for s in SIDES}
        over = {s: (overhang if w[s] > 0 else 0.0) for s in SIDES}
        outer = (u0 - over["w"], u1 + over["e"], v0 - over["s"], v1 + over["n"])
        inner = (u0 + w["w"], u1 - w["e"], v0 + w["s"], v1 - w["n"])
        z_cap = z_eave + rise
        tile, soffit = color("ab2_tile"), color("stucco_white")
        for side in SIDES:
            oa, ob = edge_of(outer, side)
            ia, ib = edge_of(inner, side)
            if w[side] > 0:
                self.quad([(*oa, z_eave), (*ob, z_eave), (*ib, z_cap), (*ia, z_cap)], tile)
                wa, wb = edge_of(rect, side)
                self.quad([(*oa, z_eave), (*wa, z_eave), (*wb, z_eave), (*ob, z_eave)], soffit)
            else:
                self.quad([(*oa, z_eave), (*ob, z_eave), (*ib, z_cap), (*ia, z_cap)], color("stucco_cream"))
        self.flat(inner, z_cap, cap)
        return z_cap

    def hip_roof(self, rect: Rect, z_eave: float, rise: float, rgba: RGBA, overhang: float = 0.8) -> None:
        """Four-sided pitched roof with its ridge along the longer axis, plus an underside soffit."""
        u0, u1, v0, v1 = (rect[0] - overhang, rect[1] + overhang, rect[2] - overhang, rect[3] + overhang)
        sw, se, ne, nw = [(u, v, z_eave) for u, v in _corners((u0, u1, v0, v1))]
        du, dv = u1 - u0, v1 - v0
        zr = z_eave + rise
        uc, vc = (u0 + u1) / 2.0, (v0 + v1) / 2.0
        if du >= dv:
            half = max(0.05, (du - dv) / 2.0)
            r0, r1 = (uc - half, vc, zr), (uc + half, vc, zr)
            self.quad([sw, se, r1, r0], rgba)
            self.tri([se, ne, r1], rgba)
            self.quad([ne, nw, r0, r1], rgba)
            self.tri([nw, sw, r0], rgba)
        else:
            half = max(0.05, (dv - du) / 2.0)
            r0, r1 = (uc, vc - half, zr), (uc, vc + half, zr)
            self.tri([sw, se, r0], rgba)
            self.quad([se, ne, r1, r0], rgba)
            self.tri([ne, nw, r1], rgba)
            self.quad([nw, sw, r0, r1], rgba)
        self.quad([nw, ne, se, sw], color("stucco_white"))

    def frustum_roof(self, base: Rect, top: Rect, z0: float, z1: float, rgba: RGBA) -> None:
        for side in SIDES:
            a, b = edge_of(base, side)
            c, d = edge_of(top, side)
            self.quad([(*a, z0), (*b, z0), (*d, z1), (*c, z1)], rgba)

    def pyramid(self, rect: Rect, z0: float, z_apex: float, rgba: RGBA) -> None:
        apex = ((rect[0] + rect[1]) / 2.0, (rect[2] + rect[3]) / 2.0, z_apex)
        for side in SIDES:
            a, b = edge_of(rect, side)
            self.tri([(*a, z0), (*b, z0), apex], rgba)

    def solar_rows(self, rect: Rect, z: float, pitch: float = 2.6, depth: float = 1.5) -> None:
        u0, u1, v0, v1 = rect
        panel = color("solar_panel")
        v = v0
        while v + depth <= v1 + 1e-6:
            self.quad([(u0, v, z + 0.12), (u1, v, z + 0.12), (u1, v + depth, z + 0.55), (u0, v + depth, z + 0.55)], panel)
            v += pitch


def side_length(rect: Rect, side: str) -> float:
    return (rect[1] - rect[0]) if side in ("s", "n") else (rect[3] - rect[2])


def bay_centres(length: float, pitch: float, width: float, margin: float) -> list[float]:
    """Evenly spaced bay centres (distance along an edge), centred on the edge."""
    usable = length - 2.0 * margin
    if usable < width:
        return []
    count = int((usable - width) // pitch) + 1
    start = length / 2.0 - (count - 1) * pitch / 2.0
    return [start + i * pitch for i in range(count)]


def _corners(rect: Rect) -> list[tuple[float, float]]:
    u0, u1, v0, v1 = rect
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def _along(rect: Rect, side: str, d: float, proud: float) -> tuple[float, float]:
    (au, av), (bu, bv) = edge_of(rect, side)
    length = max(1e-6, side_length(rect, side))
    t = d / length
    nu, nv = _OUTWARD[side]
    return (au + (bu - au) * t + nu * proud, av + (bv - av) * t + nv * proud)
