export interface TileGridRange {
  zoom: number;
  minTx: number;
  maxTx: number;
  minTy: number;
  maxTy: number;
  tilesX: number;
  tilesY: number;
}

export interface StitchedSatelliteResult extends TileGridRange {
  canvas: HTMLCanvasElement;
  failedTiles: number;
}

const TILE_PX = 256;
const CONCURRENCY = 8;

/** Project WGS84 (lat, lon) to fractional Web Mercator Slippy Map tile coordinates. */
export function latLonToTileFloat(
  lat: number,
  lon: number,
  zoom: number,
): { x: number; y: number } {
  const n = 2 ** zoom;
  const clampedLat = Math.max(-85.0511, Math.min(85.0511, lat));
  const latRad = (clampedLat * Math.PI) / 180;
  const x = ((lon + 180) / 360) * n;
  const y =
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;
  return { x, y };
}

/** Compute covering Web Mercator tile bounds for bbox [south, west, north, east]. */
export function bboxToTileRange(
  bbox: [number, number, number, number],
  zoom: number,
): TileGridRange {
  const [south, west, north, east] = bbox;
  const nw = latLonToTileFloat(north, west, zoom);
  const se = latLonToTileFloat(south, east, zoom);
  const minTx = Math.floor(Math.min(nw.x, se.x));
  const maxTx = Math.floor(Math.max(nw.x, se.x));
  const minTy = Math.floor(Math.min(nw.y, se.y));
  const maxTy = Math.floor(Math.max(nw.y, se.y));
  return {
    zoom,
    minTx,
    maxTx,
    minTy,
    maxTy,
    tilesX: Math.max(1, maxTx - minTx + 1),
    tilesY: Math.max(1, maxTy - minTy + 1),
  };
}

function loadTileImage(
  url: string,
  signal?: AbortSignal,
): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const img = new Image();
    img.crossOrigin = "anonymous";

    const cleanup = () => {
      img.onload = null;
      img.onerror = null;
      signal?.removeEventListener("abort", onAbort);
    };

    const onAbort = () => {
      cleanup();
      img.src = "";
      reject(new DOMException("Aborted", "AbortError"));
    };

    signal?.addEventListener("abort", onAbort, { once: true });

    img.onload = () => {
      cleanup();
      resolve(img);
    };
    img.onerror = () => {
      cleanup();
      reject(new Error(`Failed to load tile: ${url}`));
    };
    img.src = url;
  });
}

/** Fetch and stitch Esri World Imagery tiles covering the campus bbox onto an offscreen canvas. */
export async function stitchEsriSatelliteCanvas(
  bbox: [number, number, number, number],
  zoom = 17,
  signal?: AbortSignal,
): Promise<StitchedSatelliteResult> {
  const range = bboxToTileRange(bbox, zoom);
  const canvas = document.createElement("canvas");
  canvas.width = range.tilesX * TILE_PX;
  canvas.height = range.tilesY * TILE_PX;

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Could not acquire 2D canvas context for satellite tiles.");
  }

  ctx.fillStyle = "#4b5b49";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const jobs: Array<{ tx: number; ty: number }> = [];
  for (let ty = range.minTy; ty <= range.maxTy; ty++) {
    for (let tx = range.minTx; tx <= range.maxTx; tx++) {
      jobs.push({ tx, ty });
    }
  }

  let failedTiles = 0;
  let cursor = 0;

  const worker = async () => {
    while (cursor < jobs.length) {
      if (signal?.aborted) {
        throw new DOMException("Aborted", "AbortError");
      }
      const { tx, ty } = jobs[cursor++];
      const url = `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${zoom}/${ty}/${tx}`;
      try {
        const img = await loadTileImage(url, signal);
        if (!signal?.aborted) {
          ctx.drawImage(
            img,
            (tx - range.minTx) * TILE_PX,
            (ty - range.minTy) * TILE_PX,
            TILE_PX,
            TILE_PX,
          );
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          throw err;
        }
        failedTiles++;
      }
    }
  };

  await Promise.all(
    Array.from({ length: Math.min(CONCURRENCY, jobs.length) }, () => worker()),
  );

  if (failedTiles === jobs.length && jobs.length > 0) {
    throw new Error("All Esri World Imagery satellite tiles failed to load.");
  }

  return {
    ...range,
    canvas,
    failedTiles,
  };
}

/** Shoelace polygon area in square meters on the horizontal glTF XZ plane. */
export function polygonAreaM2XZ(pointsXZ: Array<[number, number]>): number {
  if (pointsXZ.length < 3) {
    return 0;
  }
  let area2 = 0;
  for (let i = 0; i < pointsXZ.length; i++) {
    const [x1, z1] = pointsXZ[i];
    const [x2, z2] = pointsXZ[(i + 1) % pointsXZ.length];
    area2 += x1 * z2 - x2 * z1;
  }
  return Math.abs(area2) * 0.5;
}

/** Generate a stable custom/<slug> ID from a building name. */
export function slugifyBuildingId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `custom/${slug || "new-building"}`;
}
