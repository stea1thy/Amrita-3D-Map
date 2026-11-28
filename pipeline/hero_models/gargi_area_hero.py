"""Gargi Bhavanam and the staff housing round Link Road / Guest House Road, traced from Google satellite.

What the imagery shows (and the plain OSM extrusions missed):
- Gargi Bhavanam (`way/380702791`) is not a hollow square: it is two halves of long east-west blocks
  either side of a lower north-south corridor, with tree-filled courts between the rows. Blocks are
  pale-walled with weathered brown roofs, dark light-well strips down their middles and a saw-tooth of
  balcony/stair bays along the court sides. Row positions are measured from the roof image and anchored
  to the OSM outline (frame below), so the outer walls stay where the rest of the map expects them.
- The residences (Business School Dean's Residence, Director - ICT Residence, A1 Staff Quarters and the
  bungalows near them) are one- and two-storey houses with grey or green pitched metal roofs.
- `way/380702792` beside the basketball court is a single tall hall under a tan metal gable roof.
- The cross-shaped house on Link Road has grey hipped roofs; the Ambulance Yard shed and the small
  Guest House annex have terracotta roofs; the Ashram office has a grey metal gable roof.
- Flat-roofed blocks keep the generic extrusion but get their real roof colour and floor count, and the
  Guest House gets the conical terracotta roof over its round east pavilion.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .facade_kit import Kit, Rect, bay_centres, color
from .geom_helpers import srgb_hex_to_linear_rgba

HERO_GARGI_ID = "way/380702791"
HERO_GUEST_HOUSE_ID = "way/380829427"

# Gargi frame: origin at the OSM south-west corner, u along the south wall (east), v north
_GARGI_ORIGIN = (-133.8, -13.8)
_GARGI_ROT = math.atan2(-9.1 + 13.8, -37.4 + 133.8)
GARGI_FLOORS = 5
GARGI_STEP_M = 3.3
GARGI_DEPTH_V = 94.0
# (v0, v1, light-well centre or None) per half, west half u 1.5..47.5, east half u 52..96
GARGI_WEST: tuple[tuple[float, float, float | None], ...] = (
    (75.0, 94.0, 84.5), (50.5, 67.5, 59.5), (24.5, 44.0, 34.0), (0.0, 18.0, 9.0),
)
GARGI_EAST: tuple[tuple[float, float, float | None], ...] = (
    (74.0, 94.0, 84.0), (62.0, 70.0, None), (38.0, 60.0, 49.0), (26.0, 31.5, None), (0.0, 17.5, 9.5),
)
GARGI_HALVES = ((1.5, 47.5, GARGI_WEST), (52.0, 96.0, GARGI_EAST))
GARGI_SPINE: Rect = (47.5, 52.0, 0.0, GARGI_DEPTH_V)
GARGI_BAY_PITCH_M = 6.0
GARGI_BAY_DEPTH_M = 1.4

# Pitched-roof houses: fid -> (floors, wall height m, roof colour hex)
PITCHED: dict[str, tuple[int, float, str]] = {
    "way/380702796": (2, 6.4, "#7FA36A"),   # Business School Dean's Residence (green roof)
    "way/380702797": (2, 6.4, "#86A872"),   # green roof
    "way/380702798": (2, 6.4, "#B9BCBE"),
    "way/380702799": (2, 6.4, "#AEB2B4"),
    "way/380702800": (2, 6.4, "#C3C6C8"),   # Director - ICT Residence
    "way/380702801": (2, 6.4, "#BFC3C6"),   # A1 Staff Quarters
    "way/380702805": (2, 6.4, "#C6C9CB"),
    "way/380702806": (2, 6.4, "#C1C4C6"),
    "overture/3ce226d1-484": (2, 6.0, "#9A9C9C"),
    "way/546394566": (2, 6.4, "#9EA4A8"),   # Ashram office (grey metal gable)
    "overture/92ed51bd-ee0": (1, 3.6, "#B85A3E"),   # Ambulance Yard shed
    "overture/5f45283a-f87": (1, 3.4, "#B5583C"),   # Guest House annex
}
# Tall hall with a tan metal gable roof
HALL_ID = "way/380702792"
HALL_WALL_M, HALL_RISE_M, HALL_ROOF_HEX = 8.0, 2.4, "#CDAE90"
# Flat-roofed blocks: fid -> (floors, height m, roof colour hex)
FLAT: dict[str, tuple[int, float, str]] = {
    "way/380702802": (3, 10.2, "#9C8070"),
    "way/380702803": (3, 10.2, "#A08573"),
    "overture/db73729f-7f9": (2, 7.0, "#C8C1B5"),
    HERO_GUEST_HOUSE_ID: (2, 7.4, "#C2B8AA"),
    "overture/ad2c8b1e-452": (1, 3.4, "#CFC8BC"),
    "way/546394567": (1, 3.8, "#CEC7BB"),
    "overture/5d5587c9-1c1": (1, 3.6, "#D3CCC0"),
    "overture/a7905bc9-634": (1, 3.4, "#D0C9BD"),
}
GUEST_HOUSE_DOME = ((-183.6, -138.2), 6.6, 3.2)  # centre, radius, rise: circle fitted to the OSM round bay
GUEST_HOUSE_BAY_WEST_X = -187.7  # the bay is a circle cut by the building's front wall here


def calibration(fid: str) -> tuple[int, float] | None:
    """(floors, height m) for buildings this module styles."""
    if fid in PITCHED:
        floors, wall, _ = PITCHED[fid]
        return floors, wall
    if fid == HALL_ID:
        return 1, HALL_WALL_M
    if fid in FLAT:
        floors, height, _ = FLAT[fid]
        return floors, height
    if fid == HERO_GARGI_ID:
        return GARGI_FLOORS, GARGI_FLOORS * GARGI_STEP_M
    return None


def get_roof_hex(fid: str) -> str | None:
    return FLAT[fid][2] if fid in FLAT else None


def builds(fid: str) -> bool:
    return fid == HERO_GARGI_ID or fid in PITCHED or fid == HALL_ID


def _gargi_xy(u: float, v: float) -> tuple[float, float]:
    ca, sa = math.cos(_GARGI_ROT), math.sin(_GARGI_ROT)
    return (_GARGI_ORIGIN[0] + u * ca - v * sa, _GARGI_ORIGIN[1] + u * sa + v * ca)


def normalize_gargi_footprint_rings() -> list[list[tuple[float, float]]]:
    return [[_gargi_xy(u, v) for u, v in ((1.5, 0.0), (96.0, 0.0), (96.0, GARGI_DEPTH_V), (1.5, GARGI_DEPTH_V))]]


def build(
    fid: str,
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    rings: list[list[tuple[float, float]]],
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build one styled building. Returns world vertices."""
    if fid == HERO_GARGI_ID:
        return _build_gargi(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz)
    frame = _ring_frame(rings[0])
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=frame.to_xy)
    zs = [terrain.sample(x, y) for x, y in rings[0]]
    z_bottom, z_floor = min(zs) - 1.0, max(zs) + 0.2
    if fid == HALL_ID:
        _hall(kit, frame.bbox(rings[0]), z_bottom, z_floor)
    else:
        floors, wall, roof_hex = PITCHED[fid]
        for rect in _orthogonal_rects(frame, rings[0]):
            _house(kit, rect, z_bottom, z_floor, floors, wall, srgb_hex_to_linear_rgba(roof_hex))
    return kit.world_pts


def append_details(fid: str, bm: bmesh.types.BMesh, col_layer: Any, terrain: Any,
                   offset_xyz: tuple[float, float, float], z_top: float) -> None:
    """Extra roof pieces on generically extruded buildings (Guest House pavilion cone)."""
    if fid != HERO_GUEST_HOUSE_ID:
        return
    (cx, cy), radius, rise = GUEST_HOUSE_DOME
    kit = Kit(bm, col_layer, None, None, offset_xyz, to_xy=lambda u, v: (cx + u, cy + v))
    tile = color("asb_porch_tile")
    sides = 12
    cut = GUEST_HOUSE_BAY_WEST_X - cx  # keep the roof over the bay, not the courtyard beside it
    ring = [(max(cut, radius * math.cos(2 * math.pi * i / sides)), radius * math.sin(2 * math.pi * i / sides))
            for i in range(sides)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        kit.tri([(*a, z_top), (*b, z_top), (0.0, 0.0, z_top + rise)], tile)


# -- Gargi ---------------------------------------------------------------------

def _build_gargi(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz) -> list[tuple[float, float, float]]:
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=_gargi_xy)
    zs = [terrain.sample(*_gargi_xy(u, v)) for u in (1.5, 48.0, 96.0) for v in (0.0, 47.0, GARGI_DEPTH_V)]
    z_bottom, z_floor = min(zs) - 1.5, max(zs) + 0.2
    z_roof = z_floor + GARGI_FLOORS * GARGI_STEP_M
    wall, roof, well = color("stucco_cream"), srgb_hex_to_linear_rgba("#8F776A"), srgb_hex_to_linear_rgba("#4F3F38")
    for u0, u1, blocks in GARGI_HALVES:
        for v0, v1, light_well in blocks:
            rect = (u0, u1, v0, v1)
            _block(kit, rect, z_bottom, z_floor, z_roof, wall, roof)
            if light_well is not None:
                kit.flat((u0 + 1.5, u1 - 1.5, light_well - 1.8, light_well + 1.8), z_roof + 0.83, well)
    z_spine = z_floor + 3 * GARGI_STEP_M
    kit.box(GARGI_SPINE, z_bottom, z_spine, wall, color("ab4_concrete"))
    kit.window_row(GARGI_SPINE, "e", z_floor + 1.0, z_floor + 2.4, 5.0, 1.4)
    kit.window_row(GARGI_SPINE, "w", z_floor + 1.0, z_floor + 2.4, 5.0, 1.4)
    return kit.world_pts


def _block(kit: Kit, rect: Rect, z_bottom: float, z_floor: float, z_roof: float, wall, roof) -> None:
    """Five-storey block: walls with window bays, parapet band, saw-tooth balcony bays on the long sides."""
    u0, u1, v0, v1 = rect
    z_top = z_roof + 0.8
    kit.box(rect, z_bottom, z_top, wall, roof)
    for side in ("e", "w"):
        kit.panel(rect, side, 0.0, v1 - v0, z_top - 0.3, z_top, color("sandstone_plinth"), proud=0.03)
    for side in ("s", "n"):
        length = u1 - u0
        kit.panel(rect, side, 0.0, length, z_top - 0.3, z_top, color("sandstone_plinth"), proud=0.03)
        for d in bay_centres(length, GARGI_BAY_PITCH_M, 2.2, 1.6):
            ua = u0 + d - 1.1 if side == "s" else u1 - d - 1.1
            bay = (ua, ua + 2.2, v0 - GARGI_BAY_DEPTH_M, v0) if side == "s" else (ua, ua + 2.2, v1, v1 + GARGI_BAY_DEPTH_M)
            kit.box(bay, z_floor, z_top - 0.2, color("stucco_white"), color("sandstone_plinth"))
        for d in bay_centres(length, GARGI_BAY_PITCH_M, 2.2, 1.6 + GARGI_BAY_PITCH_M / 2.0):
            for level in range(GARGI_FLOORS):
                za = z_floor + level * GARGI_STEP_M
                kit.window(rect, side, d - 0.8, d + 0.8, za + 0.9, za + 2.3)


# -- houses and hall -------------------------------------------------------------

class _Frame:
    def __init__(self, origin: tuple[float, float], angle: float) -> None:
        self.origin, self.ca, self.sa = origin, math.cos(angle), math.sin(angle)

    def to_xy(self, u: float, v: float) -> tuple[float, float]:
        return (self.origin[0] + u * self.ca - v * self.sa, self.origin[1] + u * self.sa + v * self.ca)

    def to_uv(self, x: float, y: float) -> tuple[float, float]:
        dx, dy = x - self.origin[0], y - self.origin[1]
        return (dx * self.ca + dy * self.sa, -dx * self.sa + dy * self.ca)

    def bbox(self, ring: list[tuple[float, float]]) -> Rect:
        uv = [self.to_uv(*p) for p in ring]
        return (min(p[0] for p in uv), max(p[0] for p in uv), min(p[1] for p in uv), max(p[1] for p in uv))


def _ring_frame(ring: list[tuple[float, float]]) -> _Frame:
    """Frame aligned with the ring's longest edge."""
    a, b = max(zip(ring, ring[1:] + ring[:1]), key=lambda e: math.dist(*e))
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    return _Frame(ring[0], angle)


def _inside(u: float, v: float, poly: list[tuple[float, float]]) -> bool:
    odd = False
    for (au, av), (bu, bv) in zip(poly, poly[1:] + poly[:1]):
        if (av > v) != (bv > v) and u < au + (v - av) * (bu - au) / (bv - av):
            odd = not odd
    return odd


def _snap(values: list[float], tol: float = 0.8) -> list[float]:
    out: list[float] = []
    for value in sorted(values):
        if not out or value - out[-1] > tol:
            out.append(value)
    return out


def _orthogonal_rects(frame: _Frame, ring: list[tuple[float, float]]) -> list[Rect]:
    """Split a near-orthogonal outline into rectangles (grid cells merged into rows, rows merged down)."""
    uv = [frame.to_uv(*p) for p in ring]
    us, vs = _snap([p[0] for p in uv]), _snap([p[1] for p in uv])
    rows: list[list[tuple[float, float]]] = []
    for va, vb in zip(vs, vs[1:]):
        runs: list[tuple[float, float]] = []
        for ua, ub in zip(us, us[1:]):
            if _inside((ua + ub) / 2.0, (va + vb) / 2.0, uv):
                if runs and abs(runs[-1][1] - ua) < 1e-6:
                    runs[-1] = (runs[-1][0], ub)
                else:
                    runs.append((ua, ub))
        rows.append(runs)
    rects: list[Rect] = []
    for i, runs in enumerate(rows):
        for ua, ub in runs:
            rects.append((ua, ub, vs[i], vs[i + 1]))
    merged: list[Rect] = []
    for r in sorted(rects, key=lambda r: (r[0], r[1], r[2])):
        if merged and abs(merged[-1][0] - r[0]) < 1e-6 and abs(merged[-1][1] - r[1]) < 1e-6 and abs(merged[-1][3] - r[2]) < 1e-6:
            merged[-1] = (r[0], r[1], merged[-1][2], r[3])
        else:
            merged.append(r)
    return merged or [frame.bbox(ring)]


def _house(kit: Kit, rect: Rect, z_bottom: float, z_floor: float, floors: int, wall_m: float, roof) -> None:
    z_eave = z_floor + wall_m
    kit.box(rect, z_bottom, z_eave, color("stucco_cream"), color("stucco_cream"))
    step = wall_m / floors
    for side in ("s", "e", "n", "w"):
        for level in range(floors):
            za = z_floor + level * step
            kit.window_row(rect, side, za + 0.9, za + min(2.3, step - 0.5), 3.6, 1.2, margin=0.8)
    u0, u1, v0, v1 = rect
    rise = min(2.6, 0.32 * min(u1 - u0, v1 - v0))
    kit.hip_roof(rect, z_eave, rise, roof, overhang=0.6)


def _hall(kit: Kit, rect: Rect, z_bottom: float, z_floor: float) -> None:
    """Tall hall under a shallow tan metal gable running along its long axis."""
    u0, u1, v0, v1 = rect
    z_eave = z_floor + HALL_WALL_M
    kit.box(rect, z_bottom, z_eave, color("stucco_cream"))
    for side in ("s", "n", "e", "w"):
        kit.window_row(rect, side, z_floor + 4.5, z_floor + 6.8, 4.5, 2.0, margin=1.5)
    roof, over = srgb_hex_to_linear_rgba(HALL_ROOF_HEX), 0.7
    a0, a1, b0, b1 = u0 - over, u1 + over, v0 - over, v1 + over
    if (u1 - u0) >= (v1 - v0):  # ridge along u
        vm = (v0 + v1) / 2.0
        kit.quad([(a0, b0, z_eave), (a1, b0, z_eave), (a1, vm, z_eave + HALL_RISE_M), (a0, vm, z_eave + HALL_RISE_M)], roof)
        kit.quad([(a1, b1, z_eave), (a0, b1, z_eave), (a0, vm, z_eave + HALL_RISE_M), (a1, vm, z_eave + HALL_RISE_M)], roof)
        for u, flip in ((u0, False), (u1, True)):
            tri = [(u, v0, z_eave), (u, v1, z_eave), (u, vm, z_eave + HALL_RISE_M)]
            kit.tri(tri if flip else tri[::-1], color("stucco_cream"))
    else:  # ridge along v
        um = (u0 + u1) / 2.0
        kit.quad([(a1, b0, z_eave), (a1, b1, z_eave), (um, b1, z_eave + HALL_RISE_M), (um, b0, z_eave + HALL_RISE_M)], roof)
        kit.quad([(a0, b1, z_eave), (a0, b0, z_eave), (um, b0, z_eave + HALL_RISE_M), (um, b1, z_eave + HALL_RISE_M)], roof)
        for v, flip in ((v0, False), (v1, True)):
            tri = [(u0, v, z_eave), (u1, v, z_eave), (um, v, z_eave + HALL_RISE_M)]
            kit.tri(tri[::-1] if flip else tri, color("stucco_cream"))


def gargi_tree_spots() -> list[tuple[float, float, int, tuple[float, float], int]]:
    """Trees filling the courts between Gargi's blocks (satellite: dense canopy), world XY."""
    spots: list[tuple[float, float, int, tuple[float, float], int]] = []
    for u0, u1, blocks in GARGI_HALVES:
        edges = sorted(blocks)
        for (_, top, _), (bottom, _, _) in zip(edges, edges[1:]):
            gap = bottom - top
            if gap < 5.0:
                continue
            v = (top + bottom) / 2.0
            n = 0
            u = u0 + 3.5
            while u < u1 - 3.0:
                spots.append((*_gargi_xy(u + (1.2 if n % 2 else -1.2), v), 1, (0.62, 0.8), 4))
                u += 6.5
                n += 1
    return spots
