"use client";

import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { TreePlacement, TreesData } from "@/types/campus";

interface InstancedTreesProps {
  treesData: TreesData | null;
}

const PALM_SHADES = ["#3E663A", "#497141", "#355934", "#557A46"];
const CANOPY_SHADES = ["#2F5534", "#3E623B", "#4B693D", "#2A4A30"];

function toFlatNonIndexed(geom: THREE.BufferGeometry): THREE.BufferGeometry {
  const nonIdx = geom.index ? geom.toNonIndexed() : geom;
  if (nonIdx.getAttribute("uv")) {
    nonIdx.deleteAttribute("uv");
  }
  nonIdx.computeVertexNormals();
  return nonIdx;
}

function buildPalmGeometries(): {
  trunk: THREE.BufferGeometry;
  crown: THREE.BufferGeometry;
} {
  // Slightly curved 3-segment coconut palm trunk (~8.2m tall)
  const trunkParts: THREE.BufferGeometry[] = [];
  const segSpecs: Array<[number, number, number, number, number, number]> = [
    [0.25, 0.21, 2.8, 0.06, 1.3, 0.0],
    [0.21, 0.17, 2.8, 0.22, 4.0, -0.05],
    [0.17, 0.13, 2.8, 0.42, 6.6, -0.14],
  ];
  for (let i = 0; i < segSpecs.length; i++) {
    const [rB, rT, h, x, y, tiltZ] = segSpecs[i];
    const g = new THREE.CylinderGeometry(rT, rB, h, 6, 1, false);
    g.rotateZ(tiltZ);
    g.translate(x, y, 0);
    trunkParts.push(toFlatNonIndexed(g));
    g.dispose();
  }

  // 7 arched palm fronds radiating from top of trunk
  const crownParts: THREE.BufferGeometry[] = [];
  const frondCount = 7;
  for (let i = 0; i < frondCount; i++) {
    const ang = (Math.PI * 2 * i) / frondCount + (i % 2) * 0.14;
    const inner = new THREE.BoxGeometry(0.42, 0.08, 1.55);
    inner.translate(0, 0, 0.85);
    inner.rotateX(-0.24);

    const outer = new THREE.BoxGeometry(0.28, 0.06, 1.25);
    outer.translate(0, -0.04, 2.05);
    outer.rotateX(0.32);

    for (const part of [inner, outer]) {
      part.rotateY(ang);
      part.translate(0.50, 7.95, 0);
      crownParts.push(toFlatNonIndexed(part));
      part.dispose();
    }
  }

  const head = new THREE.IcosahedronGeometry(0.38, 0);
  head.translate(0.50, 7.75, 0);
  crownParts.push(toFlatNonIndexed(head));
  head.dispose();

  return {
    trunk: mergeGeometries(trunkParts, false),
    crown: mergeGeometries(crownParts, false),
  };
}

function buildCanopyGeometries(): {
  trunk: THREE.BufferGeometry;
  crown: THREE.BufferGeometry;
} {
  const t = new THREE.CylinderGeometry(0.18, 0.30, 3.0, 5, 1, false);
  t.translate(0, 1.35, 0);
  const trunk = toFlatNonIndexed(t);
  t.dispose();

  const lobes: Array<[number, number, number, number, number]> = [
    [2.05, 0.0, 4.35, 0.0, 0.88],
    [1.52, 1.0, 3.65, 0.56, 0.92],
    [1.45, -0.92, 3.72, -0.62, 0.90],
  ];
  const crownParts: THREE.BufferGeometry[] = [];
  for (const [radius, x, y, z, sy] of lobes) {
    const g = new THREE.IcosahedronGeometry(radius, 1);
    g.scale(1.0, sy, 1.0);
    g.translate(x, y, z);
    crownParts.push(toFlatNonIndexed(g));
    g.dispose();
  }

  return {
    trunk,
    crown: mergeGeometries(crownParts, false),
  };
}

export default function InstancedTrees({ treesData }: InstancedTreesProps) {
  const palmTrunkRef = useRef<THREE.InstancedMesh | null>(null);
  const palmCrownRef = useRef<THREE.InstancedMesh | null>(null);
  const canopyTrunkRef = useRef<THREE.InstancedMesh | null>(null);
  const canopyCrownRef = useRef<THREE.InstancedMesh | null>(null);

  const geometries = useMemo(() => {
    const palm = buildPalmGeometries();
    const canopy = buildCanopyGeometries();
    return { palm, canopy };
  }, []);

  useEffect(() => {
    return () => {
      geometries.palm.trunk.dispose();
      geometries.palm.crown.dispose();
      geometries.canopy.trunk.dispose();
      geometries.canopy.crown.dispose();
    };
  }, [geometries]);

  const { palms, canopies } = useMemo(() => {
    const palmList: TreePlacement[] = [];
    const canopyList: TreePlacement[] = [];
    for (const item of treesData?.trees ?? []) {
      if (item[5] === 0) {
        palmList.push(item);
      } else {
        canopyList.push(item);
      }
    }
    return { palms: palmList, canopies: canopyList };
  }, [treesData]);

  useLayoutEffect(() => {
    const dummy = new THREE.Object3D();
    const color = new THREE.Color();

    const applyList = (
      list: TreePlacement[],
      trunkMesh: THREE.InstancedMesh | null,
      crownMesh: THREE.InstancedMesh | null,
      shades: string[],
    ) => {
      if (!trunkMesh || !crownMesh || list.length === 0) {
        return;
      }
      for (let i = 0; i < list.length; i++) {
        const [x, y, z, scale, rotY, , shade] = list[i];
        dummy.position.set(x, y - 0.18, z);
        dummy.rotation.set(0, rotY, 0);
        dummy.scale.setScalar(scale);
        dummy.updateMatrix();
        trunkMesh.setMatrixAt(i, dummy.matrix);
        crownMesh.setMatrixAt(i, dummy.matrix);

        color.set(shades[shade % shades.length]);
        crownMesh.setColorAt(i, color);
      }
      trunkMesh.instanceMatrix.needsUpdate = true;
      crownMesh.instanceMatrix.needsUpdate = true;
      if (crownMesh.instanceColor) {
        crownMesh.instanceColor.needsUpdate = true;
      }
    };

    applyList(palms, palmTrunkRef.current, palmCrownRef.current, PALM_SHADES);
    applyList(canopies, canopyTrunkRef.current, canopyCrownRef.current, CANOPY_SHADES);
  }, [palms, canopies]);

  if (!treesData || treesData.trees.length === 0) {
    return null;
  }

  return (
    <group name="INSTANCED_TREES">
      {palms.length > 0 && (
        <>
          <instancedMesh
            ref={palmTrunkRef}
            args={[geometries.palm.trunk, undefined, palms.length]}
            frustumCulled={false}
          >
            <meshStandardMaterial color="#7E6449" roughness={0.92} />
          </instancedMesh>
          <instancedMesh
            ref={palmCrownRef}
            args={[geometries.palm.crown, undefined, palms.length]}
            castShadow
            frustumCulled={false}
          >
            <meshStandardMaterial color="#ffffff" roughness={0.82} />
          </instancedMesh>
        </>
      )}

      {canopies.length > 0 && (
        <>
          <instancedMesh
            ref={canopyTrunkRef}
            args={[geometries.canopy.trunk, undefined, canopies.length]}
            frustumCulled={false}
          >
            <meshStandardMaterial color="#6B513B" roughness={0.92} />
          </instancedMesh>
          <instancedMesh
            ref={canopyCrownRef}
            args={[geometries.canopy.crown, undefined, canopies.length]}
            castShadow
            frustumCulled={false}
          >
            <meshStandardMaterial color="#ffffff" roughness={0.86} />
          </instancedMesh>
        </>
      )}
    </group>
  );
}
