"""Build a terrain-snapped, hill-aware walking graph from OSM paths and campus elevation."""

from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from typing import Any

import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.ops import unary_union

try:
    from . import campus_frame, config, footbridges, terrain_utils
except ImportError:
    import campus_frame
    import config
    import footbridges
    import terrain_utils

WALKABLE_HIGHWAY_SUBTYPES = {
    "footway",
    "path",
    "pedestrian",
    "service",
    "residential",
    "steps",
    "unclassified",
}
MAX_EDGE_LENGTH_M = 18.0
STEPS_SPEED_MULTIPLIER = 0.85
TOBLER_FLAT_MAX_KMH = 6.0


class TerrainSampler:
    """Exact height sampler matching the graded upsampled 49x49 terrain mesh in build_scene.py."""

    def __init__(
        self,
        lats: list[float],
        lons: list[float],
        elevations: list[list[float]],
        datum_m: float,
        raw_osm: dict[str, Any] | None = None,
    ) -> None:
        raw_z = np.asarray(elevations, dtype=float) - datum_m
        up_rows = terrain_utils.upsample_1d_catmull_rom(raw_z)
        up_zs: np.ndarray = terrain_utils.upsample_1d_catmull_rom(up_rows.T).T

        south_y = -config.latlon_to_local_xz(lats[0], config.ORIGIN[1])[1]
        north_y = -config.latlon_to_local_xz(lats[-1], config.ORIGIN[1])[1]
        west_x = config.latlon_to_local_xz(config.ORIGIN[0], lons[0])[0]
        east_x = config.latlon_to_local_xz(config.ORIGIN[0], lons[-1])[0]

        ny, nx = up_zs.shape
        self.xs: np.ndarray = np.linspace(west_x, east_x, nx)
        self.ys: np.ndarray = np.linspace(south_y, north_y, ny)
        self.zs: np.ndarray = terrain_utils.grade_core_terrain_pads(self.xs, self.ys, up_zs, raw_osm)
        self.min_x = float(self.xs[0])
        self.max_x = float(self.xs[-1])
        self.min_y = float(self.ys[0])
        self.max_y = float(self.ys[-1])

    def sample_gltf_y(self, x_east: float, z_south: float) -> float:
        """Sample glTF Y elevation at local (x_east, z_south) coordinates."""
        bx = min(max(x_east, self.min_x), self.max_x)
        by = min(max(-z_south, self.min_y), self.max_y)

        nx = len(self.xs)
        ny = len(self.ys)
        fx = (bx - self.min_x) / (self.max_x - self.min_x) * (nx - 1)
        fy = (by - self.min_y) / (self.max_y - self.min_y) * (ny - 1)

        c = min(max(int(math.floor(fx)), 0), nx - 2)
        r = min(max(int(math.floor(fy)), 0), ny - 2)
        u = fx - c
        v = fy - r

        z00 = self.zs[r, c]
        z10 = self.zs[r, c + 1]
        z01 = self.zs[r + 1, c]
        z11 = self.zs[r + 1, c + 1]

        z = z00 + u * (z10 - z00) + v * (z11 - z10) if u >= v else z00 + v * (z01 - z00) + u * (z11 - z01)
        return float(z) + campus_frame.rise_offset(bx, by)


def _add_footbridge_line(lines: list[LineString], bridge: footbridges.Footbridge) -> None:
    """Add a bridge as a densified walkable line, splitting any path its landings rest on."""
    steps = max(2, int(math.ceil(bridge.length / 4.0)))
    deck = [bridge.point_at(i / steps)[:2] for i in range(steps + 1)]
    deck_xz = [(x, -y) for x, y in deck]
    for end in (0, -1):
        px, pz = deck_xz[end]
        for index, line in enumerate(lines):
            coords = list(line.coords)
            for seg, ((ax, az), (bx, bz)) in enumerate(zip(coords, coords[1:])):
                dx, dz = bx - ax, bz - az
                span2 = dx * dx + dz * dz
                if span2 <= 1e-8:
                    continue
                f = ((px - ax) * dx + (pz - az) * dz) / span2
                if 0.0 < f < 1.0 and math.hypot(px - ax - f * dx, pz - az - f * dz) <= 0.6:
                    deck_xz[end] = (px, pz)
                    lines[index] = LineString(coords[: seg + 1] + [(px, pz)] + coords[seg + 1 :])
                    break
    lines.append(LineString(deck_xz))


def tobler_speed_mps(slope: float) -> float:
    """Tobler's hiking function speed in m/s for grade slope = dh / dx."""
    speed_kmh = TOBLER_FLAT_MAX_KMH * math.exp(-3.5 * abs(slope + 0.05))
    return max(0.15, speed_kmh / 3.6)


def _extract_lines(geom: Any) -> list[LineString]:
    """Flatten Shapely geometry into non-empty LineString objects."""
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom] if len(geom.coords) >= 2 else []
    if isinstance(geom, MultiLineString):
        return [g for g in geom.geoms if len(g.coords) >= 2]
    if hasattr(geom, "geoms"):
        out: list[LineString] = []
        for g in geom.geoms:
            out.extend(_extract_lines(g))
        return out
    return []


def _largest_component_nodes(
    node_count: int,
    edges: list[tuple[int, int, bool]],
) -> set[int]:
    """Return node IDs belonging to the largest connected component."""
    adj: dict[int, list[int]] = defaultdict(list)
    for u, v, _ in edges:
        adj[u].append(v)
        adj[v].append(u)

    visited: set[int] = set()
    best_comp: set[int] = set()
    for start in range(node_count):
        if start in visited:
            continue
        comp: set[int] = set()
        queue = deque([start])
        visited.add(start)
        while queue:
            curr = queue.popleft()
            comp.add(curr)
            for nxt in adj[curr]:
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        if len(comp) > len(best_comp):
            best_comp = comp
    return best_comp


def main() -> None:
    """Generate walk_graph.json and update campus_meta.json with nearestNodeId."""
    raw_osm = json.loads(config.RAW_OSM_PATH.read_text(encoding="utf-8"))
    elevation = json.loads(config.ELEVATION_PATH.read_text(encoding="utf-8"))
    campus_meta = json.loads(config.CAMPUS_META_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(config.OVERRIDES_PATH.read_text(encoding="utf-8"))

    datum_m = float(elevation["metadata"]["stats"]["origin_elevation_m"])
    terrain = TerrainSampler(
        lats=elevation["lats"],
        lons=elevation["lons"],
        elevations=elevation["elevations"],
        datum_m=datum_m,
        raw_osm=raw_osm,
    )

    tb = campus_meta["terrainBounds"]
    clip_rect: Any = box(
        float(tb["minX"]) + 1.5,
        float(tb["minZ"]) + 1.5,
        float(tb["maxX"]) - 1.5,
        float(tb["maxZ"]) - 1.5,
    )

    campus_ctx = terrain_utils.extract_campus_boundary_and_rail(raw_osm)
    boundary_ring = campus_ctx["boundary_ring"]
    rail_lines = campus_ctx["rail_lines"]
    if len(boundary_ring) >= 3:
        boundary_xz = Polygon([(x, -y) for x, y in boundary_ring]).buffer(15.0)
        if not boundary_xz.is_empty:
            clip_rect = clip_rect.intersection(boundary_xz)
    if rail_lines:
        xs_rail = np.linspace(float(tb["minX"]) - 20.0, float(tb["maxX"]) + 20.0, 65)
        north_xz: list[tuple[float, float]] = []
        for xr in xs_rail:
            ry = terrain_utils.rail_north_y_at_x(rail_lines, float(xr))
            if ry is not None:
                north_xz.append((float(xr), -(ry - 12.0)))
        if len(north_xz) >= 2:
            xz_poly = Polygon(
                north_xz
                + [
                    (float(tb["maxX"]) + 40.0, float(tb["minZ"]) - 40.0),
                    (float(tb["minX"]) - 40.0, float(tb["minZ"]) - 40.0),
                ]
            ).buffer(0)
            if not xz_poly.is_empty:
                clip_rect = clip_rect.intersection(xz_poly)

    walkable_lines: list[LineString] = []
    step_segments: list[tuple[float, float, float, float]] = []

    excluded_ids = {str(x) for x in (overrides.get("exclude_ids") or [])}
    for feat in raw_osm.get("features", []):
        props = feat.get("properties", {})
        if props.get("layer") != "path" or str(feat.get("id", "")) in excluded_ids:
            continue
        subtype = str(props.get("subtype", ""))
        if subtype not in WALKABLE_HIGHWAY_SUBTYPES:
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") != "LineString":
            continue

        xz_pts = [config.latlon_to_local_xz(pt[1], pt[0]) for pt in config.path_coords(feat)]
        if len(xz_pts) < 2:
            continue
        clipped = LineString(xz_pts).intersection(clip_rect)
        for line in _extract_lines(clipped):
            walkable_lines.append(line)
            if subtype == "steps":
                coords = list(line.coords)
                for a, b in zip(coords, coords[1:]):
                    step_segments.append((a[0], a[1], b[0], b[1]))

    for custom_road in overrides.get("custom_roads") or []:
        if not isinstance(custom_road, dict):
            continue
        subtype = str(custom_road.get("subtype", "residential"))
        if subtype not in WALKABLE_HIGHWAY_SUBTYPES:
            continue
        raw_pts = custom_road.get("points") or []
        if len(raw_pts) < 2:
            continue
        xz_pts = [config.latlon_to_local_xz(float(pt[0]), float(pt[1])) for pt in raw_pts]
        clipped = LineString(xz_pts).intersection(clip_rect)
        for line in _extract_lines(clipped):
            walkable_lines.append(line)

    bridges = footbridges.load_footbridges(overrides)
    for bridge in bridges:
        _add_footbridge_line(walkable_lines, bridge)

    if not walkable_lines:
        raise RuntimeError("No walkable OSM paths found inside terrain bounds")

    noded = unary_union(walkable_lines)
    noded_lines = _extract_lines(noded)

    raw_key_to_id: dict[tuple[float, float], int] = {}
    raw_coords: list[tuple[float, float]] = []
    raw_edges: list[tuple[int, int, bool]] = []

    def _get_raw_id(x: float, z: float) -> int:
        key = (round(x, 2), round(z, 2))
        if key not in raw_key_to_id:
            raw_key_to_id[key] = len(raw_coords)
            raw_coords.append((x, z))
        return raw_key_to_id[key]

    def _is_step_edge(ax: float, az: float, bx: float, bz: float) -> bool:
        if not step_segments:
            return False
        mx = 0.5 * (ax + bx)
        mz = 0.5 * (az + bz)
        for sx0, sz0, sx1, sz1 in step_segments:
            dx, dz = sx1 - sx0, sz1 - sz0
            len2 = dx * dx + dz * dz
            if len2 <= 1e-8:
                continue
            t = max(0.0, min(1.0, ((mx - sx0) * dx + (mz - sz0) * dz) / len2))
            px, pz = sx0 + t * dx, sz0 + t * dz
            if (mx - px) ** 2 + (mz - pz) ** 2 < 0.25:
                return True
        return False

    for line in noded_lines:
        coords = list(line.coords)
        for (ax, az), (bx, bz) in zip(coords, coords[1:]):
            u = _get_raw_id(ax, az)
            v = _get_raw_id(bx, bz)
            if u != v:
                raw_edges.append((u, v, _is_step_edge(ax, az, bx, bz)))

    main_nodes = _largest_component_nodes(len(raw_coords), raw_edges)

    # Subdivide long edges and quantize nodes to 1 decimal place
    q_key_to_id: dict[tuple[float, float], int] = {}
    q_xz: list[tuple[float, float]] = []
    unique_edges: dict[tuple[int, int], bool] = {}

    def _get_quantized_id(x: float, z: float) -> int:
        qx = round(float(x), 1)
        qz = round(float(z), 1)
        key = (qx, qz)
        if key not in q_key_to_id:
            q_key_to_id[key] = len(q_xz)
            q_xz.append(key)
        return q_key_to_id[key]

    for u_raw, v_raw, is_steps in raw_edges:
        if u_raw not in main_nodes or v_raw not in main_nodes:
            continue
        ax, az = raw_coords[u_raw]
        bx, bz = raw_coords[v_raw]
        horiz = math.hypot(bx - ax, bz - az)
        segs = max(1, int(math.ceil(horiz / MAX_EDGE_LENGTH_M)))

        prev_id = _get_quantized_id(ax, az)
        for s in range(1, segs + 1):
            t = s / segs
            px = ax + t * (bx - ax)
            pz = az + t * (bz - az)
            curr_id = _get_quantized_id(px, pz)
            if curr_id != prev_id:
                ekey = (min(prev_id, curr_id), max(prev_id, curr_id))
                unique_edges[ekey] = unique_edges.get(ekey, False) or is_steps
                prev_id = curr_id

    def _node_height(qx: float, qz: float) -> float:
        for bridge in bridges:
            t, dist = bridge.project(qx, -qz)
            if dist <= 0.2:
                return bridge.deck_height(t, lambda x, y: terrain.sample_gltf_y(x, -y))
        return terrain.sample_gltf_y(qx, qz)

    nodes: list[list[float]] = [[qx, round(_node_height(qx, qz), 1), qz] for qx, qz in q_xz]

    edges: list[list[Any]] = []
    for (u, v), is_steps in sorted(unique_edges.items()):
        x1, y1, z1 = nodes[u]
        x2, y2, z2 = nodes[v]
        horiz = math.hypot(x2 - x1, z2 - z1)
        dh = y2 - y1
        dist_3d = math.hypot(horiz, dh)
        step_factor = STEPS_SPEED_MULTIPLIER if is_steps else 1.0

        speed_uv = tobler_speed_mps(dh / max(horiz, 0.05)) * step_factor
        speed_vu = tobler_speed_mps(-dh / max(horiz, 0.05)) * step_factor
        time_uv = dist_3d / speed_uv
        time_vu = dist_3d / speed_vu

        edges.append([u, v, round(dist_3d, 1), round(time_uv, 1), round(time_vu, 1)])

    # Verify final quantized graph is a single connected component
    final_comp = _largest_component_nodes(len(nodes), [(e[0], e[1], False) for e in edges])
    if len(final_comp) != len(nodes):
        raise RuntimeError(
            f"Final walk graph is disconnected: {len(final_comp)}/{len(nodes)} reachable nodes"
        )

    walk_graph = {
        "metadata": {
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "units": "meters_and_seconds",
            "toblerMaxSpeedMps": round(TOBLER_FLAT_MAX_KMH / 3.6, 4),
            "coordinateSpace": "glTF Y-up (+X East, +Y Up, +Z South)",
        },
        "nodes": nodes,
        "edges": edges,
    }

    config.WALK_GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with config.WALK_GRAPH_PATH.open("w", encoding="utf-8") as fh:
        json.dump(walk_graph, fh, separators=(",", ":"))

    # Snap every building centroid in campus_meta.json to nearest reachable graph node
    snap_dists: list[float] = []
    named_snap_dists: list[float] = []
    for b in campus_meta.get("buildings", []):
        bx, _, bz = b["center"]
        best_id = 0
        best_d2 = float("inf")
        for nid, (nx, _, nz) in enumerate(nodes):
            d2 = (nx - bx) ** 2 + (nz - bz) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_id = nid
        b["nearestNodeId"] = best_id
        d = math.sqrt(best_d2)
        snap_dists.append(d)
        if b.get("isNamed"):
            named_snap_dists.append(d)

    with config.CAMPUS_META_PATH.open("w", encoding="utf-8") as fh:
        json.dump(campus_meta, fh, indent=2, ensure_ascii=False)

    size_kb = config.WALK_GRAPH_PATH.stat().st_size / 1024.0
    avg_snap = sum(snap_dists) / len(snap_dists) if snap_dists else 0.0
    max_snap = max(snap_dists) if snap_dists else 0.0
    max_named_snap = max(named_snap_dists) if named_snap_dists else 0.0

    print(f"Saved {config.WALK_GRAPH_PATH} ({size_kb:.1f} KB)")
    print(
        f"Walk graph summary: nodes={len(nodes)}, edges={len(edges)}, "
        f"connected=True, buildings_snapped={len(snap_dists)}"
    )
    print(
        f"Snap distances: avg={avg_snap:.1f}m, max_all={max_snap:.1f}m, "
        f"max_named={max_named_snap:.1f}m"
    )


if __name__ == "__main__":
    main()
