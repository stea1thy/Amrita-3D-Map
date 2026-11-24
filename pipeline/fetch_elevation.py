"""Fetch a 25x25 terrain elevation grid via Open-Meteo Elevation API."""

from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np
import requests

try:
    from . import config
except ImportError:
    import config


def _parse_retry_after(header_value: str | None) -> float | None:
    """Parse numeric Retry-After header seconds if present."""
    if not header_value:
        return None
    try:
        return max(1.0, float(header_value.strip()))
    except ValueError:
        return None


def fetch_elevation_batch(
    session: requests.Session,
    coords: list[tuple[float, float]],
    max_retries: int = 5,
) -> list[float]:
    """Query Open-Meteo Elevation API for up to 80 (lat, lon) pairs with retries."""
    lat_str = ",".join(f"{lat:.6f}" for lat, _ in coords)
    lon_str = ",".join(f"{lon:.6f}" for _, lon in coords)
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json",
    }
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = session.get(
                config.OPEN_METEO_ELEVATION_URL,
                params={"latitude": lat_str, "longitude": lon_str},
                headers=headers,
                timeout=30,
            )

            if response.status_code in (429, 500, 502, 503, 504):
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                wait_s = retry_after or (min(20.0, 1.5 * (2**attempt)) + random.uniform(0.2, 0.8))
                last_error = RuntimeError(f"HTTP {response.status_code} from Open-Meteo")
                print(f"[retry {attempt + 1}/{max_retries}] {last_error}; waiting {wait_s:.1f}s...")
                time.sleep(wait_s)
                continue

            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            elevations = payload.get("elevation")

            if not isinstance(elevations, list) or len(elevations) != len(coords):
                raise ValueError(
                    f"Expected {len(coords)} elevations, got "
                    f"{len(elevations) if isinstance(elevations, list) else type(elevations).__name__}"
                )
            if any(val is None for val in elevations):
                raise ValueError("Received null elevation value in API response")

            return [round(float(val), 2) for val in elevations]

        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                wait_s = min(20.0, 1.5 * (2**attempt)) + random.uniform(0.2, 0.8)
                print(f"[retry {attempt + 1}/{max_retries}] {exc}; waiting {wait_s:.1f}s...")
                time.sleep(wait_s)

    raise RuntimeError(f"Failed Open-Meteo elevation batch after {max_retries} attempts: {last_error}")


def bilinear_elevation(
    lats: list[float],
    lons: list[float],
    matrix: np.ndarray,
    target_lat: float,
    target_lon: float,
) -> float:
    """Compute bilinearly interpolated elevation (meters) at (target_lat, target_lon)."""
    lat_arr = np.asarray(lats, dtype=float)
    lon_arr = np.asarray(lons, dtype=float)

    row_pos = float(np.interp(target_lat, lat_arr, np.arange(len(lats))))
    col_pos = float(np.interp(target_lon, lon_arr, np.arange(len(lons))))

    r0 = min(max(int(np.floor(row_pos)), 0), len(lats) - 2)
    c0 = min(max(int(np.floor(col_pos)), 0), len(lons) - 2)
    r1, c1 = r0 + 1, c0 + 1

    dr = row_pos - r0
    dc = col_pos - c0

    v00 = matrix[r0, c0]
    v01 = matrix[r0, c1]
    v10 = matrix[r1, c0]
    v11 = matrix[r1, c1]

    val = (
        v00 * (1.0 - dr) * (1.0 - dc)
        + v01 * (1.0 - dr) * dc
        + v10 * dr * (1.0 - dc)
        + v11 * dr * dc
    )
    return round(float(val), 2)


def main() -> None:
    """Build 25x25 campus elevation grid and write pipeline/data/elevation.json."""
    south, west, north, east = config.BBOX
    grid_n = config.ELEVATION_GRID_SIZE
    batch_size = config.ELEVATION_BATCH_SIZE

    lats = [round(float(v), 6) for v in np.linspace(south, north, grid_n)]
    lons = [round(float(v), 6) for v in np.linspace(west, east, grid_n)]

    coords = [(lat, lon) for lat in lats for lon in lons]
    total_points = len(coords)
    batches = [coords[i : i + batch_size] for i in range(0, total_points, batch_size)]

    print(
        f"Fetching {grid_n}x{grid_n} ({total_points}) elevation points "
        f"in {len(batches)} batches (max {batch_size}/batch)..."
    )

    session = requests.Session()
    flat_elevations: list[float] = []

    for idx, batch in enumerate(batches):
        batch_vals = fetch_elevation_batch(session, batch)
        flat_elevations.extend(batch_vals)
        if idx + 1 < len(batches):
            time.sleep(0.25)

    matrix = np.asarray(flat_elevations, dtype=float).reshape((grid_n, grid_n))
    origin_elev = bilinear_elevation(lats, lons, matrix, config.ORIGIN[0], config.ORIGIN[1])

    stats = {
        "min_m": round(float(np.min(matrix)), 2),
        "max_m": round(float(np.max(matrix)), 2),
        "mean_m": round(float(np.mean(matrix)), 2),
        "relief_m": round(float(np.max(matrix) - np.min(matrix)), 2),
        "origin_elevation_m": origin_elev,
    }

    output = {
        "metadata": {
            "source": "Open-Meteo Elevation API (Copernicus DEM 90m)",
            "endpoint": config.OPEN_METEO_ELEVATION_URL,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bbox": list(config.BBOX),
            "origin": list(config.ORIGIN),
            "grid_size": [grid_n, grid_n],
            "total_points": total_points,
            "batch_size": batch_size,
            "batch_count": len(batches),
            "axis_order": "elevations[lat_index_south_to_north][lon_index_west_to_east]",
            "stats": stats,
        },
        "lats": lats,
        "lons": lons,
        "elevations": [[round(float(v), 2) for v in row] for row in matrix.tolist()],
    }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with config.ELEVATION_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)

    size_kb = config.ELEVATION_PATH.stat().st_size / 1024.0
    print(f"Saved {config.ELEVATION_PATH} ({size_kb:.1f} KB)")
    print(
        "Elevation summary: "
        f"grid={grid_n}x{grid_n}, "
        f"points={total_points}, "
        f"batches={len(batches)}, "
        f"min={stats['min_m']}m, "
        f"max={stats['max_m']}m, "
        f"mean={stats['mean_m']}m, "
        f"origin={stats['origin_elevation_m']}m"
    )


if __name__ == "__main__":
    main()
