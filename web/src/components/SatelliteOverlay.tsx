"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { localXZToLatLon } from "@/lib/debugPicking";
import {
  latLonToTileFloat,
  stitchEsriSatelliteCanvas,
  type StitchedSatelliteResult,
} from "@/lib/satelliteTiles";

const DRACO_PATH = "/draco/";
const MODEL_PATH = "/models/campus.glb";
const NOOP_RAYCAST = () => {};

interface SatelliteOverlayProps {
  enabled: boolean;
  opacity: number;
  bbox: [number, number, number, number];
  origin: [number, number];
  traceActive: boolean;
  onTraceClick: (point: THREE.Vector3) => void;
  onTraceHover?: (point: THREE.Vector3 | null) => void;
  onStatusChange?: (status: "idle" | "loading" | "ready" | "error") => void;
}

function isTerrainGroundMesh(obj: THREE.Object3D): obj is THREE.Mesh {
  if (!(obj instanceof THREE.Mesh)) {
    return false;
  }
  const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
  const hasGroundMat = mats.some((m) =>
    m?.name?.startsWith("MAT_TerrainGround"),
  );
  if (hasGroundMat) {
    return true;
  }
  let curr: THREE.Object3D | null = obj;
  while (curr) {
    if (curr.name.startsWith("TERRAIN_Campus")) {
      return !mats.some((m) => m?.name?.startsWith("MAT_TerrainSkirt"));
    }
    curr = curr.parent;
  }
  return false;
}

function buildDrapedTerrainGeometry(
  scene: THREE.Object3D,
  grid: StitchedSatelliteResult,
  origin: [number, number],
): THREE.BufferGeometry | null {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const tempPos = new THREE.Vector3();

  const { zoom, minTx, maxTx, minTy, maxTy, tilesX, tilesY } = grid;
  const maxTxEdge = maxTx + 1;
  const maxTyEdge = maxTy + 1;
  let globalVertexOffset = 0;

  scene.updateWorldMatrix(true, true);

  scene.traverse((obj) => {
    if (!isTerrainGroundMesh(obj)) {
      return;
    }

    const srcGeom = obj.geometry;
    const posAttr = srcGeom.getAttribute("position");
    if (!posAttr) {
      return;
    }

    // If geometry uses multiple material groups, restrict to MAT_TerrainGround group(s)
    const mats = Array.isArray(obj.material) ? obj.material : null;
    const indexAttr = srcGeom.getIndex();
    const totalCount = indexAttr ? indexAttr.count : posAttr.count;
    const ranges: Array<{ start: number; count: number }> = [];

    if (mats && srcGeom.groups.length > 0) {
      for (const grp of srcGeom.groups) {
        const mat = mats[grp.materialIndex ?? 0];
        if (mat?.name?.startsWith("MAT_TerrainGround")) {
          ranges.push({ start: grp.start, count: grp.count });
        }
      }
    }
    if (ranges.length === 0) {
      ranges.push({ start: 0, count: totalCount });
    }

    const vertCount = posAttr.count;
    const worldX = new Float64Array(vertCount);
    const worldY = new Float64Array(vertCount);
    const worldZ = new Float64Array(vertCount);
    const tileFX = new Float64Array(vertCount);
    const tileFY = new Float64Array(vertCount);
    const inBounds = new Uint8Array(vertCount);

    for (let i = 0; i < vertCount; i++) {
      tempPos.fromBufferAttribute(posAttr, i).applyMatrix4(obj.matrixWorld);
      worldX[i] = tempPos.x;
      worldY[i] = tempPos.y;
      worldZ[i] = tempPos.z;
      const [lat, lon] = localXZToLatLon(tempPos.x, tempPos.z, origin);
      const tf = latLonToTileFloat(lat, lon, zoom);
      tileFX[i] = tf.x;
      tileFY[i] = tf.y;
      if (
        tf.x >= minTx &&
        tf.x <= maxTxEdge &&
        tf.y >= minTy &&
        tf.y <= maxTyEdge
      ) {
        inBounds[i] = 1;
      }
    }

    const remap = new Int32Array(vertCount).fill(-1);
    const getOrAddVertex = (srcIdx: number): number => {
      if (remap[srcIdx] !== -1) {
        return remap[srcIdx];
      }
      const nextIdx = globalVertexOffset++;
      remap[srcIdx] = nextIdx;
      positions.push(worldX[srcIdx], worldY[srcIdx] + 0.22, worldZ[srcIdx]);
      const u = (tileFX[srcIdx] - minTx) / tilesX;
      const v = 1 - (tileFY[srcIdx] - minTy) / tilesY;
      uvs.push(u, v);
      return nextIdx;
    };

    for (const range of ranges) {
      const end = Math.min(totalCount, range.start + range.count);
      for (let k = range.start; k + 2 < end; k += 3) {
        const i0 = indexAttr ? indexAttr.getX(k) : k;
        const i1 = indexAttr ? indexAttr.getX(k + 1) : k + 1;
        const i2 = indexAttr ? indexAttr.getX(k + 2) : k + 2;
        if (!inBounds[i0] || !inBounds[i1] || !inBounds[i2]) {
          continue;
        }
        indices.push(
          getOrAddVertex(i0),
          getOrAddVertex(i1),
          getOrAddVertex(i2),
        );
      }
    }
  });

  if (indices.length === 0) {
    return null;
  }

  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  out.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  out.setIndex(indices);
  out.computeVertexNormals();
  return out;
}

export default function SatelliteOverlay({
  enabled,
  opacity,
  bbox,
  origin,
  traceActive,
  onTraceClick,
  onTraceHover,
  onStatusChange,
}: SatelliteOverlayProps) {
  const { scene } = useGLTF(MODEL_PATH, DRACO_PATH);
  const [stitched, setStitched] = useState<StitchedSatelliteResult | null>(
    null,
  );
  const fetchedKeyRef = useRef<string | null>(null);
  const onStatusRef = useRef(onStatusChange);

  useEffect(() => {
    onStatusRef.current = onStatusChange;
  }, [onStatusChange]);

  const bboxKey = `${bbox[0]},${bbox[1]},${bbox[2]},${bbox[3]}`;

  useEffect(() => {
    if (!enabled) {
      return;
    }
    if (fetchedKeyRef.current === bboxKey && stitched) {
      onStatusRef.current?.("ready");
      return;
    }

    const controller = new AbortController();
    onStatusRef.current?.("loading");

    stitchEsriSatelliteCanvas(bbox, 17, controller.signal)
      .then((res) => {
        if (controller.signal.aborted) {
          return;
        }
        fetchedKeyRef.current = bboxKey;
        setStitched(res);
        onStatusRef.current?.("ready");
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        onStatusRef.current?.("error");
      });

    return () => controller.abort();
  }, [enabled, bbox, bboxKey, stitched]);

  const texture = useMemo(() => {
    if (!stitched) {
      return null;
    }
    const tex = new THREE.CanvasTexture(stitched.canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.anisotropy = 4;
    tex.needsUpdate = true;
    return tex;
  }, [stitched]);

  useEffect(() => {
    return () => {
      texture?.dispose();
    };
  }, [texture]);

  const drapedGeometry = useMemo(() => {
    if (!stitched) {
      return null;
    }
    return buildDrapedTerrainGeometry(scene, stitched, origin);
  }, [scene, stitched, origin]);

  useEffect(() => {
    return () => {
      drapedGeometry?.dispose();
    };
  }, [drapedGeometry]);

  if (!enabled || !texture || !drapedGeometry) {
    return null;
  }

  return (
    <mesh
      name="DEBUG_SatelliteOverlay"
      geometry={drapedGeometry}
      raycast={traceActive ? undefined : NOOP_RAYCAST}
      onClick={(e: ThreeEvent<MouseEvent>) => {
        if (!traceActive || e.delta > 6) {
          return;
        }
        e.stopPropagation();
        onTraceClick(e.point);
      }}
      onPointerMove={(e: ThreeEvent<PointerEvent>) => {
        if (!traceActive || !onTraceHover) {
          return;
        }
        e.stopPropagation();
        onTraceHover(e.point);
        document.body.style.cursor = "crosshair";
      }}
      onPointerOut={() => {
        if (traceActive && onTraceHover) {
          onTraceHover(null);
          document.body.style.cursor = "auto";
        }
      }}
    >
      <meshBasicMaterial
        map={texture}
        transparent
        opacity={opacity}
        depthWrite={false}
        polygonOffset
        polygonOffsetFactor={-2}
        polygonOffsetUnits={-2}
      />
    </mesh>
  );
}
