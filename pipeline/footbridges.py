"""Raised pedestrian footbridges declared in `overrides.json` (pure Python, shared by scene and routing).

The first and last points rest on the ground; every point between them is at one raised deck level,
so the end segments are stair flights. Coordinates are Blender XY (+X East, +Y North);
`ground(x, y)` returns terrain height.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import config

LANDING_LIFT_M = 0.15
SAMPLES_PER_SEGMENT = 8


@dataclass(frozen=True)
class Footbridge:
    id: str
    name: str
    points: tuple[tuple[float, float], ...]
    width: float
    clearance: float
    roof: bool

    @property
    def length(self) -> float:
        return sum(math.dist(a, b) for a, b in zip(self.points, self.points[1:]))

    def vertex_fractions(self) -> list[float]:
        """Arc-length fraction of every point."""
        run, out = 0.0, [0.0]
        for a, b in zip(self.points, self.points[1:]):
            run += math.dist(a, b)
            out.append(run / self.length)
        return out

    def point_at(self, t: float) -> tuple[float, float, float, float]:
        """(x, y, unit tangent x, unit tangent y) at arc-length fraction t."""
        target = min(max(t, 0.0), 1.0) * self.length
        segments = list(zip(self.points, self.points[1:]))
        for index, (a, b) in enumerate(segments):
            span = math.dist(a, b)
            if target <= span or index == len(segments) - 1:
                f = target / span
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f,
                        (b[0] - a[0]) / span, (b[1] - a[1]) / span)
            target -= span
        raise ValueError(f"Footbridge {self.id} has no segments")

    def deck_level(self, ground: Callable[[float, float], float]) -> float:
        """Height of the raised span: `clearance` above the highest ground beneath it."""
        zs: list[float] = []
        for a, b in zip(self.points[1:-1], self.points[2:-1]):
            for i in range(SAMPLES_PER_SEGMENT + 1):
                f = i / SAMPLES_PER_SEGMENT
                zs.append(ground(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
        return max(zs) + self.clearance

    def deck_height(self, t: float, ground: Callable[[float, float], float]) -> float:
        """Walking surface at arc-length fraction t."""
        level = self.deck_level(ground)
        heights = [ground(*self.points[0]) + LANDING_LIFT_M]
        heights += [level] * (len(self.points) - 2)
        heights.append(ground(*self.points[-1]) + LANDING_LIFT_M)
        fractions = self.vertex_fractions()
        t = min(max(t, 0.0), 1.0)
        for i, (f0, f1) in enumerate(zip(fractions, fractions[1:])):
            if t <= f1 or i == len(fractions) - 2:
                return heights[i] + (heights[i + 1] - heights[i]) * (t - f0) / (f1 - f0)
        raise ValueError(f"Footbridge {self.id} has no segments")

    def vertex_sides(self, index: int, half: float) -> tuple[tuple[float, float], tuple[float, float]]:
        """(right, left) edge points `half` out from points[index], mitred where the bridge turns."""
        p = self.points[index]
        segments = list(zip(self.points, self.points[1:]))[max(index - 1, 0):index + 1]
        normals = [((b[1] - a[1]) / math.dist(a, b), (a[0] - b[0]) / math.dist(a, b)) for a, b in segments]
        (ax, ay), (bx, by) = normals[0], normals[-1]
        scale = half / (1.0 + ax * bx + ay * by)
        mx, my = (ax + bx) * scale, (ay + by) * scale
        return (p[0] + mx, p[1] + my), (p[0] - mx, p[1] - my)

    def project(self, x: float, y: float) -> tuple[float, float]:
        """(arc-length fraction, distance) of the closest point on the bridge centre line."""
        best_t, best_d, run = 0.0, float("inf"), 0.0
        for a, b in zip(self.points, self.points[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            span2 = dx * dx + dy * dy
            f = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / span2))
            d = math.hypot(x - (a[0] + f * dx), y - (a[1] + f * dy))
            if d < best_d:
                best_t, best_d = (run + f * math.sqrt(span2)) / self.length, d
            run += math.sqrt(span2)
        return best_t, best_d


def load_footbridges(overrides: dict[str, Any]) -> list[Footbridge]:
    bridges: list[Footbridge] = []
    for entry in overrides.get("footbridges") or []:
        pts: list[tuple[float, float]] = []
        for lat, lon in entry["points"]:
            x, z = config.latlon_to_local_xz(float(lat), float(lon))
            pts.append((x, -z))
        if len(pts) < 4:
            raise ValueError(f"Footbridge {entry.get('id')} needs two ground ends and a raised span")
        bridges.append(Footbridge(
            id=str(entry["id"]),
            name=str(entry.get("name") or entry["id"]),
            points=tuple(pts),
            width=float(entry.get("width", 2.4)),
            clearance=float(entry.get("clearance", 3.2)),
            roof=bool(entry.get("roof", False)),
        ))
    return bridges


def gully_tree_spots(overrides: dict[str, Any]) -> list[tuple[float, float, int, tuple[float, float]]]:
    """Low canopy trees either side of each raised span, so the bridge reads as crossing a wooded gully."""
    spots: list[tuple[float, float, int, tuple[float, float]]] = []
    for bridge in load_footbridges(overrides):
        first, last = bridge.vertex_fractions()[1], bridge.vertex_fractions()[-2]
        for side, fractions in ((-1.0, (0.05, 0.3, 0.55)), (1.0, (0.18, 0.43, 0.68))):
            for f in fractions:
                x, y, tx, ty = bridge.point_at(first + (last - first) * f)
                offset = side * (bridge.width / 2.0 + 4.4)
                spots.append((x - ty * offset, y + tx * offset, 1, (0.55, 0.75)))
    return spots
