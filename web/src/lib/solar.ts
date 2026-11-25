import { getPosition } from "suncalc";
import * as THREE from "three";

export const CAMPUS_LAT = 10.9027;
export const CAMPUS_LON = 76.9006;
const SUN_ORBIT_RADIUS = 650;

export type TimePreset =
  | "sunrise"
  | "midday"
  | "golden"
  | "night"
  | "live"
  | "custom";

export const TIME_PRESETS: Array<{
  id: Exclude<TimePreset, "custom">;
  label: string;
  minutes: number | null;
}> = [
  { id: "sunrise", label: "Sunrise", minutes: 6 * 60 + 25 },
  { id: "midday", label: "Midday", minutes: 10 * 60 + 30 },
  { id: "golden", label: "Golden hour", minutes: 17 * 60 + 35 },
  { id: "night", label: "Night", minutes: 21 * 60 },
  { id: "live", label: "Now", minutes: null },
];

export interface SolarLightingState {
  minutesIst: number;
  altitudeDeg: number;
  azimuthDeg: number;
  isNight: boolean;
  nightFactor: number;
  skyColor: string;
  skyHorizonColor: string;
  skyTopColor: string;
  fogColor: string;
  fogNear: number;
  fogFar: number;
  sunPosition: [number, number, number];
  sunColor: string;
  sunIntensity: number;
  hemiSky: string;
  hemiGround: string;
  hemiIntensity: number;
  fillColor: string;
  fillIntensity: number;
  envIntensity: number;
  toneMappingExposure: number;
}

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = clamp01((x - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
}

function mixNum(a: number, b: number, t: number): number {
  return a + (b - a) * clamp01(t);
}

function mixHex(hexA: string, hexB: string, t: number): string {
  const c = new THREE.Color(hexA).lerp(new THREE.Color(hexB), clamp01(t));
  return `#${c.getHexString()}`;
}

export function getCurrentIstMinutes(now: Date = new Date()): number {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(now);

  const rawHour = Number(parts.find((p) => p.type === "hour")?.value ?? "10");
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? "0");
  const hour = rawHour === 24 ? 0 : rawHour;
  return hour * 60 + minute;
}

export function formatIstMinutes(minutesIst: number): string {
  const wrapped = ((Math.round(minutesIst) % 1440) + 1440) % 1440;
  const hh = String(Math.floor(wrapped / 60)).padStart(2, "0");
  const mm = String(wrapped % 60).padStart(2, "0");
  return `${hh}:${mm} IST`;
}

function istMinutesToUtcDate(minutesIst: number, refDate: Date): Date {
  const dateStr = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(refDate);
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 0, minutesIst - 330, 0));
}

export function computeSolarLighting(
  minutesIst: number,
  refDate: Date = new Date(),
): SolarLightingState {
  const solarDate = istMinutesToUtcDate(minutesIst, refDate);
  const pos = getPosition(solarDate, CAMPUS_LAT, CAMPUS_LON);

  // suncalc v2.x returns azimuth (deg clockwise from North) and altitude (deg)
  const altDeg = pos.altitude;
  const azDeg = pos.azimuth;
  const altRad = (altDeg * Math.PI) / 180;
  const azRad = (azDeg * Math.PI) / 180;

  const dayFactor = smoothstep(0, 22, altDeg);
  const nightFactor = 1 - smoothstep(-4, 2, altDeg);
  const goldenFactor =
    Math.exp(-Math.pow((altDeg - 7) / 10, 2)) * (1 - nightFactor);

  // Convert North-clockwise azimuth to glTF (+X East, +Y Up, +Z South)
  const cosAlt = Math.cos(altRad);
  const rawSunX = Math.sin(azRad) * cosAlt * SUN_ORBIT_RADIUS;
  const rawSunY = Math.max(40, Math.sin(altRad) * SUN_ORBIT_RADIUS);
  const rawSunZ = -Math.cos(azRad) * cosAlt * SUN_ORBIT_RADIUS;

  const moonBlend = smoothstep(4, -2, altDeg);
  const sunPosition: [number, number, number] = [
    mixNum(rawSunX, -220, moonBlend),
    mixNum(rawSunY, 420, moonBlend),
    mixNum(rawSunZ, -180, moonBlend),
  ];

  const dayHorizon = mixHex("#CDE4F9", "#F2C9A2", goldenFactor * 0.72);
  const skyHorizonColor = mixHex(dayHorizon, "#12233B", nightFactor);

  const dayTop = mixHex("#6DA8E3", "#5E83B8", goldenFactor * 0.55);
  const skyTopColor = mixHex(dayTop, "#070F1D", nightFactor);

  const daySunColor = mixHex("#FFF8EB", "#FFA85C", goldenFactor * 0.85);
  const sunColor = mixHex(daySunColor, "#84A9E0", nightFactor);
  const sunIntensity =
    2.1 * dayFactor +
    1.0 * goldenFactor * (1 - nightFactor) +
    0.42 * nightFactor;

  const hemiSky = mixHex(
    mixHex("#CFE8FF", "#F5CAA0", goldenFactor * 0.55),
    "#233A56",
    nightFactor,
  );
  const hemiGround = mixHex("#699C5D", "#1A2330", nightFactor);
  const hemiIntensity = mixNum(1.12, 0.55, nightFactor);

  const fillColor = mixHex("#BDE0FF", "#395980", nightFactor);
  const fillIntensity = mixNum(0.32, 0.25, nightFactor);

  return {
    minutesIst,
    altitudeDeg: Math.round(altDeg * 10) / 10,
    azimuthDeg: Math.round(azDeg * 10) / 10,
    isNight: altDeg < 0,
    nightFactor,
    skyColor: skyHorizonColor,
    skyHorizonColor,
    skyTopColor,
    fogColor: skyHorizonColor,
    fogNear: Math.round(mixNum(950, 750, nightFactor)),
    fogFar: Math.round(mixNum(3400, 2600, nightFactor)),
    sunPosition,
    sunColor,
    sunIntensity,
    hemiSky,
    hemiGround,
    hemiIntensity,
    fillColor,
    fillIntensity,
    envIntensity: mixNum(0.42, 0.12, nightFactor),
    toneMappingExposure: mixNum(1.06, 1.14, nightFactor),
  };
}
