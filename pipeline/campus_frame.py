"""Satellite-traced local frame for the AB-2 / Central Library cluster (pure Python, no Blender).

Both buildings share one orientation, so their plans are traced as axis-aligned
rectangles in a rotated (u = east along the facade, v = north) frame read off a
de-rotated Esri World Imagery crop. `REGISTRATION_UV` nudges the traced imagery
onto the OSM road network so walls stay clear of kerbs.
"""

from __future__ import annotations

import math

FRAME_ORIGIN_XY: tuple[float, float] = (-210.0, 170.0)  # Blender XY of (u, v) = (0, 0)
FRAME_ROT_RAD: float = 0.118
REGISTRATION_UV: tuple[float, float] = (-2.5, -3.5)  # imagery -> OSM offset in metres

# Graded building terrace under the cluster: (u0, u1, v0, v1) in traced coordinates
TERRACE_RECT_UV: tuple[float, float, float, float] = (-92.0, 88.0, -62.0, 56.0)
TERRACE_LEVEL_M: float = 7.0  # metres above the elevation datum
TERRACE_APRON_M: float = 24.0
TERRACE_BLEND_M: float = 40.0


# Relocated IT Canteen footprint (OSM outline moved by its `shift_footprints` override), Blender XY
CANTEEN_RING_XY: list[tuple[float, float]] = [(-308.6, 236.5), (-273.5, 244.8), (-282.3, 281.8), (-317.3, 273.5)]
CANTEEN_LEVEL_M = 10.9

# Courtyard hostel south-east of the Nataraja fountain (corners SW, SE, NE, NW), traced from Google satellite
HOSTEL_RING_XY: list[tuple[float, float]] = [(-209.9, -26.9), (-142.6, -21.9), (-147.6, 44.9), (-214.9, 39.9)]
HOSTEL_LEVEL_M = -0.6

# Academic Block 4: frame on the Google "AB 4" pin, and the level pad it stands on
AB4_ORIGIN_XY: tuple[float, float] = (371.3, 189.27)
AB4_ROT_RAD: float = 0.12
AB4_PAD_RING_XY: list[tuple[float, float]] = [
    (366.2, 148.4), (485.3, 162.7), (481.7, 192.5), (400.3, 182.7), (390.2, 266.1),
    (413.3, 274.9), (409.5, 306.7), (369.8, 301.9), (371.8, 285.0), (352.0, 282.6),
]
AB4_LEVEL_M = 2.4

# Business School, MBA canteen and Pandal share one traced frame; CIR has its own (Google satellite)
SOUTH_ORIGIN_XY: tuple[float, float] = (180.0, 200.0)
SOUTH_ROT_RAD: float = 0.095
SOUTH_PAD_UV: list[tuple[float, float]] = [(-70.0, -36.0), (18.0, -36.0), (18.0, -56.0), (60.0, -56.0), (60.0, 46.0), (-70.0, 46.0)]
SOUTH_LEVEL_M = 5.2
CIR_ORIGIN_XY: tuple[float, float] = (142.0, 302.0)
CIR_ROT_RAD: float = 0.10
CIR_PAD_UV: list[tuple[float, float]] = [(-37.0, -31.0), (44.0, -31.0), (44.0, 33.0), (-37.0, 33.0)]
CIR_LEVEL_M = 10.55


def _turned(origin: tuple[float, float], rot: float, u: float, v: float) -> tuple[float, float]:
    ca, sa = math.cos(rot), math.sin(rot)
    return (origin[0] + u * ca - v * sa, origin[1] + u * sa + v * ca)


def south_to_xy(u: float, v: float) -> tuple[float, float]:
    """Business School / MBA canteen / Pandal frame to world Blender XY."""
    return _turned(SOUTH_ORIGIN_XY, SOUTH_ROT_RAD, u, v)


def cir_to_xy(u: float, v: float) -> tuple[float, float]:
    """Corporate and Industry Relations frame to world Blender XY."""
    return _turned(CIR_ORIGIN_XY, CIR_ROT_RAD, u, v)


# The Central Library stands about 4 ft above AB-2 (owner's observation): the ground climbs from the
# front road up both side roads. Offsets are piecewise linear between these traced (u, v) lines.
LIBRARY_RISE_M = 1.2
RISE_U_LINES: tuple[float, ...] = (-6.0, 0.0, 5.0, 9.4, 10.8, 16.0, 24.0, 34.0, 46.0, 58.0, 70.0, 82.0, 95.0, 108.0, 119.0, 130.0)
RISE_V_LINES: tuple[float, ...] = (-63.0, -52.0, -40.0, -29.0, -18.0, -5.0, 8.0, 12.0, 15.0, 22.0, 29.0, 31.0, 44.0, 56.0, 64.0, 72.0)


def _ramp(x: float, x0: float, x1: float) -> float:
    """0 at x0 rising linearly to 1 at x1 (x0 < x1), clamped."""
    return max(0.0, min(1.0, (x - x0) / (x1 - x0)))


def xy_to_uv(x: float, y: float) -> tuple[float, float]:
    dx, dy = x - FRAME_ORIGIN_XY[0], y - FRAME_ORIGIN_XY[1]
    ca, sa = math.cos(FRAME_ROT_RAD), math.sin(FRAME_ROT_RAD)
    return (dx * ca + dy * sa - REGISTRATION_UV[0], -dx * sa + dy * ca - REGISTRATION_UV[1])


def rise_offset_uv(u: float, v: float) -> float:
    """Extra ground height at traced (u, v)."""
    along = _ramp(v, -63.0, -18.0) * (1.0 - _ramp(v, 56.0, 72.0))
    if along <= 0.0:
        return 0.0
    # AB-2 stays low: the bank sits just east of its wall, easing out where the parking road enters
    open_yard = _ramp(v, 12.0, 15.0) * (1.0 - _ramp(v, 29.0, 31.0))
    u_start = 9.4 - 15.4 * open_yard
    across = _ramp(u, u_start, 10.8) * (1.0 - _ramp(u, 108.0, 130.0))
    return LIBRARY_RISE_M * along * across


def rise_offset(x: float, y: float) -> float:
    return rise_offset_uv(*xy_to_uv(x, y))


def uv_to_xy(u: float, v: float) -> tuple[float, float]:
    """Convert traced (u, v) metres to world Blender XY."""
    ru, rv = u + REGISTRATION_UV[0], v + REGISTRATION_UV[1]
    ca, sa = math.cos(FRAME_ROT_RAD), math.sin(FRAME_ROT_RAD)
    return (
        FRAME_ORIGIN_XY[0] + ru * ca - rv * sa,
        FRAME_ORIGIN_XY[1] + ru * sa + rv * ca,
    )


def ring_to_xy(ring_uv: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [uv_to_xy(u, v) for u, v in ring_uv]


def rect_uv(u0: float, u1: float, v0: float, v1: float) -> list[tuple[float, float]]:
    """CCW rectangle corners (SW, SE, NE, NW)."""
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def terraces() -> list[tuple[list[tuple[float, float]], float, float, float]]:
    """(ring, level, apron, blend) building terraces, applied to the terrain in order."""
    return [
        (ring_to_xy(rect_uv(*TERRACE_RECT_UV)), TERRACE_LEVEL_M, TERRACE_APRON_M, TERRACE_BLEND_M),
        (CANTEEN_RING_XY, CANTEEN_LEVEL_M, 20.0, 32.0),
        (HOSTEL_RING_XY, HOSTEL_LEVEL_M, 8.0, 24.0),
        (AB4_PAD_RING_XY, AB4_LEVEL_M, 20.0, 28.0),
        ([south_to_xy(*p) for p in SOUTH_PAD_UV], SOUTH_LEVEL_M, 7.0, 20.0),
        ([cir_to_xy(*p) for p in CIR_PAD_UV], CIR_LEVEL_M, 4.0, 14.0),
    ]
