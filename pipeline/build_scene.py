"""Build Amrita Coimbatore 3D campus GLB (with Hero landmarks, Western Ghats backdrop, and courtyard detail) + trees.json."""

from __future__ import annotations

import json
import math
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
import mathutils
import numpy as np

# Ensure sibling modules in pipeline/ are importable when launched via Blender
PIPELINE_DIR = Path(__file__).resolve().parent
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

import campus_frame  # noqa: E402
import config  # noqa: E402
import footbridges  # noqa: E402
import terrain_utils  # noqa: E402
import verify_budget  # noqa: E402
from hero_models import (  # noqa: E402
    HERO_AB1_ID,
    HERO_AB2_ID,
    HERO_AB2_SKYBRIDGE_ID,
    HERO_AB3_ID,
    HERO_AB4_ID,
    HERO_AMRITESHWARI_ID,
    HERO_ASB_ID,
    HERO_MBA_CANTEEN_ID,
    HERO_PANDAL_ID,
    HERO_GATE_BANK_ID,
    HERO_IT_CANTEEN_ID,
    HERO_LIBRARY_ID,
    HERO_MAIN_CANTEEN_ID,
    HERO_NEW_HOSTEL_ID,
    HERO_PLAYGROUND_ID,
    HERO_POOL_DECK_ID,
    HERO_POOL_WATER_ID,
    HERO_SHRINE_ID,
    HERO_WORKSHOPS_EAST_ID,
    HERO_WORKSHOPS_WEST_ID,
    ab1_hero,
    ab2_hero,
    ab3_hero,
    ab4_hero,
    amriteshwari_hero,
    asb_hero,
    campus_landmarks,
    it_canteen_hero,
    mba_canteen_hero,
    pandal_hero,
    library_hero,
    new_hostel_hero,
    workshops_hero,
)

FOUNDATION_SINK_M = 3.0
FLOOR_HEIGHT_M = 3.6
TERRAIN_SKIRT_DEPTH_M = 34.0
TERRAIN_EDGE_MARGIN_M = 25.0

EXTEND_SHORT_M = (60.0, 145.0, 265.0, 420.0)
EXTEND_MOUNTAIN_M = (60.0, 140.0, 240.0, 380.0, 540.0, 740.0, 980.0, 1250.0)

GARDEN_PALM_SHADE, GARDEN_TREE_SHADE = 5, 4  # light greens in the web viewer's tree palettes
TARGET_TREE_COUNT = 2800
MIN_TREE_COUNT = 2520
MAX_TREE_COUNT = 2850

# Amrita South Indian institutional maquette palette (sRGB hex, sampled from reference photos)
PALETTE: dict[str, str] = {
    # Sunlit Ettimadai tropical greens & Bouluvampatty Western Ghats foothills
    "terrain_campus": "#6EAA59",
    "terrain_park": "#5BA54F",
    "terrain_emerald": "#3E8349",
    "terrain_mountain_mid": "#396456",
    "terrain_mountain_peak": "#5A787E",
    "terrain_meadow": "#7FB461",
    "terrain_red_earth": "#CAB08E",
    "terrain_courtyard": "#DFD5C3",
    "terrain_skirt": "#4F5A54",
    # Water, pool, sports, plazas & planters
    "water_pond": "#3893C6",
    "pool_water": "#1CB5D8",
    "pool_deck": "#EDE7DA",
    "sports_pitch": "#4E9E47",
    "sports_court": "#C86743",
    "lawn_courtyard": "#56A14A",
    "plaza_sandstone": "#DED4C3",
    "plaza_charcoal": "#4A4E54",
    "plaza_ab1": "#8E7A68",
    "planter_stone": "#C4B8A5",
    # Roads & Indian alternating curbs
    "retaining_wall": "#CFC6B8",
    # Roads, curbs & broad-gauge railway
    "road_asphalt": "#9EA4AB",
    "curb_black": "#2C3035",
    "curb_yellow": "#E5C544",
    "rail_ballast": "#8A8378",
    "rail_sleeper": "#5A4F46",
    "rail_steel": "#B8C0C8",
    "rail_crossing": "#7C7974",
    # Amrita institutional buildings
    "wall_academic": "#EFE8DC",
    "wall_landmark": "#F2ECE0",
    "wall_hostel": "#E8DCCB",
    "wall_food": "#F0E4D2",
    "wall_admin": "#E8E2D7",
    "wall_sports": "#EAE8E2",
    "wall_default": "#EBE4D8",
    "trim_terracotta": "#B8593B",
    "trim_ochre": "#C77952",
    "trim_hostel": "#967B64",
    "parapet_coping": "#F8F5EE",
    "balcony_recess": "#5E544C",
    "portico_column": "#373B42",
    "ab3_accent_brick": "#A54E37",
    "ab3_orange_trim": "#EA8540",
    "roof_ab3_slab": "#A9A69F",
    "roof_ab1_concrete": "#D3CBBD",
    "ab1_cornice_trim": "#BFA185",
    "ab1_band_trim": "#D2BEA6",
    "amh_band_orange": "#E08A5E",
    "roof_amh_slab": "#B9B4AA",
    # Roofs (Mangalore terracotta vs slate)
    "roof_terracotta": "#B54E34",
    "roof_terracotta_top": "#C56244",
    "roof_hostel": "#6A7581",
    "roof_slate": "#5A6772",
    # Warm charcoal/slate-tinted WindowGlass & Hero accents
    "window_glass": "#2B353C",
    "hero_white": "#F4F1EA",
    "hero_bronze": "#D4A13E",
    "hero_bleacher": "#E5E2DA",
}

ROAD_SPECS: dict[str, tuple[float, float, float]] = {
    "primary": (3.5, 0.40, 0.09),
    "secondary": (3.5, 0.40, 0.09),
    "tertiary": (3.5, 0.40, 0.09),
    "unclassified": (2.4, 0.40, 0.09),
    "service": (2.3, 0.40, 0.09),
    "residential": (2.4, 0.40, 0.09),
    "footway": (1.1, 0.25, 0.085),
    "path": (1.1, 0.25, 0.085),
    "pedestrian": (1.2, 0.25, 0.085),
    "steps": (1.1, 0.25, 0.085),
    "cycleway": (1.1, 0.25, 0.085),
}


def _tint_hex_for_id(hex_color: str, fid: str) -> str:
    """Apply subtle deterministic organic warmth/value variation by building ID."""
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) != 6:
        return hex_color
    h = sum((idx + 3) * ord(ch) for idx, ch in enumerate(fid))
    delta_r = (h % 9) - 4
    delta_g = ((h // 7) % 9) - 5
    delta_b = ((h // 13) % 11) - 6
    r = min(255, max(0, int(cleaned[0:2], 16) + delta_r))
    g = min(255, max(0, int(cleaned[2:4], 16) + delta_g))
    b = min(255, max(0, int(cleaned[4:6], 16) + delta_b))
    return f"#{r:02X}{g:02X}{b:02X}"


def latlon_to_blender_xy(lat: float, lon: float) -> tuple[float, float]:
    """Convert (lat, lon) to Blender Z-up XY meters (+X East, +Y North)."""
    x_east, z_south = config.latlon_to_local_xz(lat, lon)
    return (x_east, -z_south)


def blender_to_gltf_xyz(bx: float, by: float, bz: float) -> list[float]:
    """Convert Blender Z-up (bx, by, bz) to glTF Y-up [x, y, z]."""
    return [round(float(bx), 3), round(float(bz), 3), round(float(-by), 3)]


def srgb_hex_to_linear_rgba(
    hex_color: str,
    scale: float = 1.0,
) -> tuple[float, float, float, float]:
    """Convert '#RRGGBB' sRGB hex string to linear RGBA tuple."""
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    rgb = [int(cleaned[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [
        min(1.0, max(0.0, (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) * scale))
        for c in rgb
    ]
    return (linear[0], linear[1], linear[2], 1.0)


def mix_linear_rgba(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    t: float,
) -> tuple[float, float, float, float]:
    """Linearly interpolate two linear RGBA colors."""
    ct = max(0.0, min(1.0, t))
    return (
        a[0] + (b[0] - a[0]) * ct,
        a[1] + (b[1] - a[1]) * ct,
        a[2] + (b[2] - a[2]) * ct,
        1.0,
    )


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """Cubic Hermite interpolation clamped to [0, 1]."""
    if abs(edge1 - edge0) < 1e-9:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def make_palette_material(
    name: str,
    hex_color: str,
    roughness: float = 0.85,
    metallic: float = 0.0,
) -> bpy.types.Material:
    """Create a flat-palette Principled BSDF material."""
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    mat = bpy.data.materials.new(name=name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = srgb_hex_to_linear_rgba(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def make_vertex_color_material(
    name: str,
    roughness: float = 0.82,
    metallic: float = 0.0,
    layer_name: str = "Color",
) -> bpy.types.Material:
    """Create a Principled BSDF material driven by mesh vertex color attribute."""
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    mat = bpy.data.materials.new(name=name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new(type="ShaderNodeBsdfPrincipled")
    vcol = nt.nodes.new(type="ShaderNodeVertexColor")
    vcol.layer_name = layer_name
    nt.links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def _upsample_1d_catmull_rom(vals: np.ndarray) -> np.ndarray:
    """Upsample 1D grid axis (N -> 2N - 1) using clamped Catmull-Rom interpolation."""
    n = vals.shape[0]
    out = np.empty((2 * n - 1,) + vals.shape[1:], dtype=float)
    out[0::2] = vals
    for i in range(n - 1):
        p0 = vals[max(0, i - 1)]
        p1 = vals[i]
        p2 = vals[i + 1]
        p3 = vals[min(n - 1, i + 2)]
        mid = (-p0 + 9.0 * p1 + 9.0 * p2 - p3) / 16.0
        lo = np.minimum(p1, p2)
        hi = np.maximum(p1, p2)
        out[2 * i + 1] = np.clip(mid, lo, hi)
    return out


class TerrainSurface:
    """Upsampled campus terrain extended northward/northwestward into Bouluvampatty Western Ghats."""
    """Graded upsampled campus terrain extended northward/northwestward into Bouluvampatty Western Ghats."""

    def __init__(
        self,
        lats: list[float],
        lons: list[float],
        elevations: list[list[float]],
        datum_m: float,
        raw_osm: dict[str, Any] | None = None,
    ) -> None:
        raw_z = np.asarray(elevations, dtype=float) - datum_m
        up_rows = _upsample_1d_catmull_rom(raw_z)
        core_zs: np.ndarray = _upsample_1d_catmull_rom(up_rows.T).T
        up_rows = terrain_utils.upsample_1d_catmull_rom(raw_z)
        up_zs: np.ndarray = terrain_utils.upsample_1d_catmull_rom(up_rows.T).T

        south_y = latlon_to_blender_xy(lats[0], config.ORIGIN[1])[1]
        north_y = latlon_to_blender_xy(lats[-1], config.ORIGIN[1])[1]
        west_x = latlon_to_blender_xy(config.ORIGIN[0], lons[0])[0]
        east_x = latlon_to_blender_xy(config.ORIGIN[0], lons[-1])[0]

        c_ny, c_nx = core_zs.shape
        c_ny, c_nx = up_zs.shape
        core_xs = np.linspace(west_x, east_x, c_nx)
        core_ys = np.linspace(south_y, north_y, c_ny)
        core_zs = terrain_utils.grade_core_terrain_pads(core_xs, core_ys, up_zs, raw_osm)

        self.core_min_x = float(core_xs[0])
        self.core_max_x = float(core_xs[-1])
        self.core_min_y = float(core_ys[0])
        self.core_max_y = float(core_ys[-1])

        pad_west = [self.core_min_x - d for d in reversed(EXTEND_MOUNTAIN_M)]
        pad_east = [self.core_max_x + d for d in EXTEND_SHORT_M]
        pad_south = [self.core_min_y - d for d in reversed(EXTEND_SHORT_M)]
        pad_north = [self.core_max_y + d for d in EXTEND_MOUNTAIN_M]

        self.xs = np.concatenate([pad_west, core_xs, pad_east])
        self.ys = np.concatenate([pad_south, core_ys, pad_north])

        ext_ny, ext_nx = len(self.ys), len(self.xs)
        self.zs = np.empty((ext_ny, ext_nx), dtype=float)

        def _sample_core(x: float, y: float) -> tuple[float, float, float]:
            cx = min(max(x, self.core_min_x), self.core_max_x)
            cy = min(max(y, self.core_min_y), self.core_max_y)
            fx = (cx - self.core_min_x) / (self.core_max_x - self.core_min_x) * (c_nx - 1)
            fy = (cy - self.core_min_y) / (self.core_max_y - self.core_min_y) * (c_ny - 1)
            c = min(max(int(math.floor(fx)), 0), c_nx - 2)
            r = min(max(int(math.floor(fy)), 0), c_ny - 2)
            u, v = fx - c, fy - r
            z00, z10 = core_zs[r, c], core_zs[r, c + 1]
            z01, z11 = core_zs[r + 1, c], core_zs[r + 1, c + 1]
            z = z00 + u * (z10 - z00) + v * (z11 - z10) if u >= v else z00 + v * (z01 - z00) + u * (z11 - z01)
            return float(z), cx, cy

        dx_step = (self.core_max_x - self.core_min_x) / (c_nx - 1)
        dy_step = (self.core_max_y - self.core_min_y) / (c_ny - 1)
        pad_w_n = len(EXTEND_MOUNTAIN_M)
        pad_s_n = len(EXTEND_SHORT_M)

        for r in range(ext_ny):
            y = float(self.ys[r])
            for c in range(ext_nx):
                x = float(self.xs[c])
                if pad_s_n <= r < pad_s_n + c_ny and pad_w_n <= c < pad_w_n + c_nx:
                    self.zs[r, c] = core_zs[r - pad_s_n, c - pad_w_n]
                else:
                    edge_z, cx, cy = _sample_core(x, y)
                    ox, oy = x - cx, y - cy
                    dist = math.hypot(ox, oy)
                    nx_dir = ox / dist if dist > 1e-6 else 0.0
                    ny_dir = oy / dist if dist > 1e-6 else 0.0

                    z_in, _, _ = _sample_core(cx - nx_dir * dx_step, cy - ny_dir * dy_step)
                    out_slope = max(-0.02, min(0.11, (edge_z - z_in) / max(dx_step, dy_step)))
                    damped = out_slope * 130.0 * (1.0 - math.exp(-dist / 160.0))

                    # Dramatic Bouluvampatty Western Ghats mountain backdrop rising N & NW
                    north_w = smoothstep(-320.0, 320.0, y)
                    west_w = smoothstep(280.0, -400.0, x)
                    mtn_mask = min(1.0, max(north_w * 0.98, west_w * 0.80) + 0.28 * north_w * west_w)

                    r1 = 1.0 - abs(math.sin(0.0028 * x + 0.0041 * y + 0.55))
                    r2 = 1.0 - abs(math.sin(0.0052 * x - 0.0033 * y + 1.35))
                    r3 = 0.5 + 0.5 * math.cos(0.0088 * x + 0.0072 * y)
                    ridge = 0.54 * (r1 ** 1.35) + 0.31 * (r2 ** 1.3) + 0.15 * r3

                    ramp = smoothstep(25.0, 1180.0, dist)
                    mtn_lift = mtn_mask * ramp * (230.0 + 245.0 * ridge)
                    plain_undul = (1.0 - mtn_mask) * smoothstep(25.0, 320.0, dist) * (
                        3.5 * math.sin(0.011 * x + 0.009 * y) + 2.2 * math.cos(0.017 * x - 0.013 * y)
                    )
                    self.zs[r, c] = edge_z + damped + mtn_lift + plain_undul

        self.min_x = float(self.xs[0])
        self.max_x = float(self.xs[-1])
        self.min_y = float(self.ys[0])
        self.max_y = float(self.ys[-1])
        self.min_z = float(np.min(self.zs))
        self.max_z = float(np.max(self.zs))

    def sample(self, x: float, y: float) -> float:
        """Sample exact height on the triangulated terrain surface at Blender (x, y)."""
        cx = min(max(x, self.min_x), self.max_x)
        cy = min(max(y, self.min_y), self.max_y)
        nx, ny = len(self.xs), len(self.ys)
        c = min(max(int(np.searchsorted(self.xs, cx, side="right")) - 1, 0), nx - 2)
        r = min(max(int(np.searchsorted(self.ys, cy, side="right")) - 1, 0), ny - 2)
        u = (cx - self.xs[c]) / (self.xs[c + 1] - self.xs[c])
        v = (cy - self.ys[r]) / (self.ys[r + 1] - self.ys[r])
        z00, z10 = self.zs[r, c], self.zs[r, c + 1]
        z01, z11 = self.zs[r + 1, c], self.zs[r + 1, c + 1]
        z = z00 + u * (z10 - z00) + v * (z11 - z10) if u >= v else z00 + v * (z01 - z00) + u * (z11 - z01)
        return float(z) + campus_frame.rise_offset(cx, cy)


def signed_area_2d(ring: list[tuple[float, float]]) -> float:
    """Compute signed shoelace area of a 2D polygon ring (>0 is CCW)."""
    n = len(ring)
    if n < 3:
        return 0.0
    area2 = 0.0
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    return 0.5 * area2


def clean_ring_2d(
    pts: list[tuple[float, float]],
    min_edge_m: float = 0.15,
    min_area_m2: float = 1.5,
) -> list[tuple[float, float]]:
    """Strip closing duplicate, collapse tiny edges, and validate polygon area."""
    if len(pts) < 3:
        return []
    work = list(pts)
    if math.hypot(work[0][0] - work[-1][0], work[0][1] - work[-1][1]) < 1e-4:
        work.pop()
    cleaned: list[tuple[float, float]] = []
    for pt in work:
        if not cleaned or math.hypot(pt[0] - cleaned[-1][0], pt[1] - cleaned[-1][1]) >= min_edge_m:
            cleaned.append(pt)
    if len(cleaned) >= 2 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) < min_edge_m:
        cleaned.pop()
    if len(cleaned) < 3 or abs(signed_area_2d(cleaned)) < min_area_m2:
        return []
    return cleaned


def ring_centroid_2d(ring: list[tuple[float, float]]) -> tuple[float, float]:
    """Compute 2D polygon centroid."""
    area = signed_area_2d(ring)
    if abs(area) < 1e-6:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    f = 1.0 / (6.0 * area)
    return (cx * f, cy * f)


def point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-ring test."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, rings: list[list[tuple[float, float]]]) -> bool:
    """Test whether (x, y) lies inside outer ring and outside any hole rings."""
    if not rings or not point_in_ring(x, y, rings[0]):
        return False
    return not any(point_in_ring(x, y, hole) for hole in rings[1:])


def bbox_of_ring(ring: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) bounding box of a 2D ring."""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return (min(xs), min(ys), max(xs), max(ys))


def dist_point_to_segment_sq(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    """Squared Euclidean distance from point P to segment AB."""
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq <= 1e-12:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    return (px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2


def dist_point_to_polygon_edge(x: float, y: float, ring: list[tuple[float, float]]) -> float:
    """Minimum Euclidean distance from point (x, y) to any segment of ring."""
    best = float("inf")
    n = len(ring)
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        d2 = dist_point_to_segment_sq(x, y, ax, ay, bx, by)
        if d2 < best:
            best = d2
    return math.sqrt(best)


def convex_hull_2d(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Monotone chain 2D convex hull (CCW)."""
    unique = sorted(set(pts))
    if len(unique) <= 2:
        return unique

    def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in unique:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(unique):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def inset_ccw_ring_2d(
    ring: list[tuple[float, float]],
    inset_m: float,
    min_ratio: float = 0.25,
    min_area: float = 12.0,
) -> list[tuple[float, float]] | None:
    """Safely inset a CCW polygon ring inward."""
    n = len(ring)
    if n < 3:
        return None
    orig_area = signed_area_2d(ring)
    if orig_area < max(min_area * 1.5, inset_m * inset_m * 4.0):
        return None

    tangents: list[tuple[float, float]] = []
    normals: list[tuple[float, float]] = []
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        d = math.hypot(dx, dy)
        if d < 1e-4:
            return None
        tx, ty = dx / d, dy / d
        tangents.append((tx, ty))
        normals.append((-ty, tx))

    out: list[tuple[float, float]] = []
    for i in range(n):
        prev = (i - 1) % n
        t1x, t1y = tangents[prev]
        t2x, t2y = tangents[i]
        n1x, n1y = normals[prev]
        n2x, n2y = normals[i]
        px, py = ring[i]

        det = t1x * t2y - t1y * t2x
        if abs(det) < 0.08:
            mx, my = n1x + n2x, n1y + n2y
            ml = math.hypot(mx, my)
            if ml < 1e-6:
                return None
            ox, oy = px + (mx / ml) * inset_m, py + (my / ml) * inset_m
        else:
            p1x, p1y = px + n1x * inset_m, py + n1y * inset_m
            p2x, p2y = px + n2x * inset_m, py + n2y * inset_m
            dx, dy = p2x - p1x, p2y - p1y
            s = (dx * t2y - dy * t2x) / det
            ox, oy = p1x + s * t1x, p1y + s * t1y
            if math.hypot(ox - px, oy - py) > inset_m * 2.2:
                return None

        if not point_in_ring(ox, oy, ring):
            return None
        out.append((ox, oy))

    new_area = signed_area_2d(out)
    if new_area < max(min_area, orig_area * min_ratio):
        return None
    # Verify non-self-intersecting tessellation
    if not mathutils.geometry.tessellate_polygon([[mathutils.Vector((x, y, 0.0)) for x, y in out]]):
        return None
    return out


def clip_polygon_bbox(
    ring: list[tuple[float, float]],
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> list[tuple[float, float]]:
    """Clip a 2D polygon ring against an axis-aligned rectangle."""
    edges = [
        (lambda p: p[0] >= min_x, lambda a, b: (min_x, a[1] + (b[1] - a[1]) * (min_x - a[0]) / ((b[0] - a[0]) or 1e-12))),
        (lambda p: p[0] <= max_x, lambda a, b: (max_x, a[1] + (b[1] - a[1]) * (max_x - a[0]) / ((b[0] - a[0]) or 1e-12))),
        (lambda p: p[1] >= min_y, lambda a, b: (a[0] + (b[0] - a[0]) * (min_y - a[1]) / ((b[1] - a[1]) or 1e-12), min_y)),
        (lambda p: p[1] <= max_y, lambda a, b: (a[0] + (b[0] - a[0]) * (max_y - a[1]) / ((b[1] - a[1]) or 1e-12), max_y)),
    ]
    output = list(ring)
    for inside_fn, intersect_fn in edges:
        if not output:
            return []
        inp = output
        output = []
        prev = inp[-1]
        prev_in = inside_fn(prev)
        for curr in inp:
            curr_in = inside_fn(curr)
            if curr_in:
                if not prev_in:
                    output.append(intersect_fn(prev, curr))
                output.append(curr)
            elif prev_in:
                output.append(intersect_fn(prev, curr))
            prev = curr
            prev_in = curr_in
    return clean_ring_2d(output, min_edge_m=0.1, min_area_m2=1.0)


def _clip_segment_liang_barsky(
    a: tuple[float, float],
    b: tuple[float, float],
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    x0, y0 = a
    x1, y1 = b
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - min_x), (dx, max_x - x0), (-dy, y0 - min_y), (dy, max_y - y0)):
        if abs(p) < 1e-12:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return None
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return None
                if r < t1:
                    t1 = r
    return ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))


def clip_polyline_bbox(
    pts: list[tuple[float, float]],
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> list[list[tuple[float, float]]]:
    """Clip a 2D polyline against an axis-aligned rectangle."""
    chains: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for i in range(len(pts) - 1):
        clipped = _clip_segment_liang_barsky(pts[i], pts[i + 1], min_x, min_y, max_x, max_y)
        if clipped is None:
            if len(current) >= 2:
                chains.append(current)
            current = []
            continue
        p0, p1 = clipped
        if not current:
            current = [p0, p1]
        elif math.hypot(current[-1][0] - p0[0], current[-1][1] - p0[1]) < 0.05:
            if math.hypot(current[-1][0] - p1[0], current[-1][1] - p1[1]) >= 0.05:
                current.append(p1)
        else:
            if len(current) >= 2:
                chains.append(current)
            current = [p0, p1]
    if len(current) >= 2:
        chains.append(current)
    return chains


def geojson_polygon_rings_to_blender(geom: dict[str, Any]) -> list[list[list[tuple[float, float]]]]:
    """Extract GeoJSON Polygon or MultiPolygon rings converted to Blender XY meters."""
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    polys_raw = [coords] if gtype == "Polygon" else coords if gtype == "MultiPolygon" else []
    result: list[list[list[tuple[float, float]]]] = []
    for poly_rings in polys_raw:
        converted: list[list[tuple[float, float]]] = []
        for idx, ring in enumerate(poly_rings):
            xy_pts = [latlon_to_blender_xy(pt[1], pt[0]) for pt in ring]
            cleaned = clean_ring_2d(xy_pts)
            if not cleaned:
                if idx == 0:
                    converted = []
                    break
                continue
            area = signed_area_2d(cleaned)
            if idx == 0 and area < 0:
                cleaned.reverse()
            elif idx > 0 and area > 0:
                cleaned.reverse()
            converted.append(cleaned)
        if converted:
            result.append(converted)
    return result


def infer_building_category(name: str | None, subtype: str, tags: dict[str, Any]) -> str:
    """Infer semantic campus building category from OSM name and tags."""
    text = " ".join(
        str(v)
        for v in (name or "", subtype or "", tags.get("amenity", ""), tags.get("building", ""), tags.get("leisure", ""))
        if v
    ).lower()
    amenity = str(tags.get("amenity", "")).lower()

    if amenity in {"restaurant", "cafe", "fast_food", "food_court"} or any(
        kw in text for kw in ("canteen", "mess", "kitchen", "cafe", "dining", "bakery")
    ):
        return "food"
    if subtype in {"apartments", "residential", "dormitory"} or any(
        kw in text for kw in ("bhavanam", "hostel", "guest house", "quarters", "residence")
    ):
        return "hostel"
    if tags.get("leisure") in {"sports_centre", "fitness_centre", "stadium"} or any(
        kw in text for kw in ("gym", "sadhanam", "stadium", "sports", "pool")
    ):
        return "sports"
    if amenity in {"bank", "post_office", "townhall"} or any(
        kw in text for kw in ("bank", "corporate", "admin", "office", "registrar")
    ):
        return "admin"
    if amenity in {"library", "place_of_worship"} or any(
        kw in text for kw in ("shrine", "temple", "auditorium", "hall", "library", "prayer")
    ):
        return "landmark"
    if subtype in {"university", "school", "college"} or any(
        kw in text for kw in ("academic", "school", "block", "workshop", "research", "lab", "centre", "center")
    ):
        return "academic"
    return "default"


def create_mesh_object(name: str, bm: bmesh.types.BMesh, materials: list[bpy.types.Material]) -> bpy.types.Object:
    """Create a Blender Mesh and Object from a BMesh and link it to the active scene."""
    mesh = bpy.data.meshes.new(name=name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name=name, object_data=mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _set_face_color(face: bmesh.types.BMFace, col_layer: Any, rgba: tuple[float, float, float, float]) -> None:
    for loop in face.loops:
        loop[col_layer] = rgba


def _add_tri_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    verts: tuple[bmesh.types.BMVert, bmesh.types.BMVert, bmesh.types.BMVert],
    mat_idx: int,
    rgba: tuple[float, float, float, float],
) -> None:
    try:
        f = bm.faces.new(verts)
        f.smooth = False
        f.material_index = mat_idx
        _set_face_color(f, col_layer, rgba)
    except ValueError:
        pass


def _add_box_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    hx: float,
    hy: float,
    wall_rgba: tuple[float, float, float, float],
    cap_rgba: tuple[float, float, float, float],
    rot_rad: float = 0.0,
) -> None:
    """Emit a rotated architectural box (columns, stair towers, bleachers, AC units)."""
    ca, sa = math.cos(rot_rad), math.sin(rot_rad)
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    pts = [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in corners]
    b = [bm.verts.new((px, py, z0)) for px, py in pts]
    t = [bm.verts.new((px, py, z1)) for px, py in pts]
    for i in range(4):
        j = (i + 1) % 4
        _add_tri_vc(bm, col_layer, (b[i], b[j], t[j]), 0, wall_rgba)
        _add_tri_vc(bm, col_layer, (b[i], t[j], t[i]), 0, wall_rgba)
    _add_tri_vc(bm, col_layer, (t[0], t[1], t[2]), 0, cap_rgba)
    _add_tri_vc(bm, col_layer, (t[0], t[2], t[3]), 0, cap_rgba)


def _add_hipped_roof_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z_eave: float,
    z_peak: float,
    hx: float,
    hy: float,
    roof_rgba: tuple[float, float, float, float],
    gable_rgba: tuple[float, float, float, float] | None = None,
) -> None:
    """Emit a 4-sided pitched hipped terracotta roof (+ optional front south gable pediment)."""
    c = [
        bm.verts.new((cx - hx, cy - hy, z_eave)),
        bm.verts.new((cx + hx, cy - hy, z_eave)),
        bm.verts.new((cx + hx, cy + hy, z_eave)),
        bm.verts.new((cx - hx, cy + hy, z_eave)),
    ]
    ridge_half = max(0.5, hx * 0.45)
    r_left = bm.verts.new((cx - ridge_half, cy, z_peak))
    r_right = bm.verts.new((cx + ridge_half, cy, z_peak))

    _add_tri_vc(bm, col_layer, (c[0], c[1], r_right), 0, roof_rgba)
    _add_tri_vc(bm, col_layer, (c[0], r_right, r_left), 0, roof_rgba)
    _add_tri_vc(bm, col_layer, (c[1], c[2], r_right), 0, roof_rgba)
    _add_tri_vc(bm, col_layer, (c[2], c[3], r_left), 0, roof_rgba)
    _add_tri_vc(bm, col_layer, (c[2], r_left, r_right), 0, roof_rgba)
    _add_tri_vc(bm, col_layer, (c[3], c[0], r_left), 0, roof_rgba)

    if gable_rgba is not None:
        g_l = bm.verts.new((cx - 4.2, cy - hy - 0.15, z_eave + 0.1))
        g_r = bm.verts.new((cx + 4.2, cy - hy - 0.15, z_eave + 0.1))
        g_top = bm.verts.new((cx, cy - hy + 1.4, z_eave + 2.4))
        _add_tri_vc(bm, col_layer, (g_l, g_r, g_top), 0, gable_rgba)


def _add_cylinder_vc(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    r0: float,
    r1: float,
    segments: int,
    side_rgba: tuple[float, float, float, float],
    cap_rgba: tuple[float, float, float, float] | None = None,
) -> None:
    """Emit a tapered cylinder/column with clean outward normals."""
    b_ring: list[bmesh.types.BMVert] = []
    t_ring: list[bmesh.types.BMVert] = []
    for i in range(segments):
        ang = (2.0 * math.pi * i) / segments
        ca, sa = math.cos(ang), math.sin(ang)
        b_ring.append(bm.verts.new((cx + r0 * ca, cy + r0 * sa, z0)))
        t_ring.append(bm.verts.new((cx + r1 * ca, cy + r1 * sa, z1)))
    for i in range(segments):
        j = (i + 1) % segments
        _add_tri_vc(bm, col_layer, (b_ring[i], b_ring[j], t_ring[j]), 0, side_rgba)
        _add_tri_vc(bm, col_layer, (b_ring[i], t_ring[j], t_ring[i]), 0, side_rgba)
    if cap_rgba is not None and r1 > 0.05:
        center_top = bm.verts.new((cx, cy, z1))
        for i in range(segments):
            j = (i + 1) % segments
            _add_tri_vc(bm, col_layer, (t_ring[i], t_ring[j], center_top), 0, cap_rgba)


def build_terrain_object(
    terrain: TerrainSurface,
    green_features: list[dict[str, Any]],
    courtyard_polys: list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]],
    road_colliders: list[tuple[list[tuple[float, float]], float, float]],
    mat_ground: bpy.types.Material,
    mat_skirt: bpy.types.Material,
) -> tuple[bpy.types.Object, list[tuple[str, tuple[float, float, float, float], list[list[tuple[float, float]]]]]]:
    """Build Western Ghats mountain backdrop + lush tropical terrain with vertex colors."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")
    ny, nx = terrain.zs.shape

    c_campus = srgb_hex_to_linear_rgba(PALETTE["terrain_campus"])
    c_park = srgb_hex_to_linear_rgba(PALETTE["terrain_park"])
    c_emerald = srgb_hex_to_linear_rgba(PALETTE["terrain_emerald"])
    c_mtn_mid = srgb_hex_to_linear_rgba(PALETTE["terrain_mountain_mid"])
    c_mtn_peak = srgb_hex_to_linear_rgba(PALETTE["terrain_mountain_peak"])
    c_meadow = srgb_hex_to_linear_rgba(PALETTE["terrain_meadow"])
    c_earth = srgb_hex_to_linear_rgba(PALETTE["terrain_red_earth"])
    c_courtyard = srgb_hex_to_linear_rgba(PALETTE["terrain_courtyard"])
    c_skirt = srgb_hex_to_linear_rgba(PALETTE["terrain_skirt"])

    green_entries: list[tuple[str, tuple[float, float, float, float], list[list[tuple[float, float]]]]] = []
    priority_order = {"grass": 0, "park": 0, "garden": 0, "wood": 1, "forest": 1, "farmland": 2}
    for feat in green_features:
        subtype = str(feat["properties"].get("subtype", "grass"))
        if subtype == "tree_row":
            continue
        for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
            green_entries.append((subtype, bbox_of_ring(rings[0]), rings))
    green_entries.sort(key=lambda item: priority_order.get(item[0], 3))

    # Build quick footpath proximity list for subtle red-earth shoulders
    footpath_aabbs: list[tuple[float, float, float, float, list[tuple[float, float]]]] = []
    for pts, half_w, _ in road_colliders:
        if half_w <= 1.2:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            footpath_aabbs.append((min(xs) - 18.0, min(ys) - 18.0, max(xs) + 18.0, max(ys) + 18.0, pts))

    vert_colors: list[list[tuple[float, float, float, float]]] = []
    top_verts: list[list[bmesh.types.BMVert]] = []

    for r in range(ny):
        row_verts: list[bmesh.types.BMVert] = []
        row_cols: list[tuple[float, float, float, float]] = []
        y = float(terrain.ys[r])
        r0, r1 = max(0, r - 1), min(ny - 1, r + 1)
        dy_span = max(1e-3, float(terrain.ys[r1] - terrain.ys[r0]))

        for c in range(nx):
            x = float(terrain.xs[c])
            z = float(terrain.zs[r, c])
            row_verts.append(bm.verts.new((x, y, z)))

            c0, c1 = max(0, c - 1), min(nx - 1, c + 1)
            dx_span = max(1e-3, float(terrain.xs[c1] - terrain.xs[c0]))
            dzdx = (float(terrain.zs[r, c1]) - float(terrain.zs[r, c0])) / dx_span
            dzdy = (float(terrain.zs[r1, c]) - float(terrain.zs[r0, c])) / dy_span
            slope = math.hypot(dzdx, dzdy)

            cx = min(max(x, terrain.core_min_x), terrain.core_max_x)
            cy = min(max(y, terrain.core_min_y), terrain.core_max_y)
            dist_out = math.hypot(x - cx, y - cy)

            col = c_campus

            # Tropical hillside emerald & Bouluvampatty mountain ridge tones
            hill_t = max(smoothstep(0.055, 0.18, slope), smoothstep(9.0, 32.0, z))
            outer_t = smoothstep(0.0, 90.0, dist_out)
            col = mix_linear_rgba(col, c_emerald, 0.90 * max(hill_t, outer_t))
            col = mix_linear_rgba(col, c_mtn_mid, 0.92 * smoothstep(28.0, 95.0, z))
            col = mix_linear_rgba(col, c_mtn_peak, 0.90 * smoothstep(85.0, 290.0, z))

            # OSM landcover tints inside campus
            for subtype, (gx0, gy0, gx1, gy1), rings in green_entries:
                if gx0 <= x <= gx1 and gy0 <= y <= gy1 and point_in_polygon(x, y, rings):
                    if subtype in {"farmland", "meadow", "orchard"}:
                        col = mix_linear_rgba(col, c_meadow, 0.72)
                    elif subtype in {"wood", "forest", "scrub"}:
                        col = mix_linear_rgba(col, c_mtn_mid, 0.70)
                    else:
                        col = mix_linear_rgba(col, c_park, 0.80)
                    break

            # Subtle warm red-earth shoulders near campus footpaths
            if dist_out < 1.0 and slope < 0.14:
                min_fp_d2 = 9999.0
                for fx0, fy0, fx1, fy1, pts in footpath_aabbs:
                    if fx0 <= x <= fx1 and fy0 <= y <= fy1:
                        for i in range(len(pts) - 1):
                            d2 = dist_point_to_segment_sq(x, y, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
                            if d2 < min_fp_d2:
                                min_fp_d2 = d2
                if min_fp_d2 < 225.0:
                    fp_t = 0.28 * smoothstep(15.0, 2.0, math.sqrt(min_fp_d2))
                    col = mix_linear_rgba(col, c_earth, fp_t)

            # Warm sandstone courtyard plazas near academic & landmark blocks
            if dist_out < 1.0 and slope < 0.18:
                min_cd = 999.0
                for (bx0, by0, bx1, by1), rings in courtyard_polys:
                    if bx0 <= x <= bx1 and by0 <= y <= by1:
                        if point_in_polygon(x, y, rings):
                            min_cd = 0.0
                            break
                        d_edge = dist_point_to_polygon_edge(x, y, rings[0])
                        if d_edge < min_cd:
                            min_cd = d_edge
                if min_cd < 22.0:
                    stone_t = 0.75 * smoothstep(22.0, 4.0, min_cd) * (1.0 - smoothstep(0.09, 0.18, slope))
                    col = mix_linear_rgba(col, c_courtyard, stone_t)

            mod = 1.0 + 0.03 * math.sin(0.019 * x) * math.cos(0.015 * y)
            col = (
                min(1.0, max(0.0, col[0] * mod)),
                min(1.0, max(0.0, col[1] * mod)),
                min(1.0, max(0.0, col[2] * mod)),
                1.0,
            )
            row_cols.append(col)

        top_verts.append(row_verts)
        vert_colors.append(row_cols)

    for r in range(ny - 1):
        for c in range(nx - 1):
            v00, v10 = top_verts[r][c], top_verts[r][c + 1]
            v01, v11 = top_verts[r + 1][c], top_verts[r + 1][c + 1]
            c00, c10 = vert_colors[r][c], vert_colors[r][c + 1]
            c01, c11 = vert_colors[r + 1][c], vert_colors[r + 1][c + 1]

            f1 = bm.faces.new((v00, v10, v11))
            f1.smooth = True
            f1.material_index = 0
            f1.loops[0][col_layer] = c00
            f1.loops[1][col_layer] = c10
            f1.loops[2][col_layer] = c11

            f2 = bm.faces.new((v00, v11, v01))
            f2.smooth = True
            f2.material_index = 0
            f2.loops[0][col_layer] = c00
            f2.loops[1][col_layer] = c11
            f2.loops[2][col_layer] = c01

    _append_rise_patch(bm, col_layer, terrain, vert_colors)

    skirt_z = terrain.min_z - TERRAIN_SKIRT_DEPTH_M

    def _add_skirt_strip(top_edge: list[bmesh.types.BMVert]) -> None:
        bot_edge = [bm.verts.new((v.co.x, v.co.y, skirt_z)) for v in top_edge]
        for i in range(len(top_edge) - 1):
            t0, t1 = top_edge[i], top_edge[i + 1]
            b0, b1 = bot_edge[i], bot_edge[i + 1]
            for tri in ((b0, b1, t1), (b0, t1, t0)):
                f = bm.faces.new(tri)
                f.smooth = False
                f.material_index = 1
                _set_face_color(f, col_layer, c_skirt)

    south_edge = [top_verts[0][c] for c in range(nx)]
    east_edge = [top_verts[r][nx - 1] for r in range(ny)]
    north_edge = [top_verts[ny - 1][c] for c in range(nx - 1, -1, -1)]
    west_edge = [top_verts[r][0] for r in range(ny - 1, -1, -1)]
    for edge in (south_edge, east_edge, north_edge, west_edge):
        _add_skirt_strip(edge)

    bm.normal_update()
    return create_mesh_object("TERRAIN_Campus", bm, [mat_ground, mat_skirt]), green_entries


def _append_rise_patch(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    terrain: TerrainSurface,
    vert_colors: list[list[tuple[float, float, float, float]]],
) -> None:
    """Fine terrain sheet over the raised library ground (the base grid is too coarse for the slope)."""

    def _color_at(x: float, y: float) -> tuple[float, float, float, float]:
        c = min(max(int(np.searchsorted(terrain.xs, x, side="right")) - 1, 0), len(terrain.xs) - 2)
        r = min(max(int(np.searchsorted(terrain.ys, y, side="right")) - 1, 0), len(terrain.ys) - 2)
        fx = (x - terrain.xs[c]) / (terrain.xs[c + 1] - terrain.xs[c])
        fy = (y - terrain.ys[r]) / (terrain.ys[r + 1] - terrain.ys[r])
        mix = [
            (vert_colors[r][c][k] * (1 - fx) + vert_colors[r][c + 1][k] * fx) * (1 - fy)
            + (vert_colors[r + 1][c][k] * (1 - fx) + vert_colors[r + 1][c + 1][k] * fx) * fy
            for k in range(3)
        ]
        return (float(mix[0]), float(mix[1]), float(mix[2]), 1.0)

    us, vs = campus_frame.RISE_U_LINES, campus_frame.RISE_V_LINES
    verts: dict[tuple[int, int], tuple[bmesh.types.BMVert, tuple[float, float, float, float]]] = {}

    def _vert(i: int, j: int) -> tuple[bmesh.types.BMVert, tuple[float, float, float, float]]:
        if (i, j) not in verts:
            x, y = campus_frame.uv_to_xy(us[i], vs[j])
            verts[(i, j)] = (bm.verts.new((x, y, terrain.sample(x, y) + 0.02)), _color_at(x, y))
        return verts[(i, j)]

    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            corners = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
            if max(campus_frame.rise_offset_uv(us[a], vs[b]) for a, b in corners) <= 0.001:
                continue
            quad = [_vert(a, b) for a, b in corners]
            for tri in ((0, 1, 2), (0, 2, 3)):
                face = bm.faces.new(tuple(quad[k][0] for k in tri))
                face.smooth = True
                face.material_index = 0
                for loop, k in zip(face.loops, tri):
                    loop[col_layer] = quad[k][1]


def _densify_ring_2d(ring: list[tuple[float, float]], max_step_m: float) -> list[tuple[float, float]]:
    """Insert evenly spaced intermediate points on ring segments exceeding max_step_m."""
    n = len(ring)
    if n < 3 or max_step_m <= 0.1:
        return ring
    out: list[tuple[float, float]] = []
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        out.append((ax, ay))
        d = math.hypot(bx - ax, by - ay)
        if d > max_step_m:
            steps = int(math.ceil(d / max_step_m))
            for s in range(1, steps):
                t = s / steps
                out.append((ax + t * (bx - ax), ay + t * (by - ay)))
    return out


def _tessellate_polygon_to_bm(
    bm: bmesh.types.BMesh,
    rings: list[list[tuple[float, float]]],
    terrain: TerrainSurface,
    z_offset: float,
    mat_idx: int,
    max_edge_m: float = 10.0,
    col_layer: Any = None,
    rgba: tuple[float, float, float, float] | None = None,
    max_subdiv_iters: int = 4,
    clearance_margin: float = 0.08,
    densify_ring_m: float | None = None,
) -> None:
    """Subdivide, project, and terrain-clearance-lift a 2D polygon cleanly onto terrain inside bm."""
    work_rings = [_densify_ring_2d(r, densify_ring_m) for r in rings] if densify_ring_m else rings
    poly_vecs = [[mathutils.Vector((x, y, 0.0)) for x, y in r] for r in work_rings]
    tris = mathutils.geometry.tessellate_polygon(poly_vecs)
    if not tris:
        return
    flat_pts = [v for r in poly_vecs for v in r]
    sub_bm = bmesh.new()
    sub_verts = [sub_bm.verts.new((v.x, v.y, 0.0)) for v in flat_pts]
    for i0, i1, i2 in tris:
        if len({i0, i1, i2}) < 3:
            continue
        v0, v1, v2 = flat_pts[i0], flat_pts[i1], flat_pts[i2]
        cross_z = (v1.x - v0.x) * (v2.y - v0.y) - (v1.y - v0.y) * (v2.x - v0.x)
        if abs(cross_z) < 1e-6:
            continue
        order = (sub_verts[i0], sub_verts[i1], sub_verts[i2]) if cross_z > 0 else (sub_verts[i0], sub_verts[i2], sub_verts[i1])
        try:
            sub_bm.faces.new(order)
        except ValueError:
            pass
    if not sub_bm.faces:
        sub_bm.free()
        return

    for _ in range(max_subdiv_iters):
        long_edges = [e for e in sub_bm.edges if e.calc_length() > max_edge_m]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(sub_bm, edges=long_edges, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(sub_bm, faces=sub_bm.faces[:])

    for sv in sub_bm.verts:
        sv.co.z = terrain.sample(sv.co.x, sv.co.y) + z_offset

    # Two-pass triangle centroid & edge-midpoint clearance lift so ridges never poke through
    for _ in range(2):
        lifts: dict[bmesh.types.BMVert, float] = {}
        for sf in sub_bm.faces:
            if len(sf.verts) != 3:
                continue
            v0, v1, v2 = sf.verts[0], sf.verts[1], sf.verts[2]
            c0, c1, c2 = v0.co, v1.co, v2.co
            worst_deficit = 0.0
            for w0, w1, w2 in (
                (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
                (0.5, 0.5, 0.0),
                (0.0, 0.5, 0.5),
                (0.5, 0.0, 0.5),
            ):
                px = w0 * c0.x + w1 * c1.x + w2 * c2.x
                py = w0 * c0.y + w1 * c1.y + w2 * c2.y
                z_tri = w0 * c0.z + w1 * c1.z + w2 * c2.z
                z_req = terrain.sample(px, py) + clearance_margin + 0.02
                if z_tri < z_req:
                    worst_deficit = max(worst_deficit, z_req - z_tri)
            if worst_deficit > 0.0:
                for v in (v0, v1, v2):
                    if worst_deficit > lifts.get(v, 0.0):
                        lifts[v] = worst_deficit
        if not lifts:
            break
        for v, lift in lifts.items():
            v.co.z += lift

    vert_map: dict[bmesh.types.BMVert, bmesh.types.BMVert] = {}
    for sv in sub_bm.verts:
        vert_map[sv] = bm.verts.new((sv.co.x, sv.co.y, sv.co.z))
    for sf in sub_bm.faces:
        if len(sf.verts) != 3:
            continue
        mv = [vert_map[v] for v in sf.verts]
        p0, p1, p2 = mv[0].co, mv[1].co, mv[2].co
        if (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x) < 0:
            mv = [mv[0], mv[2], mv[1]]
        try:
            f = bm.faces.new(mv)
            f.smooth = False
            f.material_index = mat_idx
            if col_layer is not None and rgba is not None:
                _set_face_color(f, col_layer, rgba)
        except ValueError:
            pass
    sub_bm.free()


def _add_flat_terrace_slab(
    bm: bmesh.types.BMesh,
    rings: list[list[tuple[float, float]]],
    z_top: float,
    z_skirt_bottom: float,
    mat_top_idx: int,
    mat_side_idx: int,
    col_layer: Any = None,
    top_rgba: tuple[float, float, float, float] | None = None,
    side_rgba: tuple[float, float, float, float] | None = None,
) -> None:
    """Emit a strictly horizontal flat terraced slab with downward retaining wall skirt."""
    if not rings or len(rings[0]) < 3:
        return
    poly_vecs = [[mathutils.Vector((x, y, 0.0)) for x, y in r] for r in rings]
    tris = mathutils.geometry.tessellate_polygon(poly_vecs)
    if not tris:
        return

    flat_xy = [pt for r in rings for pt in r]
    top_verts = [bm.verts.new((x, y, z_top)) for x, y in flat_xy]

    for i0, i1, i2 in tris:
        if len({i0, i1, i2}) < 3:
            continue
        p0, p1, p2 = flat_xy[i0], flat_xy[i1], flat_xy[i2]
        cross_z = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
        if abs(cross_z) < 1e-6:
            continue
        order = (top_verts[i0], top_verts[i1], top_verts[i2]) if cross_z > 0 else (top_verts[i0], top_verts[i2], top_verts[i1])
        try:
            f = bm.faces.new(order)
            f.smooth = False
            f.material_index = mat_top_idx
            if col_layer is not None and top_rgba is not None:
                _set_face_color(f, col_layer, top_rgba)
        except ValueError:
            pass

    if z_top - z_skirt_bottom > 0.05:
        outer = list(rings[0])
        if signed_area_2d(outer) < 0:
            outer.reverse()
        n = len(outer)
        side_top = [bm.verts.new((x, y, z_top)) for x, y in outer]
        side_bot = [bm.verts.new((x, y, z_skirt_bottom)) for x, y in outer]
        for i in range(n):
            j = (i + 1) % n
            for face_verts in ((side_bot[i], side_bot[j], side_top[j]), (side_bot[i], side_top[j], side_top[i])):
                try:
                    f = bm.faces.new(face_verts)
                    f.smooth = False
                    f.material_index = mat_side_idx
                    if col_layer is not None and side_rgba is not None:
                        _set_face_color(f, col_layer, side_rgba)
                except ValueError:
                    pass


def _grid_sample_ring_elevations(
    ring: list[tuple[float, float]],
    terrain: TerrainSurface,
    steps: int = 7,
) -> tuple[float, float]:
    """Return (max_interior_z, min_edge_z) sampled across a polygon ring and its interior grid."""
    x0, y0, x1, y1 = bbox_of_ring(ring)
    edge_zs = [terrain.sample(px, py) for px, py in ring]
    all_zs = list(edge_zs)
    for ix in range(steps):
        fx = x0 + (x1 - x0) * (ix / max(1, steps - 1))
        for iy in range(steps):
            fy = y0 + (y1 - y0) * (iy / max(1, steps - 1))
            if point_in_ring(fx, fy, ring):
                all_zs.append(terrain.sample(fx, fy))
    return (max(all_zs), min(edge_zs))


def build_ground_features_object(
    water_features: list[dict[str, Any]],
    sports_features: list[dict[str, Any]],
    courtyard_lawns: list[list[tuple[float, float]]],
    terrain: TerrainSurface,
    palette_mats: dict[str, bpy.types.Material],
) -> tuple[bpy.types.Object | None, dict[str, float]]:
    """Merge water, level pool/playground/court terraces, plazas, and courtyard lawns into GROUND_Features."""
    bm = bmesh.new()
    materials = [
        palette_mats["water_pond"],      # 0
        palette_mats["pool_water"],      # 1
        palette_mats["pool_deck"],       # 2
        palette_mats["sports_pitch"],    # 3
        palette_mats["sports_court"],    # 4
        palette_mats["lawn_courtyard"],  # 5
        palette_mats["plaza_sandstone"], # 6
        palette_mats["retaining_wall"],  # 7
        palette_mats["plaza_charcoal"],  # 8
        palette_mats["plaza_ab1"],       # 9
    ]
    flat_pad_heights: dict[str, float] = {}

    min_x, max_x = terrain.core_min_x + 2.0, terrain.core_max_x - 2.0
    min_y, max_y = terrain.core_min_y + 2.0, terrain.core_max_y - 2.0

    # Locate Pool Deck & Pool Water up front so coping/water level locks cleanly above concrete deck
    z_pool_deck: float | None = None
    for feat in sports_features:
        if feat["id"] == HERO_POOL_DECK_ID:
            for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
                clipped = clip_polygon_bbox(rings[0], min_x, min_y, max_x, max_y)
                if clipped:
                    max_z, _ = _grid_sample_ring_elevations(clipped, terrain, steps=7)
                    z_pool_deck = max_z + 0.32
                    flat_pad_heights[HERO_POOL_DECK_ID] = z_pool_deck
                    break

    for feat in sports_features:
        fid = feat["id"]
        subtype = str(feat["properties"].get("subtype", ""))
        if fid == HERO_POOL_DECK_ID or subtype == "swimming":
            for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
                clipped_outer = clip_polygon_bbox(rings[0], min_x, min_y, max_x, max_y)
                if not clipped_outer:
                    continue
                if signed_area_2d(clipped_outer) < 0:
                    clipped_outer.reverse()
                max_z, min_edge_z = _grid_sample_ring_elevations(clipped_outer, terrain, steps=7)
                z_top = z_pool_deck if z_pool_deck is not None else max_z + 0.32
                flat_pad_heights[HERO_POOL_DECK_ID] = z_top
                _add_flat_terrace_slab(bm, [clipped_outer], z_top, min_edge_z - 3.0, 2, 7)
        elif fid == HERO_PLAYGROUND_ID:
            for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
                clipped_outer = clip_polygon_bbox(rings[0], min_x, min_y, max_x, max_y)
                if not clipped_outer:
                    continue
                if signed_area_2d(clipped_outer) < 0:
                    clipped_outer.reverse()
                max_z, min_edge_z = _grid_sample_ring_elevations(clipped_outer, terrain, steps=9)
                z_top = max_z + 0.26
                flat_pad_heights[HERO_PLAYGROUND_ID] = z_top
                # Dedicated geometry is emitted by modular hero `pipeline/heroes/main_ground.py`.
                break
        elif subtype in {"pitch", "soccer", "cricket", "football"}:
            for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
                clipped_outer = clip_polygon_bbox(rings[0], min_x, min_y, max_x, max_y)
                if not clipped_outer:
                    continue
                if signed_area_2d(clipped_outer) < 0:
                    clipped_outer.reverse()
                max_z, min_edge_z = _grid_sample_ring_elevations(clipped_outer, terrain, steps=5)
                _add_flat_terrace_slab(bm, [clipped_outer], max_z + 0.20, min_edge_z - 1.8, 3, 7)
        else:
            for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
                clipped_outer = clip_polygon_bbox(rings[0], min_x, min_y, max_x, max_y)
                if not clipped_outer:
                    continue
                if signed_area_2d(clipped_outer) < 0:
                    clipped_outer.reverse()
                max_z, min_edge_z = _grid_sample_ring_elevations(clipped_outer, terrain, steps=5)
                _add_flat_terrace_slab(bm, [clipped_outer], max_z + 0.22, min_edge_z - 1.8, 4, 7)

    for feat in water_features:
        fid = feat["id"]
        if fid in config.AB1_FRONT_WATER_SUPPRESS_IDS:
            continue
        is_pool = fid == HERO_POOL_WATER_ID
        for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
            clipped_outer = clip_polygon_bbox(rings[0], min_x, min_y, max_x, max_y)
            if not clipped_outer:
                continue
            if signed_area_2d(clipped_outer) < 0:
                clipped_outer.reverse()
            if is_pool:
                max_z, min_edge_z = _grid_sample_ring_elevations(clipped_outer, terrain, steps=5)
                base_deck = z_pool_deck if z_pool_deck is not None else max_z + 0.30
                z_water = base_deck + 0.08
                z_coping = base_deck + 0.14
                flat_pad_heights[HERO_POOL_WATER_ID] = z_water
                inner_water = inset_ccw_ring_2d(clipped_outer, 0.65, min_ratio=0.50, min_area=20.0)
                if inner_water is not None:
                    inner_cw = list(reversed(inner_water))
                    _add_flat_terrace_slab(bm, [clipped_outer, inner_cw], z_coping, base_deck - 0.10, 2, 2)
                    _add_flat_terrace_slab(bm, [inner_water], z_water, z_water - 0.04, 1, 2)
                else:
                    _add_flat_terrace_slab(bm, [clipped_outer], z_water, min_edge_z - 1.5, 1, 2)
            else:
                _tessellate_polygon_to_bm(
                    bm, [clipped_outer], terrain, 0.14, 0,
                    max_edge_m=9.0, max_subdiv_iters=4, clearance_margin=0.07,
                )

    # Carved courtyard lawns & AB-1 front plaza fountain discs
    for lawn_ring in courtyard_lawns:
        ccw = list(lawn_ring)
        if signed_area_2d(ccw) < 0:
            ccw.reverse()
        _tessellate_polygon_to_bm(
            bm, [ccw], terrain, 0.14, 5,
            max_edge_m=9.0, max_subdiv_iters=4, clearance_margin=0.07,
        )

    def _add_disc(cx: float, cy: float, radius: float, segs: int, z_off: float, mat_idx: int) -> None:
        ring = [(cx + radius * math.cos(2 * math.pi * i / segs), cy + radius * math.sin(2 * math.pi * i / segs)) for i in range(segs)]
        _tessellate_polygon_to_bm(
            bm, [ring], terrain, z_off, mat_idx,
            max_edge_m=9.0, max_subdiv_iters=4, clearance_margin=max(0.07, z_off - 0.02),
        )

    def _add_rect(cx: float, cy: float, hx: float, hy: float, rot_rad: float, z_off: float, mat_idx: int) -> None:
        ca, sa = math.cos(rot_rad), math.sin(rot_rad)
        corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        ring = [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in corners]
        _tessellate_polygon_to_bm(
            bm, [ring], terrain, z_off, mat_idx,
            max_edge_m=9.0, max_subdiv_iters=4, clearance_margin=0.07,
        )

    # Scalloped dark charcoal asphalt plaza in front of AB-1, the AB-2 statue plaza, AB-3 and library paving
    _tessellate_polygon_to_bm(
        bm,
        [ab1_hero.get_ab1_plaza_ring()],
        terrain,
        0.235,
        9,
        max_edge_m=7.5,
        max_subdiv_iters=4,
        clearance_margin=0.15,
    )
    _add_rect(*ab3_hero.ab3_forecourt_rect(), 0.14, 6)   # AB-3 east forecourt (porches + garden island)
    for ring, z_off, mat_idx in ab2_hero.ab2_ground_rings() + library_hero.library_ground_rings():
        _tessellate_polygon_to_bm(
            bm, [ring], terrain, z_off, mat_idx,
            max_edge_m=7.5, max_subdiv_iters=4, clearance_margin=0.1,
        )

    if not bm.faces:
        bm.free()
        return None, flat_pad_heights
    bm.normal_update()
    return create_mesh_object("GROUND_Features", bm, materials), flat_pad_heights


def build_hero_accents_object(
    raw_features: list[dict[str, Any]],
    terrain: TerrainSurface,
    mat_vertex_lit: bpy.types.Material,
    flat_pad_heights: dict[str, float] | None = None,
) -> bpy.types.Object:
    """Build Olympic pool lanes/pavilion, Playground bleachers/goals, AB-1 Lotus fountain, ASB planter & Main Gate."""
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")
    flat_pads = flat_pad_heights or {}

    c_white = srgb_hex_to_linear_rgba(PALETTE["hero_white"])

    def _add_ground_strip(
        cx: float,
        cy: float,
        length: float,
        width: float,
        angle_rad: float,
        z_off: float,
        rgba: tuple[float, float, float, float],
        segs: int = 1,
        fixed_z: float | None = None,
    ) -> None:
        ca, sa = math.cos(angle_rad), math.sin(angle_rad)
        hw = width * 0.5
        prev_l = prev_r = None
        for i in range(segs + 1):
            t = -0.5 * length + (length * i) / segs
            px = cx + t * ca
            py = cy + t * sa
            lx, ly = px - hw * sa, py + hw * ca
            rx, ry = px + hw * sa, py - hw * ca
            zl = fixed_z if fixed_z is not None else terrain.sample(lx, ly) + z_off
            zr = fixed_z if fixed_z is not None else terrain.sample(rx, ry) + z_off
            vl = bm.verts.new((lx, ly, zl))
            vr = bm.verts.new((rx, ry, zr))
            if prev_l is not None and prev_r is not None:
                _add_tri_vc(bm, col_layer, (prev_l, prev_r, vr), 0, rgba)
                _add_tri_vc(bm, col_layer, (prev_l, vr, vl), 0, rgba)
            prev_l, prev_r = vl, vr

    # 1. Olympic Swimming Pool lane markings + red wet deck apron, toddler pool, starting blocks & pavilion
    pool_feat = next((f for f in raw_features if f["id"] == HERO_POOL_WATER_ID), None)
    if pool_feat:
        pts = [latlon_to_blender_xy(p[1], p[0]) for p in pool_feat["geometry"]["coordinates"][0][:-1]]
        if len(pts) >= 4:
            edges = [(math.hypot(pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1]), i) for i in range(4)]
            edges.sort(reverse=True)
            i0 = edges[0][1]
            p0, p1 = pts[i0], pts[(i0 + 1) % 4]
            pcx, pcy = sum(p[0] for p in pts) / 4.0, sum(p[1] for p in pts) / 4.0
            long_len = edges[0][0] * 0.90
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            nx, ny = -math.sin(ang), math.cos(ang)
            pool_fixed_z = (
                flat_pad_heights[HERO_POOL_WATER_ID] + 0.04
                if HERO_POOL_WATER_ID in flat_pad_heights
                else None
            )
            for lane in range(-3, 4):
                off = lane * 2.85
                _add_ground_strip(
                    pcx + nx * off,
                    pcy + ny * off,
                    long_len,
                    0.28,
                    ang,
                    0.125,
                    c_white,
                    segs=3,
                    fixed_z=pool_fixed_z,
                )
            campus_landmarks.append_pool_complex_hero(
                bm=bm,
                col_layer=col_layer,
                terrain=terrain,
                pool_pts=pts,
                deck_flat_z=flat_pads.get(HERO_POOL_DECK_ID),
                water_flat_z=flat_pads.get(HERO_POOL_WATER_ID),
            )

    # 2. Main Sports Ground (Amrita Playground) is now built modularly by `pipeline/heroes/main_ground.py`.

    # 3. AB-1 Circular Lotus/Saraswati Fountain Roundabout & Forecourt Planters
    ab1_hero.append_ab1_fountain_plaza(bm, col_layer, terrain)
    ab1_hero.append_ab1_parking_lot(bm, col_layer, terrain)

    # 4. ASB Curved Stone-Masonry Driveway Planter Island
    asb_hero.append_asb_driveway_planter(bm, col_layer, terrain)

    # 5. Grand Amrita Entrance Gate Archway & Checkpoint are built modularly by `pipeline/heroes/main_gate.py`.

    # 6. AB-2 Nataraja fountain and the Central Library name board
    ab2_hero.append_nataraja_fountain(bm, col_layer, terrain)
    library_hero.append_library_sign(bm, col_layer, terrain)

    bm.normal_update()
    return create_mesh_object("STATIC_HeroAccents", bm, [mat_vertex_lit])


def build_roads_object(
    path_features: list[dict[str, Any]],
    overrides: dict[str, Any],
    campus_ctx: dict[str, Any] | None,
    terrain: TerrainSurface,
    mat_road_network: bpy.types.Material,
) -> tuple[bpy.types.Object | None, list[tuple[list[tuple[float, float]], float, float]]]:
    """Build seamless Shapely-merged campus asphalt roads + grounded Indian black/yellow curb dashes."""
    road_colliders: list[tuple[list[tuple[float, float]], float, float]] = []
    min_x, max_x = terrain.core_min_x + 2.0, terrain.core_max_x - 2.0
    min_y, max_y = terrain.core_min_y + 2.0, terrain.core_max_y - 2.0
    boundary_ring = (campus_ctx or {}).get("boundary_ring") or []
    rail_lines = (campus_ctx or {}).get("rail_lines") or []

    def _keep_campus_chain(pts_xy: list[tuple[float, float]]) -> list[tuple[float, float]] | None:
        kept: list[tuple[float, float]] = [
            pt
            for pt in pts_xy
            if terrain_utils.is_point_in_campus(
                pt[0],
                pt[1],
                boundary_ring,
                rail_lines,
                pad_m=14.0,
                rail_margin_m=-10.0,
            )
        ]
        return kept if len(kept) >= 2 else None

    excluded_ids = {str(x) for x in (overrides.get("exclude_ids") or [])}
    for feat in path_features:
        if str(feat.get("id", "")) in config.AB1_FRONT_SUPPRESS_IDS | excluded_ids:
            continue
        geom = feat["geometry"]
        if geom.get("type") != "LineString":
            continue
        subtype = str(feat["properties"].get("subtype", "path"))
        half_w, curb_w, _ = ROAD_SPECS.get(subtype, (1.1, 0.25, 0.085))
        raw_pts = [latlon_to_blender_xy(pt[1], pt[0]) for pt in config.path_coords(feat)]
        if len(raw_pts) < 2:
            continue
        for chain in clip_polyline_bbox(raw_pts, min_x, min_y, max_x, max_y):
            filtered = _keep_campus_chain(chain)
            if filtered is not None:
                road_colliders.append((filtered, half_w, curb_w))

    for custom_road in overrides.get("custom_roads") or []:
        if not isinstance(custom_road, dict) or custom_road.get("render") is False:
            continue
        raw_pts_ll = custom_road.get("points") or []
        if len(raw_pts_ll) < 2:
            continue
        subtype = str(custom_road.get("subtype", "residential"))
        half_w, curb_w, _ = ROAD_SPECS.get(subtype, (2.4, 0.40, 0.09))
        raw_pts = [latlon_to_blender_xy(float(pt[0]), float(pt[1])) for pt in raw_pts_ll]
        for chain in clip_polyline_bbox(raw_pts, min_x, min_y, max_x, max_y):
            if len(chain) >= 2:
                road_colliders.append((chain, half_w, curb_w))

    merged_data = json.loads(config.ROADS_MERGED_PATH.read_text(encoding="utf-8"))
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    c_asphalt = srgb_hex_to_linear_rgba(PALETTE["road_asphalt"])
    c_curb_black = srgb_hex_to_linear_rgba(PALETTE["curb_black"])
    c_curb_yellow = srgb_hex_to_linear_rgba(PALETTE["curb_yellow"])

    # 1. Unified junction-free asphalt surfaces from Shapely unary_union polygons
    for poly_rings_raw in merged_data.get("asphaltPolygons", []):
        rings = [[(float(p[0]), float(p[1])) for p in r] for r in poly_rings_raw if len(r) >= 3]
        if rings:
            _tessellate_polygon_to_bm(
                bm,
                rings,
                terrain,
                0.23,
                0,
                max_edge_m=9.5,
                col_layer=col_layer,
                rgba=c_asphalt,
                max_subdiv_iters=4,
                clearance_margin=0.14,
                densify_ring_m=9.5,
            )

    # 2. Alternating ~2.5m Indian black/yellow curb dashes + grounded outer curb skirts
    dash_len = 3.4
    curb_in_off = 0.0
    curb_out_off = 0.42
    curb_z_off = 0.265

    def _emit_curb_quad(
        p0: tuple[float, float],
        n0: tuple[float, float],
        p1: tuple[float, float],
        n1: tuple[float, float],
        rgba: tuple[float, float, float, float],
    ) -> None:
        ix0, iy0 = p0[0] + n0[0] * curb_in_off, p0[1] + n0[1] * curb_in_off
        ox0, oy0 = p0[0] + n0[0] * curb_out_off, p0[1] + n0[1] * curb_out_off
        ix1, iy1 = p1[0] + n1[0] * curb_in_off, p1[1] + n1[1] * curb_in_off
        ox1, oy1 = p1[0] + n1[0] * curb_out_off, p1[1] + n1[1] * curb_out_off

        z_i0 = terrain.sample(ix0, iy0) + curb_z_off
        z_o0 = terrain.sample(ox0, oy0) + curb_z_off
        z_i1 = terrain.sample(ix1, iy1) + curb_z_off
        z_o1 = terrain.sample(ox1, oy1) + curb_z_off

        vi0 = bm.verts.new((ix0, iy0, z_i0))
        vo0 = bm.verts.new((ox0, oy0, z_o0))
        vi1 = bm.verts.new((ix1, iy1, z_i1))
        vo1 = bm.verts.new((ox1, oy1, z_o1))

        cross1 = (ox0 - ix0) * (oy1 - iy0) - (oy0 - iy0) * (ox1 - ix0)
        t1 = (vi0, vo0, vo1) if cross1 >= 0 else (vi0, vo1, vo0)
        cross2 = (ox1 - ix0) * (iy1 - iy0) - (oy1 - iy0) * (ix1 - ix0)
        t2 = (vi0, vo1, vi1) if cross2 >= 0 else (vi0, vi1, vo1)
        _add_tri_vc(bm, col_layer, t1, 0, rgba)
        _add_tri_vc(bm, col_layer, t2, 0, rgba)

        # Grounded outer vertical curb face extending -0.14m below terrain
        vb0 = bm.verts.new((ox0, oy0, terrain.sample(ox0, oy0) - 0.14))
        vb1 = bm.verts.new((ox1, oy1, terrain.sample(ox1, oy1) - 0.14))
        skirt_rgba = (rgba[0] * 0.72, rgba[1] * 0.72, rgba[2] * 0.72, 1.0)
        dot_out = (oy1 - oy0) * (ox0 - ix0) - (ox1 - ox0) * (oy0 - iy0)
        if dot_out >= 0:
            _add_tri_vc(bm, col_layer, (vb0, vb1, vo1), 0, skirt_rgba)
            _add_tri_vc(bm, col_layer, (vb0, vo1, vo0), 0, skirt_rgba)
        else:
            _add_tri_vc(bm, col_layer, (vb0, vo1, vb1), 0, skirt_rgba)
            _add_tri_vc(bm, col_layer, (vb0, vo0, vo1), 0, skirt_rgba)

    for ring_entry in merged_data.get("curbRings", []):
        pts = [(float(p[0]), float(p[1])) for p in ring_entry.get("pts", [])]
        out_sign = int(ring_entry.get("outSign", 1))
        n = len(pts)
        if n < 3:
            continue

        # Precompute per-vertex miter-clamped outward normals so curb dashes join cleanly on curves
        vert_norms: list[tuple[float, float]] = []
        edge_norms: list[tuple[float, float]] = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            d = math.hypot(bx - ax, by - ay)
            if d > 1e-6:
                edge_norms.append(((by - ay) / d * out_sign, -(bx - ax) / d * out_sign))
            else:
                edge_norms.append((0.0, 1.0))
        for i in range(n):
            n_prev = edge_norms[(i - 1) % n]
            n_curr = edge_norms[i]
            mx, my = n_prev[0] + n_curr[0], n_prev[1] + n_curr[1]
            mlen = math.hypot(mx, my)
            if mlen > 1e-6:
                mx, my = mx / mlen, my / mlen
                dot = max(mx * n_curr[0] + my * n_curr[1], 0.55)
                scale = min(1.35, 1.0 / dot)
                vert_norms.append((mx * scale, my * scale))
            else:
                vert_norms.append(n_curr)

        dash_idx = 0
        rem = dash_len
        for i in range(n):
            p_start = pts[i]
            p_end = pts[(i + 1) % n]
            n_start = vert_norms[i]
            n_end = vert_norms[(i + 1) % n]
            seg_len = math.hypot(p_end[0] - p_start[0], p_end[1] - p_start[1])
            if seg_len < 0.05:
                continue

            covered = 0.0
            while covered < seg_len - 1e-4:
                step = min(rem, seg_len - covered)
                t0 = covered / seg_len
                t1 = (covered + step) / seg_len
                q0 = (p_start[0] + t0 * (p_end[0] - p_start[0]), p_start[1] + t0 * (p_end[1] - p_start[1]))
                q1 = (p_start[0] + t1 * (p_end[0] - p_start[0]), p_start[1] + t1 * (p_end[1] - p_start[1]))
                nq0 = (n_start[0] + t0 * (n_end[0] - n_start[0]), n_start[1] + t0 * (n_end[1] - n_start[1]))
                nq1 = (n_start[0] + t1 * (n_end[0] - n_start[0]), n_start[1] + t1 * (n_end[1] - n_start[1]))
                col_rgba = c_curb_black if (dash_idx % 2 == 0) else c_curb_yellow
                _emit_curb_quad(q0, nq0, q1, nq1, col_rgba)
                covered += step
                rem -= step
                if rem <= 1e-4:
                    dash_idx += 1
                    rem = dash_len

    if not bm.faces:
        bm.free()
        return None, road_colliders
    bm.normal_update()
    return create_mesh_object("ROADS_Network", bm, [mat_road_network]), road_colliders


def _resample_polyline_2d(pts: list[tuple[float, float]], step_m: float) -> list[tuple[float, float]]:
    """Resample a 2D polyline at approximately uniform step_m arc-length intervals."""
    if len(pts) < 2:
        return pts
    out: list[tuple[float, float]] = [pts[0]]
    carry = 0.0
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        seg_len = math.hypot(bx - ax, by - ay)
        if seg_len < 1e-4:
            continue
        dist = step_m - carry
        while dist <= seg_len + 1e-4:
            t = min(1.0, dist / seg_len)
            out.append((ax + t * (bx - ax), ay + t * (by - ay)))
            dist += step_m
        carry = seg_len - (dist - step_m)
    if math.hypot(out[-1][0] - pts[-1][0], out[-1][1] - pts[-1][1]) > 0.25:
        out.append(pts[-1])
    return out


def build_railway_object(
    rail_features: list[dict[str, Any]],
    rail_nodes: list[dict[str, Any]],
    terrain: TerrainSurface,
    mat_railway: bpy.types.Material,
) -> tuple[bpy.types.Object | None, list[list[tuple[float, float]]]]:
    """Build the double-track broad-gauge railway corridor, sleepers, twin rails & level crossings."""
    min_x, max_x = terrain.core_min_x + 4.0, terrain.core_max_x - 4.0
    min_y, max_y = terrain.core_min_y + 4.0, terrain.core_max_y - 4.0

    crossings: list[tuple[float, float]] = []
    for node_feat in rail_nodes:
        props = node_feat.get("properties", {})
        if props.get("subtype") != "level_crossing":
            continue
        coords = node_feat.get("geometry", {}).get("coordinates", [])
        if len(coords) >= 2:
            cx, cy = latlon_to_blender_xy(float(coords[1]), float(coords[0]))
            if min_x <= cx <= max_x and min_y <= cy <= max_y:
                crossings.append((cx, cy))

    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    c_ballast = srgb_hex_to_linear_rgba(PALETTE["rail_ballast"])
    c_ballast_slope = srgb_hex_to_linear_rgba(PALETTE["rail_ballast"], scale=0.84)
    c_sleeper = srgb_hex_to_linear_rgba(PALETTE["rail_sleeper"])
    c_steel = srgb_hex_to_linear_rgba(PALETTE["rail_steel"])
    c_crossing = srgb_hex_to_linear_rgba(PALETTE["rail_crossing"])

    clipped_rail_lines: list[list[tuple[float, float]]] = []
    track_tangents: list[tuple[float, float, float]] = []  # (x, y, angle_rad)

    def _emit_quad_oriented(
        a: bmesh.types.BMVert,
        b: bmesh.types.BMVert,
        c: bmesh.types.BMVert,
        d: bmesh.types.BMVert,
        ref_n: tuple[float, float, float],
        rgba: tuple[float, float, float, float],
    ) -> None:
        e1 = b.co - a.co
        e2 = c.co - a.co
        n_vec = e1.cross(e2)
        dot = n_vec.x * ref_n[0] + n_vec.y * ref_n[1] + n_vec.z * ref_n[2]
        if dot >= 0:
            _add_tri_vc(bm, col_layer, (a, b, c), 0, rgba)
            _add_tri_vc(bm, col_layer, (a, c, d), 0, rgba)
        else:
            _add_tri_vc(bm, col_layer, (a, c, b), 0, rgba)
            _add_tri_vc(bm, col_layer, (a, d, c), 0, rgba)

    for feat in rail_features:
        geom = feat.get("geometry", {})
        if geom.get("type") != "LineString":
            continue
        raw_pts = [latlon_to_blender_xy(float(pt[1]), float(pt[0])) for pt in geom.get("coordinates", [])]
        if len(raw_pts) < 2:
            continue
        for chain in clip_polyline_bbox(raw_pts, min_x, min_y, max_x, max_y):
            if len(chain) < 2:
                continue
            clipped_rail_lines.append(chain)
            pts = _resample_polyline_2d(chain, 3.8)
            m = len(pts)
            if m < 2:
                continue

            # Tangents and right normals (+right = (ty, -tx), +left = (-ty, tx))
            tangents: list[tuple[float, float]] = []
            for i in range(m):
                p_prev = pts[max(0, i - 1)]
                p_next = pts[min(m - 1, i + 1)]
                dx, dy = p_next[0] - p_prev[0], p_next[1] - p_prev[1]
                d = math.hypot(dx, dy)
                tx, ty = (dx / d, dy / d) if d > 1e-6 else (1.0, 0.0)
                tangents.append((tx, ty))
                track_tangents.append((pts[i][0], pts[i][1], math.atan2(ty, tx)))

            bal_lt: list[bmesh.types.BMVert] = []
            bal_rt: list[bmesh.types.BMVert] = []
            bal_ltoe: list[bmesh.types.BMVert] = []
            bal_rtoe: list[bmesh.types.BMVert] = []
            z_bals: list[float] = []

            for (cx, cy), (tx, ty) in zip(pts, tangents):
                nx, ny = ty, -tx
                z_bal = terrain.sample(cx, cy) + 0.22
                z_bals.append(z_bal)
                lx, ly = cx - nx * 1.7, cy - ny * 1.7
                rx, ry = cx + nx * 1.7, cy + ny * 1.7
                ltx, lty = cx - nx * 2.7, cy - ny * 2.7
                rtx, rty = cx + nx * 2.7, cy + ny * 2.7
                bal_lt.append(bm.verts.new((lx, ly, z_bal)))
                bal_rt.append(bm.verts.new((rx, ry, z_bal)))
                bal_ltoe.append(bm.verts.new((ltx, lty, terrain.sample(ltx, lty) - 1.2)))
                bal_rtoe.append(bm.verts.new((rtx, rty, terrain.sample(rtx, rty) - 1.2)))

            for i in range(m - 1):
                nx0, ny0 = tangents[i][1], -tangents[i][0]
                _emit_quad_oriented(bal_lt[i], bal_rt[i], bal_rt[i + 1], bal_lt[i + 1], (0.0, 0.0, 1.0), c_ballast)
                _emit_quad_oriented(bal_ltoe[i], bal_lt[i], bal_lt[i + 1], bal_ltoe[i + 1], (-nx0, -ny0, 0.5), c_ballast_slope)
                _emit_quad_oriented(bal_rt[i], bal_rtoe[i], bal_rtoe[i + 1], bal_rt[i + 1], (nx0, ny0, 0.5), c_ballast_slope)

            # Concrete sleepers along the track (skipped within 5m of level crossings)
            for i in range(m):
                cx, cy = pts[i]
                if any(math.hypot(cx - lcx, cy - lcy) < 5.0 for lcx, lcy in crossings):
                    continue
                ang = math.atan2(tangents[i][1], tangents[i][0])
                zb = z_bals[i]
                ca, sa = math.cos(ang), math.sin(ang)
                top = [
                    bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, zb + 0.08))
                    for lx, ly in ((-0.15, -1.2), (0.15, -1.2), (0.15, 1.2), (-0.15, 1.2))
                ]
                _add_tri_vc(bm, col_layer, (top[0], top[1], top[2]), 0, c_sleeper)
                _add_tri_vc(bm, col_layer, (top[0], top[2], top[3]), 0, c_sleeper)

            # Twin Indian Broad Gauge (1.676m -> +-0.84m) continuous steel rails
            for r_off in (-0.84, 0.84):
                r_lt: list[bmesh.types.BMVert] = []
                r_rt: list[bmesh.types.BMVert] = []
                r_lb: list[bmesh.types.BMVert] = []
                r_rb: list[bmesh.types.BMVert] = []
                for (cx, cy), (tx, ty), zb in zip(pts, tangents, z_bals):
                    nx, ny = ty, -tx
                    rcx, rcy = cx + nx * r_off, cy + ny * r_off
                    z_bot = zb + 0.08
                    z_top = zb + 0.18
                    r_lt.append(bm.verts.new((rcx - nx * 0.09, rcy - ny * 0.09, z_top)))
                    r_rt.append(bm.verts.new((rcx + nx * 0.09, rcy + ny * 0.09, z_top)))
                    r_lb.append(bm.verts.new((rcx - nx * 0.11, rcy - ny * 0.11, z_bot)))
                    r_rb.append(bm.verts.new((rcx + nx * 0.11, rcy + ny * 0.11, z_bot)))

                for i in range(m - 1):
                    nx0, ny0 = tangents[i][1], -tangents[i][0]
                    _emit_quad_oriented(r_lt[i], r_rt[i], r_rt[i + 1], r_lt[i + 1], (0.0, 0.0, 1.0), c_steel)
                    _emit_quad_oriented(r_lb[i], r_lt[i], r_lt[i + 1], r_lb[i + 1], (-nx0, -ny0, 0.1), c_steel)
                    _emit_quad_oriented(r_rt[i], r_rb[i], r_rb[i + 1], r_rt[i + 1], (nx0, ny0, 0.1), c_steel)

    # Concrete level-crossing plates at road-rail intersections
    for lcx, lcy in crossings:
        best_ang = 0.2
        best_d2 = float("inf")
        for tx_p, ty_p, tang in track_tangents:
            d2 = (tx_p - lcx) ** 2 + (ty_p - lcy) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_ang = tang
        z_lc = terrain.sample(lcx, lcy)
        _add_box_vc(bm, col_layer, lcx, lcy, z_lc - 0.8, z_lc + 0.27, 2.2, 4.6, c_crossing, c_crossing, rot_rad=best_ang)

    if not bm.faces:
        bm.free()
        return None, clipped_rail_lines
    bm.normal_update()
    return create_mesh_object("RAILWAY_Tracks", bm, [mat_railway]), clipped_rail_lines


def _parse_float_tag(raw: Any) -> float | None:
    """Parse a signed float from a numeric or unit-suffixed OSM tag value."""
    if raw is None:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(raw).strip())
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_osm_elevation_clearance(tags: dict[str, Any]) -> tuple[bool, float]:
    """Return (is_elevated, clearance_m_above_terrain) for OSM bridge/min_height/min_level/layer tags."""
    min_h = _parse_float_tag(tags.get("min_height"))
    if min_h is not None and min_h > 0.0:
        return (True, max(1.0, min_h))

    min_lvl = _parse_float_tag(tags.get("building:min_level"))
    if min_lvl is not None and min_lvl >= 1.0:
        return (True, max(1.0, min_lvl * FLOOR_HEIGHT_M))

    bridge_tag = str(tags.get("bridge", "")).strip().lower()
    if bridge_tag and bridge_tag not in {"no", "false", "0"}:
        return (True, 4.2)

    layer_val = _parse_float_tag(tags.get("layer"))
    if layer_val is not None and layer_val >= 1.0:
        return (True, max(4.2, layer_val * FLOOR_HEIGHT_M))

    return (False, 0.0)


def _compute_building_floors_and_height(category: str, area_m2: float, rec: dict[str, Any]) -> tuple[int, float]:
    """Compute synced (floors, height_m) honoring explicit overrides and OSM tags first."""
    if rec["floors"] is not None:
        f = max(1, int(round(float(rec["floors"]))))
        h = max(3.0, float(rec["height_m"])) if rec["height_m"] is not None else round(f * FLOOR_HEIGHT_M, 2)
        return f, h
    if rec["height_m"] is not None:
        h = max(3.0, float(rec["height_m"]))
        f = max(1, int(round(h / FLOOR_HEIGHT_M)))
        return f, h
    if rec["osm_levels"] is not None:
        f = max(1, int(round(float(rec["osm_levels"]))))
        h = max(3.0, float(rec["osm_height_m"])) if rec["osm_height_m"] is not None else round(f * FLOOR_HEIGHT_M, 2)
        return f, h
    if rec["osm_height_m"] is not None:
        h = max(3.0, float(rec["osm_height_m"]))
        f = max(1, int(round(h / FLOOR_HEIGHT_M)))
        return f, h

    fid = rec["id"]
    if fid == HERO_AB1_ID:
        return 4, round(4 * FLOOR_HEIGHT_M, 2)
    if fid == HERO_AB2_ID:
        return 4, round(4 * FLOOR_HEIGHT_M, 2)
    if fid == HERO_AB3_ID:
        return 4, round(4 * FLOOR_HEIGHT_M, 2)
    if fid == HERO_ASB_ID:
        return 4, round(4 * FLOOR_HEIGHT_M, 2)
    if fid == HERO_AMRITESHWARI_ID:
        return 4, round(4 * FLOOR_HEIGHT_M, 2)  # G+3 (aerial photo): mess on G, auditorium above
    if rec.get("overture_levels") is not None:
        f = min(8, max(1, int(round(float(rec["overture_levels"])))))
        h = (
            min(28.0, max(3.0, float(rec["overture_height_m"])))
            if rec.get("overture_height_m") is not None
            else round(f * FLOOR_HEIGHT_M, 2)
        )
        return f, round(h, 2)
    if rec.get("overture_height_m") is not None:
        h = min(28.0, max(3.0, float(rec["overture_height_m"])))
        f = min(8, max(1, int(round(h / FLOOR_HEIGHT_M))))
        return f, round(h, 2)

    if category == "academic":
        f = 4 if area_m2 >= 2200.0 else 3 if area_m2 >= 750.0 else 2
        return f, round(f * FLOOR_HEIGHT_M, 2)
    if category == "hostel":
        f = 5 if area_m2 >= 2600.0 else 4 if area_m2 >= 1500.0 else 3
        return f, round(f * FLOOR_HEIGHT_M, 2)
    if category == "landmark":
        f = 3 if area_m2 >= 500.0 else 1
        return f, round(f * FLOOR_HEIGHT_M, 2)
    if category == "admin":
        f = 3 if area_m2 >= 450.0 else 1
        return f, round(f * FLOOR_HEIGHT_M, 2)
    if category == "food":
        f = 2 if area_m2 >= 500.0 else 1
        return f, round(f * FLOOR_HEIGHT_M, 2)
    if category == "sports":
        f = 2 if area_m2 >= 450.0 else 1
        return f, round(f * FLOOR_HEIGHT_M, 2)
    f = 2 if area_m2 >= 200.0 else 1
    return f, round(f * FLOOR_HEIGHT_M, 2)


def _prepare_building_records(
    osm_buildings: list[dict[str, Any]],
    overrides: dict[str, Any],
    overture_data: dict[str, Any] | None = None,
) -> tuple[
    list[dict[str, Any]],
    set[str],
    dict[str, list[list[tuple[float, float]]]],
    dict[str, dict[str, Any]],
]:
    exclude_ids: set[str] = {str(x) for x in (overrides.get("exclude_ids") or [])}
    bridges_list: list[dict[str, Any]] = overrides.get("bridges") or []
    bridge_osm_ids: set[str] = set()
    for b in bridges_list:
        if isinstance(b, dict):
            if b.get("osm_id"):
                bridge_osm_ids.add(str(b["osm_id"]))
            elif b.get("id") and (
                str(b["id"]).startswith("way/")
                or str(b["id"]).startswith("relation/")
                or str(b["id"]).startswith("overture/")
            ):
                bridge_osm_ids.add(str(b["id"]))

    rename_map: dict[str, Any] = overrides.get("rename_or_retag", {}) or {}
    shift_map: dict[str, Any] = overrides.get("shift_footprints", {}) or {}
    custom_list: list[dict[str, Any]] = overrides.get("custom_buildings", []) or []
    override_ids: set[str] = set(rename_map.keys()) - exclude_ids - bridge_osm_ids

    osm_enrichments: dict[str, Any] = (overture_data or {}).get("osm_enrichments") or {}
    ov_new_buildings: list[dict[str, Any]] = (overture_data or {}).get("new_buildings") or []
    building_places: dict[str, list[dict[str, Any]]] = (overture_data or {}).get("building_places") or {}

    osm_rings_by_id: dict[str, list[list[tuple[float, float]]]] = {}
    raw_tags_by_id: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []

    for feat in osm_buildings:
        fid = str(feat["id"])
        props = feat["properties"]
        tags = dict(props.get("tags") or {})
        polys = geojson_polygon_rings_to_blender(feat["geometry"])
        if not polys:
            continue
        osm_rings_by_id[fid] = polys[0]
        raw_tags_by_id[fid] = tags
        if fid in exclude_ids or fid in bridge_osm_ids:
            continue

        raw_name = props.get("name")
        subtype = str(props.get("subtype", "yes"))
        category = infer_building_category(raw_name, subtype, tags)
        is_elevated, min_clearance_m = _parse_osm_elevation_clearance(tags)
        ov_enr = osm_enrichments.get(fid) or {}
        records.append(
            {
                "id": fid,
                "source": "osm",
                "rings": polys[0],
                "raw_name": raw_name,
                "subtitle": None,
                "subtype": subtype,
                "tags": tags,
                "category": category,
                "osm_levels": props.get("building_levels"),
                "osm_height_m": props.get("height_m"),
                "overture_levels": ov_enr.get("num_floors"),
                "overture_height_m": ov_enr.get("height_m"),
                "override_tags": [],
                "departments": [],
                "places": [],
                "auto_name_conf": 0.0,
                "floors": None,
                "height_m": None,
                "color": None,
                "is_elevated": is_elevated,
                "min_clearance_m": min_clearance_m,
            }
        )

    for feat in ov_new_buildings:
        props = feat.get("properties") or {}
        if not props.get("include_in_scene"):
            continue
        fid = str(feat.get("id") or "")
        if not fid:
            continue
        tags = dict(props.get("tags") or {})
        polys = geojson_polygon_rings_to_blender(feat["geometry"])
        if not polys:
            continue
        osm_rings_by_id[fid] = polys[0]
        raw_tags_by_id[fid] = tags
        if fid in exclude_ids or fid in bridge_osm_ids:
            continue

        raw_name = props.get("name")
        subtype = str(props.get("subtype", "yes"))
        category = infer_building_category(raw_name, subtype, tags)
        records.append(
            {
                "id": fid,
                "source": "overture",
                "rings": polys[0],
                "raw_name": raw_name,
                "subtitle": None,
                "subtype": subtype,
                "tags": tags,
                "category": category,
                "osm_levels": None,
                "osm_height_m": None,
                "overture_levels": props.get("building_levels"),
                "overture_height_m": props.get("height_m"),
                "override_tags": [],
                "departments": [],
                "places": [],
                "auto_name_conf": 1.0 if raw_name else 0.0,
                "floors": None,
                "height_m": None,
                "color": None,
                "is_elevated": False,
                "min_clearance_m": 0.0,
            }
        )

    for idx, custom in enumerate(custom_list):
        fid = str(custom.get("id") or f"custom/building_{idx + 1}")
        if fid in exclude_ids:
            continue
        footprint = custom.get("footprint") or []
        if len(footprint) < 3:
            continue
        xy_pts = [latlon_to_blender_xy(float(pt[0]), float(pt[1])) for pt in footprint]
        cleaned = clean_ring_2d(xy_pts)
        if not cleaned:
            continue
        if signed_area_2d(cleaned) < 0:
            cleaned.reverse()
        override_ids.add(fid)
        cat = str(custom.get("category") or "default").lower()
        if cat not in config.VALID_CATEGORIES and cat != "default":
            cat = "default"
        min_h = custom.get("min_height") if custom.get("min_height") is not None else custom.get("bottomY")
        is_elev = min_h is not None and float(min_h) > 0.0
        records.append(
            {
                "id": fid,
                "source": "custom",
                "rings": [cleaned],
                "raw_name": custom.get("name"),
                "subtitle": custom.get("subtitle"),
                "subtype": "custom",
                "tags": {},
                "category": cat,
                "osm_levels": None,
                "osm_height_m": None,
                "overture_levels": None,
                "overture_height_m": None,
                "override_tags": [str(t) for t in (custom.get("tags") or [])],
                "departments": [str(d) for d in (custom.get("departments") or [])],
                "places": [],
                "auto_name_conf": 1.0,
                "floors": custom.get("floors"),
                "height_m": custom.get("height_m"),
                "color": custom.get("color"),
                "roof_color": custom.get("roofColor"),
                "is_elevated": is_elev,
                "min_clearance_m": max(1.0, float(min_h)) if is_elev else 0.0,
            }
        )

    for rec in records:
        fid = rec["id"]
        ov = rename_map.get(fid)
        if isinstance(ov, dict):
            if ov.get("name"):
                rec["raw_name"] = str(ov["name"])
            if ov.get("subtitle") is not None:
                rec["subtitle"] = str(ov["subtitle"])
            if ov.get("category"):
                cat = str(ov["category"]).lower()
                rec["category"] = cat if cat in config.VALID_CATEGORIES or cat == "default" else "default"
            if ov.get("floors") is not None:
                rec["floors"] = ov["floors"]
            if ov.get("height_m") is not None:
                rec["height_m"] = ov["height_m"]
            min_h_ov = ov.get("min_height") if ov.get("min_height") is not None else ov.get("bottomY")
            if min_h_ov is not None:
                val_min = float(min_h_ov)
                rec["is_elevated"] = val_min > 0.0
                rec["min_clearance_m"] = max(1.0, val_min) if val_min > 0.0 else 0.0
            if ov.get("tags"):
                rec["override_tags"] = [str(t) for t in ov["tags"]]
            if ov.get("departments"):
                rec["departments"] = [str(d) for d in ov["departments"]]
            if ov.get("color"):
                rec["color"] = str(ov["color"])
        shift = shift_map.get(fid)
        if isinstance(shift, (list, tuple)) and len(shift) >= 2:
            dx_m, dz_m = float(shift[0]), float(shift[1])
            rec["rings"] = [[(x + dx_m, y - dz_m) for (x, y) in ring] for ring in rec["rings"]]

        if fid == HERO_AB3_ID and rec["rings"]:
            rec["rings"], _ = ab3_hero.normalize_ab3_footprint_rings(rec["rings"][0])
        elif fid == HERO_AB1_ID and len(rec["rings"]) == 1:
            rec["rings"], _ = ab1_hero.normalize_ab1_footprint_rings(rec["rings"][0])
        elif fid == HERO_AB2_ID:
            rec["rings"] = ab2_hero.normalize_ab2_footprint_rings()
        elif fid == HERO_AMRITESHWARI_ID:
            rec["rings"] = amriteshwari_hero.normalize_amriteshwari_rings()
        elif fid == HERO_LIBRARY_ID:
            rec["rings"] = library_hero.normalize_library_footprint_rings()
        elif fid == HERO_IT_CANTEEN_ID:
            rec["rings"] = it_canteen_hero.normalize_it_canteen_footprint_rings(rec["rings"][0])
        elif fid == HERO_NEW_HOSTEL_ID:
            rec["rings"] = new_hostel_hero.normalize_hostel_footprint_rings()
        elif fid == HERO_AB4_ID:
            rec["rings"] = ab4_hero.normalize_ab4_footprint_rings()
        elif fid == HERO_PANDAL_ID:
            rec["rings"] = pandal_hero.normalize_pandal_footprint_rings()
        elif fid == HERO_MBA_CANTEEN_ID:
            rec["rings"] = mba_canteen_hero.normalize_mba_canteen_footprint_rings()

        # Attach Overture Places metadata and search aliases
        snapped_places = building_places.get(fid) or []
        if snapped_places:
            current_name_norm = str(rec["raw_name"] or "").strip().lower()
            seen_place_names: set[str] = set()
            attached: list[dict[str, str]] = []
            for pl in snapped_places:
                pname = str(pl.get("name") or "").strip()
                if not pname or pl.get("is_generic_name"):
                    continue
                norm = pname.lower()
                if norm in seen_place_names:
                    continue
                seen_place_names.add(norm)
                if norm not in {t.lower() for t in rec["override_tags"]}:
                    rec["override_tags"].append(pname)
                if norm != current_name_norm:
                    p_entry: dict[str, str] = {
                        "name": pname,
                        "category": str(pl.get("category") or "default"),
                    }
                    if pl.get("raw_category"):
                        p_entry["rawCategory"] = str(pl["raw_category"])
                    attached.append(p_entry)
            rec["places"] = attached

            if not rec["raw_name"] and fid not in rename_map and rec["source"] != "custom":
                best_named_place = next(
                    (
                        pl
                        for pl in snapped_places
                        if not pl.get("is_generic_name")
                        and float(pl.get("dist_m", 99.0)) <= 15.0
                        and float(pl.get("confidence") or 0.0) >= 0.55
                    ),
                    None,
                )
                if best_named_place is not None:
                    rec["raw_name"] = str(best_named_place["name"]).strip()
                    rec["auto_name_conf"] = float(best_named_place.get("confidence") or 0.55)
                    p_cat = str(best_named_place.get("category") or "default")
                    if rec["category"] == "default" and p_cat != "default":
                        rec["category"] = p_cat

    return records, override_ids, osm_rings_by_id, raw_tags_by_id


def _emit_quad_strip_ring(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    bot_v: list[bmesh.types.BMVert],
    top_v: list[bmesh.types.BMVert],
    rgba: tuple[float, float, float, float],
) -> None:
    n = len(bot_v)
    for i in range(n):
        j = (i + 1) % n
        _add_tri_vc(bm, col_layer, (bot_v[i], bot_v[j], top_v[j]), 0, rgba)
        _add_tri_vc(bm, col_layer, (bot_v[i], top_v[j], top_v[i]), 0, rgba)


def _append_amrita_building(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh,
    win_dark_bm: bmesh.types.BMesh,
    fid: str,
    rings: list[list[tuple[float, float]]],
    offset_xyz: tuple[float, float, float],
    z_bottom: float,
    z_base_ref: float,
    z_top: float,
    floors: int,
    area_m2: float,
    category: str,
    terrain: TerrainSurface,
    wall_hex: str,
    roof_hex: str,
    is_elevated: bool = False,
) -> list[tuple[float, float, float]]:
    """Build Amrita architectural facade (spaced window bays, 60/40 night glass split, verandas, terracotta eaves)."""
    ox, oy, oz = offset_xyz
    outer_ring = rings[0]

    c_wall = srgb_hex_to_linear_rgba(wall_hex)
    c_plinth = (
        srgb_hex_to_linear_rgba(PALETTE["amh_band_orange"]) if fid == HERO_AMRITESHWARI_ID  # orange plinth (photo)
        else srgb_hex_to_linear_rgba(wall_hex, scale=0.83)
    )
    c_coping = srgb_hex_to_linear_rgba(PALETTE["parapet_coping"])
    c_roof = srgb_hex_to_linear_rgba(
        PALETTE["roof_ab1_concrete"] if fid == HERO_AB1_ID
        else PALETTE["roof_ab3_slab"] if fid == HERO_AB3_ID
        else PALETTE["roof_amh_slab"] if fid == HERO_AMRITESHWARI_ID
        else roof_hex
    )
    c_eave_tile = srgb_hex_to_linear_rgba(PALETTE["roof_terracotta"])
    c_ab1_cornice = srgb_hex_to_linear_rgba(PALETTE["ab1_cornice_trim"])
    trim_key = "trim_hostel" if category == "hostel" else "trim_ochre" if category in {"food", "admin"} else "trim_terracotta"
    if fid == HERO_AB3_ID:
        trim_key = "ab3_orange_trim"
    elif fid == HERO_AB1_ID:
        trim_key = "ab1_band_trim"
    elif fid == HERO_AMRITESHWARI_ID:
        trim_key = "amh_band_orange"
    c_trim = srgb_hex_to_linear_rgba(PALETTE[trim_key])
    c_recess = srgb_hex_to_linear_rgba(PALETTE["balcony_recess"])
    c_ab3_brick = srgb_hex_to_linear_rgba(PALETTE["ab3_accent_brick"])

    has_terracotta_eave = category in {"academic", "landmark", "food"} and fid not in (
        HERO_AB1_ID, HERO_AB3_ID, HERO_AMRITESHWARI_ID
    )
    z_base_vis = z_bottom if is_elevated else z_base_ref
    height_vis = max(2.0, z_top - z_base_vis)
    roof_rise = min(1.05, height_vis * 0.11) if has_terracotta_eave else min(0.38, height_vis * 0.08)
    z_eave = z_top - roof_rise
    z_plinth = z_bottom if is_elevated else min(z_base_vis + min(0.45, height_vis * 0.05), z_eave - 1.2)

    world_verts: list[tuple[float, float, float]] = []

    def _v(wx: float, wy: float, wz: float) -> bmesh.types.BMVert:
        world_verts.append((wx, wy, wz))
        return bm.verts.new((wx - ox, wy - oy, wz - oz))

    if fid == HERO_SHRINE_ID:
        # Custom sculpted South Indian/Kerala shrine directly over its stepped stone plinth
        campus_landmarks.append_shrine_hero(
            bm=bm,
            col_layer=col_layer,
            terrain=terrain,
            offset_xyz=offset_xyz,
            z_plinth=z_plinth,
            z_top=z_top,
        )
        cx_s, cy_s = ring_centroid_2d(outer_ring)
        world_verts.extend(
            [
                (cx_s - 8.6, cy_s - 5.1, z_bottom),
                (cx_s + 8.6, cy_s + 5.1, z_top + 4.95),
            ]
        )
        return world_verts

    if fid in (HERO_WORKSHOPS_WEST_ID, HERO_WORKSHOPS_EAST_ID):
        return workshops_hero.append_workshop_shed_compound(
            is_west=(fid == HERO_WORKSHOPS_WEST_ID),
            bm=bm,
            col_layer=col_layer,
            win_lit_bm=win_lit_bm,
            win_dark_bm=win_dark_bm,
            terrain=terrain,
            offset_xyz=offset_xyz,
        )

    if fid == HERO_MAIN_CANTEEN_ID:
        return campus_landmarks.append_octagonal_pavilion_hero(
            bm=bm,
            col_layer=col_layer,
            win_lit_bm=win_lit_bm,
            terrain=terrain,
            offset_xyz=offset_xyz,
            z_bottom=z_bottom,
            z_plinth=z_plinth,
            z_top=z_top,
        )

    # AB-2 and the Central Library are modelled wing by wing instead of extruding their outlines
    if fid == HERO_AB2_ID:
        return ab2_hero.build_ab2_complex(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz)
    if fid == HERO_LIBRARY_ID:
        return library_hero.build_central_library(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz)
    if fid == HERO_NEW_HOSTEL_ID:
        return new_hostel_hero.build_new_hostel(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz)
    if fid == HERO_AB4_ID:
        return ab4_hero.build_ab4(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz)
    if fid == HERO_PANDAL_ID:
        return pandal_hero.build_pandal(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz)
    if fid == HERO_MBA_CANTEEN_ID:
        return mba_canteen_hero.build_mba_canteen(bm, col_layer, win_lit_bm, win_dark_bm, terrain, offset_xyz)
    if fid == HERO_IT_CANTEEN_ID:
        return it_canteen_hero.build_it_canteen(
            bm, col_layer, win_lit_bm, win_dark_bm, rings[0], terrain, offset_xyz,
        )

    # Determine safe inward ring for sloped terracotta roof eaves (try wide inset, fallback for narrow bridges)
    roof_in_ring = inset_ccw_ring_2d(
        outer_ring,
        1.15 if (has_terracotta_eave and not is_elevated) else 0.50,
        min_ratio=0.14,
        min_area=6.0,
    )
    if roof_in_ring is None and has_terracotta_eave:
        roof_in_ring = inset_ccw_ring_2d(outer_ring, 0.42, min_ratio=0.10, min_area=3.5)
    if roof_in_ring is not None and len(rings) > 1:
        if any(point_in_ring(vx, vy, hole_ring) for hole_ring in rings[1:] for vx, vy in roof_in_ring):
            roof_in_ring = None

    roof_flat_verts: list[bmesh.types.BMVert] = []
    roof_flat_world: list[tuple[float, float]] = []
    soffit_flat_verts: list[bmesh.types.BMVert] = []
    soffit_flat_world: list[tuple[float, float]] = []

    vis_floors = max(1, int(floors))
    facade_h = max(1.0, z_eave - z_plinth)
    step_h = facade_h / vis_floors
    trim_h = min(0.28, step_h * 0.12)
    b_seed = sum((idx + 3) * ord(ch) for idx, ch in enumerate(fid))

    for r_idx, ring in enumerate(rings):
        n = len(ring)
        bot_v = [_v(x, y, z_bottom) for x, y in ring]
        if is_elevated:
            prev_v = bot_v
            soffit_flat_verts.extend(bot_v)
            soffit_flat_world.extend(ring)
        else:
            pli_v = [_v(x, y, z_plinth) for x, y in ring]
            _emit_quad_strip_ring(bm, col_layer, bot_v, pli_v, c_plinth)
            prev_v = pli_v

        # Emit strictly vis_floors horizontal facade bands + terracotta/ochre stringcourses
        for fl in range(vis_floors):
            zf_trim0 = z_plinth + (fl + 1) * step_h - trim_h
            zf_top = z_plinth + (fl + 1) * step_h
            if zf_trim0 > z_plinth + fl * step_h + 0.35:
                v_mid = [_v(x, y, zf_trim0) for x, y in ring]
                _emit_quad_strip_ring(bm, col_layer, prev_v, v_mid, c_wall)
                v_top_fl = [_v(x, y, zf_top) for x, y in ring]
                fl_trim_col = (
                    c_ab1_cornice
                    if (fid == HERO_AB1_ID and fl == vis_floors - 1)
                    else c_coping if fl == vis_floors - 1 else c_trim
                )
                _emit_quad_strip_ring(bm, col_layer, v_mid, v_top_fl, fl_trim_col)
                prev_v = v_top_fl
            else:
                v_top_fl = [_v(x, y, zf_top) for x, y in ring]
                _emit_quad_strip_ring(bm, col_layer, prev_v, v_top_fl, c_wall)
                prev_v = v_top_fl

        eave_v = prev_v

        if r_idx == 0 and roof_in_ring is not None:
            top_in_v = [_v(x, y, z_top) for x, y in roof_in_ring]
            # Sloped terracotta Mangalore-tile eave skirt (or terracotta/coping rim on flat parapet roofs)
            eave_rgba = (
                c_eave_tile if has_terracotta_eave
                else c_ab1_cornice if fid == HERO_AB1_ID
                else c_trim if fid == HERO_AB3_ID
                else c_coping
            )
            _emit_quad_strip_ring(bm, col_layer, eave_v, top_in_v, eave_rgba)
            roof_flat_verts.extend(top_in_v)
            roof_flat_world.extend(roof_in_ring)
        elif fid == HERO_AB1_ID:
            top_ring_v = [_v(x, y, z_top) for x, y in ring]
            _emit_quad_strip_ring(bm, col_layer, eave_v, top_ring_v, c_ab1_cornice)
            roof_flat_verts.extend(top_ring_v)
            roof_flat_world.extend(ring)
        else:
            roof_flat_verts.extend(eave_v)
            roof_flat_world.extend(ring)

        # Emit individually spaced window bays & shaded veranda openings separated by solid stucco piers
        if facade_h >= 1.2:
            is_courtyard = r_idx > 0
            if is_courtyard:
                pitch, bay_w, bay_ratio = 4.2, 2.7, 0.56
            elif category == "hostel":
                pitch, bay_w, bay_ratio = 4.4, 2.35, 0.50
            elif is_elevated:
                pitch, bay_w, bay_ratio = 3.8, 2.1, 0.48
            elif fid in (HERO_AB1_ID, HERO_AMRITESHWARI_ID):
                # AB-1 front photo / Amriteshwari aerial: narrow ~1.35 m punched windows at ~3.3 m centres, no hoods
                pitch, bay_w, bay_ratio = 3.3, 1.35, 0.42
            else:
                pitch, bay_w, bay_ratio = 4.4, 2.2, 0.48

            band_h = min(1.30, step_h * bay_ratio)
            for i in range(n):
                j = (i + 1) % n
                ax, ay = ring[i]
                bx, by = ring[j]
                edge_len = math.hypot(bx - ax, by - ay)
                if edge_len < 4.0:
                    continue
                if fid == HERO_AMRITESHWARI_ID and max(ax, bx) < amriteshwari_hero.AMH_X0 + 0.5:
                    continue  # West front: custom open hall / glass ribbon in amriteshwari_hero
                tx, ty = (bx - ax) / edge_len, (by - ay) / edge_len
                nx, ny = ty, -tx  # Outward normal
                usable = edge_len - 1.4
                num_bays = max(1, int(usable // pitch) + (1 if (usable >= bay_w + 0.5 and usable < pitch) else 0))
                span = (num_bays - 1) * pitch
                start_d = 0.5 * edge_len - 0.5 * span
                edge_ground = max(terrain.sample(ax, ay), terrain.sample(bx, by))

                for fl in range(vis_floors):
                    wz0 = z_plinth + fl * step_h + step_h * 0.24
                    wz1 = wz0 + band_h
                    if not is_elevated:
                        wz0 = max(wz0, edge_ground + 0.08)
                    if wz1 - wz0 < 0.25 or wz1 > z_eave - 0.12:
                        continue

                    for b_i in range(num_bays):
                        cx_bay = start_d + b_i * pitch
                        d0 = cx_bay - 0.5 * bay_w
                        d1 = cx_bay + 0.5 * bay_w
                        x0, y0 = ax + tx * d0 + nx * 0.065, ay + ty * d0 + ny * 0.065
                        x1, y1 = ax + tx * d1 + nx * 0.065, ay + ty * d1 + ny * 0.065

                        if (category == "hostel" or is_courtyard) and not is_elevated:
                            rx0, ry0 = ax + tx * d0 + nx * 0.032, ay + ty * d0 + ny * 0.032
                            rx1, ry1 = ax + tx * d1 + nx * 0.032, ay + ty * d1 + ny * 0.032
                            rv0 = _v(rx0, ry0, wz1 - 0.14)
                            rv1 = _v(rx1, ry1, wz1 - 0.14)
                            rv2 = _v(rx1, ry1, wz1 + 0.10)
                            rv3 = _v(rx0, ry0, wz1 + 0.10)
                            _add_tri_vc(bm, col_layer, (rv0, rv1, rv2), 0, c_recess)
                            _add_tri_vc(bm, col_layer, (rv0, rv2, rv3), 0, c_recess)

                        target_win_bm = win_lit_bm if ((b_seed + fl * 37 + b_i * 19 + i * 11) % 10) < 6 else win_dark_bm
                        wa0 = target_win_bm.verts.new((x0, y0, wz0))
                        wb0 = target_win_bm.verts.new((x1, y1, wz0))
                        wb1 = target_win_bm.verts.new((x1, y1, wz1))
                        wa1 = target_win_bm.verts.new((x0, y0, wz1))
                        try:
                            target_win_bm.faces.new((wa0, wb0, wb1)).smooth = False
                            target_win_bm.faces.new((wa0, wb1, wa1)).smooth = False
                        except ValueError:
                            pass

    # Tessellate roof cap (upward normal)
    roof_vecs = [
        [mathutils.Vector((x, y, 0.0)) for x, y in (roof_in_ring if (i == 0 and roof_in_ring is not None) else r)]
        for i, r in enumerate(rings)
    ]
    roof_tris = mathutils.geometry.tessellate_polygon(roof_vecs)
    for i0, i1, i2 in roof_tris:
        if len({i0, i1, i2}) < 3:
            continue
        p0, p1, p2 = roof_flat_world[i0], roof_flat_world[i1], roof_flat_world[i2]
        cross_z = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
        if abs(cross_z) < 1e-6:
            continue
        order = (
            (roof_flat_verts[i0], roof_flat_verts[i1], roof_flat_verts[i2])
            if cross_z > 0
            else (roof_flat_verts[i0], roof_flat_verts[i2], roof_flat_verts[i1])
        )
        _add_tri_vc(bm, col_layer, order, 0, c_roof)

    # Tessellate underside soffit cap (downward normal) for elevated skybridges & cantilevered blocks
    if is_elevated and soffit_flat_verts:
        soffit_vecs = [[mathutils.Vector((x, y, 0.0)) for x, y in r] for r in rings]
        soffit_tris = mathutils.geometry.tessellate_polygon(soffit_vecs)
        for i0, i1, i2 in soffit_tris:
            if len({i0, i1, i2}) < 3:
                continue
            p0, p1, p2 = soffit_flat_world[i0], soffit_flat_world[i1], soffit_flat_world[i2]
            cross_z = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
            if abs(cross_z) < 1e-6:
                continue
            order = (
                (soffit_flat_verts[i0], soffit_flat_verts[i1], soffit_flat_verts[i2])
                if cross_z < 0
                else (soffit_flat_verts[i0], soffit_flat_verts[i2], soffit_flat_verts[i1])
            )
            _add_tri_vc(bm, col_layer, order, 0, c_plinth)

    # Rooftop stairwells / HVAC penthouses on large grounded blocks
    if (
        not is_elevated and area_m2 >= 600.0 and height_vis >= 9.0 and len(rings) == 1 and roof_in_ring is not None
        and fid != HERO_AMRITESHWARI_ID
    ):
        rcx, rcy = ring_centroid_2d(roof_in_ring)
        if all(
            point_in_ring(rcx + dx, rcy + dy, roof_in_ring)
            for dx, dy in ((-2.4, -2.0), (2.4, -2.0), (2.4, 2.0), (-2.4, 2.0))
        ):
            _add_box_vc(bm, col_layer, rcx - ox, rcy - oy, z_top - oz, z_top - oz + 1.8, 2.2, 1.8, c_wall, c_roof)

    # Hero architectural landmark details (modular Blender builders under pipeline/hero_models/)
    if fid == HERO_AB1_ID:
        ab1_hero.append_ab1_hero_details(
            bm=bm, col_layer=col_layer, win_lit_bm=win_lit_bm, win_dark_bm=win_dark_bm,
            terrain=terrain, offset_xyz=offset_xyz, z_plinth=z_plinth, z_eave=z_eave, z_top=z_top,
        )

    elif fid == HERO_AB3_ID:
        ab3_hero.append_ab3_hero_details(
            bm=bm, col_layer=col_layer, win_lit_bm=win_lit_bm, win_dark_bm=win_dark_bm,
            terrain=terrain, offset_xyz=offset_xyz, z_plinth=z_plinth, z_eave=z_eave, z_top=z_top,
        )

    elif fid == HERO_ASB_ID:
        asb_hero.append_asb_hero_details(
            bm=bm, col_layer=col_layer, win_lit_bm=win_lit_bm,
            terrain=terrain, offset_xyz=offset_xyz, z_plinth=z_plinth, z_eave=z_eave, z_top=z_top,
        )

    elif fid == HERO_AMRITESHWARI_ID:
        amriteshwari_hero.append_amriteshwari_hero_details(
            bm=bm, col_layer=col_layer, win_lit_bm=win_lit_bm,
            terrain=terrain, offset_xyz=offset_xyz, z_plinth=z_plinth, z_eave=z_eave, z_top=z_top,
        )

    return world_verts


def _footprint_meta_fields(outer_ring: list[tuple[float, float]]) -> tuple[list[float], list[list[float]]]:
    bx0, by0, bx1, by1 = bbox_of_ring(outer_ring)
    bounds_xz = [round(bx0, 1), round(-by1, 1), round(bx1, 1), round(-by0, 1)]
    footprint_xz = [[round(x, 1), round(-y, 1)] for (x, y) in outer_ring]
    return bounds_xz, footprint_xz


def _build_elevated_bridges(
    bridges_cfg: list[dict[str, Any]],
    osm_rings_by_id: dict[str, list[list[tuple[float, float]]]],
    raw_tags_by_id: dict[str, dict[str, Any]],
    terrain: TerrainSurface,
    mat_body: bpy.types.Material,
    win_lit_bm: bmesh.types.BMesh,
    win_dark_bm: bmesh.types.BMesh,
    used_mesh_names: set[str],
) -> list[dict[str, Any]]:
    """Build enclosed elevated skybridges floating cleanly above roads/terrain."""
    bridge_inspectables: list[dict[str, Any]] = []

    for idx, br in enumerate(bridges_cfg):
        if not isinstance(br, dict):
            continue
        bid = str(br.get("id") or br.get("osm_id") or f"bridge/skybridge_{idx + 1}")
        osm_ref = str(br.get("osm_id")) if br.get("osm_id") else (bid if bid in osm_rings_by_id else "")

        rings: list[list[tuple[float, float]]] = []
        raw_tags: dict[str, str] = {}
        sample_pts: list[tuple[float, float]] = []

        if osm_ref and osm_ref in osm_rings_by_id:
            rings = osm_rings_by_id[osm_ref]
            raw_tags = {str(k): str(v) for k, v in raw_tags_by_id.get(osm_ref, {}).items()}
            sample_pts = list(rings[0])
        elif isinstance(br.get("from"), (list, tuple)) and isinstance(br.get("to"), (list, tuple)):
            frm = br["from"]
            to = br["to"]
            if len(frm) < 2 or len(to) < 2:
                continue
            ax, ay = latlon_to_blender_xy(float(frm[0]), float(frm[1]))
            bx, by = latlon_to_blender_xy(float(to[0]), float(to[1]))
            seg_len = math.hypot(bx - ax, by - ay)
            if seg_len < 1.0:
                continue
            tx, ty = (bx - ax) / seg_len, (by - ay) / seg_len
            nx, ny = -ty, tx
            half_w = 0.5 * max(1.5, float(br.get("width", 3.5)))
            rect = [
                (ax - nx * half_w, ay - ny * half_w),
                (bx - nx * half_w, by - ny * half_w),
                (bx + nx * half_w, by + ny * half_w),
                (ax + nx * half_w, ay + ny * half_w),
            ]
            if signed_area_2d(rect) < 0:
                rect.reverse()
            rings = [rect]
            raw_tags = {"bridge": "yes", "layer": "1"}
            sample_pts = rect + [(ax, ay), (bx, by), (0.5 * (ax + bx), 0.5 * (ay + by))]
        else:
            continue

        outer_ring = rings[0]
        cx_b, cy_b = ring_centroid_2d(outer_ring)
        sample_pts.append((cx_b, cy_b))
        z_ground = max(terrain.sample(px, py) for px, py in sample_pts)
        clearance_m = max(1.0, float(br.get("bottomY", br.get("min_height", 4.2))))
        bridge_h = max(1.8, float(br.get("height", 3.2)))
        z_bottom = z_ground + clearance_m
        z_top = z_bottom + bridge_h
        cz_b = 0.5 * (z_bottom + z_top)

        wall_hex = str(br.get("color") or PALETTE["wall_academic"])
        roof_hex = str(br.get("roofColor") or PALETTE["roof_terracotta"])

        bm = bmesh.new()
        col_layer = bm.loops.layers.color.new("Color")
        if bid == HERO_AB2_SKYBRIDGE_ID and isinstance(br.get("from"), (list, tuple)) and isinstance(br.get("to"), (list, tuple)):
            ax, ay = latlon_to_blender_xy(float(br["from"][0]), float(br["from"][1]))
            bx, by = latlon_to_blender_xy(float(br["to"][0]), float(br["to"][1]))
            world_verts = ab2_hero.build_ab2_skybridge_hero(
                bm=bm,
                col_layer=col_layer,
                win_lit_bm=win_lit_bm,
                ax=ax,
                ay=ay,
                bx=bx,
                by=by,
                terrain=terrain,
                z_bottom=z_bottom,
                z_top=z_top,
                bridge_width=float(br.get("width", 4.0)),
                offset_xyz=(cx_b, cy_b, cz_b),
            )
        else:
            world_verts = _append_amrita_building(
                bm=bm,
                col_layer=col_layer,
                win_lit_bm=win_lit_bm,
                win_dark_bm=win_dark_bm,
                fid=bid,
                rings=rings,
                offset_xyz=(cx_b, cy_b, cz_b),
                z_bottom=z_bottom,
                z_base_ref=z_bottom,
                z_top=z_top,
                floors=1,
                area_m2=abs(signed_area_2d(outer_ring)),
                category="academic",
                terrain=terrain,
                wall_hex=wall_hex,
                roof_hex=roof_hex,
                is_elevated=True,
            )
        if not bm.faces:
            bm.free()
            continue
        bm.normal_update()

        sanitized = re.sub(r"[^A-Za-z0-9_]+", "_", bid).strip("_")
        mesh_name = f"BRIDGE_{sanitized}"
        if mesh_name in used_mesh_names:
            mesh_name = f"{mesh_name}_{len(used_mesh_names)}"
        used_mesh_names.add(mesh_name)

        obj = create_mesh_object(mesh_name, bm, [mat_body])
        obj.location = (cx_b, cy_b, cz_b)

        bounds_xz, footprint_xz = _footprint_meta_fields(outer_ring)
        lat_lon = list(config.local_xz_to_latlon(cx_b, -cy_b))
        bridge_inspectables.append(
            {
                "id": bid,
                "meshName": mesh_name,
                "kind": "bridge",
                "name": str(br.get("name") or f"Campus Skybridge ({bid})"),
                "subtitle": "Elevated covered skybridge",
                "isNamed": True,
                "category": "academic",
                "floors": 1,
                "heightM": round(float(bridge_h), 2),
                "center": blender_to_gltf_xyz(cx_b, cy_b, cz_b),
                "latLon": lat_lon,
                "boundsXZ": bounds_xz,
                "footprintXZ": footprint_xz,
                "rawTags": raw_tags,
                "tags": ["skybridge", "walkway", "bridge"],
                "departments": [],
                "boundingRadius": round(
                    max(
                        math.sqrt((vx - cx_b) ** 2 + (vy - cy_b) ** 2 + (vz - cz_b) ** 2)
                        for vx, vy, vz in world_verts
                    ),
                    2,
                ),
            }
        )

    return bridge_inspectables


def build_buildings(
    osm_buildings: list[dict[str, Any]],
    overrides: dict[str, Any],
    terrain: TerrainSurface,
    mat_body: bpy.types.Material,
    mat_glass_lit: bpy.types.Material,
    mat_glass_dark: bpy.types.Material,
    overture_data: dict[str, Any] | None = None,
    campus_ctx: dict[str, Any] | None = None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]],
    list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]],
    list[list[tuple[float, float]]],
]:
    """Build clickable named BLDG_* landmarks, STATIC_Buildings, elevated BRIDGE_* walkways, and 60/40 WindowGlass."""
    records, override_ids, osm_rings_by_id, raw_tags_by_id = _prepare_building_records(
        osm_buildings,
        overrides,
        overture_data=overture_data,
    )
    cat_colors = overrides.get("category_colors") or {}
    boundary_ring = (campus_ctx or {}).get("boundary_ring") or []
    rail_lines = (campus_ctx or {}).get("rail_lines") or []

    # Cap total interactive BLDG_* objects at 90 so draw calls stay cleanly under 120
    non_ov_interactive = sum(
        1
        for r in records
        if r["source"] != "overture" and (bool(r["raw_name"]) or (r["id"] in override_ids))
    )
    ov_budget = max(0, 90 - non_ov_interactive)
    ov_candidates = [
        (r["auto_name_conf"], abs(signed_area_2d(r["rings"][0])), r["id"])
        for r in records
        if r["source"] == "overture" and (bool(r["raw_name"]) or (r["id"] in override_ids))
    ]
    ov_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    promoted_ov_ids: set[str] = {item[2] for item in ov_candidates[:ov_budget]}

    meta_buildings: list[dict[str, Any]] = []
    inspectables: list[dict[str, Any]] = []
    solid_colliders: list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]] = []
    courtyard_polys: list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]] = []
    courtyard_lawns: list[list[tuple[float, float]]] = []
    used_mesh_names: set[str] = set()

    static_bm = bmesh.new()
    static_col_layer = static_bm.loops.layers.color.new("Color")
    win_lit_bm = bmesh.new()
    win_dark_bm = bmesh.new()

    for rec in records:
        fid = rec["id"]
        rings: list[list[tuple[float, float]]] = rec["rings"]
        outer_ring = rings[0]
        cx_b, cy_b = ring_centroid_2d(outer_ring)

        if (
            cx_b < terrain.core_min_x + TERRAIN_EDGE_MARGIN_M
            or cx_b > terrain.core_max_x - TERRAIN_EDGE_MARGIN_M
            or cy_b < terrain.core_min_y + TERRAIN_EDGE_MARGIN_M
            or cy_b > terrain.core_max_y - TERRAIN_EDGE_MARGIN_M
        ):
            continue

        if rec["source"] != "custom" and not terrain_utils.is_point_in_campus(
            cx_b,
            cy_b,
            boundary_ring,
            rail_lines,
            pad_m=8.0,
            rail_margin_m=8.0,
        ):
            continue

        bx0, by0, bx1, by1 = bbox_of_ring(outer_ring)
        area_m2 = abs(signed_area_2d(outer_ring))
        hull = convex_hull_2d(outer_ring)
        hull_area = abs(signed_area_2d(hull))
        concavity = (hull_area - area_m2) / hull_area if hull_area > 0 else 0.0

        is_elevated = bool(rec["is_elevated"])
        min_clearance_m = float(rec["min_clearance_m"])

        if fid in (HERO_AB1_ID, HERO_AB3_ID) and len(rings) > 1:
            # AB-3: only the big central court (rings[1]) is a garden; its small light wells are paved
            lawn_holes = rings[1:] if fid == HERO_AB1_ID else rings[1:2]
            courtyard_lawns.extend(list(reversed(h)) for h in lawn_holes)
        elif fid not in (HERO_WORKSHOPS_WEST_ID, HERO_WORKSHOPS_EAST_ID, HERO_AB3_ID, HERO_LIBRARY_ID, HERO_PANDAL_ID) and not is_elevated and len(rings) == 1 and area_m2 >= 3000.0 and concavity < 0.14:
            hole_ccw = inset_ccw_ring_2d(outer_ring, 15.2, min_ratio=0.10, min_area=320.0)
            if hole_ccw is not None:
                courtyard_lawns.append(list(hole_ccw))
                hole_cw = list(reversed(hole_ccw))
                rings = [outer_ring, hole_cw]

        if not is_elevated and len(rings) == 1 and concavity >= 0.18 and hull_area >= 2000.0:
            hx0, hy0, hx1, hy1 = bbox_of_ring(hull)
            step_l = 12.0
            ly = hy0 + 4.0
            while ly <= hy1 - 4.0:
                lx = hx0 + 4.0
                while lx <= hx1 - 4.0:
                    if point_in_ring(lx, ly, hull) and not point_in_ring(lx, ly, outer_ring):
                        if dist_point_to_polygon_edge(lx, ly, outer_ring) >= 3.0:
                            pad = [(lx - 4.5, ly - 4.5), (lx + 4.5, ly - 4.5), (lx + 4.5, ly + 4.5), (lx - 4.5, ly + 4.5)]
                            if all(not point_in_ring(px, py, outer_ring) for px, py in pad):
                                courtyard_lawns.append(pad)
                    lx += step_l
                ly += step_l

        category = rec["category"]
        floors, height_m = _compute_building_floors_and_height(category, area_m2, rec)

        sample_pts = [pt for ring in rings for pt in ring] + [(cx_b, cy_b)]
        zs = [terrain.sample(px, py) for px, py in sample_pts]
        z_min, z_max = min(zs), max(zs)
        z_centroid = terrain.sample(cx_b, cy_b)

        if is_elevated:
            z_bottom = z_max + min_clearance_m
            z_base_ref = z_bottom
            z_top = max(z_bottom + height_m, z_bottom + 2.4)
            cz_b = 0.5 * (z_bottom + z_top)
        else:
            z_bottom = z_min - FOUNDATION_SINK_M
            z_base_ref = max(z_centroid, z_max - 0.5)
            z_top = z_base_ref + height_m
            cz_b = 0.5 * (z_base_ref + z_top)
            if fid in (HERO_WORKSHOPS_WEST_ID, HERO_WORKSHOPS_EAST_ID):
                for shed_ring in workshops_hero.get_workshop_shed_footprints(is_west=(fid == HERO_WORKSHOPS_WEST_ID)):
                    sbx0, sby0, sbx1, sby1 = bbox_of_ring(shed_ring)
                    solid_colliders.append(((sbx0, sby0, sbx1, sby1), [shed_ring]))
            else:
                solid_colliders.append(((bx0 - 2.6, by0 - 2.6, bx1 + 2.6, by1 + 2.6), rings))
                if category in {"academic", "landmark"} and fid != HERO_AB1_ID:
                    courtyard_polys.append(((bx0 - 24.0, by0 - 24.0, bx1 + 24.0, by1 + 24.0), [outer_ring]))

        base_wall_hex = PALETTE.get(f"wall_{category}", PALETTE["wall_default"])
        wall_hex = str(rec["color"]) if rec["color"] else _tint_hex_for_id(base_wall_hex, fid)
        default_roof_key = (
            "roof_terracotta_top" if category in {"academic", "landmark", "food"}
            else "roof_hostel" if category in {"hostel", "admin"}
            else "roof_slate"
        )
        roof_hex = str(rec.get("roof_color") or cat_colors.get(category) or PALETTE[default_roof_key])

        tags_set: list[str] = []
        for t in rec["override_tags"]:
            if t and t not in tags_set:
                tags_set.append(t)
        for key in ("amenity", "building", "cuisine", "sport"):
            val = rec["tags"].get(key)
            if val and val != "yes" and str(val) not in tags_set:
                tags_set.append(str(val))
        if category not in tags_set:
            tags_set.append(category)

        display_name = rec["raw_name"] or f"Unnamed Structure ({fid})"
        raw_tags = {str(k): str(v) for k, v in rec["tags"].items()}
        lat_lon = list(config.local_xz_to_latlon(cx_b, -cy_b))
        bounds_xz, footprint_xz = _footprint_meta_fields(outer_ring)

        is_interactive = (
            (bool(rec["raw_name"]) or (fid in override_ids))
            and (rec["source"] != "overture" or (fid in promoted_ov_ids) or (fid in override_ids))
        )

        if is_interactive:
            bm = bmesh.new()
            col_layer = bm.loops.layers.color.new("Color")
            world_verts = _append_amrita_building(
                bm=bm,
                col_layer=col_layer,
                win_lit_bm=win_lit_bm,
                win_dark_bm=win_dark_bm,
                fid=fid,
                rings=rings,
                offset_xyz=(cx_b, cy_b, cz_b),
                z_bottom=z_bottom,
                z_base_ref=z_base_ref,
                z_top=z_top,
                floors=floors,
                area_m2=area_m2,
                category=category,
                terrain=terrain,
                wall_hex=wall_hex,
                roof_hex=roof_hex,
                is_elevated=is_elevated,
            )
            if not bm.faces:
                bm.free()
                continue
            bm.normal_update()

            sanitized = re.sub(r"[^A-Za-z0-9_]+", "_", fid).strip("_")
            mesh_name = f"BLDG_{sanitized}"
            if mesh_name in used_mesh_names:
                mesh_name = f"{mesh_name}_{len(used_mesh_names)}"
            used_mesh_names.add(mesh_name)

            obj = create_mesh_object(mesh_name, bm, [mat_body])
            obj.location = (cx_b, cy_b, cz_b)

            bounding_radius = max(
                math.sqrt((vx - cx_b) ** 2 + (vy - cy_b) ** 2 + (vz - cz_b) ** 2)
                for vx, vy, vz in world_verts
            )

            entry: dict[str, Any] = {
                "id": fid,
                "meshName": mesh_name,
                "name": display_name,
                "source": rec["source"],
                "isNamed": bool(rec["raw_name"]),
                "category": category,
                "tags": tags_set,
                "departments": rec["departments"],
                "floors": int(floors),
                "heightM": round(float(height_m), 2),
                "center": blender_to_gltf_xyz(cx_b, cy_b, cz_b),
                "boundingRadius": round(float(bounding_radius), 2),
                "latLon": lat_lon,
                "rawTags": raw_tags,
            }
            if rec.get("subtitle"):
                entry["subtitle"] = str(rec["subtitle"])
            if rec.get("places"):
                entry["places"] = rec["places"]
            meta_buildings.append(entry)

            inspectables.append(
                {
                    **entry,
                    "kind": "building",
                    "boundsXZ": bounds_xz,
                    "footprintXZ": footprint_xz,
                }
            )
        else:
            world_verts = _append_amrita_building(
                bm=static_bm,
                col_layer=static_col_layer,
                win_lit_bm=win_lit_bm,
                win_dark_bm=win_dark_bm,
                fid=fid,
                rings=rings,
                offset_xyz=(0.0, 0.0, 0.0),
                z_bottom=z_bottom,
                z_base_ref=z_base_ref,
                z_top=z_top,
                floors=floors,
                area_m2=area_m2,
                category=category,
                terrain=terrain,
                wall_hex=wall_hex,
                roof_hex=roof_hex,
                is_elevated=is_elevated,
            )
            if world_verts:
                bounding_radius = max(
                    math.sqrt((vx - cx_b) ** 2 + (vy - cy_b) ** 2 + (vz - cz_b) ** 2)
                    for vx, vy, vz in world_verts
                )
                static_entry: dict[str, Any] = {
                    "id": fid,
                    "meshName": "STATIC_Buildings",
                    "kind": "building",
                    "name": display_name,
                    "source": rec["source"],
                    "isNamed": bool(rec["raw_name"]),
                    "category": category,
                    "tags": tags_set,
                    "departments": [],
                    "floors": int(floors),
                    "heightM": round(float(height_m), 2),
                    "center": blender_to_gltf_xyz(cx_b, cy_b, cz_b),
                    "boundingRadius": round(float(bounding_radius), 2),
                    "latLon": lat_lon,
                    "boundsXZ": bounds_xz,
                    "footprintXZ": footprint_xz,
                    "rawTags": raw_tags,
                }
                if rec.get("places"):
                    static_entry["places"] = rec["places"]
                inspectables.append(static_entry)

    bridge_inspectables = _build_elevated_bridges(
        bridges_cfg=overrides.get("bridges") or [],
        osm_rings_by_id=osm_rings_by_id,
        raw_tags_by_id=raw_tags_by_id,
        terrain=terrain,
        mat_body=mat_body,
        win_lit_bm=win_lit_bm,
        win_dark_bm=win_dark_bm,
        used_mesh_names=used_mesh_names,
    )
    inspectables.extend(bridge_inspectables)

    if static_bm.faces:
        static_bm.normal_update()
        create_mesh_object("STATIC_Buildings", static_bm, [mat_body])
    else:
        static_bm.free()

    if win_lit_bm.faces:
        win_lit_bm.normal_update()
        create_mesh_object("STATIC_WindowGlassLit", win_lit_bm, [mat_glass_lit])
    else:
        win_lit_bm.free()

    if win_dark_bm.faces:
        win_dark_bm.normal_update()
        create_mesh_object("STATIC_WindowGlassDark", win_dark_bm, [mat_glass_dark])
    else:
        win_dark_bm.free()

    meta_buildings.sort(key=lambda b: (not b["isNamed"], b["name"].lower(), b["id"]))
    return meta_buildings, inspectables, solid_colliders, courtyard_polys, courtyard_lawns


def generate_trees_data(
    green_entries: list[tuple[str, tuple[float, float, float, float], list[list[tuple[float, float]]]]],
    water_features: list[dict[str, Any]],
    sports_features: list[dict[str, Any]],
    path_features: list[dict[str, Any]],
    solid_colliders: list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]],
    courtyard_polys: list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]],
    courtyard_lawns: list[list[tuple[float, float]]],
    road_colliders: list[tuple[list[tuple[float, float]], float, float]],
    terrain: TerrainSurface,
    rail_lines: list[list[tuple[float, float]]] | None = None,
    bridge_tree_spots: list[tuple[float, float, int, tuple[float, float]]] | None = None,
    hand_tree_spots: list[tuple[float, float, int, tuple[float, float]]] | None = None,
) -> list[list[Any]]:
    """Generate 2,500+ Ettimadai palm (type=0) & canopy (type=1) instances in trees.json."""
    rng = random.Random(42)

    excl_polys: list[tuple[tuple[float, float, float, float], list[list[tuple[float, float]]]]] = []
    for feat in water_features + sports_features:
        for rings in geojson_polygon_rings_to_blender(feat["geometry"]):
            x0, y0, x1, y1 = bbox_of_ring(rings[0])
            excl_polys.append(((x0 - 2.5, y0 - 2.5, x1 + 2.5, y1 + 2.5), rings))
    ab1_plaza_ring = ab1_hero.get_ab1_plaza_ring()
    px0, py0, px1, py1 = bbox_of_ring(ab1_plaza_ring)
    excl_polys.append(((px0 - 2.2, py0 - 2.2, px1 + 2.2, py1 + 2.2), [ab1_plaza_ring]))

    road_aabbs: list[tuple[float, float, float, float, list[tuple[float, float]], float]] = []
    for pts, half_w, curb_w in road_colliders:
        pad = half_w + curb_w + 2.0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        road_aabbs.append((min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad, pts, pad * pad))
    for r_pts in rail_lines or []:
        if len(r_pts) < 2:
            continue
        pad = 5.5
        xs = [p[0] for p in r_pts]
        ys = [p[1] for p in r_pts]
        road_aabbs.append((min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad, r_pts, pad * pad))

    cell_size = 7.0
    spatial_hash: dict[tuple[int, int], list[tuple[float, float]]] = {}
    placed: list[list[Any]] = []

    def _is_clear(
        tx: float,
        ty: float,
        min_tree_spacing: float,
        avoid_courtyards: bool,
        allow_inside_courtyard_hole: bool = False,
        allow_ab1_entry: bool = False,
        allow_ab3_front: bool = False,
    ) -> bool:
        if (
            tx < terrain.min_x + 15.0
            or tx > terrain.max_x - 15.0
            or ty < terrain.min_y + 15.0
            or ty > terrain.max_y - 15.0
        ):
            return False

        if not allow_ab1_entry and 202.0 <= tx <= 286.0 and -354.0 <= ty <= -274.0:
            return False

        sp2 = min_tree_spacing * min_tree_spacing
        gx = int(math.floor(tx / cell_size))
        gy = int(math.floor(ty / cell_size))
        rad_cells = int(math.ceil(min_tree_spacing / cell_size))
        for dx in range(-rad_cells, rad_cells + 1):
            for dy in range(-rad_cells, rad_cells + 1):
                for ox, oy in spatial_hash.get((gx + dx, gy + dy), ()):
                    if (tx - ox) ** 2 + (ty - oy) ** 2 < sp2:
                        return False

        for (x0, y0, x1, y1), rings in solid_colliders:
            if x0 <= tx <= x1 and y0 <= ty <= y1:
                if point_in_polygon(tx, ty, rings):
                    return False
                in_hole = any(point_in_ring(tx, ty, h) for h in rings[1:])
                if in_hole:
                    if not allow_inside_courtyard_hole:
                        return False
                    if dist_point_to_polygon_edge(tx, ty, rings[1]) < 3.0:
                        return False
                elif dist_point_to_polygon_edge(tx, ty, rings[0]) < 2.6:
                    return False

        for (x0, y0, x1, y1), rings in excl_polys:
            if x0 <= tx <= x1 and y0 <= ty <= y1:
                if point_in_polygon(tx, ty, rings) or dist_point_to_polygon_edge(tx, ty, rings[0]) < 2.2:
                    return False

        for rx0, ry0, rx1, ry1, pts, pad_sq in road_aabbs:
            if rx0 <= tx <= rx1 and ry0 <= ty <= ry1:
                for i in range(len(pts) - 1):
                    if dist_point_to_segment_sq(tx, ty, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) < pad_sq:
                        return False

        # Keep hero plazas, AB-1 Lotus Fountain & ASB median planter clear of trees
        hero_clear_discs = (
            (ab1_hero.AB1_FOUNTAIN_CX, ab1_hero.AB1_FOUNTAIN_CY, 11.5 * 11.5),
            (132.5, 157.2, 6.5 * 6.5),
            (ab1_hero.AB1_PARKING_CX, ab1_hero.AB1_PARKING_CY, 22.5 * 22.5),
        ) + (() if allow_ab3_front else tuple(ab3_hero.ab3_front_clear_discs()))
        hero_clear_discs += ((*ab2_hero.ab2_statue_xy(), 17.0 * 17.0),)
        hero_clear_discs += tuple((x, y, 6.5 * 6.5) for x, y, _, _ in library_hero.library_front_tree_spots())
        for hx, hy, hr2 in hero_clear_discs:
            if (tx - hx) ** 2 + (ty - hy) ** 2 < hr2:
                return False

        if avoid_courtyards:
            for (cx0, cy0, cx1, cy1), rings in courtyard_polys:
                if cx0 <= tx <= cx1 and cy0 <= ty <= cy1:
                    if point_in_polygon(tx, ty, rings) or dist_point_to_polygon_edge(tx, ty, rings[0]) < 15.0:
                        return False
        return True

    def _place(
        tx: float, ty: float, tree_type: int, scale_range: tuple[float, float], garden_shade: int | None = None,
    ) -> None:
        tz = terrain.sample(tx, ty)
        gx, gy, gz = blender_to_gltf_xyz(tx, ty, tz)
        sc = round(rng.uniform(*scale_range), 2)
        rot_y = round(rng.uniform(0.0, 6.28), 2)
        shade = rng.randrange(0, 4)
        if garden_shade is not None:
            shade = garden_shade
        placed.append([round(gx, 1), round(gy, 1), round(gz, 1), sc, rot_y, tree_type, shade])
        cgx = int(math.floor(tx / cell_size))
        cgy = int(math.floor(ty / cell_size))
        spatial_hash.setdefault((cgx, cgy), []).append((tx, ty))

    # 1. Ornamental palms inside carved quadrangle courtyards & AB-1 front lawn / entry palm clusters
    for lawn in courtyard_lawns:
        lx, ly = ring_centroid_2d(lawn)
        if _is_clear(lx, ly, min_tree_spacing=6.5, avoid_courtyards=False, allow_inside_courtyard_hole=True):
            _place(lx, ly, 0, (0.72, 0.92))

    # Two small neat palm clusters flanking the straight entry driveway just south of the fountain
    entry_palm_spots = (
        (238.5, -330.0), (239.5, -336.5), (237.0, -343.0), (239.5, -350.0),
        (258.5, -330.0), (257.5, -336.5), (260.0, -343.0), (257.5, -350.0),
    )
    for px, py in entry_palm_spots:
        if _is_clear(px, py, min_tree_spacing=4.2, avoid_courtyards=False, allow_ab1_entry=True):
            _place(px, py, 0, (1.2, 1.4), GARDEN_PALM_SHADE)

    # AB-1 front landscaping from the aerial photos: fountain palms, East garden round bush & shrubs, West lawn shrubs
    for px, py, ttype, scale_rng in ab1_hero.ab1_front_tree_spots():
        if _is_clear(px, py, min_tree_spacing=3.0, avoid_courtyards=False, allow_ab1_entry=True):
            _place(px, py, ttype, scale_rng, GARDEN_PALM_SHADE if ttype == 0 else GARDEN_TREE_SHADE)

    # AB-3 East front garden: palms & a shade tree on the raised island, palms flanking the twin porches
    for px, py, ttype, scale_rng in ab3_hero.ab3_front_tree_spots():
        if _is_clear(px, py, min_tree_spacing=3.0, avoid_courtyards=False, allow_ab3_front=True):
            _place(px, py, ttype, scale_rng)

    # AB-2 front garden & courtyard palms and Central Library entrance trees (hand-placed spots)
    hand_spots = ab2_hero.ab2_front_tree_spots() + library_hero.library_front_tree_spots()
    for px, py, ttype, scale_rng, *shade in hand_spots + list(hand_tree_spots or []):
        _place(px, py, ttype, scale_rng, *shade)

    # Wooded gully either side of the footbridges
    for px, py, ttype, scale_rng in bridge_tree_spots or []:
        if _is_clear(px, py, min_tree_spacing=2.5, avoid_courtyards=False):
            _place(px, py, ttype, scale_rng)

    # Loose natural perimeter clusters on outer AB-1 lawn edges & back corners (clear central lawn & sightline!)
    ab1_grove_candidates: list[tuple[float, float, int]] = []
    for gx0, gy0, gx1, gy1, step in (
        (176.0, -356.0, 200.0, -272.0, 12.0),  # Outer West fence edge
        (288.0, -354.0, 314.0, -268.0, 12.0),  # Outer East fence edge
        (175.0, -246.0, 312.0, -186.0, 13.5),  # Back corners behind AB-1
    ):
        gy = gy0 + 2.0
        while gy <= gy1 - 2.0:
            gx = gx0 + 2.0
            while gx <= gx1 - 2.0:
                jx = gx + rng.uniform(-2.4, 2.4)
                jy = gy + rng.uniform(-2.4, 2.4)
                ttype = 0 if rng.random() < 0.20 else 1
                ab1_grove_candidates.append((jx, jy, ttype))
                gx += step
            gy += step
    rng.shuffle(ab1_grove_candidates)
    ab1_canopy_count = 0
    for jx, jy, ttype in ab1_grove_candidates:
        if ab1_canopy_count >= 32:
            break
        if _is_clear(jx, jy, min_tree_spacing=9.5, avoid_courtyards=False):
            _place(jx, jy, ttype, (0.52, 0.72) if ttype == 1 else (0.78, 0.98))
            ab1_canopy_count += 1

    # 1B. Main Sports Ground dense tropical canopy belt behind east gallery & along north/west edges
    from heroes import main_ground as hero_main_ground

    mg_belt_candidates: list[tuple[float, float, int, float]] = []
    for belt_name, u0, u1, v0, v1, step in hero_main_ground.get_main_ground_tree_belts():
        vu = v0 + 1.0
        while vu <= v1 - 1.0:
            uu = u0 + 1.0
            while uu <= u1 - 1.0:
                ju = uu + rng.uniform(-1.6, 1.6)
                jv = vu + rng.uniform(-1.8, 1.8)
                wx, wy = hero_main_ground.belt_local_to_world(ju, jv)
                ttype = 0 if (belt_name != "east_gallery_screen" and rng.random() < 0.12) else 1
                spacing = 4.8 if belt_name == "east_gallery_screen" else 5.8
                mg_belt_candidates.append((wx, wy, ttype, spacing))
                uu += step
            vu += step
    rng.shuffle(mg_belt_candidates)
    for wx, wy, ttype, spacing in mg_belt_candidates:
        if _is_clear(wx, wy, min_tree_spacing=spacing, avoid_courtyards=False):
            _place(wx, wy, ttype, (1.05, 1.48) if ttype == 1 else (0.90, 1.22))

    # 1C. Main Gate & Parking Perimeter tropical shade trees (outside sheds/lots/rail crossing)
    from heroes import main_gate as hero_main_gate

    for fx, fy, ftype, fscale in hero_main_gate.get_main_gate_feature_trees():
        _place(fx, fy, ftype, (fscale, fscale))

    gate_candidates: list[tuple[float, float, int]] = []
    for gx0, gy0, gx1, gy1, step in hero_main_gate.get_main_gate_shade_tree_belts():
        yg = gy0 + 1.5
        while yg <= gy1 - 1.5:
            xg = gx0 + 1.5
            while xg <= gx1 - 1.5:
                jx = xg + rng.uniform(-1.8, 1.8)
                jy = yg + rng.uniform(-1.8, 1.8)
                gate_candidates.append((jx, jy, 0 if rng.random() < 0.25 else 1))
                xg += step
            yg += step
    rng.shuffle(gate_candidates)
    for wx, wy, ttype in gate_candidates:
        if _is_clear(wx, wy, min_tree_spacing=7.5, avoid_courtyards=False):
            _place(wx, wy, ttype, (0.95, 1.35) if ttype == 1 else (0.88, 1.18))

    # 2. Coconut palm & shade avenues flanking both sides of campus roads (4-6m offset)
    for pts, half_w, curb_w in road_colliders:
        offset_base = max(4.0, min(6.0, half_w + curb_w + 2.3))
        acc = 0.0
        next_spawn = rng.uniform(5.0, 10.0)
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            seg_len = math.hypot(bx - ax, by - ay)
            if seg_len < 0.5:
                continue
            tx_dir, ty_dir = (bx - ax) / seg_len, (by - ay) / seg_len
            nx, ny = -ty_dir, tx_dir
            while acc + seg_len >= next_spawn and len(placed) < 920:
                t = (next_spawn - acc) / seg_len
                px, py = ax + t * (bx - ax), ay + t * (by - ay)
                for side in (-1.0, 1.0):
                    off = offset_base + rng.uniform(-0.3, 0.7)
                    cx, cy = px + side * nx * off, py + side * ny * off
                    if _is_clear(cx, cy, min_tree_spacing=8.5, avoid_courtyards=False):
                        ttype = 0 if rng.random() < 0.72 else 1
                        _place(cx, cy, ttype, (0.85, 1.25))
                next_spawn += rng.uniform(12.0, 16.5)
            acc += seg_len

    # 2B. Balanced natural tree clusters across core campus lawns, hostels, and perimeter pockets
    core_clusters: list[tuple[float, float]] = []
    cy_cur = terrain.core_min_y + 25.0
    while cy_cur <= terrain.core_max_y - 25.0:
        cx_cur = terrain.core_min_x + 25.0
        while cx_cur <= terrain.core_max_x - 25.0:
            core_clusters.append((cx_cur + rng.uniform(-5.0, 5.0), cy_cur + rng.uniform(-5.0, 5.0)))
            cx_cur += 16.0
        cy_cur += 16.0
    rng.shuffle(core_clusters)
    for ccx, ccy in core_clusters:
        if len(placed) >= 1400:
            break
        if _is_clear(ccx, ccy, min_tree_spacing=10.5, avoid_courtyards=True):
            _place(ccx, ccy, 0 if rng.random() < 0.25 else 1, (0.88, 1.32))

    # 3. OSM green zones & plantation areas (coconut palms + tropical shade trees)
    green_candidates: list[tuple[float, float, str]] = []
    for subtype, (zx0, zy0, zx1, zy1), rings in green_entries:
        cx0 = max(zx0, terrain.min_x + 18.0)
        cy0 = max(zy0, terrain.min_y + 18.0)
        cx1 = min(zx1, terrain.max_x - 18.0)
        cy1 = min(zy1, terrain.max_y - 18.0)
        if cx0 >= cx1 or cy0 >= cy1:
            continue
        step = 11.0 if subtype in {"wood", "forest"} else 12.0 if subtype in {"grass", "park", "garden"} else 18.0
        y = cy0 + 2.0
        while y <= cy1 - 2.0:
            x = cx0 + 2.0
            while x <= cx1 - 2.0:
                jx = x + rng.uniform(-0.35 * step, 0.35 * step)
                jy = y + rng.uniform(-0.35 * step, 0.35 * step)
                if point_in_polygon(jx, jy, rings):
                    green_candidates.append((jx, jy, subtype))
                x += step
            y += step

    rng.shuffle(green_candidates)
    for jx, jy, subtype in green_candidates:
        if len(placed) >= 1950:
            break
        spacing = 8.0 if subtype in {"wood", "forest"} else 9.0
        if _is_clear(jx, jy, min_tree_spacing=spacing, avoid_courtyards=True):
            # Plantation / farmland & grass get coconut palms + canopy; woods mostly dense tropical canopy
            palm_prob = 0.42 if subtype in {"farmland", "grass", "park", "garden"} else 0.14
            ttype = 0 if rng.random() < palm_prob else 1
            _place(jx, jy, ttype, (0.95, 1.42))

    # 4. Dense tropical canopy blanketing Western Ghats foothill slopes & campus perimeter
    hill_candidates: list[tuple[float, float, float]] = []
    step_hill = 20.0
    y = terrain.min_y + 22.0
    while y <= terrain.max_y - 22.0:
        x = terrain.min_x + 22.0
        while x <= terrain.max_x - 22.0:
            jx = x + rng.uniform(-8.0, 8.0)
            jy = y + rng.uniform(-8.0, 8.0)
            cx = min(max(jx, terrain.core_min_x), terrain.core_max_x)
            cy = min(max(jy, terrain.core_min_y), terrain.core_max_y)
            dist_out = math.hypot(jx - cx, jy - cy)
            z = terrain.sample(jx, jy)
            # Focus dense canopy on visible Western Ghats foothills & campus perimeter
            score = (1.6 if 0 < dist_out < 750 else 0.6) + (1.2 if 4.0 < z < 155.0 else 0.2) + rng.uniform(0.0, 1.4)
            hill_candidates.append((score, jx, jy))
            x += step_hill
        y += step_hill

    hill_candidates.sort(key=lambda item: item[0], reverse=True)
    for _, jx, jy in hill_candidates:
        if len(placed) >= TARGET_TREE_COUNT:
            break
        z = terrain.sample(jx, jy)
        spacing = 11.5 if z > 12.0 else 12.5
        if _is_clear(jx, jy, min_tree_spacing=spacing, avoid_courtyards=True):
            ttype = 0 if (z < 12.0 and rng.random() < 0.20) else 1
            _place(jx, jy, ttype, (1.10, 1.60))

    if len(placed) < MIN_TREE_COUNT:
        for _, jx, jy in hill_candidates:
            if len(placed) >= MIN_TREE_COUNT + 80:
                break
            jx2 = jx + rng.uniform(-6.0, 6.0)
            jy2 = jy + rng.uniform(-6.0, 6.0)
            if _is_clear(jx2, jy2, min_tree_spacing=8.5, avoid_courtyards=True):
                _place(jx2, jy2, 1, (0.88, 1.55))

    return placed[:MAX_TREE_COUNT]


def _import_manual_hero_glbs(hero_models_dir: Path, terrain: TerrainSurface) -> int:
    """Auto-import any manual `.glb` hero assets from `pipeline/hero_models/` onto terrain."""
    if not hero_models_dir.exists():
        return 0
    imported_count = 0
    for glb_path in sorted(hero_models_dir.glob("*.glb")):
        if glb_path.name.startswith(("_", ".")):
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(glb_path))
        added = [obj for obj in bpy.data.objects if obj not in before]
        cfg_path = glb_path.with_suffix(".json")
        if cfg_path.exists() and added:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            px = float(cfg.get("x", 0.0))
            py = float(cfg.get("y", 0.0))
            pz = float(cfg.get("z", terrain.sample(px, py) + float(cfg.get("z_offset", 0.0))))
            rot_z = math.radians(float(cfg.get("rot_z_deg", 0.0)))
            scale = float(cfg.get("scale", 1.0))
            for obj in added:
                if obj.parent is None:
                    obj.location = (px, py, pz)
                    obj.rotation_euler[2] += rot_z
                    if scale != 1.0:
                        obj.scale = (obj.scale[0] * scale, obj.scale[1] * scale, obj.scale[2] * scale)
        imported_count += 1
    return imported_count


def main() -> None:
    """Build Amrita Coimbatore 3D scene GLB, campus_meta.json, trees.json, and verify budgets."""
    print("Merging roads (Shapely unary_union), Indian curbs & streetlamps.json...")
    try:
        import merge_roads
        merge_roads.build_merged_roads_and_lamps()
    except ImportError:
        venv_dir = config.PIPELINE_DIR / ".venv"
        venv_candidates = (venv_dir / "Scripts" / "python.exe", venv_dir / "bin" / "python")
        venv_py = next((p for p in venv_candidates if p.exists()), None)
        py_exe = str(venv_py) if venv_py is not None else sys.executable
        subprocess.run([py_exe, str(config.PIPELINE_DIR / "merge_roads.py")], check=True)

    print("Loading raw_osm.json, elevation.json, overrides.json, and optional overture_campus.json...")
    raw_osm = json.loads(config.RAW_OSM_PATH.read_text(encoding="utf-8"))
    elevation = json.loads(config.ELEVATION_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(config.OVERRIDES_PATH.read_text(encoding="utf-8"))
    overture_data: dict[str, Any] | None = (
        json.loads(config.OVERTURE_PATH.read_text(encoding="utf-8"))
        if config.OVERTURE_PATH.exists()
        else None
    )

    bpy.ops.wm.read_factory_settings(use_empty=True)

    mat_terrain_ground = make_vertex_color_material("MAT_TerrainGround", roughness=0.90)
    mat_terrain_skirt = make_palette_material("MAT_TerrainSkirt", PALETTE["terrain_skirt"], roughness=0.92)
    mat_building_body = make_vertex_color_material("BuildingBody", roughness=0.76)
    mat_window_glass_lit = make_palette_material("WindowGlassLit", PALETTE["window_glass"], roughness=0.14, metallic=0.25)
    mat_window_glass_dark = make_palette_material("WindowGlassDark", PALETTE["window_glass"], roughness=0.16, metallic=0.25)
    mat_hero_accents = make_vertex_color_material("MAT_HeroAccents", roughness=0.68, metallic=0.08)
    mat_road_network = make_vertex_color_material("MAT_RoadNetwork", roughness=0.86)
    mat_railway = make_vertex_color_material("MAT_Railway", roughness=0.72, metallic=0.18)

    palette_mats: dict[str, bpy.types.Material] = {
        "water_pond": make_palette_material("MAT_WaterPond", PALETTE["water_pond"], roughness=0.14, metallic=0.12),
        "pool_water": make_palette_material("MAT_PoolWater", PALETTE["pool_water"], roughness=0.10, metallic=0.15),
        "pool_deck": make_palette_material("MAT_PoolDeck", PALETTE["pool_deck"], roughness=0.82),
        "sports_pitch": make_palette_material("MAT_SportsPitch", PALETTE["sports_pitch"], roughness=0.84),
        "sports_court": make_palette_material("MAT_SportsCourt", PALETTE["sports_court"], roughness=0.78),
        "lawn_courtyard": make_palette_material("MAT_LawnCourtyard", PALETTE["lawn_courtyard"], roughness=0.88),
        "plaza_sandstone": make_palette_material("MAT_PlazaSandstone", PALETTE["plaza_sandstone"], roughness=0.86),
        "plaza_charcoal": make_palette_material("MAT_PlazaCharcoal", PALETTE["plaza_charcoal"], roughness=0.86),
        "plaza_ab1": make_palette_material("MAT_PlazaAB1", PALETTE["plaza_ab1"], roughness=0.9),
        "retaining_wall": make_palette_material("MAT_RetainingWall", PALETTE["retaining_wall"], roughness=0.88),
    }

    exclude_ids: set[str] = {str(x) for x in (overrides.get("exclude_ids") or [])}
    features = raw_osm.get("features", [])
    by_layer: dict[str, list[dict[str, Any]]] = {
        "building": [],
        "path": [],
        "water": [],
        "sports": [],
        "green": [],
        "railway": [],
        "railway_node": [],
    }
    for feat in features:
        layer = feat.get("properties", {}).get("layer")
        if layer in by_layer:
            if layer in {"water", "sports"} and str(feat.get("id")) in exclude_ids:
                continue
            by_layer[layer].append(feat)

    campus_ctx = terrain_utils.extract_campus_boundary_and_rail(raw_osm)
    datum_m = float(elevation["metadata"]["stats"]["origin_elevation_m"])
    terrain = TerrainSurface(
        lats=elevation["lats"],
        lons=elevation["lons"],
        elevations=elevation["elevations"],
        datum_m=datum_m,
        raw_osm=raw_osm,
    )

    print("Building campus-filtered Amrita blocks, spaced window bays, hero landmarks & skybridge...")
    meta_buildings, inspectables, solid_colliders, courtyard_polys, courtyard_lawns = build_buildings(
        by_layer["building"],
        overrides,
        terrain,
        mat_building_body,
        mat_window_glass_lit,
        mat_window_glass_dark,
        overture_data=overture_data,
        campus_ctx=campus_ctx,
    )

    print("Building Shapely-merged campus asphalt roads & grounded black/yellow curbs...")
    _, road_colliders = build_roads_object(
        by_layer["path"],
        overrides,
        campus_ctx,
        terrain,
        mat_road_network,
    )

    print("Building double-track broad-gauge railway corridor south of campus...")
    _, rail_excl_lines = build_railway_object(
        by_layer["railway"],
        by_layer["railway_node"],
        terrain,
        mat_railway,
    )

    print("Building Western Ghats backdrop & graded sunlit tropical terrain...")
    _, green_entries = build_terrain_object(
        terrain,
        by_layer["green"],
        courtyard_polys,
        road_colliders,
        mat_terrain_ground,
        mat_terrain_skirt,
    )

    print("Building merged water, terraced pool & sports slabs, sandstone plazas & courtyard lawns...")
    _, flat_pad_heights = build_ground_features_object(
        by_layer["water"],
        by_layer["sports"],
        courtyard_lawns,
        terrain,
        palette_mats,
    )

    print("Building Hero sports markings, bleachers, Nataraja fountain & curb planters...")
    build_hero_accents_object(features, terrain, mat_hero_accents, flat_pad_heights=flat_pad_heights)

    import heroes  # noqa: E402

    hero_ctx: dict[str, Any] = {
        "terrain": terrain,
        "overrides": overrides,
        "raw_osm": raw_osm,
        "mat_body": mat_building_body,
        "mat_hero_accents": mat_hero_accents,
        "mat_glass_lit": mat_window_glass_lit,
        "mat_glass_dark": mat_window_glass_dark,
        "solid_colliders": solid_colliders,
        "courtyard_lawns": courtyard_lawns,
        "meta_buildings": meta_buildings,
        "inspectables": inspectables,
        "flat_pad_heights": flat_pad_heights,
        "config": config,
        "hand_tree_spots": [],
    }
    ran_heroes = heroes.discover_and_run_heroes(hero_ctx)
    if ran_heroes:
        print(f"Executed modular hero generators ({len(ran_heroes)}): {', '.join(ran_heroes)}")

    manual_glb_count = _import_manual_hero_glbs(config.HERO_MODELS_DIR, terrain)
    if manual_glb_count:
        print(f"Auto-imported {manual_glb_count} manual hero GLB asset(s) from {config.HERO_MODELS_DIR}")

    print("Scattering 2,500+ Ettimadai palms & tropical canopy trees (trees.json)...")
    trees = generate_trees_data(
        green_entries=green_entries,
        water_features=by_layer["water"],
        sports_features=by_layer["sports"],
        path_features=by_layer["path"],
        solid_colliders=solid_colliders,
        courtyard_polys=courtyard_polys,
        courtyard_lawns=courtyard_lawns,
        road_colliders=road_colliders,
        terrain=terrain,
        rail_lines=rail_excl_lines,
        bridge_tree_spots=footbridges.gully_tree_spots(overrides),
        hand_tree_spots=hero_ctx["hand_tree_spots"],
    )

    config.CAMPUS_GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.CAMPUS_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.TREES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.DEBUG_BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(config.DEBUG_BLEND_PATH), compress=True)
    print(f"Saved debug Blender scene to {config.DEBUG_BLEND_PATH}")

    print(f"Exporting Draco-compressed GLB to {config.CAMPUS_GLB_PATH}...")
    bpy.ops.export_scene.gltf(
        filepath=str(config.CAMPUS_GLB_PATH),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_texcoords=False,
        export_normals=True,
        export_vertex_color="MATERIAL",
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_draco_color_quantization=10,
    )

    trees_output = {
        "count": len(trees),
        "format": "[x,y,z,scale,rotY,type,shade]",
        "types": ["palm", "canopy"],
        "trees": trees,
    }
    with config.TREES_JSON_PATH.open("w", encoding="utf-8") as fh:
        json.dump(trees_output, fh, separators=(",", ":"))

    bridge_count = sum(1 for item in inspectables if item.get("kind") == "bridge")
    overture_pois: list[dict[str, Any]] = []
    if overture_data:
        for pl in overture_data.get("unmatched_places") or []:
            if pl.get("is_generic_name"):
                continue
            xz = pl.get("centerXZ")
            if not isinstance(xz, (list, tuple)) or len(xz) < 2:
                continue
            px, pz = float(xz[0]), float(xz[1])
            py_b = -pz
            if not (terrain.core_min_x <= px <= terrain.core_max_x and terrain.core_min_y <= py_b <= terrain.core_max_y):
                continue
            py_elev = terrain.sample(px, py_b)
            poi_entry: dict[str, Any] = {
                "id": str(pl["id"]),
                "name": str(pl["name"]),
                "category": str(pl.get("category") or "default"),
                "latLon": pl["latLon"],
                "position": [round(px, 2), round(py_elev + 0.5, 2), round(pz, 2)],
            }
            if pl.get("raw_category"):
                poi_entry["rawCategory"] = str(pl["raw_category"])
            if pl.get("confidence") is not None:
                poi_entry["confidence"] = pl["confidence"]
            overture_pois.append(poi_entry)

    ov_meta = (overture_data or {}).get("metadata") or {}
    ov_counts = ov_meta.get("counts") or {}
    ov_bldg_count = sum(1 for item in inspectables if item.get("source") == "overture")

    meta_output: dict[str, Any] = {
        "origin": list(config.ORIGIN),
        "bbox": list(config.BBOX),
        "elevationDatumM": round(datum_m, 2),
        "terrainBounds": {
            "minX": round(terrain.core_min_x, 2),
            "maxX": round(terrain.core_max_x, 2),
            "minZ": round(-terrain.core_max_y, 2),
            "maxZ": round(-terrain.core_min_y, 2),
            "minY": round(terrain.min_z, 2),
            "maxY": round(terrain.max_z, 2),
        },
        "extendedBounds": {
            "minX": round(terrain.min_x, 2),
            "maxX": round(terrain.max_x, 2),
            "minZ": round(-terrain.max_y, 2),
            "maxZ": round(-terrain.min_y, 2),
        },
        "counts": {
            "buildings": len(meta_buildings),
            "namedBuildings": sum(1 for b in meta_buildings if b["isNamed"]),
            "bridges": bridge_count,
            "inspectables": len(inspectables),
            "trees": len(trees),
            "palms": sum(1 for t in trees if t[5] == 0),
            "canopy": sum(1 for t in trees if t[5] == 1),
            "overtureBuildings": ov_bldg_count,
            "overturePlaces": int(ov_counts.get("places_matched_to_buildings", 0)) + len(overture_pois),
            "unmatchedPois": len(overture_pois),
        },
        "buildings": meta_buildings,
        "inspectables": inspectables,
        "overturePois": overture_pois,
    }
    if ov_meta.get("release"):
        meta_output["overtureRelease"] = str(ov_meta["release"])
    with config.CAMPUS_META_PATH.open("w", encoding="utf-8") as fh:
        json.dump(meta_output, fh, indent=2, ensure_ascii=False)

    trees_kb = config.TREES_JSON_PATH.stat().st_size / 1024.0
    print(
        f"Exported {len(meta_buildings)} interactive buildings "
        f"({meta_output['counts']['namedBuildings']} named), {bridge_count} bridges, "
        f"{len(inspectables)} inspectables to {config.CAMPUS_META_PATH}"
    )
    print(
        f"Exported {len(trees)} trees ({meta_output['counts']['palms']} palms, "
        f"{meta_output['counts']['canopy']} canopy) to {config.TREES_JSON_PATH} ({trees_kb:.1f} KB)"
    )

    passed, _ = verify_budget.verify_glb(config.CAMPUS_GLB_PATH)
    if "--" in sys.argv:
        extra_args = sys.argv[sys.argv.index("--") + 1 :]
        if "--save-blend" in extra_args:
            idx = extra_args.index("--save-blend")
            if idx + 1 < len(extra_args):
                blend_out = Path(extra_args[idx + 1]).resolve()
                blend_out.parent.mkdir(parents=True, exist_ok=True)
                bpy.ops.wm.save_as_mainfile(filepath=str(blend_out), compress=True)
                print(f"Saved full Blender scene to {blend_out}")
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


if __name__ == "__main__":
    main()
