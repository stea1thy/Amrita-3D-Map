"""1-floor Engineering Workshop, Foundry, Chemical Lab & Lathe sheds behind AB-1."""

from __future__ import annotations

import math
from typing import Any

import bmesh

from .geom_helpers import (
    add_box_vc,
    add_gabled_roof_vc,
    add_glass_panel,
    local_to_world_2d,
    srgb_hex_to_linear_rgba,
)

# West zone (way/380926299): 130.5m x 48.3m behind AB-1 north-west courtyard alley
WORKSHOPS_WEST_CX = 234.65
WORKSHOPS_WEST_CY = -142.71
WORKSHOPS_WEST_ROT = 0.1171  # +6.71 deg

# East zone (way/380926300): 39.0m x 83.1m behind AB-1 north-east (Lathe & Mechanical Workshops)
WORKSHOPS_EAST_CX = 325.10
WORKSHOPS_EAST_CY = -152.24
WORKSHOPS_EAST_ROT = 0.1208  # +6.92 deg

# 6 parallel North-South sheds inside way/380926299: (lx, ly, half_len, half_wid)
WEST_SHED_SPECS: tuple[tuple[float, float, float, float], ...] = (
    (-56.0, 0.5, 19.5, 5.8),   # Far-west shed near Ettimadai Rd
    (-33.5, 0.0, 19.0, 5.8),   # Chemical Laboratory
    (-12.0, 0.5, 19.5, 5.8),   # West of Viruksa Garden
    (11.5, 1.0, 19.5, 5.8),    # East of Viruksa Garden
    (34.5, 1.5, 20.0, 6.0),    # Central-east workshop
    (55.0, 2.0, 19.5, 6.0),    # Foundry
)

# 4 parallel East-West sheds inside way/380926300: (lx, ly, half_len, half_wid)
EAST_SHED_SPECS: tuple[tuple[float, float, float, float], ...] = (
    (0.0, 31.5, 17.0, 5.6),    # North workshop shed
    (0.0, 11.0, 17.5, 5.8),    # Lathe Workshop
    (0.0, -10.5, 17.5, 5.8),   # Middle-south mechanical shed
    (0.0, -31.5, 17.0, 5.6),   # South mechanical shed
)


def _zone_params(is_west: bool) -> tuple[float, float, float, float, tuple[tuple[float, float, float, float], ...]]:
    if is_west:
        return (
            WORKSHOPS_WEST_CX,
            WORKSHOPS_WEST_CY,
            WORKSHOPS_WEST_ROT,
            WORKSHOPS_WEST_ROT + 0.5 * math.pi,
            WEST_SHED_SPECS,
        )
    return (
        WORKSHOPS_EAST_CX,
        WORKSHOPS_EAST_CY,
        WORKSHOPS_EAST_ROT,
        WORKSHOPS_EAST_ROT,
        EAST_SHED_SPECS,
    )


def get_workshop_shed_footprints(
    is_west: bool,
    pad_m: float = 0.8,
) -> list[list[tuple[float, float]]]:
    """Return CCW 2D world-space footprints for each individual shed (for tree/road clearance)."""
    zcx, zcy, zrot, shed_rot, specs = _zone_params(is_west)
    footprints: list[list[tuple[float, float]]] = []
    for lx, ly, half_len, half_wid in specs:
        sx, sy = local_to_world_2d(zcx, zcy, lx, ly, zrot)
        hx = half_len + pad_m
        hy = half_wid + pad_m
        corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        footprints.append([local_to_world_2d(sx, sy, px, py, shed_rot) for px, py in corners])
    return footprints


def append_workshop_shed(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    sx: float,
    sy: float,
    half_len: float,
    half_wid: float,
    shed_rot: float,
    offset_xyz: tuple[float, float, float],
    seed_idx: int = 0,
) -> list[tuple[float, float, float]]:
    """Append a single 1-floor industrial shed with light-grey pitched roof, ridge vents, and clerestory glass."""
    c_plinth = srgb_hex_to_linear_rgba("#9B958B")
    c_wall = srgb_hex_to_linear_rgba("#EFEAE1")
    c_roof = srgb_hex_to_linear_rgba("#D4D8DC")
    c_soffit = srgb_hex_to_linear_rgba("#767D84")
    c_vent = srgb_hex_to_linear_rgba("#5C646C")
    c_shutter = srgb_hex_to_linear_rgba("#485058")

    corners_local = [
        (-half_len, -half_wid),
        (half_len, -half_wid),
        (half_len, half_wid),
        (-half_len, half_wid),
    ]
    corners_world = [local_to_world_2d(sx, sy, px, py, shed_rot) for px, py in corners_local]
    zs = [terrain.sample(wx, wy) for wx, wy in corners_world]
    z_center = terrain.sample(sx, sy)

    z_bottom = min(zs) - 2.2
    z_base = max(z_center, max(zs) - 0.35)
    z_plinth = z_base + 0.38
    z_eave = z_base + 3.85
    z_peak = z_eave + 1.80

    # 1. Grounded plinth + 1-floor institutional shed body
    add_box_vc(
        bm, col_layer, sx, sy, z_bottom, z_plinth,
        half_len + 0.12, half_wid + 0.12, c_plinth, c_plinth,
        rot_rad=shed_rot, offset_xyz=offset_xyz,
    )
    add_box_vc(
        bm, col_layer, sx, sy, z_plinth, z_eave,
        half_len, half_wid, c_wall, c_wall,
        rot_rad=shed_rot, offset_xyz=offset_xyz,
    )

    # 2. Overhanging corrugated silver-grey pitched gable roof
    add_gabled_roof_vc(
        bm, col_layer, sx, sy, z_eave, z_peak,
        half_len + 0.55, half_wid + 0.55, c_roof, c_wall,
        rot_rad=shed_rot, ridge_along_x=True, soffit_rgba=c_soffit, offset_xyz=offset_xyz,
    )

    # 3. Ridge skylight / turbo-vent units along the roof crest
    vent_count = 5 if half_len >= 18.5 else 4
    vent_span = max(8.0, 2.0 * half_len - 8.0)
    for vi in range(vent_count):
        vx_loc = -0.5 * vent_span + (vent_span * vi) / max(1, vent_count - 1)
        vx, vy = local_to_world_2d(sx, sy, vx_loc, 0.0, shed_rot)
        add_box_vc(
            bm, col_layer, vx, vy, z_peak - 0.15, z_peak + 0.42,
            1.1, 0.65, c_vent, c_vent,
            rot_rad=shed_rot, offset_xyz=offset_xyz,
        )

    # 4. Clerestory industrial glass bays along both long walls
    bay_count = 5
    bay_span = max(8.0, 2.0 * half_len - 7.0)
    for side_idx, (facing_south, local_y) in enumerate(((True, -(half_wid + 0.06)), (False, +(half_wid + 0.06)))):
        for bi in range(bay_count):
            bx_loc = -0.5 * bay_span + (bay_span * bi) / max(1, bay_count - 1)
            bx, by = local_to_world_2d(sx, sy, bx_loc, 0.0, shed_rot)
            target_bm = win_lit_bm if ((seed_idx * 17 + side_idx * 7 + bi * 13) % 10) < 6 else win_dark_bm
            add_glass_panel(
                target_bm, bx, by, z_base + 2.05, z_base + 3.15,
                1.9, local_y, rot_rad=shed_rot, facing_south=facing_south,
            )

    # 5. Industrial roll-up shutter doors at both gable ends
    for end_sign in (-1.0, 1.0):
        gx, gy = local_to_world_2d(sx, sy, end_sign * (half_len + 0.04), 0.0, shed_rot)
        add_box_vc(
            bm, col_layer, gx, gy, z_base, z_base + 2.85,
            0.08, 1.9, c_shutter, c_shutter,
            rot_rad=shed_rot, offset_xyz=offset_xyz,
        )

    world_verts: list[tuple[float, float, float]] = []
    for wx, wy in corners_world:
        world_verts.append((wx, wy, z_bottom))
        world_verts.append((wx, wy, z_peak))
    return world_verts


def append_workshop_shed_compound(
    is_west: bool,
    bm: bmesh.types.BMesh,
    col_layer: Any,
    win_lit_bm: bmesh.types.BMesh | None,
    win_dark_bm: bmesh.types.BMesh | None,
    terrain: Any,
    offset_xyz: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Build all 1-floor sheds in the West (Chemical Lab / Foundry) or East (Lathe) compound."""
    zcx, zcy, zrot, shed_rot, specs = _zone_params(is_west)
    world_verts: list[tuple[float, float, float]] = []
    for idx, (lx, ly, half_len, half_wid) in enumerate(specs):
        sx, sy = local_to_world_2d(zcx, zcy, lx, ly, zrot)
        world_verts.extend(
            append_workshop_shed(
                bm=bm,
                col_layer=col_layer,
                win_lit_bm=win_lit_bm,
                win_dark_bm=win_dark_bm,
                terrain=terrain,
                sx=sx,
                sy=sy,
                half_len=half_len,
                half_wid=half_wid,
                shed_rot=shed_rot,
                offset_xyz=offset_xyz,
                seed_idx=(10 if is_west else 30) + idx,
            )
        )
    return world_verts
