"use client";

import { useEffect, useMemo } from "react";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";
import { CATEGORY_META, type OverturePoi } from "@/types/campus";

interface PolygonTracerLayerProps {
  points: Array<[number, number, number]>;
  hoverPoint: [number, number, number] | null;
  overturePois?: OverturePoi[];
  showPois: boolean;
  isNight: boolean;
}

export default function PolygonTracerLayer({
  points,
  hoverPoint,
  overturePois,
  showPois,
  isNight,
}: PolygonTracerLayerProps) {
  const closedOutlinePts = useMemo(() => {
    if (points.length < 2) {
      return null;
    }
    const elevated = points.map(
      ([x, y, z]): [number, number, number] => [x, y + 0.65, z],
    );
    if (points.length >= 3) {
      elevated.push(elevated[0]);
    }
    return elevated;
  }, [points]);

  const previewSegment = useMemo(() => {
    if (points.length === 0 || !hoverPoint) {
      return null;
    }
    const last = points[points.length - 1];
    return [
      [last[0], last[1] + 0.65, last[2]] as [number, number, number],
      [hoverPoint[0], hoverPoint[1] + 0.65, hoverPoint[2]] as [
        number,
        number,
        number,
      ],
    ];
  }, [points, hoverPoint]);

  const fillGeometry = useMemo(() => {
    if (points.length < 3) {
      return null;
    }
    const contour = points.map(([x, , z]) => new THREE.Vector2(x, z));
    const tris = THREE.ShapeUtils.triangulateShape(contour, []);
    if (tris.length === 0) {
      return null;
    }

    const avgY =
      points.reduce((acc, p) => acc + p[1], 0) / Math.max(1, points.length);
    const positions: number[] = [];
    for (const [x, , z] of points) {
      positions.push(x, avgY + 0.48, z);
    }
    const indices: number[] = [];
    for (const [a, b, c] of tris) {
      indices.push(a, b, c);
    }

    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geom.setIndex(indices);
    geom.computeVertexNormals();
    return geom;
  }, [points]);

  useEffect(() => {
    return () => {
      fillGeometry?.dispose();
    };
  }, [fillGeometry]);

  return (
    <group>
      {points.map(([x, y, z], idx) => (
        <mesh key={`${idx}-${x}-${z}`} position={[x, y + 0.78, z]}>
          <sphereGeometry args={[idx === 0 ? 1.15 : 0.9, 12, 10]} />
          <meshBasicMaterial color={idx === 0 ? "#22c55e" : "#06b6d4"} />
        </mesh>
      ))}

      {closedOutlinePts && (
        <Line
          points={closedOutlinePts}
          color="#22d3ee"
          lineWidth={2.5}
          transparent
          opacity={0.95}
        />
      )}

      {previewSegment && (
        <Line
          points={previewSegment}
          color="#f59e0b"
          lineWidth={1.75}
          dashed
          dashSize={2.2}
          gapSize={1.4}
          transparent
          opacity={0.8}
        />
      )}

      {fillGeometry && (
        <mesh geometry={fillGeometry}>
          <meshBasicMaterial
            color="#06b6d4"
            transparent
            opacity={0.28}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      )}

      {showPois &&
        overturePois?.map((poi) => {
          const [px, py, pz] = poi.position;
          const color = CATEGORY_META[poi.category]?.dotColor ?? "#f59e0b";
          return (
            <group key={poi.id} position={[px, py, pz]}>
              <mesh position={[0, 4.5, 0]}>
                <cylinderGeometry args={[0.18, 0.18, 9, 8]} />
                <meshBasicMaterial color="#f59e0b" />
              </mesh>
              <mesh position={[0, 9.6, 0]}>
                <sphereGeometry args={[1.1, 12, 10]} />
                <meshBasicMaterial color={color} />
              </mesh>
              <Html
                position={[0, 12.2, 0]}
                center
                zIndexRange={[8, 0]}
                style={{ pointerEvents: "none" }}
              >
                <div
                  className={`pointer-events-none select-none whitespace-nowrap rounded-md border px-1.5 py-0.5 font-mono text-[10px] font-medium shadow-sm backdrop-blur-sm ${
                    isNight
                      ? "border-amber-400/35 bg-slate-950/88 text-amber-200"
                      : "border-amber-800/25 bg-amber-50/92 text-amber-950"
                  }`}
                >
                  {poi.name}
                </div>
              </Html>
            </group>
          );
        })}
    </group>
  );
}
