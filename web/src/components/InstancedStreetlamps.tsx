"use client";

import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { StreetlampsData } from "@/types/campus";

interface InstancedStreetlampsProps {
  lampsData: StreetlampsData | null;
  nightFactor: number;
}

function toFlatNonIndexed(geom: THREE.BufferGeometry): THREE.BufferGeometry {
  const nonIdx = geom.index ? geom.toNonIndexed() : geom;
  if (nonIdx.getAttribute("uv")) {
    nonIdx.deleteAttribute("uv");
  }
  nonIdx.computeVertexNormals();
  return nonIdx;
}

function buildStreetlampGeometries(): {
  pole: THREE.BufferGeometry;
  head: THREE.BufferGeometry;
} {
  const post = new THREE.CylinderGeometry(0.08, 0.13, 5.4, 6, 1, false);
  post.translate(0, 2.7, 0);

  const arm = new THREE.BoxGeometry(0.1, 0.1, 1.35);
  arm.rotateX(-0.18);
  arm.translate(0, 5.46, 0.56);

  const hood = new THREE.BoxGeometry(0.32, 0.09, 0.54);
  hood.translate(0, 5.62, 1.2);

  const bulb = new THREE.BoxGeometry(0.28, 0.11, 0.46);
  bulb.translate(0, 5.53, 1.2);

  const poleParts = [post, arm, hood].map((g) => {
    const out = toFlatNonIndexed(g);
    g.dispose();
    return out;
  });
  const head = toFlatNonIndexed(bulb);
  bulb.dispose();

  return {
    pole: mergeGeometries(poleParts, false),
    head,
  };
}

export default function InstancedStreetlamps({
  lampsData,
  nightFactor,
}: InstancedStreetlampsProps) {
  const poleRef = useRef<THREE.InstancedMesh | null>(null);
  const headRef = useRef<THREE.InstancedMesh | null>(null);

  const geometries = useMemo(() => buildStreetlampGeometries(), []);

  useEffect(() => {
    return () => {
      geometries.pole.dispose();
      geometries.head.dispose();
    };
  }, [geometries]);

  const lamps = useMemo(() => lampsData?.lamps ?? [], [lampsData]);

  useLayoutEffect(() => {
    const poleMesh = poleRef.current;
    const headMesh = headRef.current;
    if (!poleMesh || !headMesh || lamps.length === 0) {
      return;
    }
    const dummy = new THREE.Object3D();
    for (let i = 0; i < lamps.length; i++) {
      const [x, y, z, rotY] = lamps[i];
      dummy.position.set(x, y - 0.05, z);
      dummy.rotation.set(0, rotY, 0);
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      poleMesh.setMatrixAt(i, dummy.matrix);
      headMesh.setMatrixAt(i, dummy.matrix);
    }
    poleMesh.instanceMatrix.needsUpdate = true;
    headMesh.instanceMatrix.needsUpdate = true;
  }, [lamps]);

  if (lamps.length === 0) {
    return null;
  }

  const lit = nightFactor > 0.02;

  return (
    <group name="INSTANCED_STREETLAMP_POLES">
      <instancedMesh
        ref={poleRef}
        args={[geometries.pole, undefined, lamps.length]}
        frustumCulled={false}
      >
        <meshStandardMaterial color="#30363C" roughness={0.65} metalness={0.35} />
      </instancedMesh>
      <instancedMesh
        ref={headRef}
        args={[geometries.head, undefined, lamps.length]}
        frustumCulled={false}
      >
        <meshStandardMaterial
          color={lit ? "#FFE6A6" : "#EAE6DB"}
          emissive="#FFC45E"
          emissiveIntensity={lit ? 1.9 * nightFactor : 0}
          roughness={0.35}
        />
      </instancedMesh>
    </group>
  );
}
