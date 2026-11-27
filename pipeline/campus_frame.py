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
CANTEEN_RING_XY: list[tuple[float, float]] = [(-338.5, 253.5), (-316.9, 260.9), (-324.8, 294.9), (-347.7, 288.9)]
CANTEEN_LEVEL_M = 10.8


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
        (CANTEEN_RING_XY, CANTEEN_LEVEL_M, 22.0, 34.0),
    ]
