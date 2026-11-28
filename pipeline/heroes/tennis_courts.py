"""Modular hero: the twin floodlit tennis courts south of the hostels, west of AB-1 (OSM `way/380925362`).

References:
  - `pipeline/refs/tennis_marked_map.webp`: the user's markup of the site (red) and the two courts (blue).
  - `pipeline/refs/tennis_irl_day_court.webp`, `tennis_irl_night_fence.jpg`, `tennis_irl_night_lights.jpg`:
    the user's own photos.
  - `pipeline/refs/tennis_courts_sat.jpg`: Esri imagery (older, pre-resurfacing), which confirms the enclosure
    position and that the two courts run north-south side by side.

What the photos show:
  - Two hard courts side by side, long axis north-south, nets parallel: blue playing area bounded by the
    white doubles lines, inside a green acrylic surround.
  - The enclosure is a dark-green chain-link fence (~4 m) standing on a low green-painted wall; modelled as
    the wall plus the fence's top rail (see the note in `build_hero`).
  - Tall slender light-grey floodlight poles with single LED heads along the side fences and in the gap
    between the courts.

The OSM polygon replaced here is excluded in `overrides.json`. Flat geometry and the floodlights are merged
into `STATIC_HeroAccents` (no extra draw call or material). Budget: ~150 tris, ~0.7 KB of GLB.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from hero_models.geom_helpers import add_quad_vc, srgb_hex_to_linear_rgba

REPLACED_OSM_SPORTS_IDS: tuple[str, ...] = ("way/380925362",)

# Enclosure frame taken from the OSM polygon (local metres, +x east, +y north): the polygon's east-west edges
# are rotated ~4.2 deg counter-clockwise from the x axis.
CENTER_XY = (124.4, -349.3)
ROT_DEG = 4.2
ENC_HW = 17.6  # half width across the two courts (u, east)
ENC_HL = 17.6  # half length along the courts (v, north)

# ITF doubles court: 10.97 x 23.77 m, singles 8.23 m, service line 6.40 m from the net, net posts 0.914 m out.
COURT_HW = 10.97 / 2
COURT_HL = 23.77 / 2
SINGLES_HW = 8.23 / 2
SERVICE_V = 6.40
NET_POST_U = COURT_HW + 0.914
COURT_CENTERS_U = (-8.0, 8.0)

C_SURROUND = "#5FA35A"   # light green acrylic run-off (photos)
C_COURT = "#2F64A8"      # blue playing area
C_LINE = "#F4F3EE"
C_WALL = "#2E6B3A"       # low green wall under the fence
C_POST = "#2A5A36"       # dark-green fence rail
C_NET = "#8E979C"         # mostly see-through mesh reads as light grey from above
C_LIGHT_POLE = "#C9CCCF"
C_LAMP = "#FFF6DA"

LINE_W = 0.1
WALL_H = 0.9
FENCE_H = 4.2
RAIL_H = 0.14

# Floodlight poles (u, v) in the enclosure frame: three along each side fence and two in the gap between
# the courts, matching the photos (poles stand just outside the doubles sidelines).
POLE_H = 10.0
POLES_UV: tuple[tuple[float, float], ...] = (
    (-ENC_HW + 0.4, -9.0), (-ENC_HW + 0.4, 0.0), (-ENC_HW + 0.4, 9.0),
    (ENC_HW - 0.4, -9.0), (ENC_HW - 0.4, 0.0), (ENC_HW - 0.4, 9.0),
    (0.0, -6.5), (0.0, 6.5),
)


class _Frame:
    def __init__(self, cx: float, cy: float, rot_rad: float) -> None:
        self.cx, self.cy, self.rot = cx, cy, rot_rad
        self.ca, self.sa = math.cos(rot_rad), math.sin(rot_rad)

    def w(self, u: float, v: float) -> tuple[float, float]:
        return (self.cx + u * self.ca - v * self.sa, self.cy + u * self.sa + v * self.ca)


def _rect(fr: _Frame, u0: float, v0: float, u1: float, v1: float) -> list[tuple[float, float]]:
    return [fr.w(u0, v0), fr.w(u1, v0), fr.w(u1, v1), fr.w(u0, v1)]


def _flat_quad(bm: bmesh.types.BMesh, col: Any, pts: list[tuple[float, float]], z: float, rgba: Any) -> None:
    v = [bm.verts.new((x, y, z)) for x, y in pts]
    add_quad_vc(bm, col, v[0], v[1], v[2], v[3], rgba)


def _line(bm: bmesh.types.BMesh, col: Any, fr: _Frame, u0: float, v0: float, u1: float, v1: float, z: float, rgba: Any) -> None:
    hw = LINE_W * 0.5
    if abs(u1 - u0) > abs(v1 - v0):
        pts = _rect(fr, min(u0, u1) - hw, v0 - hw, max(u0, u1) + hw, v0 + hw)
    else:
        pts = _rect(fr, u0 - hw, min(v0, v1) - hw, u0 + hw, max(v0, v1) + hw)
    _flat_quad(bm, col, pts, z, rgba)


def _vquad2(bm: bmesh.types.BMesh, col: Any, a: tuple[float, float], b: tuple[float, float], z0: float, z1: float, rgba: Any) -> None:
    """Double-sided vertical quad from a to b."""
    v = [bm.verts.new((a[0], a[1], z0)), bm.verts.new((b[0], b[1], z0)), bm.verts.new((b[0], b[1], z1)), bm.verts.new((a[0], a[1], z1))]
    add_quad_vc(bm, col, v[0], v[1], v[2], v[3], rgba)
    add_quad_vc(bm, col, v[3], v[2], v[1], v[0], rgba)


def _prism3(bm: bmesh.types.BMesh, col: Any, cx: float, cy: float, z0: float, z1: float, r: float, rgba: Any) -> None:
    """Open three-sided pole (6 tris); its cap is hidden under the lamp head."""
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in (0.0, 2.094, 4.189)]
    b = [bm.verts.new((x, y, z0)) for x, y in pts]
    t = [bm.verts.new((x, y, z1)) for x, y in pts]
    for i in range(3):
        j = (i + 1) % 3
        add_quad_vc(bm, col, b[i], b[j], t[j], t[i], rgba)


def get_tennis_feature_trees() -> list[tuple[float, float, int, float]]:
    """Hand-placed (x, y, type, scale) trees around the enclosure (type 0 = palm, 1 = broadleaf).

    The photos show areca palms and broadleaf trees hugging the fence on every side.
    """
    fr = _Frame(CENTER_XY[0], CENTER_XY[1], math.radians(ROT_DEG))
    spots = [
        (-ENC_HW - 3.5, -12.0, 1, 1.35), (-ENC_HW - 3.0, 0.0, 0, 1.1), (-ENC_HW - 3.8, 12.5, 1, 1.4),
        (ENC_HW + 3.5, -11.0, 1, 1.3), (ENC_HW + 3.0, 1.5, 0, 1.05), (ENC_HW + 3.8, 13.0, 1, 1.45),
        (-11.0, ENC_HL + 3.5, 1, 1.3), (2.0, ENC_HL + 3.2, 0, 1.1), (12.5, ENC_HL + 3.8, 1, 1.35),
        (-7.0, -ENC_HL - 3.5, 0, 1.05), (-2.0, -ENC_HL - 3.8, 1, 1.4), (11.0, -ENC_HL - 3.3, 0, 1.1),
    ]
    out = []
    for u, v, t, s in spots:
        x, y = fr.w(u, v)
        out.append((x, y, t, s))
    return out


def build_hero(context: dict[str, Any]) -> None:
    import bpy

    terrain = context["terrain"]
    solid_colliders = context["solid_colliders"]
    fr = _Frame(CENTER_XY[0], CENTER_XY[1], math.radians(ROT_DEG))

    zs = [terrain.sample(*fr.w(-ENC_HW + 2 * ENC_HW * i / 4, -ENC_HL + 2 * ENC_HL * j / 4)) for i in range(5) for j in range(5)]
    z_top, z_bot = max(zs) + 0.15, min(zs) - 1.5
    print(f"  Tennis courts: terrain spread {max(zs) - min(zs):.2f} m")

    host = bpy.data.objects.get("STATIC_HeroAccents")
    if host is None:
        raise RuntimeError("tennis_courts needs STATIC_HeroAccents")
    bm = bmesh.new()
    bm.from_mesh(host.data)
    col = bm.loops.layers.color.get("Color") or bm.loops.layers.color.new("Color")

    c = {k: srgb_hex_to_linear_rgba(h) for k, h in {
        "surround": C_SURROUND, "court": C_COURT, "line": C_LINE, "wall": C_WALL,
        "post": C_POST, "net": C_NET, "pole": C_LIGHT_POLE, "lamp": C_LAMP,
    }.items()}

    # Green surround slab (top + retaining skirts)
    ring = _rect(fr, -ENC_HW, -ENC_HL, ENC_HW, ENC_HL)
    t = [bm.verts.new((x, y, z_top)) for x, y in ring]
    add_quad_vc(bm, col, t[0], t[1], t[2], t[3], c["surround"])
    # Outer skirt runs from below grade up to the top of the low wall, so it doubles as the wall's outer face
    b = [bm.verts.new((x, y, z_bot)) for x, y in ring]
    w = [bm.verts.new((x, y, z_top + WALL_H)) for x, y in ring]
    for i in range(4):
        j = (i + 1) % 4
        add_quad_vc(bm, col, b[i], b[j], w[j], w[i], c["wall"])
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    solid_colliders.append(((min(xs) - 2.0, min(ys) - 2.0, max(xs) + 2.0, max(ys) + 2.0), [ring]))

    # Two blue courts with white lines and nets
    z_c, z_l = z_top + 0.05, z_top + 0.09  # clear of z-fighting at map viewing distances
    for cu in COURT_CENTERS_U:
        _flat_quad(bm, col, _rect(fr, cu - COURT_HW, -COURT_HL, cu + COURT_HW, COURT_HL), z_c, c["court"])
        for su in (-COURT_HW, COURT_HW, -SINGLES_HW, SINGLES_HW):
            _line(bm, col, fr, cu + su, -COURT_HL, cu + su, COURT_HL, z_l, c["line"])
        for sv in (-COURT_HL, COURT_HL):
            _line(bm, col, fr, cu - COURT_HW, sv, cu + COURT_HW, sv, z_l, c["line"])
        for sv in (-SERVICE_V, SERVICE_V):
            _line(bm, col, fr, cu - SINGLES_HW, sv, cu + SINGLES_HW, sv, z_l, c["line"])
        _line(bm, col, fr, cu, -SERVICE_V, cu, SERVICE_V, z_l, c["line"])
        # Net
        a, b2 = fr.w(cu - NET_POST_U, 0.0), fr.w(cu + NET_POST_U, 0.0)
        _vquad2(bm, col, a, b2, z_top + 0.05, z_top + 1.07, c["net"])  # posts and headband omitted (sub-pixel)

    # Low green wall around the enclosure: inner faces only (the outer faces are the slab skirt, carried up)
    for k in range(4):
        a, b2 = ring[(k + 1) % 4], ring[k]
        v = [bm.verts.new((a[0], a[1], z_top)), bm.verts.new((b2[0], b2[1], z_top)),
             bm.verts.new((b2[0], b2[1], z_top + WALL_H)), bm.verts.new((a[0], a[1], z_top + WALL_H))]
        add_quad_vc(bm, col, v[0], v[1], v[2], v[3], c["wall"])

    # Floodlights: slender light-grey pole + flat LED head
    for u, v in POLES_UV:
        px, py = fr.w(u, v)
        _prism3(bm, col, px, py, z_top, z_top + POLE_H, 0.1, c["pole"])
        hu = u - math.copysign(0.35, u) if abs(u) > 0.1 else u
        hx, hy = fr.w(hu, v)
        lamp = [fr.w(hu - 0.32, v - 0.22), fr.w(hu + 0.32, v - 0.22), fr.w(hu + 0.32, v + 0.22), fr.w(hu - 0.32, v + 0.22)]
        lv = [bm.verts.new((x, y, z_top + POLE_H)) for x, y in lamp]
        add_quad_vc(bm, col, lv[0], lv[1], lv[2], lv[3], c["lamp"])  # glowing LED panel seen from above
        add_quad_vc(bm, col, lv[3], lv[2], lv[1], lv[0], c["lamp"])  # and from below

    # Chain-link fence: an alpha-blended mesh material costs ~1 KB of GLB on its own, more than the budget
    # allows, so the fence reads as its dark-green top rail (both faces) above the low green wall.
    corners = [fr.w(-ENC_HW, -ENC_HL), fr.w(ENC_HW, -ENC_HL), fr.w(ENC_HW, ENC_HL), fr.w(-ENC_HW, ENC_HL)]
    for k in range(4):
        _vquad2(bm, col, corners[k], corners[(k + 1) % 4], z_top + FENCE_H - RAIL_H, z_top + FENCE_H, c["post"])

    bm.normal_update()
    bm.to_mesh(host.data)
    host.data.update()
    bm.free()
