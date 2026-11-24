import type * as THREE from "three";
import type { InspectableFeature } from "@/types/campus";

const EARTH_RADIUS_M = 6378137.0;

/** Project glTF XZ meters back to approximate [lat, lon] degrees around campus origin. */
export function localXZToLatLon(
  xEast: number,
  zSouth: number,
  origin: [number, number] = [10.9027, 76.9006],
): [number, number] {
  const [originLat, originLon] = origin;
  const lat = originLat - (zSouth / EARTH_RADIUS_M) * (180 / Math.PI);
  const lon =
    originLon +
    (xEast / (EARTH_RADIUS_M * Math.cos((originLat * Math.PI) / 180))) *
      (180 / Math.PI);
  return [Number(lat.toFixed(6)), Number(lon.toFixed(6))];
}

/** Ray-casting 2D point-in-polygon check in glTF XZ plane. */
export function pointInPolygonXZ(
  x: number,
  z: number,
  ring: Array<[number, number]>,
): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, zi] = ring[i];
    const [xj, zj] = ring[j];
    const intersects =
      zi > z !== zj > z &&
      x < ((xj - xi) * (z - zi)) / (zj - zi || 1e-12) + xi;
    if (intersects) {
      inside = !inside;
    }
  }
  return inside;
}

function findInspectableNodeName(obj: THREE.Object3D | null): string | null {
  let curr: THREE.Object3D | null = obj;
  while (curr) {
    if (curr.name.startsWith("BLDG_") || curr.name.startsWith("BRIDGE_")) {
      return curr.name;
    }
    curr = curr.parent;
  }
  return null;
}

function matchStaticBuildingAtPoint(
  x: number,
  z: number,
  staticFeatures: InspectableFeature[],
): InspectableFeature | null {
  for (const feat of staticFeatures) {
    const b = feat.boundsXZ;
    if (
      b &&
      x >= b[0] - 1.5 &&
      x <= b[2] + 1.5 &&
      z >= b[1] - 1.5 &&
      z <= b[3] + 1.5 &&
      feat.footprintXZ &&
      pointInPolygonXZ(x, z, feat.footprintXZ)
    ) {
      return feat;
    }
  }

  let best: InspectableFeature | null = null;
  let bestDist2 = 25.0; // within 5m of footprint box / center fallback
  for (const feat of staticFeatures) {
    const b = feat.boundsXZ;
    if (!b) {
      continue;
    }
    const dx = Math.max(b[0] - x, 0, x - b[2]);
    const dz = Math.max(b[1] - z, 0, z - b[3]);
    const d2 = dx * dx + dz * dz;
    if (d2 < bestDist2) {
      bestDist2 = d2;
      best = feat;
    }
  }
  return best;
}

/** Resolve any hovered/clicked glTF mesh hit into an InspectableFeature for ?debug=1. */
export function resolveDebugHit(
  object: THREE.Object3D,
  hitPoint: THREE.Vector3,
  byMeshName: Map<string, InspectableFeature>,
  staticBuildings: InspectableFeature[],
  origin: [number, number] = [10.9027, 76.9006],
  includeFallbackMesh = false,
): InspectableFeature | null {
  const namedNode = findInspectableNodeName(object);
  if (namedNode) {
    const found = byMeshName.get(namedNode);
    if (found) {
      return found;
    }
  }

  const objName = object.name || "SceneMesh";
  if (objName.startsWith("STATIC_Buildings")) {
    const matched = matchStaticBuildingAtPoint(
      hitPoint.x,
      hitPoint.z,
      staticBuildings,
    );
    if (matched) {
      return matched;
    }
  }

  if (!includeFallbackMesh) {
    return null;
  }

  const meshKey = objName.replace(/[^A-Za-z0-9_-]+/g, "_");
  return {
    id: `mesh/${meshKey}`,
    meshName: objName,
    kind: "mesh",
    name: objName,
    isNamed: false,
    category: "default",
    tags: [],
    departments: [],
    floors: 0,
    heightM: Number(hitPoint.y.toFixed(1)),
    center: [
      Number(hitPoint.x.toFixed(2)),
      Number(hitPoint.y.toFixed(2)),
      Number(hitPoint.z.toFixed(2)),
    ],
    boundingRadius: 12,
    latLon: localXZToLatLon(hitPoint.x, hitPoint.z, origin),
    rawTags: { mesh: objName },
  };
}
