"""Arched pedestrian footbridges declared in `overrides.json` (pure Python, shared by scene and routing).

Coordinates here are Blender XY (+X East, +Y North); `ground(x, y)` returns terrain height.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import config

DECK_CLEARANCE_M = 0.15


@dataclass(frozen=True)
class Footbridge:
    id: str
    name: str
    points: tuple[tuple[float, float], ...]
    width: float
    rise: float

    @property
    def length(self) -> float:
        return sum(math.dist(a, b) for a, b in zip(self.points, self.points[1:]))

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

    def deck_height(self, t: float, ground: Callable[[float, float], float]) -> float:
        """Walking surface: climbs from one landing, crests mid-span and comes down at the other."""
        z0, z1 = ground(*self.points[0]), ground(*self.points[-1])
        t = min(max(t, 0.0), 1.0)
        return z0 + (z1 - z0) * t + self.rise * math.sin(math.pi * t) + DECK_CLEARANCE_M

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
        if len(pts) < 2:
            raise ValueError(f"Footbridge {entry.get('id')} needs at least two points")
        bridges.append(Footbridge(
            id=str(entry["id"]),
            name=str(entry.get("name") or entry["id"]),
            points=tuple(pts),
            width=float(entry.get("width", 2.4)),
            rise=float(entry.get("rise", 2.5)),
        ))
    return bridges


def gully_tree_spots(overrides: dict[str, Any]) -> list[tuple[float, float, int, tuple[float, float]]]:
    """Low canopy trees either side of each deck, so the bridge reads as crossing a wooded gully."""
    spots: list[tuple[float, float, int, tuple[float, float]]] = []
    for bridge in load_footbridges(overrides):
        for side, fractions in ((-1.0, (0.14, 0.36, 0.58, 0.80)), (1.0, (0.24, 0.46, 0.68, 0.90))):
            for t in fractions:
                x, y, tx, ty = bridge.point_at(t)
                offset = side * (bridge.width / 2.0 + 4.2)
                spots.append((x - ty * offset, y + tx * offset, 1, (0.55, 0.75)))
    return spots
