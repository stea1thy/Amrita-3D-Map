"""Download and stitch zoom-18/19 Esri World Imagery satellite tiles into `pipeline/refs/<target>_sat.jpg`."""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import requests
from PIL import Image

PIPELINE_DIR = Path(__file__).resolve().parent
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

import config  # noqa: E402

ESRI_TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

BUILTIN_ALIASES: dict[str, str] = {
    "ab1": "way/380925364",
    "ab2": "way/380702789",
    "ab3": "way/380829415",
    "asb": "way/380829759",
    "library": "way/380702790",
    "centrallibrary": "way/380702790",
    "amriteshwari": "way/380925370",
    "canteen": "way/546394562",
    "maincanteen": "way/546394562",
    "shrine": "way/531394576",
    "playground": "way/528938316",
    "pool": "way/1210976885",
    "workshops": "way/380926299",
    "workshopswest": "way/380926299",
    "workshopseast": "way/380926300",
}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "target"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _latlon_to_tile_float(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    n = 2.0 ** zoom
    tx = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    ty = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return (tx, ty)


def _coords_from_geom(geom: dict[str, Any]) -> list[tuple[float, float]]:
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    pts: list[tuple[float, float]] = []
    if gtype == "Polygon":
        for ring in coords:
            pts.extend((float(p[1]), float(p[0])) for p in ring if len(p) >= 2)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                pts.extend((float(p[1]), float(p[0])) for p in ring if len(p) >= 2)
    elif gtype == "LineString":
        pts.extend((float(p[1]), float(p[0])) for p in coords if len(p) >= 2)
    elif gtype == "Point" and len(coords) >= 2:
        pts.append((float(coords[1]), float(coords[0])))
    return pts


def _resolve_latlon_bbox(target: str) -> tuple[str, str, tuple[float, float, float, float]]:
    q_norm = _norm(target)
    canonical_id = BUILTIN_ALIASES.get(q_norm)

    meta = json.loads(config.CAMPUS_META_PATH.read_text(encoding="utf-8")) if config.CAMPUS_META_PATH.exists() else {}
    items: list[dict[str, Any]] = list(meta.get("buildings") or []) + list(meta.get("inspectables") or [])

    matched_item: dict[str, Any] | None = None
    if canonical_id:
        matched_item = next((it for it in items if str(it.get("id")) == canonical_id), None)
    if matched_item is None:
        for check_fn in (
            lambda it: str(it.get("id", "")).lower() == target.lower(),
            lambda it: _norm(str(it.get("name", ""))) == q_norm,
            lambda it: q_norm in _norm(str(it.get("name", ""))),
            lambda it: any(q_norm in _norm(str(t)) for t in (it.get("tags") or [])),
        ):
            matched_item = next((it for it in items if check_fn(it)), None)
            if matched_item is not None:
                break

    target_id = str(matched_item.get("id")) if matched_item else (canonical_id or target)
    label = str(matched_item.get("name")) if matched_item and matched_item.get("name") else target_id

    if config.RAW_OSM_PATH.exists():
        raw_osm = json.loads(config.RAW_OSM_PATH.read_text(encoding="utf-8"))
        for feat in raw_osm.get("features", []):
            props = feat.get("properties") or {}
            fid = str(props.get("osm_id") or feat.get("id") or "")
            fname = str(props.get("name") or "")
            if fid.lower() == target_id.lower() or (fname and q_norm in _norm(fname) and not canonical_id):
                pts = _coords_from_geom(feat.get("geometry") or {})
                if pts:
                    lats = [p[0] for p in pts]
                    lons = [p[1] for p in pts]
                    return (label, fid, (min(lats), min(lons), max(lats), max(lons)))

    if matched_item is not None:
        bnds = matched_item.get("boundsXZ")
        if isinstance(bnds, (list, tuple)) and len(bnds) == 4:
            min_x, min_z, max_x, max_z = float(bnds[0]), float(bnds[1]), float(bnds[2]), float(bnds[3])
            s_lat, w_lon = config.local_xz_to_latlon(min_x, max_z)
            n_lat, e_lon = config.local_xz_to_latlon(max_x, min_z)
            return (label, target_id, (s_lat, w_lon, n_lat, e_lon))
        c = matched_item.get("center") or [0.0, 0.0, 0.0]
        r = max(16.0, float(matched_item.get("boundingRadius") or 24.0))
        s_lat, w_lon = config.local_xz_to_latlon(float(c[0]) - r, float(c[2]) + r)
        n_lat, e_lon = config.local_xz_to_latlon(float(c[0]) + r, float(c[2]) - r)
        return (label, target_id, (s_lat, w_lon, n_lat, e_lon))

    raise SystemExit(f"Target '{target}' not found in campus_meta.json or raw_osm.json.")


def _is_placeholder_tile(tile_img: Image.Image) -> bool:
    """Detect Esri's uniform grey 'Map data not yet available' placeholder tiles."""
    extrema = tile_img.convert("L").getextrema()
    # Real satellite tiles have rich luminance spread; Esri placeholder is flat ~204 grey + white text
    hist = tile_img.convert("RGB").getcolors(maxcolors=256)
    if hist is not None:
        # Dominant single grey pixel > 80% of 256x256=65536 indicates placeholder tile
        top_count, top_rgb = max(hist, key=lambda x: x[0])
        if top_count > 52000 and max(top_rgb) - min(top_rgb) < 12:
            return True
    return (extrema[1] - extrema[0]) < 18


def _fetch_stitched_satellite(
    south: float,
    west: float,
    north: float,
    east: float,
    preferred_zoom: int = 18,
) -> tuple[Image.Image, int, int]:
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})

    zooms = [preferred_zoom, 18, 17] if preferred_zoom > 18 else [preferred_zoom, 17]
    for zoom in zooms:
        x0_f, y1_f = _latlon_to_tile_float(south, west, zoom)
        x1_f, y0_f = _latlon_to_tile_float(north, east, zoom)
        tx0, tx1 = int(math.floor(x0_f)), int(math.floor(x1_f))
        ty0, ty1 = int(math.floor(y0_f)), int(math.floor(y1_f))
        nx, ny = (tx1 - tx0 + 1), (ty1 - ty0 + 1)
        if nx * ny > 30 and zoom > 17:
            continue

        canvas = Image.new("RGB", (nx * 256, ny * 256))
        ok = True
        for ix, tx in enumerate(range(tx0, tx1 + 1)):
            for iy, ty in enumerate(range(ty0, ty1 + 1)):
                url = ESRI_TILE_URL.format(z=zoom, y=ty, x=tx)
                try:
                    resp = session.get(url, timeout=15)
                    resp.raise_for_status()
                    tile_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    if _is_placeholder_tile(tile_img):
                        print(f"Tile z={zoom} ({tx},{ty}) is Esri placeholder; retrying lower zoom...")
                        ok = False
                        break
                except Exception as exc:
                    print(f"Tile z={zoom} ({tx},{ty}) failed ({exc}); retrying lower zoom...")
                    ok = False
                    break
                canvas.paste(tile_img, (ix * 256, iy * 256))
            if not ok:
                break
        if ok:
            px_left = max(0, int(round((x0_f - tx0) * 256)))
            px_top = max(0, int(round((y0_f - ty0) * 256)))
            px_right = min(canvas.width, int(round((x1_f - tx0) * 256)))
            px_bottom = min(canvas.height, int(round((y1_f - ty0) * 256)))
            cropped = canvas.crop((px_left, px_top, max(px_left + 16, px_right), max(px_top + 16, px_bottom)))
            return (cropped, zoom, nx * ny)

    raise RuntimeError("Failed to download Esri World Imagery tiles at any fallback zoom.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Esri World Imagery satellite reference for a campus target.")
    parser.add_argument("--target", required=True, help="Target name or OSM ID (e.g. ab1, ab3, way/380925364)")
    parser.add_argument("--margin", type=float, default=40.0, help="Margin in meters around building bounds (default 40)")
    parser.add_argument("--zoom", type=int, default=19, help="Preferred Esri tile zoom level (auto-falls back to 18/17 on placeholders)")
    parser.add_argument("--out", type=Path, default=None, help="Optional explicit output path")
    args = parser.parse_args()

    label, fid, (s_lat, w_lon, n_lat, e_lon) = _resolve_latlon_bbox(args.target)
    mid_lat = 0.5 * (s_lat + n_lat)
    dlat = args.margin / 111320.0
    dlon = args.margin / (111320.0 * max(0.2, math.cos(math.radians(mid_lat))))

    img, used_zoom, tile_count = _fetch_stitched_satellite(
        s_lat - dlat,
        w_lon - dlon,
        n_lat + dlat,
        e_lon + dlon,
        preferred_zoom=args.zoom,
    )

    max_dim = max(img.width, img.height)
    if max_dim > 1600:
        scale = 1600.0 / max_dim
        img = img.resize((int(round(img.width * scale)), int(round(img.height * scale))), Image.Resampling.LANCZOS)
    elif max_dim < 640:
        scale = 640.0 / max_dim
        img = img.resize((int(round(img.width * scale)), int(round(img.height * scale))), Image.Resampling.LANCZOS)

    out_path = args.out.resolve() if args.out else (config.REFS_DIR / f"{_slugify(args.target)}_sat.jpg")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="JPEG", quality=92)
    print(
        f"Fetched satellite ref for '{label}' ({fid}): zoom={used_zoom}, tiles={tile_count}, "
        f"size={img.width}x{img.height} -> {out_path}"
    )


if __name__ == "__main__":
    main()
