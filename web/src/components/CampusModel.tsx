"use client";

import { useEffect, useMemo, useRef } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { Html, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { resolveDebugHit } from "@/lib/debugPicking";
import {
  CATEGORY_META,
  type BuildingMeta,
  type FilterCategory,
  type InspectableFeature,
} from "@/types/campus";

const DRACO_PATH = "/draco/";
const MODEL_PATH = "/models/campus.glb";

const HOVER_EMISSIVE = new THREE.Color("#3B7A82");
const SELECT_EMISSIVE = new THREE.Color("#1D5C63");
const NIGHT_HOVER_EMISSIVE = new THREE.Color("#38BDF8");
const NIGHT_SELECT_EMISSIVE = new THREE.Color("#2DD4BF");
const CATEGORY_LIFT_EMISSIVE = new THREE.Color("#334155");
const WARM_FACADE_EMISSIVE = new THREE.Color("#D99148");
const WARM_WINDOW_EMISSIVE = new THREE.Color("#FFC466");
const DIM_COLOR_FACTOR = 0.78;
const STATIC_WINDOW_KEY = "__STATIC_WINDOW__";
const STATIC_WINDOW_LIT_KEY = "__STATIC_WINDOW_LIT__";
const STATIC_WINDOW_DARK_KEY = "__STATIC_WINDOW_DARK__";
const STATIC_BLDG_KEY = "__STATIC_BLDG__";

interface MaterialRecord {
  material: THREE.MeshStandardMaterial;
  baseColor: THREE.Color;
  baseEmissive: THREE.Color;
  baseOpacity: number;
  baseTransparent: boolean;
  baseDepthWrite: boolean;
}

interface RestoreEntry {
  mesh: THREE.Mesh;
  prevMaterial: THREE.Material | THREE.Material[];
  cloned: THREE.MeshStandardMaterial[];
}

function cloneMeshMaterialsIntoMap(
  mesh: THREE.Mesh,
  key: string,
  recordsMap: Map<string, MaterialRecord[]>,
  restoreQueue: RestoreEntry[],
) {
  const prevMaterial = mesh.material;
  const clonedList: THREE.MeshStandardMaterial[] = [];

  const cloneOne = (mat: THREE.Material): THREE.Material => {
    if (!(mat instanceof THREE.MeshStandardMaterial)) {
      return mat;
    }
    const copy = mat.clone();
    clonedList.push(copy);
    const list = recordsMap.get(key) ?? [];
    list.push({
      material: copy,
      baseColor: mat.color.clone(),
      baseEmissive: mat.emissive.clone(),
      baseOpacity: mat.opacity,
      baseTransparent: mat.transparent,
      baseDepthWrite: mat.depthWrite,
    });
    recordsMap.set(key, list);
    return copy;
  };

  mesh.material = Array.isArray(prevMaterial)
    ? prevMaterial.map(cloneOne)
    : cloneOne(prevMaterial);
  restoreQueue.push({ mesh, prevMaterial, cloned: clonedList });
}

function setRecordGhostOpacity(
  rec: MaterialRecord,
  ghosted: boolean,
  ghostOpacity: number,
) {
  const nextTransparent = ghosted ? true : rec.baseTransparent;
  const nextOpacity = ghosted ? ghostOpacity : rec.baseOpacity;
  const nextDepthWrite = ghosted ? false : rec.baseDepthWrite;
  const changed = rec.material.transparent !== nextTransparent;
  rec.material.transparent = nextTransparent;
  rec.material.opacity = nextOpacity;
  rec.material.depthWrite = nextDepthWrite;
  if (changed) {
    rec.material.needsUpdate = true;
  }
}

const NOOP_RAYCAST = () => { };

interface CampusModelProps {
  buildings: BuildingMeta[];
  inspectables: InspectableFeature[];
  origin?: [number, number];
  selectedId: string | null;
  hoveredId: string | null;
  debugMode: boolean;
  ghostBuildings?: boolean;
  traceMode?: boolean;
  debugSelected: InspectableFeature | null;
  debugHovered: InspectableFeature | null;
  activeCategory: FilterCategory;
  nightFactor: number;
  isNight: boolean;
  onHover: (id: string | null) => void;
  onSelect: (id: string | null) => void;
  onDebugHover: (feature: InspectableFeature | null) => void;
  onDebugSelect: (feature: InspectableFeature | null) => void;
  onTraceClick?: (point: THREE.Vector3) => void;
  onTraceHover?: (point: THREE.Vector3 | null) => void;
  onReady: () => void;
}

function findBuildingNodeName(obj: THREE.Object3D | null): string | null {
  let curr: THREE.Object3D | null = obj;
  while (curr) {
    if (curr.name.startsWith("BLDG_")) {
      return curr.name;
    }
    curr = curr.parent;
  }
  return null;
}

function DebugWireframeHighlight({
  feature,
  color,
}: {
  feature: InspectableFeature;
  color: string;
}) {
  if (!feature.boundsXZ) {
    return null;
  }
  const [minX, minZ, maxX, maxZ] = feature.boundsXZ;
  const width = Math.max(2, maxX - minX + 1.0);
  const depth = Math.max(2, maxZ - minZ + 1.0);
  const height = Math.max(2, feature.heightM + 1.0);

  return (
    <mesh position={feature.center} raycast={NOOP_RAYCAST}>
      <boxGeometry args={[width, height, depth]} />
      <meshBasicMaterial color={color} wireframe transparent opacity={0.85} />
    </mesh>
  );
}

export default function CampusModel({
  buildings,
  inspectables,
  origin,
  selectedId,
  hoveredId,
  debugMode,
  ghostBuildings = false,
  traceMode = false,
  debugSelected,
  debugHovered,
  activeCategory,
  nightFactor,
  isNight,
  onHover,
  onSelect,
  onDebugHover,
  onDebugSelect,
  onTraceClick,
  onTraceHover,
  onReady,
}: CampusModelProps) {
  const { scene } = useGLTF(MODEL_PATH, DRACO_PATH);
  const recordsByIdRef = useRef<Map<string, MaterialRecord[]>>(new Map());

  const buildingByMesh = useMemo(() => {
    const map = new Map<string, BuildingMeta>();
    for (const b of buildings) {
      map.set(b.meshName, b);
    }
    return map;
  }, [buildings]);

  const buildingById = useMemo(() => {
    const map = new Map<string, BuildingMeta>();
    for (const b of buildings) {
      map.set(b.id, b);
    }
    return map;
  }, [buildings]);

  const inspectableByMesh = useMemo(() => {
    const map = new Map<string, InspectableFeature>();
    for (const item of inspectables) {
      if (item.meshName !== "STATIC_Buildings") {
        map.set(item.meshName, item);
      }
    }
    return map;
  }, [inspectables]);

  const staticInspectables = useMemo(
    () => inspectables.filter((item) => item.meshName === "STATIC_Buildings"),
    [inspectables],
  );

  // Clone building materials once, configure shadows, and disable raycast on merged window glass
  useEffect(() => {
    const recordsMap = new Map<string, MaterialRecord[]>();
    const restoreRaycasts: Array<{
      mesh: THREE.Mesh;
      prevRaycast: THREE.Mesh["raycast"];
    }> = [];
    const restoreQueue: RestoreEntry[] = [];

    scene.traverse((obj) => {
      if (!(obj instanceof THREE.Mesh)) {
        return;
      }

      if (obj.name.startsWith("STATIC_WindowGlass")) {
        obj.castShadow = false;
        obj.receiveShadow = false;
        restoreRaycasts.push({ mesh: obj, prevRaycast: obj.raycast });
        obj.raycast = NOOP_RAYCAST;
        const winKey = obj.name.startsWith("STATIC_WindowGlassDark")
          ? STATIC_WINDOW_DARK_KEY
          : obj.name.startsWith("STATIC_WindowGlassLit")
            ? STATIC_WINDOW_LIT_KEY
            : STATIC_WINDOW_KEY;
        cloneMeshMaterialsIntoMap(obj, winKey, recordsMap, restoreQueue);
        return;
      }

      if (obj.name.startsWith("STATIC_Buildings")) {
        obj.castShadow = true;
        obj.receiveShadow = true;
        cloneMeshMaterialsIntoMap(obj, STATIC_BLDG_KEY, recordsMap, restoreQueue);
        return;
      }

      if (obj.name.startsWith("BRIDGE_")) {
        obj.castShadow = true;
        obj.receiveShadow = true;
        cloneMeshMaterialsIntoMap(obj, obj.name, recordsMap, restoreQueue);
        return;
      }

      const bldgMeshName = findBuildingNodeName(obj);
      if (bldgMeshName) {
        obj.castShadow = true;
        obj.receiveShadow = true;

        const meta = buildingByMesh.get(bldgMeshName);
        if (!meta) {
          return;
        }

        obj.userData.buildingId = meta.id;
        cloneMeshMaterialsIntoMap(obj, meta.id, recordsMap, restoreQueue);
        return;
      }

      if (obj.name.startsWith("TREES_")) {
        obj.castShadow = true;
        obj.receiveShadow = false;
      } else {
        obj.castShadow = false;
        obj.receiveShadow = true;
      }
    });

    recordsByIdRef.current = recordsMap;
    onReady();

    return () => {
      for (const entry of restoreQueue) {
        entry.mesh.material = entry.prevMaterial;
        delete entry.mesh.userData.buildingId;
        for (const clonedMat of entry.cloned) {
          clonedMat.dispose();
        }
      }
      for (const rc of restoreRaycasts) {
        rc.mesh.raycast = rc.prevRaycast;
      }
      recordsMap.clear();
      document.body.style.cursor = "auto";
    };
  }, [scene, buildingByMesh, onReady]);

  // Apply hover, selection, category filter, bridge/ghost debug highlights, and nocturnal window/facade glow
  useEffect(() => {
    const ghosted = debugMode && ghostBuildings;

    for (const [id, records] of recordsByIdRef.current.entries()) {
      if (id === STATIC_WINDOW_KEY || id === STATIC_WINDOW_LIT_KEY) {
        const strength = id === STATIC_WINDOW_LIT_KEY ? 1.45 : 1.25;
        for (const rec of records) {
          setRecordGhostOpacity(rec, ghosted, 0.16);
          if (nightFactor > 0.01) {
            rec.material.emissive.copy(WARM_WINDOW_EMISSIVE);
            rec.material.emissiveIntensity = strength * nightFactor;
          } else {
            rec.material.emissive.copy(rec.baseEmissive);
            rec.material.emissiveIntensity = 0;
          }
        }
        continue;
      }

      if (id === STATIC_WINDOW_DARK_KEY) {
        for (const rec of records) {
          setRecordGhostOpacity(rec, ghosted, 0.16);
          if (nightFactor > 0.01) {
            rec.material.emissive.copy(WARM_WINDOW_EMISSIVE);
            rec.material.emissiveIntensity = 0.04 * nightFactor;
          } else {
            rec.material.emissive.copy(rec.baseEmissive);
            rec.material.emissiveIntensity = 0;
          }
        }
        continue;
      }

      if (id === STATIC_BLDG_KEY) {
        for (const rec of records) {
          setRecordGhostOpacity(rec, ghosted, 0.34);
          if (nightFactor > 0.01) {
            rec.material.emissive.copy(WARM_FACADE_EMISSIVE);
            rec.material.emissiveIntensity = 0.05 * nightFactor;
          } else {
            rec.material.emissive.copy(rec.baseEmissive);
            rec.material.emissiveIntensity = 0;
          }
        }
        continue;
      }

      if (id.startsWith("BRIDGE_")) {
        const isDbgSelected = debugMode && debugSelected?.meshName === id;
        const isDbgHovered = debugMode && debugHovered?.meshName === id;
        for (const rec of records) {
          setRecordGhostOpacity(rec, ghosted, 0.34);
          rec.material.color.copy(rec.baseColor);
          rec.material.emissive.copy(rec.baseEmissive);
          rec.material.emissiveIntensity = 0;
          if (isDbgSelected) {
            rec.material.emissive.copy(isNight ? NIGHT_SELECT_EMISSIVE : SELECT_EMISSIVE);
            rec.material.emissiveIntensity = isNight ? 0.55 : 0.42;
          } else if (isDbgHovered) {
            rec.material.emissive.copy(isNight ? NIGHT_HOVER_EMISSIVE : HOVER_EMISSIVE);
            rec.material.emissiveIntensity = isNight ? 0.4 : 0.28;
          } else if (nightFactor > 0.01) {
            rec.material.emissive.copy(WARM_FACADE_EMISSIVE);
            rec.material.emissiveIntensity = 0.07 * nightFactor;
          }
        }
        continue;
      }

      const meta = buildingById.get(id);
      const isSelected = id === selectedId || (debugMode && debugSelected?.id === id);
      const isHovered = id === hoveredId || (debugMode && debugHovered?.id === id);
      const matchesFilter =
        activeCategory === "all" || meta?.category === activeCategory;

      for (const rec of records) {
        setRecordGhostOpacity(rec, ghosted, 0.34);
        rec.material.color.copy(rec.baseColor);
        rec.material.emissive.copy(rec.baseEmissive);
        rec.material.emissiveIntensity = 0;

        if (!matchesFilter && !isSelected && !isHovered) {
          rec.material.color.multiplyScalar(DIM_COLOR_FACTOR);
        }

        if (isSelected) {
          rec.material.emissive.copy(
            isNight ? NIGHT_SELECT_EMISSIVE : SELECT_EMISSIVE,
          );
          rec.material.emissiveIntensity = isNight ? 0.55 : 0.42;
        } else if (isHovered) {
          rec.material.emissive.copy(
            isNight ? NIGHT_HOVER_EMISSIVE : HOVER_EMISSIVE,
          );
          rec.material.emissiveIntensity = isNight ? 0.4 : 0.28;
        } else if (activeCategory !== "all" && matchesFilter) {
          if (nightFactor > 0.05) {
            rec.material.emissive.copy(WARM_FACADE_EMISSIVE);
            rec.material.emissiveIntensity = 0.22 * nightFactor;
          } else {
            rec.material.emissive.copy(CATEGORY_LIFT_EMISSIVE);
            rec.material.emissiveIntensity = 0.08;
          }
        } else if (nightFactor > 0.01) {
          rec.material.emissive.copy(WARM_FACADE_EMISSIVE);
          rec.material.emissiveIntensity = 0.07 * nightFactor;
        }
      }
    }
  }, [
    selectedId,
    hoveredId,
    activeCategory,
    nightFactor,
    isNight,
    buildingById,
    debugMode,
    ghostBuildings,
    debugSelected,
    debugHovered,
  ]);

  const handlePointerMove = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    if (debugMode && traceMode) {
      onTraceHover?.(e.point);
      document.body.style.cursor = "crosshair";
      return;
    }
    const bid = (e.object.userData.buildingId as string | undefined) ?? null;
    if (bid !== hoveredId) {
      onHover(bid);
    }
    let hasDebugHit = false;
    if (debugMode) {
      const dbg = resolveDebugHit(
        e.object,
        e.point,
        inspectableByMesh,
        staticInspectables,
        origin,
        false,
      );
      hasDebugHit = dbg !== null;
      if ((dbg?.id ?? null) !== (debugHovered?.id ?? null)) {
        onDebugHover(dbg);
      }
    }
    document.body.style.cursor = bid || hasDebugHit ? "pointer" : "auto";
  };

  const handlePointerOut = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    if (debugMode && traceMode) {
      onTraceHover?.(null);
      document.body.style.cursor = "auto";
      return;
    }
    if (hoveredId !== null) {
      onHover(null);
    }
    if (debugMode && debugHovered !== null) {
      onDebugHover(null);
    }
    document.body.style.cursor = "auto";
  };

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    if (e.delta > 6) {
      return;
    }
    e.stopPropagation();
    if (debugMode && traceMode) {
      onTraceClick?.(e.point);
      return;
    }
    const bid = (e.object.userData.buildingId as string | undefined) ?? null;
    if (debugMode) {
      const dbg = resolveDebugHit(
        e.object,
        e.point,
        inspectableByMesh,
        staticInspectables,
        origin,
        true,
      );
      onDebugSelect(dbg);
    }
    onSelect(bid);
  };

  const hoveredBuilding =
    !debugMode && hoveredId ? buildingById.get(hoveredId) ?? null : null;

  return (
    <group>
      <primitive
        object={scene}
        onPointerMove={handlePointerMove}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
      />

      {debugMode &&
        debugHovered &&
        (debugHovered.meshName === "STATIC_Buildings" ||
          debugHovered.kind === "bridge") && (
          <DebugWireframeHighlight feature={debugHovered} color="#38bdf8" />
        )}

      {debugMode &&
        debugSelected &&
        (debugSelected.meshName === "STATIC_Buildings" ||
          debugSelected.kind === "bridge") && (
          <DebugWireframeHighlight feature={debugSelected} color="#f59e0b" />
        )}

      {debugMode && debugHovered && (
        <Html
          position={[
            debugHovered.center[0],
            debugHovered.center[1] + Math.max(4, debugHovered.heightM * 0.5 + 5),
            debugHovered.center[2],
          ]}
          center
          zIndexRange={[10, 0]}
          style={{ pointerEvents: "none" }}
        >
          <div
            className={`pointer-events-none select-none whitespace-nowrap rounded-md border px-2 py-0.5 font-mono text-[11px] opacity-80 shadow-sm backdrop-blur-sm ${isNight
              ? "border-amber-400/25 bg-slate-950/82 text-amber-200"
              : "border-slate-900/15 bg-[#FAFBF9]/85 text-slate-800"
              }`}
          >
            <span>{debugHovered.id}</span>
            {debugHovered.isNamed && (
              <span className="ml-1.5 opacity-75">
                · {debugHovered.name} ({debugHovered.floors}F)
              </span>
            )}
          </div>
        </Html>
      )}

      {hoveredBuilding && (
        <Html
          position={[
            hoveredBuilding.center[0],
            hoveredBuilding.center[1] + hoveredBuilding.heightM * 0.5 + 8,
            hoveredBuilding.center[2],
          ]}
          center
          zIndexRange={[10, 0]}
          style={{ pointerEvents: "none" }}
        >
          <div
            className={`pointer-events-none select-none whitespace-nowrap rounded-lg border px-2.5 py-1 text-xs font-medium shadow-sm backdrop-blur-md ${isNight
              ? "border-slate-300/20 bg-slate-900/90 text-slate-100"
              : "border-slate-900/15 bg-[#FAFBF9]/92 text-slate-900"
              }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{
                  backgroundColor: CATEGORY_META[hoveredBuilding.category].dotColor,
                }}
              />
              <span>{hoveredBuilding.name}</span>
            </span>
          </div>
        </Html>
      )}
    </group>
  );
}

useGLTF.preload(MODEL_PATH, DRACO_PATH);
