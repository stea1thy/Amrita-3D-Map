"use client";

interface NightLightsProps {
  nightFactor: number;
}

const PLAZA_LIGHTS: Array<[number, number, number]> = [
  [240, 24, 245],   // AB-1 & Main Canteen
  [-200, 30, -175], // AB-2 & Central Library
  [380, 24, 180],   // Eastern Hostels & Playground edge
];

export default function NightLights({ nightFactor }: NightLightsProps) {
  const active = nightFactor > 0.02;
  const pointIntensity = active ? 22 * nightFactor : 0;

  return (
    <group name="NIGHT_CAMPUS_LIGHTS">
      {PLAZA_LIGHTS.map((pos, idx) => (
        <pointLight
          key={idx}
          position={pos}
          color="#FFBA6B"
          intensity={pointIntensity}
          distance={260}
          decay={2}
        />
      ))}
    </group>
  );
}
