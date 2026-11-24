"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { RouteResult } from "@/types/campus";

interface RouteRibbonProps {
  route: RouteResult;
}

const RIBBON_Y_OFFSET = 0.6;
const MARKER_COUNT = 3;
const UP_AXIS = new THREE.Vector3(0, 1, 0);

export default function RouteRibbon({ route }: RouteRibbonProps) {
  const markerRefs = useRef<Array<THREE.Mesh | null>>([]);
  const haloMatRef = useRef<THREE.MeshBasicMaterial | null>(null);

  const built = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (const [x, y, z] of route.points) {
      const v = new THREE.Vector3(x, y + RIBBON_Y_OFFSET, z);
      if (pts.length === 0 || pts[pts.length - 1].distanceTo(v) >= 0.05) {
        pts.push(v);
      }
    }
    if (pts.length < 2) {
      return null;
    }

    const curve = new THREE.CatmullRomCurve3(pts, false, "centripetal", 0.45);
    const tubularSegments = Math.min(240, Math.max(32, pts.length * 3));

    const coreGeom = new THREE.TubeGeometry(curve, tubularSegments, 0.85, 8, false);
    const haloGeom = new THREE.TubeGeometry(curve, tubularSegments, 1.5, 8, false);
    const coneGeom = new THREE.ConeGeometry(1.55, 3.6, 8);
    const startGeom = new THREE.CylinderGeometry(2.4, 2.4, 1.0, 16);
    const endGeom = new THREE.SphereGeometry(2.4, 16, 12);

    return {
      curve,
      startPos: pts[0],
      endPos: pts[pts.length - 1],
      coreGeom,
      haloGeom,
      coneGeom,
      startGeom,
      endGeom,
    };
  }, [route]);

  useEffect(() => {
    return () => {
      if (!built) {
        return;
      }
      built.coreGeom.dispose();
      built.haloGeom.dispose();
      built.coneGeom.dispose();
      built.startGeom.dispose();
      built.endGeom.dispose();
    };
  }, [built]);

  useFrame((state) => {
    if (!built) {
      return;
    }

    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const elapsed = state.clock.elapsedTime;
    const speed = Math.max(0.06, Math.min(0.22, 22 / Math.max(route.distanceM, 60)));

    for (let i = 0; i < MARKER_COUNT; i++) {
      const mesh = markerRefs.current[i];
      if (!mesh) {
        continue;
      }
      const baseT = (i + 0.5) / MARKER_COUNT;
      const t = reducedMotion ? baseT : (elapsed * speed + i / MARKER_COUNT) % 1;
      const pos = built.curve.getPointAt(t);
      const tangent = built.curve.getTangentAt(t).normalize();
      mesh.position.set(pos.x, pos.y + 0.35, pos.z);
      mesh.quaternion.setFromUnitVectors(UP_AXIS, tangent);
    }

    if (haloMatRef.current) {
      haloMatRef.current.opacity = reducedMotion
        ? 0.24
        : 0.16 + 0.12 * (0.5 + 0.5 * Math.sin(elapsed * 3.4));
    }
  });

  if (!built) {
    return null;
  }

  return (
    <group name="WALK_ROUTE_RIBBON">
      {/* Core glowing route tube */}
      <mesh geometry={built.coreGeom} renderOrder={2}>
        <meshStandardMaterial
          color="#0F766E"
          emissive="#14B8A6"
          emissiveIntensity={0.85}
          roughness={0.3}
          metalness={0.05}
        />
      </mesh>

      {/* Outer translucent pulse halo */}
      <mesh geometry={built.haloGeom} renderOrder={1}>
        <meshBasicMaterial
          ref={haloMatRef}
          color="#2DD4BF"
          transparent
          opacity={0.24}
          depthWrite={false}
        />
      </mesh>

      {/* Animated directional arrow cones */}
      {Array.from({ length: MARKER_COUNT }).map((_, idx) => (
        <mesh
          key={idx}
          ref={(el) => {
            markerRefs.current[idx] = el;
          }}
          geometry={built.coneGeom}
          renderOrder={3}
        >
          <meshStandardMaterial
            color="#FAFBF9"
            emissive="#99F6E4"
            emissiveIntensity={0.65}
            roughness={0.35}
          />
        </mesh>
      ))}

      {/* Start marker */}
      <mesh
        geometry={built.startGeom}
        position={[built.startPos.x, built.startPos.y + 0.5, built.startPos.z]}
        renderOrder={3}
      >
        <meshStandardMaterial
          color="#0F766E"
          emissive="#14B8A6"
          emissiveIntensity={0.6}
          roughness={0.4}
        />
      </mesh>

      {/* Destination beacon */}
      <mesh
        geometry={built.endGeom}
        position={[built.endPos.x, built.endPos.y + 2.4, built.endPos.z]}
        renderOrder={3}
      >
        <meshStandardMaterial
          color="#D97706"
          emissive="#F59E0B"
          emissiveIntensity={0.65}
          roughness={0.35}
        />
      </mesh>
    </group>
  );
}
