"""Vasishta Bhavanam: five-floor boys' hostel with a comb plan, flat roofs and a tiled north front.

Plan traced from Esri World Imagery (zoom 18) registered onto the OSM outline (way/380829425):
a north front block with five thick wings running south, separated by four gaps that stay open to
the south. Each outer wing has a narrow light well down its middle; the central wing carries a
terracotta-tiled hall roof. Roofs are flat weathered concrete with white parapets; lighter roof
patches mark the wing ends. The north front (entrance side) is styled from the owner's ground
photo: white stucco, salmon-pink pilasters and floor bands, a sloping Mangalore-tile skirt along
the roofline, taller projecting stair blocks with hip roofs, and white-columned entrance porches.

Local frame: u = metres east along the facade from the south-west corner, v = metres north.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

import config

from .facade_kit import SIDES, Kit, Rect, bay_centres, color, edge_of, side_length

FLOORS = 5
FLOOR_STEP_M = 3.15
FOUNDATION_M = 1.5
PARAPET_M = 0.9
BAND_M = 0.28  # salmon floor band under each slab line

# OSM corners (lat, lon): south-west, south-east, north-west
_SW_LL = (10.901402, 76.8953595)
_SE_LL = (10.9014546, 76.8967327)
_NW_LL = (10.9018234, 76.895338)


def _ll_xy(lat: float, lon: float) -> tuple[float, float]:
    x_east, z_south = config.latlon_to_local_xz(lat, lon)
    return (x_east, -z_south)


_ORIGIN_XY = _ll_xy(*_SW_LL)
_SE_XY = _ll_xy(*_SE_LL)
_NW_XY = _ll_xy(*_NW_LL)
ROTATION_RAD = math.atan2(_SE_XY[1] - _ORIGIN_XY[1], _SE_XY[0] - _ORIGIN_XY[0])
LENGTH_U = math.dist(_ORIGIN_XY, _SE_XY)  # ~150 m
DEPTH_V = math.dist(_ORIGIN_XY, _NW_XY)  # ~47 m

CENTRE_U = LENGTH_U / 2.0
SPINE_V = DEPTH_V - 9.0  # back (south face) of the north front block
# Open gaps between the wings: (centre offset from the middle, width), mirrored east and west
_GAPS = ((17.0, 8.5), (47.0, 9.5))
GAPS: tuple[Rect, ...] = tuple(sorted(
    (CENTRE_U + s * off - w / 2.0, CENTRE_U + s * off + w / 2.0, 0.0, SPINE_V)
    for off, w in _GAPS
    for s in (-1.0, 1.0)
))
_edges = [0.0, *(x for g in GAPS for x in (g[0], g[1])), LENGTH_U]
WINGS: tuple[Rect, ...] = tuple((a, b, 0.0, SPINE_V) for a, b in zip(_edges[0::2], _edges[1::2]))
# Narrow light wells down the middle of the four outer wings
_WELLS = ((32.0, 6.5), (62.5, 6.5))
WELL_V0 = 12.0
WELLS: tuple[Rect, ...] = tuple(sorted(
    (CENTRE_U + s * off - w / 2.0, CENTRE_U + s * off + w / 2.0, WELL_V0, SPINE_V - 0.5)
    for off, w in _WELLS
    for s in (-1.0, 1.0)
))
CENTRAL_HALL: Rect = (CENTRE_U - 8.0, CENTRE_U + 8.0, WELL_V0, DEPTH_V - 6.0)  # terracotta hall roof
# Stair/lobby blocks projecting from the north front, one storey higher in roofline
PROJECTIONS: tuple[Rect, ...] = (
    (CENTRE_U - 46.0, CENTRE_U - 32.0, DEPTH_V, DEPTH_V + 6.0),
    (CENTRE_U + 32.0, CENTRE_U + 46.0, DEPTH_V, DEPTH_V + 6.0),
)
# Single-storey entrance porches beside each projection (flat white slab on columns + tiled hip)
PORCHES: tuple[Rect, ...] = (
    (CENTRE_U - 31.0, CENTRE_U - 21.0, DEPTH_V, DEPTH_V + 8.0),
    (CENTRE_U + 21.0, CENTRE_U + 31.0, DEPTH_V, DEPTH_V + 8.0),
)


def to_xy(u: float, v: float) -> tuple[float, float]:
    ca, sa = math.cos(ROTATION_RAD), math.sin(ROTATION_RAD)
    return (_ORIGIN_XY[0] + u * ca - v * sa, _ORIGIN_XY[1] + u * sa + v * ca)


def normalize_vasishta_footprint_rings() -> list[list[tuple[float, float]]]:
    """Comb outline (CCW) with the north projections, and the four light wells as clockwise holes."""
    outer: list[tuple[float, float]] = []
    for i, (u0, u1, _, _) in enumerate(WINGS):
        outer += [(u0, 0.0), (u1, 0.0)]
        if i + 1 < len(WINGS):
            outer += [(u1, SPINE_V), (WINGS[i + 1][0], SPINE_V)]
    outer.append((LENGTH_U, DEPTH_V))
    for u0, u1, _, v1 in sorted(PROJECTIONS, key=lambda r: -r[0]):
        outer += [(u1, DEPTH_V), (u1, v1), (u0, v1), (u0, DEPTH_V)]
    outer.append((0.0, DEPTH_V))
    holes = [[(u0, v0), (u0, v1), (u1, v1), (u1, v0)] for u0, u1, v0, v1 in WELLS]
    return [[to_xy(*p) for p in outer]] + [[to_xy(*p) for p in hole] for hole in holes]


def build_vasishta(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build walls, light wells, flat roofs with parapets, the tiled front, projections and porches."""
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=to_xy)
    zs = [terrain.sample(*to_xy(LENGTH_U * i / 8.0, DEPTH_V * j / 4.0)) for i in range(9) for j in range(5)]
    z_bottom, z_floor = min(zs) - FOUNDATION_M, max(zs) + 0.2
    z_roof = z_floor + FLOORS * FLOOR_STEP_M + 0.3
    z_top = z_roof + PARAPET_M

    _walls(kit, z_bottom, z_floor, z_top)
    for well in WELLS:
        _light_well(kit, well, z_floor, z_roof, z_top)
    _roofs(kit, z_roof, z_top)
    for rect in PROJECTIONS:
        _projection(kit, rect, z_bottom, z_floor, z_top)
    for rect in PORCHES:
        _porch(kit, rect, z_bottom, z_floor)
    return kit.world_pts


# -- walls -------------------------------------------------------------------------------
def _span(rect: Rect, side: str, a: float, b: float) -> tuple[float, float]:
    """Absolute range a..b (u for s/n walls, v for e/w walls) as distances along edge_of(rect, side)."""
    u0, u1, v0, v1 = rect
    return {"s": (a - u0, b - u0), "n": (u1 - b, u1 - a), "e": (a - v0, b - v0), "w": (v1 - b, v1 - a)}[side]


def _facade(
    kit: Kit, rect: Rect, side: str, a: float, b: float,
    z_bottom: float, z_floor: float, z_top: float, *, pitch: float = 3.6, pilasters: bool = True,
) -> None:
    """White stucco run a..b: plinth, salmon floor bands, pilasters, one window per bay per floor, parapet cap."""
    d0, d1 = _span(rect, side, a, b)
    white, pink = color("stucco_white"), color("vasishta_pink")
    kit.panel(rect, side, d0, d1, z_bottom, z_floor, color("sandstone_plinth"))
    kit.panel(rect, side, d0, d1, z_floor, z_top, white)
    for level in range(1, FLOORS + 1):
        zb = z_floor + level * FLOOR_STEP_M
        kit.panel(rect, side, d0, d1, zb - BAND_M, zb, pink, proud=0.05)
    _cap(kit, rect, side, d0, d1, z_top)
    if d1 - d0 < 2.0:
        return
    bays = [d0 + c for c in bay_centres(d1 - d0, pitch, 1.4, 0.8)]
    for level in range(FLOORS):
        za = z_floor + level * FLOOR_STEP_M
        for c in bays:
            kit.window(rect, side, c - 0.7, c + 0.7, za + 0.95, za + 2.3)
    if pilasters:
        for c in bays[:-1]:
            p = c + pitch / 2.0
            kit.panel(rect, side, p - 0.22, p + 0.22, z_floor, z_top - 0.2, pink, proud=0.12)


def _cap(kit: Kit, rect: Rect, side: str, d0: float, d1: float, z: float, width: float = 0.5) -> None:
    """White parapet top along a wall run, so roof outlines read white from above like the satellite."""
    (au, av), (bu, bv) = edge_of(rect, side)
    length = max(1e-6, side_length(rect, side))
    ou, ov = {"s": (0.0, 1.0), "n": (0.0, -1.0), "e": (-1.0, 0.0), "w": (1.0, 0.0)}[side]  # inward
    p = [(au + (bu - au) * d / length, av + (bv - av) * d / length) for d in (d0, d1)]
    kit.quad([(p[0][0], p[0][1], z), (p[1][0], p[1][1], z),
              (p[1][0] + ou * width, p[1][1] + ov * width, z), (p[0][0] + ou * width, p[0][1] + ov * width, z)],
             color("stucco_white"))


def _walls(kit: Kit, z_bottom: float, z_floor: float, z_top: float) -> None:
    body: Rect = (0.0, LENGTH_U, 0.0, DEPTH_V)
    spine: Rect = (0.0, LENGTH_U, SPINE_V, DEPTH_V)
    # North front between the projecting stair blocks
    cuts = sorted((r[0], r[1]) for r in PROJECTIONS)
    a = 0.0
    for c0, c1 in cuts + [(LENGTH_U, LENGTH_U)]:
        if c0 - a > 0.5:
            _facade(kit, spine, "n", a, c0, z_bottom, z_floor, z_top)
        a = c1
    # West and east ends of the whole building
    _facade(kit, body, "w", 0.0, DEPTH_V, z_bottom, z_floor, z_top, pilasters=False)
    _facade(kit, body, "e", 0.0, DEPTH_V, z_bottom, z_floor, z_top, pilasters=False)
    for wing in WINGS:
        u0, u1, v0, v1 = wing
        _facade(kit, wing, "s", u0, u1, z_bottom, z_floor, z_top)
        if u0 > 0.1:
            _facade(kit, wing, "w", v0, v1, z_bottom, z_floor, z_top, pilasters=False)
        if u1 < LENGTH_U - 0.1:
            _facade(kit, wing, "e", v0, v1, z_bottom, z_floor, z_top, pilasters=False)
    for gap in GAPS:  # back of the front block, seen down each gap
        _facade(kit, spine, "s", gap[0], gap[1], z_bottom, z_floor, z_top, pilasters=False)
    tile = color("vasishta_tile")
    for side in ("n", "w", "e"):  # sloping tile skirt along the front block's roofline (ground photo)
        kit.shade(spine, side, z_top - 0.55, z_top + 0.45, 1.1, tile)
    z_shade = z_floor + FLOOR_STEP_M
    kit.shade(spine, "n", z_shade - 0.5, z_shade + 0.05, 0.9, tile)


def _light_well(kit: Kit, well: Rect, z_floor: float, z_roof: float, z_top: float) -> None:
    """Inward-facing walls of a narrow open light well, white rim on top, red-earth floor."""
    u0, u1, v0, v1 = well
    white = color("stucco_white")
    for face, wall in (("e", (u0 - 1.0, u0, v0, v1)), ("w", (u1, u1 + 1.0, v0, v1)),
                       ("n", (u0, u1, v0 - 1.0, v0)), ("s", (u0, u1, v1, v1 + 1.0))):
        length = side_length(wall, face)
        kit.panel(wall, face, 0.0, length, z_floor - 0.6, z_top, white)
        _cap(kit, wall, face, 0.0, length, z_top)
        if face in ("e", "w"):
            for level in range(FLOORS):
                za = z_floor + level * FLOOR_STEP_M
                kit.window_row(wall, face, za + 0.95, za + 2.3, 4.8, 1.3, margin=1.2)
    kit.flat(well, z_floor - 0.6, color("vasishta_earth"))


# -- roofs -------------------------------------------------------------------------------
def _roofs(kit: Kit, z_roof: float, z_top: float) -> None:
    """Flat weathered-concrete roofs, light end patches on each wing, and the central tiled hall roof."""
    slab = color("vasishta_roof")
    kit.flat((0.0, LENGTH_U, SPINE_V, DEPTH_V), z_roof, slab)
    for wing in WINGS:
        u0, u1, v0, v1 = wing
        holes = [[(w[0], w[2]), (w[0], w[3]), (w[1], w[3]), (w[1], w[2])] for w in WELLS if u0 < w[0] < u1]
        kit.polygon([(u0, v0), (u1, v0), (u1, v1 + 0.01), (u0, v1 + 0.01)], holes, z_roof, slab)
        kit.flat((u0 + 0.5, u1 - 0.5, 0.5, WELL_V0 - 1.0), z_roof + 0.05, color("stucco_cream"))
    kit.hip_roof(CENTRAL_HALL, z_roof + 0.2, 1.9, color("terracotta_portal"), overhang=0.3)


# -- north front features ----------------------------------------------------------------
def _projection(kit: Kit, rect: Rect, z_bottom: float, z_floor: float, z_top: float) -> None:
    """Projecting stair/lobby block: same facade, a tile sunshade at mid height, a higher hip roof."""
    u0, u1, v0, v1 = rect
    z_eave = z_top + 1.2
    _facade(kit, rect, "n", u0, u1, z_bottom, z_floor, z_eave, pitch=3.4)
    _facade(kit, rect, "e", v0, v1, z_bottom, z_floor, z_eave, pilasters=False)
    _facade(kit, rect, "w", v0, v1, z_bottom, z_floor, z_eave, pilasters=False)
    tile = color("vasishta_tile")
    z_mid = z_floor + 3 * FLOOR_STEP_M
    kit.shade(rect, "n", z_mid - 0.55, z_mid + 0.05, 1.0, tile)
    kit.hip_roof((u0, u1, v0 - 2.0, v1), z_eave, 2.6, tile, overhang=0.8)


def _porch(kit: Kit, rect: Rect, z_bottom: float, z_floor: float) -> None:
    """Entrance porch: four white columns, a deep white slab carrying the blue name board, a tiled hip roof."""
    u0, u1, v0, v1 = rect
    white = color("stucco_white")
    z_slab = z_floor + 3.4
    for u in (u0 + 0.5, u1 - 0.9):
        for v in (v1 - 0.9, v0 + 3.2):
            _column(kit, (u, u + 0.4, v, v + 0.4), z_bottom, z_slab, white)
    kit.box((u0, u1, v0, v1), z_slab, z_slab + 0.8, white)
    _name_board(kit, (u0 + u1) / 2.0, v1, z_slab + 0.08, z_slab + 0.72)
    kit.hip_roof((u0 + 0.6, u1 - 0.6, v0, v1 - 0.6), z_slab + 0.8, 1.6, color("vasishta_tile"), overhang=0.5)
    kit.flat((u0, u1, v0, v1), z_floor + 0.02, color("sandstone_plinth"))


# 5x7 block font for the name board (only the letters it needs); rows top to bottom
_FONT: dict[str, tuple[str, ...]] = {
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    " ": ("00000",) * 7,
}
BOARD_TEXT = "VASISHTA BHAVANAM"  # as written on the real sign


def _name_board(kit: Kit, u_mid: float, v_face: float, z0: float, z1: float) -> None:
    """Blue board on the porch's north fascia with white block letters (one quad per run of lit pixels)."""
    cols = len(BOARD_TEXT) * 6 - 1
    px = (z1 - z0 - 0.12) / 7.0
    width = cols * px + 0.3
    board: Rect = (u_mid - width / 2.0, u_mid + width / 2.0, v_face - 0.05, v_face)
    kit.panel(board, "n", 0.0, width, z0, z1, color("vasishta_sign"), proud=0.03)
    letter = color("stucco_white")
    u_start, z_top = board[0] + 0.15, z1 - 0.06
    for i, ch in enumerate(BOARD_TEXT):
        for r, row in enumerate(_FONT[ch]):
            c = 0
            while c < 5:
                if row[c] != "1":
                    c += 1
                    continue
                run = c
                while run < 5 and row[run] == "1":
                    run += 1
                ua = u_start + (i * 6 + c) * px
                ub = u_start + (i * 6 + run) * px
                za = z_top - (r + 1) * px
                # a north wall's edge runs east -> west, i.e. left -> right for someone facing it
                kit.panel(board, "n", ua - board[0], ub - board[0], za, za + px, letter, proud=0.06)
                c = run


def _column(kit: Kit, rect: Rect, z0: float, z1: float, rgba: tuple[float, float, float, float]) -> None:
    for side in SIDES:
        a, b = edge_of(rect, side)
        kit.quad([(*a, z0), (*b, z0), (*b, z1), (*a, z1)], rgba)
