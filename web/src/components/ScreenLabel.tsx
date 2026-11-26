"use client";

import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

interface ScreenLabelProps {
  position: [number, number, number];
  center?: boolean;
  zIndexRange?: [number, number];
  style?: CSSProperties;
  children: ReactNode;
}

const objectPos = new THREE.Vector3();
const cameraPos = new THREE.Vector3();
const cameraDir = new THREE.Vector3();
const ndc = new THREE.Vector3();

/**
 * Screen-space HTML label anchored to a 3D point (drop-in for drei `<Html center>` without `transform`).
 *
 * drei's `<Html>` mounts a separate React DOM root per label and unmounts it synchronously inside a
 * layout-effect cleanup. That cleanup runs during the R3F reconciler's commit, so React 19 logs
 * "Attempted to synchronously unmount a root while React was already rendering" every time a label
 * disappears (hover out, selection, zoom-tier change). This component defers the root unmount until
 * the current render has finished.
 */
export default function ScreenLabel({
  position,
  center = false,
  zIndexRange = [16777271, 0],
  style,
  children,
}: ScreenLabelProps) {
  const groupRef = useRef<THREE.Group>(null);
  const elRef = useRef<HTMLDivElement | null>(null);
  const rootRef = useRef<Root | null>(null);
  const lastRef = useRef({ x: Number.NaN, y: Number.NaN, z: Number.NaN, hidden: false });
  const gl = useThree((s) => s.gl);
  const connected = useThree((s) => s.events.connected) as HTMLElement | undefined;

  useLayoutEffect(() => {
    const target = connected ?? gl.domElement.parentElement;
    if (!target) {
      return;
    }
    const el = document.createElement("div");
    el.style.cssText = "position:absolute;top:0;left:0;transform-origin:0 0;display:none;";
    target.appendChild(el);
    const root = createRoot(el);
    elRef.current = el;
    rootRef.current = root;
    lastRef.current = { x: Number.NaN, y: Number.NaN, z: Number.NaN, hidden: true };
    return () => {
      elRef.current = null;
      rootRef.current = null;
      el.remove();
      // Unmounting synchronously here would race the in-progress R3F commit; defer to the next task.
      setTimeout(() => root.unmount(), 0);
    };
  }, [gl, connected]);

  useLayoutEffect(() => {
    rootRef.current?.render(
      <div
        style={{
          position: "absolute",
          transform: center ? "translate3d(-50%,-50%,0)" : "none",
          ...style,
        }}
      >
        {children}
      </div>,
    );
  });

  useFrame(({ camera, size }) => {
    const group = groupRef.current;
    const el = elRef.current;
    if (!group || !el) {
      return;
    }
    objectPos.setFromMatrixPosition(group.matrixWorld);
    cameraPos.setFromMatrixPosition(camera.matrixWorld);
    camera.getWorldDirection(cameraDir);
    const hidden = objectPos.clone().sub(cameraPos).angleTo(cameraDir) > Math.PI / 2;
    const last = lastRef.current;

    if (hidden !== last.hidden) {
      el.style.display = hidden ? "none" : "block";
      last.hidden = hidden;
    }
    if (hidden) {
      return;
    }

    ndc.copy(objectPos).project(camera);
    const x = Math.round((ndc.x * 0.5 + 0.5) * size.width);
    const y = Math.round((-ndc.y * 0.5 + 0.5) * size.height);
    if (x !== last.x || y !== last.y) {
      el.style.transform = `translate3d(${x}px,${y}px,0)`;
      last.x = x;
      last.y = y;
    }

    if (camera instanceof THREE.PerspectiveCamera || camera instanceof THREE.OrthographicCamera) {
      const a = (zIndexRange[1] - zIndexRange[0]) / (camera.far - camera.near);
      const b = zIndexRange[1] - a * camera.far;
      const z = Math.round(a * objectPos.distanceTo(cameraPos) + b);
      if (z !== last.z) {
        el.style.zIndex = String(z);
        last.z = z;
      }
    }
  });

  return <group ref={groupRef} position={position} />;
}
