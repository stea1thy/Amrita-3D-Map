"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

export interface DevPerfStats {
  fps: number;
  triangles: number;
  calls: number;
  geometries: number;
}

const TRIANGLE_BUDGET = 150_000;

export function DevPerfProbe({
  onStats,
}: {
  onStats: (stats: DevPerfStats) => void;
}) {
  const framesRef = useRef(0);
  const lastSampleRef = useRef(0);

  useFrame((state) => {
    const now = performance.now();
    if (lastSampleRef.current === 0) {
      lastSampleRef.current = now;
      return;
    }

    framesRef.current += 1;
    const elapsed = now - lastSampleRef.current;
    if (elapsed >= 500) {
      const fps = Math.round((framesRef.current * 1000) / elapsed);
      const { triangles, calls } = state.gl.info.render;
      const { geometries } = state.gl.info.memory;
      onStats({ fps, triangles, calls, geometries });
      framesRef.current = 0;
      lastSampleRef.current = now;
    }
  });

  return null;
}

export function DevPerfBadge({
  stats,
  isNight,
}: {
  stats: DevPerfStats;
  isNight: boolean;
}) {
  const overBudget = stats.triangles > TRIANGLE_BUDGET;

  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none fixed bottom-14 right-3 z-10 hidden items-center gap-2 rounded-lg border px-2.5 py-1 font-mono text-[11px] backdrop-blur-md sm:flex ${
        isNight
          ? "border-slate-400/20 bg-slate-900/80 text-slate-200"
          : "border-slate-900/12 bg-[#FAFBF9]/85 text-slate-700"
      }`}
    >
      <span className="font-semibold tabular-nums">{stats.fps} FPS</span>
      <span className="opacity-40">|</span>
      <span
        className={`tabular-nums ${
          overBudget
            ? "font-semibold text-red-500"
            : isNight
              ? "text-emerald-300"
              : "text-emerald-700"
        }`}
      >
        {stats.triangles.toLocaleString()} / 150k tris
      </span>
      <span className="opacity-40">|</span>
      <span className="tabular-nums">{stats.calls} draws</span>
    </div>
  );
}
