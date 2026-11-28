"use client";

import { Component, Suspense, useEffect, type ReactNode } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, useProgress } from "@react-three/drei";
import * as THREE from "three";
import CampusModel from "./CampusModel";
import CameraRig, { DEFAULT_CAMERA_POSITION } from "./CameraRig";
import { DevPerfProbe, type DevPerfStats } from "./DevPerfMonitor";
import InstancedStreetlamps from "./InstancedStreetlamps";
import InstancedTrees from "./InstancedTrees";
import LandmarkLabels from "./LandmarkLabels";
import NightLights from "./NightLights";
import PolygonTracerLayer from "./PolygonTracerLayer";
import RouteRibbon from "./RouteRibbon";
import SatelliteOverlay from "./SatelliteOverlay";
import SkyDome from "./SkyDome";
import type { TourStop } from "@/data/tourStops";
import { useRenderProfile } from "@/lib/deviceProfile";
import type { SolarLightingState } from "@/lib/solar";
import type {
  BuildingMeta,
  FilterCategory,
  InspectableFeature,
  OverturePoi,
  RouteResult,
  StreetlampsData,
  TerrainBounds,
  TreesData,
} from "@/types/campus";

const DEFAULT_ORIGIN: [number, number] = [10.9027, 76.9006];
const DEFAULT_BBOX: [number, number, number, number] = [
  10.8965, 76.8935, 10.9095, 76.9075,
];

interface CustomFocusTarget {
  center: [number, number, number];
  offset?: [number, number, number];
  nonce: number;
}

interface CampusCanvasProps {
  buildings: BuildingMeta[];
  inspectables: InspectableFeature[];
  overturePois?: OverturePoi[];
  origin?: [number, number];
  bbox?: [number, number, number, number];
  treesData: TreesData | null;
  lampsData: StreetlampsData | null;
  terrainBounds?: TerrainBounds;
  lighting: SolarLightingState;
  fogEnabled: boolean;
  shadowsEnabled?: boolean;
  selectedId: string | null;
  hoveredId: string | null;
  debugMode: boolean;
  debugSatelliteEnabled: boolean;
  debugSatelliteOpacity: number;
  debugGhostBuildings: boolean;
  debugShowPois: boolean;
  debugTraceMode: boolean;
  tracedPoints: Array<[number, number, number]>;
  tracedHoverPoint: [number, number, number] | null;
  topDownNonce: number;
  isTourActive: boolean;
  debugSelected: InspectableFeature | null;
  debugHovered: InspectableFeature | null;
  activeCategory: FilterCategory;
  activeRoute: RouteResult | null;
  activeTourStop: TourStop | null;
  customFocusTarget: CustomFocusTarget | null;
  focusNonce: number;
  routeFocusNonce: number;
  tourFocusNonce: number;
  resetToken: number;
  onHover: (id: string | null) => void;
  onSelect: (id: string | null) => void;
  onSelectLandmark: (building: BuildingMeta) => void;
  onDebugHover: (feature: InspectableFeature | null) => void;
  onDebugSelect: (feature: InspectableFeature | null) => void;
  onTraceClick: (point: { x: number; y: number; z: number }) => void;
  onTraceHover: (point: { x: number; y: number; z: number } | null) => void;
  onSatelliteStatusChange: (status: "idle" | "loading" | "ready" | "error") => void;
  onProgress: (pct: number) => void;
  onReady: () => void;
  onDevStats?: (stats: DevPerfStats) => void;
}

class EnvErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }

  render() {
    return this.state.hasError ? null : this.props.children;
  }
}

function ProgressTracker({ onProgress }: { onProgress: (pct: number) => void }) {
  const { progress, active, loaded } = useProgress();

  useEffect(() => {
    if (active || loaded > 0) {
      onProgress(active ? progress : 100);
    }
  }, [progress, active, loaded, onProgress]);

  return null;
}

function ExposureSync({ exposure }: { exposure: number }) {
  useFrame((state) => {
    if (Math.abs(state.gl.toneMappingExposure - exposure) > 0.002) {
      state.gl.toneMappingExposure = exposure;
    }
  });
  return null;
}

export default function CampusCanvas({
  buildings,
  inspectables,
  overturePois,
  origin,
  bbox,
  treesData,
  lampsData,
  terrainBounds,
  lighting,
  fogEnabled,
  shadowsEnabled = false,
  selectedId,
  hoveredId,
  debugMode,
  debugSatelliteEnabled,
  debugSatelliteOpacity,
  debugGhostBuildings,
  debugShowPois,
  debugTraceMode,
  tracedPoints,
  tracedHoverPoint,
  topDownNonce,
  isTourActive,
  debugSelected,
  debugHovered,
  activeCategory,
  activeRoute,
  activeTourStop,
  customFocusTarget,
  focusNonce,
  routeFocusNonce,
  tourFocusNonce,
  resetToken,
  onHover,
  onSelect,
  onSelectLandmark,
  onDebugHover,
  onDebugSelect,
  onTraceClick,
  onTraceHover,
  onSatelliteStatusChange,
  onProgress,
  onReady,
  onDevStats,
}: CampusCanvasProps) {
  const profile = useRenderProfile();

  const selectedBuilding =
    selectedId ? buildings.find((b) => b.id === selectedId) ?? null : null;

  const tourBuilding = activeTourStop
    ? buildings.find((b) => b.id === activeTourStop.buildingId) ?? null
    : null;

  return (
    <div className="relative h-full w-full touch-none select-none">
      <Canvas
        shadows={shadowsEnabled ? "basic" : false}
        dpr={profile.dpr}
        camera={{
          position: DEFAULT_CAMERA_POSITION,
          fov: 42,
          near: 2,
          far: 4500,
        }}
        gl={{
          antialias: true,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: lighting.toneMappingExposure,
        }}
      >
        <color attach="background" args={[lighting.skyHorizonColor]} />
        <SkyDome
          horizonColor={lighting.skyHorizonColor}
          topColor={lighting.skyTopColor}
        />
        {fogEnabled && (
          <fog
            attach="fog"
            args={[lighting.fogColor, lighting.fogNear, lighting.fogFar]}
          />
        )}

        <hemisphereLight
          args={[
            lighting.hemiSky,
            lighting.hemiGround,
            lighting.hemiIntensity,
          ]}
        />
        <directionalLight
          position={lighting.sunPosition}
          intensity={lighting.sunIntensity}
          color={lighting.sunColor}
          castShadow={shadowsEnabled}
          key={`${profile.shadowMapSize}-${shadowsEnabled}`}
          shadow-mapSize={[profile.shadowMapSize, profile.shadowMapSize]}
          shadow-bias={-0.0003}
          shadow-normalBias={0.04}
          shadow-camera-left={-680}
          shadow-camera-right={680}
          shadow-camera-top={680}
          shadow-camera-bottom={-680}
          shadow-camera-near={50}
          shadow-camera-far={1750}
        />
        <directionalLight
          position={[-340, 220, -280]}
          intensity={lighting.fillIntensity}
          color={lighting.fillColor}
        />

        <EnvErrorBoundary>
          <Suspense fallback={null}>
            <Environment
              preset="park"
              environmentIntensity={lighting.envIntensity}
            />
          </Suspense>
        </EnvErrorBoundary>

        <ExposureSync exposure={lighting.toneMappingExposure} />
        <ProgressTracker onProgress={onProgress} />

        {process.env.NODE_ENV === "development" && onDevStats && (
          <DevPerfProbe onStats={onDevStats} />
        )}

        <Suspense fallback={null}>
          <CampusModel
            buildings={buildings}
            inspectables={inspectables}
            origin={origin}
            selectedId={selectedId}
            hoveredId={hoveredId}
            debugMode={debugMode}
            ghostBuildings={debugGhostBuildings}
            traceMode={debugTraceMode}
            debugSelected={debugSelected}
            debugHovered={debugHovered}
            activeCategory={activeCategory}
            nightFactor={lighting.nightFactor}
            isNight={lighting.isNight}
            onHover={onHover}
            onSelect={onSelect}
            onDebugHover={onDebugHover}
            onDebugSelect={onDebugSelect}
            onTraceClick={onTraceClick}
            onTraceHover={onTraceHover}
            onReady={onReady}
          />
          {debugMode && (
            <SatelliteOverlay
              enabled={debugSatelliteEnabled}
              opacity={debugSatelliteOpacity}
              bbox={bbox ?? DEFAULT_BBOX}
              origin={origin ?? DEFAULT_ORIGIN}
              traceActive={debugTraceMode}
              onTraceClick={onTraceClick}
              onTraceHover={onTraceHover}
              onStatusChange={onSatelliteStatusChange}
            />
          )}
        </Suspense>

        {debugMode && (
          <PolygonTracerLayer
            points={tracedPoints}
            hoverPoint={tracedHoverPoint}
            overturePois={overturePois}
            showPois={debugShowPois}
            isNight={lighting.isNight}
          />
        )}

        <InstancedTrees treesData={treesData} simple={profile.simpleTrees} />
        <InstancedStreetlamps
          lampsData={lampsData}
          nightFactor={lighting.nightFactor}
        />
        <NightLights nightFactor={lighting.nightFactor} />
        <LandmarkLabels
          buildings={buildings}
          selectedId={selectedId}
          hoveredId={hoveredId}
          debugMode={debugMode}
          isTourActive={isTourActive}
          isNight={lighting.isNight}
          onSelect={onSelectLandmark}
        />
        {activeRoute && <RouteRibbon route={activeRoute} />}

        <CameraRig
          selectedBuilding={selectedBuilding}
          activeRoute={activeRoute}
          activeTourStop={activeTourStop}
          tourBuilding={tourBuilding}
          customFocusTarget={customFocusTarget}
          terrainBounds={terrainBounds}
          debugMode={debugMode}
          topDownNonce={topDownNonce}
          focusNonce={focusNonce}
          routeFocusNonce={routeFocusNonce}
          tourFocusNonce={tourFocusNonce}
          resetToken={resetToken}
        />
      </Canvas>
    </div>
  );
}
