"use client";

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import ScreenLabel from "./ScreenLabel";
import type { BuildingMeta } from "@/types/campus";

interface LandmarkLabelsProps {
  buildings: BuildingMeta[];
  selectedId: string | null;
  hoveredId: string | null;
  debugMode: boolean;
  isTourActive: boolean;
  isNight: boolean;
  onSelect: (building: BuildingMeta) => void;
}

interface LandmarkSpec {
  id: string;
  shortLabel: string;
  tier: "primary" | "secondary";
}

const MAJOR_LANDMARKS: LandmarkSpec[] = [
  { id: "hero/main-gate", shortLabel: "Main Gate", tier: "primary" },
  { id: "hero/security-office", shortLabel: "Security Office", tier: "secondary" },
  { id: "hero/students-parking", shortLabel: "Student's Parking", tier: "secondary" },
  { id: "hero/visitor-parking", shortLabel: "Car Parking", tier: "secondary" },
  { id: "way/380925364", shortLabel: "AB-1", tier: "primary" },
  { id: "way/380702789", shortLabel: "AB-2", tier: "primary" },
  { id: "way/380829415", shortLabel: "AB-3", tier: "primary" },
  { id: "custom/academic-block-4", shortLabel: "AB-4", tier: "primary" },
  { id: "way/380702790", shortLabel: "Central Library", tier: "primary" },
  { id: "way/380829759", shortLabel: "ASB", tier: "primary" },
  { id: "way/546394562", shortLabel: "Main Canteen", tier: "primary" },
  { id: "way/380925366", shortLabel: "Hostels", tier: "primary" },
  { id: "way/380925370", shortLabel: "Amriteshwari Hall", tier: "secondary" },
  { id: "way/380829758", shortLabel: "Pandal", tier: "secondary" },
  { id: "way/380829757", shortLabel: "CIR", tier: "secondary" },
  { id: "way/1080744354", shortLabel: "IT Canteen", tier: "secondary" },
  { id: "way/380702791", shortLabel: "Gargi Bhavanam", tier: "secondary" },
  { id: "way/380829420", shortLabel: "Gauthama Bhavanam", tier: "secondary" },
  { id: "way/380829425", shortLabel: "Vasishta Bhavanam", tier: "secondary" },
  { id: "way/1256941484", shortLabel: "Adithi Bhavanam", tier: "secondary" },
  { id: "way/380829427", shortLabel: "Guest House", tier: "secondary" },
];

export default function LandmarkLabels({
  buildings,
  selectedId,
  hoveredId,
  debugMode,
  isTourActive,
  isNight,
  onSelect,
}: LandmarkLabelsProps) {
  const [zoomTier, setZoomTier] = useState<"close" | "overview" | "far">(
    "overview",
  );
  const tierRef = useRef<"close" | "overview" | "far">("overview");

  useFrame((state) => {
    const camY = state.camera.position.y;
    const nextTier = camY < 245 ? "close" : camY < 760 ? "overview" : "far";
    if (nextTier !== tierRef.current) {
      tierRef.current = nextTier;
      setZoomTier(nextTier);
    }
  });

  const resolved = useMemo(() => {
    const byId = new Map<string, BuildingMeta>();
    for (const b of buildings) {
      byId.set(b.id, b);
    }
    return MAJOR_LANDMARKS.map((spec) => {
      const building = byId.get(spec.id);
      return building ? { ...spec, building } : null;
    }).filter((x): x is LandmarkSpec & { building: BuildingMeta } => x !== null);
  }, [buildings]);

  if (debugMode || isTourActive || zoomTier === "far" || resolved.length === 0) {
    return null;
  }

  return (
    <group name="LANDMARK_PILL_LABELS">
      {resolved.map(({ id, shortLabel, tier, building }) => {
        if (tier === "secondary" && zoomTier !== "close") {
          return null;
        }
        if (id === hoveredId || id === selectedId) {
          return null;
        }
        return (
          <ScreenLabel
            key={id}
            position={[
              building.center[0],
              building.center[1] + building.heightM * 0.5 + 4.5,
              building.center[2],
            ]}
            center
            zIndexRange={[4, 0]}
          >
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelect(building);
              }}
              className={`cursor-pointer select-none whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-tight shadow-sm backdrop-blur-sm transition-transform hover:scale-105 ${
                isNight
                  ? "border-slate-300/20 bg-slate-900/86 text-slate-100 hover:bg-slate-800"
                  : "border-slate-900/12 bg-white/92 text-slate-900 hover:bg-white"
              }`}
            >
              {shortLabel}
            </button>
          </ScreenLabel>
        );
      })}
    </group>
  );
}
