"use client";

import { useEffect, useRef, type ComponentRef } from "react";
import { useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { TourStop } from "@/data/tourStops";
import type { BuildingMeta, RouteResult, TerrainBounds } from "@/types/campus";

type OrbitControlsHandle = ComponentRef<typeof OrbitControls>;

export const DEFAULT_CAMERA_POSITION: [number, number, number] = [260, 290, 380];
const DEFAULT_CAMERA_TARGET: [number, number, number] = [-80, 5, -40];

interface CustomFocusTarget {
  center: [number, number, number];
  offset?: [number, number, number];
  nonce: number;
}

interface CameraRigProps {
  selectedBuilding: BuildingMeta | null;
  activeRoute: RouteResult | null;
  activeTourStop: TourStop | null;
  tourBuilding: BuildingMeta | null;
  customFocusTarget?: CustomFocusTarget | null;
  terrainBounds?: TerrainBounds;
  debugMode?: boolean;
  topDownNonce?: number;
  focusNonce: number;
  routeFocusNonce: number;
  tourFocusNonce: number;
  resetToken: number;
}

export default function CameraRig({
  selectedBuilding,
  activeRoute,
  activeTourStop,
  tourBuilding,
  customFocusTarget,
  terrainBounds,
  debugMode = false,
  topDownNonce = 0,
  focusNonce,
  routeFocusNonce,
  tourFocusNonce,
  resetToken,
}: CameraRigProps) {
  const controlsRef = useRef<OrbitControlsHandle | null>(null);

  const goalPosRef = useRef<THREE.Vector3 | null>(null);
  const goalTargetRef = useRef<THREE.Vector3 | null>(null);
  const isFlyingRef = useRef(false);
  const initializedRef = useRef(false);

  const bounds = terrainBounds ?? {
    minX: -776,
    maxX: 754,
    minZ: -757,
    maxZ: 690,
    minY: -22,
    maxY: 132,
  };

  // Set initial camera overview target once controls mount
  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls || initializedRef.current) {
      return;
    }
    initializedRef.current = true;
    controls.object.position.set(...DEFAULT_CAMERA_POSITION);
    controls.target.set(...DEFAULT_CAMERA_TARGET);
    controls.update();
  }, []);

  // Trigger smooth fly-to when a building is selected or refocused (unless framing route/tour)
  useEffect(() => {
    if (!selectedBuilding || activeRoute || activeTourStop) {
      return;
    }
    const controls = controlsRef.current;
    const [cx, cy, cz] = selectedBuilding.center;
    const target = new THREE.Vector3(cx, cy, cz);

    const dist = Math.max(
      85,
      Math.min(230, selectedBuilding.boundingRadius * 2.55),
    );
    const pos = new THREE.Vector3(
      THREE.MathUtils.clamp(cx + dist * 0.56, bounds.minX + 40, bounds.maxX - 40),
      Math.max(cy + 24, cy + dist * 0.62),
      THREE.MathUtils.clamp(cz + dist * 0.58, bounds.minZ + 40, bounds.maxZ - 40),
    );

    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reducedMotion && controls) {
      isFlyingRef.current = false;
      controls.object.position.copy(pos);
      controls.target.copy(target);
      controls.update();
      return;
    }

    goalTargetRef.current = target;
    goalPosRef.current = pos;
    isFlyingRef.current = true;
  }, [
    selectedBuilding,
    activeRoute,
    activeTourStop,
    focusNonce,
    bounds.minX,
    bounds.maxX,
    bounds.minZ,
    bounds.maxZ,
  ]);

  // Smoothly frame each Fresher Orientation Tour stop
  useEffect(() => {
    if (!activeTourStop) {
      return;
    }
    const baseCenter =
      activeTourStop.targetOverride ?? tourBuilding?.center ?? [0, 5, 0];
    const [cx, cy, cz] = baseCenter;
    const target = new THREE.Vector3(cx, cy, cz);

    const offset = activeTourStop.cameraOffset ?? [120, 108, 128];
    const pos = new THREE.Vector3(
      THREE.MathUtils.clamp(cx + offset[0], bounds.minX + 40, bounds.maxX - 40),
      Math.max(cy + 24, cy + offset[1]),
      THREE.MathUtils.clamp(cz + offset[2], bounds.minZ + 40, bounds.maxZ - 40),
    );

    const controls = controlsRef.current;
    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reducedMotion && controls) {
      isFlyingRef.current = false;
      controls.object.position.copy(pos);
      controls.target.copy(target);
      controls.update();
      return;
    }

    goalTargetRef.current = target;
    goalPosRef.current = pos;
    isFlyingRef.current = true;
  }, [
    activeTourStop,
    tourBuilding,
    tourFocusNonce,
    bounds.minX,
    bounds.maxX,
    bounds.minZ,
    bounds.maxZ,
  ]);

  // Auto-frame the full walking route when computed or refocused
  useEffect(() => {
    if (!activeRoute) {
      return;
    }
    const controls = controlsRef.current;
    const [cx, cy, cz] = activeRoute.bounds.center;
    const target = new THREE.Vector3(cx, cy, cz);

    const dist = Math.max(
      125,
      Math.min(680, activeRoute.bounds.radius * 2.35),
    );
    const pos = new THREE.Vector3(
      THREE.MathUtils.clamp(cx + dist * 0.45, bounds.minX + 40, bounds.maxX - 40),
      Math.max(cy + 48, cy + dist * 0.74),
      THREE.MathUtils.clamp(cz + dist * 0.55, bounds.minZ + 40, bounds.maxZ - 40),
    );

    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reducedMotion && controls) {
      isFlyingRef.current = false;
      controls.object.position.copy(pos);
      controls.target.copy(target);
      controls.update();
      return;
    }

    goalTargetRef.current = target;
    goalPosRef.current = pos;
    isFlyingRef.current = true;
  }, [
    activeRoute,
    routeFocusNonce,
    bounds.minX,
    bounds.maxX,
    bounds.minZ,
    bounds.maxZ,
  ]);

  // Smoothly fly to a custom campus coordinate (e.g. Sports Ground quick jump)
  useEffect(() => {
    if (!customFocusTarget || customFocusTarget.nonce === 0) {
      return;
    }
    const [cx, cy, cz] = customFocusTarget.center;
    const offset = customFocusTarget.offset ?? [135, 118, 155];
    const target = new THREE.Vector3(cx, cy, cz);
    const pos = new THREE.Vector3(
      THREE.MathUtils.clamp(cx + offset[0], bounds.minX + 40, bounds.maxX - 40),
      Math.max(cy + 24, cy + offset[1]),
      THREE.MathUtils.clamp(cz + offset[2], bounds.minZ + 40, bounds.maxZ - 40),
    );
    const controls = controlsRef.current;
    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion && controls) {
      isFlyingRef.current = false;
      controls.object.position.copy(pos);
      controls.target.copy(target);
      controls.update();
      return;
    }
    goalTargetRef.current = target;
    goalPosRef.current = pos;
    isFlyingRef.current = true;
  }, [customFocusTarget, bounds.minX, bounds.maxX, bounds.minZ, bounds.maxZ]);

  // Reset camera overview when requested
  useEffect(() => {
    if (resetToken === 0) {
      return;
    }
    const controls = controlsRef.current;
    const pos = new THREE.Vector3(...DEFAULT_CAMERA_POSITION);
    const target = new THREE.Vector3(...DEFAULT_CAMERA_TARGET);

    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reducedMotion && controls) {
      isFlyingRef.current = false;
      controls.object.position.copy(pos);
      controls.target.copy(target);
      controls.update();
      return;
    }

    goalPosRef.current = pos;
    goalTargetRef.current = target;
    isFlyingRef.current = true;
  }, [resetToken]);

  // Move overhead directly above current OrbitControls target for top-down satellite tracing
  useEffect(() => {
    if (!topDownNonce) {
      return;
    }
    const controls = controlsRef.current;
    if (!controls) {
      return;
    }
    const tx = THREE.MathUtils.clamp(
      controls.target.x,
      bounds.minX + 100,
      bounds.maxX - 100,
    );
    const tz = THREE.MathUtils.clamp(
      controls.target.z,
      bounds.minZ + 100,
      bounds.maxZ - 100,
    );
    const ty = THREE.MathUtils.clamp(controls.target.y, -5, 85);
    const target = new THREE.Vector3(tx, ty, tz);
    const pos = new THREE.Vector3(tx, Math.max(ty + 420, 420), tz + 8);

    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) {
      isFlyingRef.current = false;
      controls.object.position.copy(pos);
      controls.target.copy(target);
      controls.update();
      return;
    }
    goalTargetRef.current = target;
    goalPosRef.current = pos;
    isFlyingRef.current = true;
  }, [topDownNonce, bounds.minX, bounds.maxX, bounds.minZ, bounds.maxZ]);

  useFrame((state, delta) => {
    const controls = controlsRef.current;
    if (!controls) {
      return;
    }
    const cam = state.camera;

    if (isFlyingRef.current && goalPosRef.current && goalTargetRef.current) {
      const alpha = 1 - Math.exp(-5.5 * Math.min(delta, 0.1));
      cam.position.lerp(goalPosRef.current, alpha);
      controls.target.lerp(goalTargetRef.current, alpha);

      if (
        cam.position.distanceTo(goalPosRef.current) < 0.5 &&
        controls.target.distanceTo(goalTargetRef.current) < 0.5
      ) {
        cam.position.copy(goalPosRef.current);
        controls.target.copy(goalTargetRef.current);
        isFlyingRef.current = false;
      }
    }

    // Keep pan target within campus bounds and above terrain datum
    controls.target.x = THREE.MathUtils.clamp(
      controls.target.x,
      bounds.minX + 100,
      bounds.maxX - 100,
    );
    controls.target.z = THREE.MathUtils.clamp(
      controls.target.z,
      bounds.minZ + 100,
      bounds.maxZ - 100,
    );
    controls.target.y = THREE.MathUtils.clamp(controls.target.y, -5, 85);

    const minCamY = Math.max(14, controls.target.y + 10);
    if (cam.position.y < minCamY) {
      cam.position.y = minCamY;
    }

    controls.update();
  });

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping
      dampingFactor={0.08}
      rotateSpeed={0.75}
      zoomSpeed={0.9}
      panSpeed={0.85}
      touches={{
        ONE: THREE.TOUCH.ROTATE,
        TWO: THREE.TOUCH.DOLLY_PAN,
      }}
      screenSpacePanning={false}
      minPolarAngle={debugMode ? 0.02 : 0.2}
      maxPolarAngle={Math.PI / 2 - 0.14}
      minDistance={45}
      maxDistance={1150}
      onStart={() => {
        isFlyingRef.current = false;
      }}
    />
  );
}
