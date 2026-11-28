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
  - The enclosure is a dark-green chain-link fence (~4 m) on dark-green posts, standing on a low
    green-painted wall.
  - Tall slender light-grey floodlight poles with single LED heads along the side fences and in the gap
    between the courts.

The OSM polygon replaced here is excluded in `overrides.json`. Everything opaque is merged into
`STATIC_HeroAccents`. The see-through chain-link mesh is its own `GROUND_TennisFence` object with an
alpha-blended material: the web app only lets `STATIC_HeroAccents` cast shadows, and three.js shadows
ignore opacity, so keeping the panels separate stops them throwing a solid shadow over the courts.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

from hero_models.geom_helpers import add_box_vc, add_quad_vc, srgb_hex_to_linear_rgba

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
C_POST = "#2A5A36"       # dark-green fence posts and rail
C_CHAINLINK = "#1E4A2C"  # chain-link mesh tint
CHAINLINK_ALPHA = 0.35
C_NET = "#8E979C"         # mostly see-through mesh reads as light grey from above
C_LIGHT_POLE = "#C9CCCF"
C_LAMP = "#FFF6DA"

LINE_W = 0.1
WALL_H = 0.9
FENCE_H = 4.2
RAIL_H = 0.14
FENCE_POST_STEP = 4.4  # post spacing along each side (8 bays)

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


def _make_chainlink_material() -> Any:
    """Double-sided, alpha-blended dark-green tint (exported as glTF alphaMode BLEND, doubleSided)."""
    import bpy

    mat = bpy.data.materials.get("MAT_TennisChainLink")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name="MAT_TennisChainLink")
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None) or nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = srgb_hex_to_linear_rgba(C_CHAINLINK)
    bsdf.inputs["Alpha"].default_value = CHAINLINK_ALPHA
    bsdf.inputs["Roughness"].default_value = 0.9
    mat.use_backface_culling = False
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    return mat


# Road centrelines next to the courts (OSM way/128964701 main road, way/128964700 N-S road to AB-1), local metres
_ROADS_XY: tuple[tuple[tuple[float, float], ...], ...] = (
    ((1.0, -382.0), (112.0, -378.0), (162.0, -374.0), (171.0, -373.0)),
    ((171.0, -373.0), (172.0, -354.0), (172.0, -321.0)),
)
ROAD_CLEAR = 6.0  # tree trunk to road centreline (asphalt half-width ~3.5 m + canopy)

# Tree belts from the user's Google Earth view of the site (shared in chat, 2026-11-28): dense canopy boxes the courts in on
# the west, east and north, a strip between the fence and the main road, and a belt between road and railway.
_BELTS: tuple[tuple[float, float, float, float], ...] = (
    (78.0, -372.0, 104.0, -316.0),   # west
    (144.0, -370.0, 166.0, -314.0),  # east, up to the N-S road
    (102.0, -328.0, 146.0, -314.0),  # north, below the hostel yard
    (102.0, -373.0, 146.0, -368.0),  # thin strip between the fence and the main road
    (70.0, -394.0, 168.0, -383.0),   # between the main road and the railway
)
BELT_STEP = 5.2
MIN_TREE_GAP = 4.2


def _seg_dist(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
    return math.hypot(px - a[0] - t * dx, py - a[1] - t * dy)


def _hash01(i: int, j: int, k: int) -> float:
    """Deterministic 0..1 jitter (keeps the shared tree rng untouched)."""
    h = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791)
    return ((h & 0xFFFF) / 65535.0)


def get_tennis_feature_trees(existing_xy: list[tuple[float, float]] | None = None) -> list[tuple[float, float, int, float]]:
    """(x, y, type, scale) trees around the enclosure (type 0 = palm, 1 = broadleaf).

    Hand-placed trees hug the fence (photos show areca palms and broadleaf trees on every side); a jittered
    grid then fills the belts from the Google view, skipping roads, the enclosure and any tree within
    MIN_TREE_GAP of an existing one.
    """
    fr = _Frame(CENTER_XY[0], CENTER_XY[1], math.radians(ROT_DEG))
    spots = [
        (-ENC_HW - 3.5, -12.0, 1, 1.35), (-ENC_HW - 3.0, 0.0, 0, 1.1), (-ENC_HW - 3.8, 12.5, 1, 1.4),
        (ENC_HW + 3.5, -11.0, 1, 1.3), (ENC_HW + 3.0, 1.5, 0, 1.05), (ENC_HW + 3.8, 13.0, 1, 1.45),
        (-11.0, ENC_HL + 3.5, 1, 1.3), (2.0, ENC_HL + 3.2, 0, 1.1), (12.5, ENC_HL + 3.8, 1, 1.35),
        (-7.0, -ENC_HL - 3.5, 0, 1.05), (-2.0, -ENC_HL - 3.8, 1, 1.4), (11.0, -ENC_HL - 3.3, 0, 1.1),
    ]
    out: list[tuple[float, float, int, float]] = []
    taken: list[tuple[float, float]] = list(existing_xy or [])

    def _clear(x: float, y: float) -> bool:
        if any(_seg_dist(x, y, a, b) < ROAD_CLEAR for road in _ROADS_XY for a, b in zip(road, road[1:])):
            return False
        dx, dy = x - CENTER_XY[0], y - CENTER_XY[1]
        u = dx * fr.ca + dy * fr.sa
        v = -dx * fr.sa + dy * fr.ca
        if abs(u) < ENC_HW + 2.2 and abs(v) < ENC_HL + 2.2:
            return False
        return all(math.hypot(x - tx, y - ty) >= MIN_TREE_GAP for tx, ty in taken)

    for u, v, t, sc in spots:
        x, y = fr.w(u, v)
        if all(math.hypot(x - tx, y - ty) >= MIN_TREE_GAP for tx, ty in taken):
            out.append((x, y, t, sc))
            taken.append((x, y))

    for bi, (x0, y0, x1, y1) in enumerate(_BELTS):
        nx = max(1, int((x1 - x0) / BELT_STEP))
        ny = max(1, int((y1 - y0) / BELT_STEP))
        for i in range(nx + 1):
            for j in range(ny + 1):
                x = x0 + (x1 - x0) * i / nx + (_hash01(i, j, bi) - 0.5) * 2.4
                y = y0 + (y1 - y0) * j / ny + (_hash01(j, i, bi + 7) - 0.5) * 2.4
                if not _clear(x, y):
                    continue
                r = _hash01(i, j, bi + 13)
                out.append((round(x, 2), round(y, 2), 0 if r < 0.22 else 1, round(1.05 + 0.45 * _hash01(i, j, bi + 29), 2)))
                taken.append((x, y))
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
        # Net: grey mesh with the white headband, between two dark net posts
        a, b2 = fr.w(cu - NET_POST_U, 0.0), fr.w(cu + NET_POST_U, 0.0)
        _vquad2(bm, col, a, b2, z_top + 0.05, z_top + 0.98, c["net"])
        _vquad2(bm, col, a, b2, z_top + 0.98, z_top + 1.07, c["line"])
        for su in (-NET_POST_U, NET_POST_U):
            px, py = fr.w(cu + su, 0.0)
            add_box_vc(bm, col, px, py, z_top, z_top + 1.07, 0.05, 0.05, c["post"], rot_rad=fr.rot)

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

    # Fence posts along every side, plus the top rail (both faces)
    corners = [fr.w(-ENC_HW, -ENC_HL), fr.w(ENC_HW, -ENC_HL), fr.w(ENC_HW, ENC_HL), fr.w(-ENC_HW, ENC_HL)]
    n_bays = max(1, round(2 * ENC_HW / FENCE_POST_STEP))
    for k in range(4):
        a, b2 = corners[k], corners[(k + 1) % 4]
        for n in range(n_bays):  # the next side adds the closing corner post
            f = n / n_bays
            add_box_vc(bm, col, a[0] + (b2[0] - a[0]) * f, a[1] + (b2[1] - a[1]) * f, z_top + WALL_H, z_top + FENCE_H,
                       0.05, 0.05, c["post"], rot_rad=fr.rot)
        _vquad2(bm, col, a, b2, z_top + FENCE_H - RAIL_H, z_top + FENCE_H, c["post"])

    bm.normal_update()
    bm.to_mesh(host.data)
    host.data.update()
    bm.free()

    # See-through chain-link panels between the wall and the rail: own object, no shadow (see module docstring)
    fbm = bmesh.new()
    for k in range(4):
        a, b2 = corners[k], corners[(k + 1) % 4]
        fbm.faces.new([fbm.verts.new((a[0], a[1], z_top + WALL_H)), fbm.verts.new((b2[0], b2[1], z_top + WALL_H)),
                       fbm.verts.new((b2[0], b2[1], z_top + FENCE_H - RAIL_H)), fbm.verts.new((a[0], a[1], z_top + FENCE_H - RAIL_H))])
    bmesh.ops.triangulate(fbm, faces=fbm.faces[:])
    fmesh = bpy.data.meshes.new("GROUND_TennisFence")
    fbm.to_mesh(fmesh)
    fbm.free()
    fmesh.materials.append(_make_chainlink_material())
    fobj = bpy.data.objects.new("GROUND_TennisFence", fmesh)
    bpy.context.scene.collection.objects.link(fobj)
