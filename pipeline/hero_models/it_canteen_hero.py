"""IT Canteen: single-storey dining hall under a two-tier tile roof, facing its lawn to the east.

Modelled on the "AB2 IT Canteen" Google Maps photos (see `pipeline/refs/ab2_library_sources.md`).
The hall follows the (already shifted) footprint it is given, so `shift_footprints` still moves it.
Local frame: u = metres east across the hall, v = metres north along it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import bmesh

from .facade_kit import SIDES, Kit, Rect, color, edge_of, side_length

# Hall plan inside the OSM outline, relative to the outline centre; the east strip is left as garden
HALL_OFFSET_U = -3.0
HALL: Rect = (-8.0, 8.0, -17.0, 17.0)

SILL_M = 1.15
EAVE_M = 3.3
EAVE_OVERHANG_M = 1.6
CLERESTORY_INSET_M = 3.6
LOWER_RISE_M = 1.5
CLERESTORY_M = 1.0
UPPER_RISE_M = 1.9
HEIGHT_M = EAVE_M + LOWER_RISE_M + CLERESTORY_M + UPPER_RISE_M

DOOR_V: tuple[float, float] = (2.0, 7.0)  # entrance opening on the east front


@dataclass(frozen=True)
class CanteenFrame:
    origin: tuple[float, float]
    north: tuple[float, float]  # unit vector along the hall

    def to_xy(self, u: float, v: float) -> tuple[float, float]:
        nx, ny = self.north
        return (self.origin[0] + u * ny + v * nx, self.origin[1] - u * nx + v * ny)

    def ring(self, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [self.to_xy(u, v) for u, v in points]


def frame_from_hall_ring(ring: list[tuple[float, float]]) -> CanteenFrame:
    """Recover the frame from the CCW hall ring (SW, SE, NE, NW) emitted by the footprint normaliser."""
    sw, se, ne, nw = ring[:4]
    dx = (ne[0] - se[0]) + (nw[0] - sw[0])
    dy = (ne[1] - se[1]) + (nw[1] - sw[1])
    span = math.hypot(dx, dy)
    centre = (sum(p[0] for p in ring[:4]) / 4.0, sum(p[1] for p in ring[:4]) / 4.0)
    return CanteenFrame(centre, (dx / span, dy / span))


def normalize_it_canteen_footprint_rings(outline: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """Replace the OSM outline with the hall rectangle, aligned to the outline's long axis."""
    pts = outline[:-1] if len(outline) > 1 and outline[0] == outline[-1] else outline
    centre = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    ax, ay = max(
        ((b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:] + pts[:1])),
        key=lambda d: math.hypot(*d),
    )
    if ay < 0:
        ax, ay = -ax, -ay
    span = math.hypot(ax, ay)
    outline_frame = CanteenFrame(centre, (ax / span, ay / span))
    hall_frame = CanteenFrame(outline_frame.to_xy(HALL_OFFSET_U, 0.0), outline_frame.north)
    u0, u1, v0, v1 = HALL
    return [hall_frame.ring([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])]


def build_it_canteen(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    ring: list[tuple[float, float]],
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build the hall walls, window band, entrance and two-tier roof. Returns world vertices."""
    frame = frame_from_hall_ring(ring)
    kit = Kit(bm, col_layer, win_lit_bm, win_dark_bm, offset_xyz, to_xy=frame.to_xy)
    zs = [terrain.sample(*p) for p in ring]
    z_bottom, z_floor = min(zs) - 1.2, max(zs) + 0.25
    z_eave = z_floor + EAVE_M

    for side in SIDES:
        _wall(kit, side, z_bottom, z_floor, z_eave)
    _entrance(kit, z_floor, z_eave)
    _roof(kit, z_eave)
    return kit.world_pts


def _wall(kit: Kit, side: str, z_bottom: float, z_floor: float, z_eave: float) -> None:
    """Cream dado wall under a continuous band of dark windows divided by slim posts."""
    length = side_length(HALL, side)
    cream, post = color("canteen_wall"), color("canteen_wall", 0.9)
    kit.panel(HALL, side, 0.0, length, z_bottom, z_floor, color("sandstone_plinth"))
    kit.panel(HALL, side, 0.0, length, z_floor, z_floor + SILL_M, cream)
    kit.panel(HALL, side, 0.0, length, z_floor + SILL_M, z_eave, color("verandah_shadow"))
    bays = max(1, round(length / 2.6))
    step = length / bays
    for i in range(bays):
        kit.window(HALL, side, i * step + 0.22, (i + 1) * step - 0.22, z_floor + SILL_M + 0.15, z_eave - 0.35, 0.05)
    for i in range(bays + 1):
        d = min(max(i * step, 0.14), length - 0.14)
        kit.panel(HALL, side, d - 0.14, d + 0.14, z_floor + SILL_M, z_eave, post, proud=0.09)
    if side == "e":  # solid white end bay north of the entrance, as in the photos
        kit.panel(HALL, side, length - 5.0, length, z_floor, z_eave, cream, proud=0.12)
        kit.window(HALL, side, length - 3.4, length - 2.0, z_floor + 1.3, z_floor + 2.4, 0.17)


def _entrance(kit: Kit, z_floor: float, z_eave: float) -> None:
    d0, d1 = DOOR_V[0] - HALL[2], DOOR_V[1] - HALL[2]
    kit.panel(HALL, "e", d0, d1, z_floor, z_eave - 0.1, color("recess_shadow"), proud=0.14)
    for d in (d0, (d0 + d1) / 2.0, d1):
        kit.panel(HALL, "e", d - 0.16, d + 0.16, z_floor, z_eave, color("stucco_white"), proud=0.2)
    u1 = HALL[1]
    kit.box((u1, u1 + 1.1, DOOR_V[0] - 0.4, DOOR_V[1] + 0.4), z_floor - 0.6, z_floor,
            color("sandstone_plinth"), color("path_stone"))


def _roof(kit: Kit, z_eave: float) -> None:
    """Wide lower tile skirt, shaded clerestory with posts, then the hipped upper roof."""
    u0, u1, v0, v1 = HALL
    o, i = EAVE_OVERHANG_M, CLERESTORY_INSET_M
    outer: Rect = (u0 - o, u1 + o, v0 - o, v1 + o)
    inner: Rect = (u0 + i, u1 - i, v0 + i, v1 - i)
    z_break = z_eave + LOWER_RISE_M
    z_top = z_break + CLERESTORY_M
    tile = color("canteen_tile")

    kit.frustum_roof(outer, inner, z_eave - 0.15, z_break, tile)
    for side in SIDES:  # soffit under the deep eave
        oa, ob = edge_of(outer, side)
        wa, wb = edge_of(HALL, side)
        kit.quad([(*oa, z_eave - 0.15), (*wa, z_eave), (*wb, z_eave), (*ob, z_eave - 0.15)], color("timber_post"))
    for side in SIDES:
        length = side_length(inner, side)
        kit.panel(inner, side, 0.0, length, z_break, z_top, color("verandah_shadow"))
        posts = max(2, round(length / 3.0))
        for k in range(posts + 1):
            d = min(max(k * length / posts, 0.12), length - 0.12)
            kit.panel(inner, side, d - 0.12, d + 0.12, z_break, z_top, color("canteen_wall"), proud=0.07)
    kit.hip_roof(inner, z_top, UPPER_RISE_M, tile, overhang=1.1)
