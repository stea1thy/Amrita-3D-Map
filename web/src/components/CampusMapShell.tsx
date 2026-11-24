"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { TOUR_STOPS } from "@/data/tourStops";
import { buildAdjacency, findWalkingRoute } from "@/lib/pathfinding";
import {
  TIME_PRESETS,
  computeSolarLighting,
  getCurrentIstMinutes,
  type TimePreset,
} from "@/lib/solar";
import BuildingInfoCard from "./BuildingInfoCard";
import {
  AboutModal,
  CampusListPanel,
  QuickJumpBar,
  TopRightBar,
  type QuickJumpItem,
} from "./CampusHudPanels";
import DebugInspectorOverlay from "./DebugInspectorOverlay";
import { DevPerfBadge, type DevPerfStats } from "./DevPerfMonitor";
import DirectionsPanel from "./DirectionsPanel";
import LoadingOverlay from "./LoadingOverlay";
import SearchBar from "./SearchBar";
import TimeOfDayControl from "./TimeOfDayControl";
import TourOverlay from "./TourOverlay";
import type {
  BuildingMeta,
  CampusMeta,
  FilterCategory,
  InspectableFeature,
  StreetlampsData,
  TreesData,
  WalkGraph,
} from "@/types/campus";

const CampusCanvas = dynamic(() => import("./CampusCanvas"), { ssr: false });

function subscribeLocation(callback: () => void) {
  window.addEventListener("popstate", callback);
  return () => window.removeEventListener("popstate", callback);
}

function getDebugModeSnapshot() {
  return new URLSearchParams(window.location.search).get("debug") === "1";
}

function getDebugModeServerSnapshot() {
  return false;
}

export default function CampusMapShell() {
  const debugMode = useSyncExternalStore(
    subscribeLocation,
    getDebugModeSnapshot,
    getDebugModeServerSnapshot,
  );

  const [meta, setMeta] = useState<CampusMeta | null>(null);
  const [walkGraph, setWalkGraph] = useState<WalkGraph | null>(null);
  const [treesData, setTreesData] = useState<TreesData | null>(null);
  const [lampsData, setLampsData] = useState<StreetlampsData | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [debugSelected, setDebugSelected] = useState<InspectableFeature | null>(
    null,
  );
  const [debugHovered, setDebugHovered] = useState<InspectableFeature | null>(
    null,
  );
  const [activeCategory, setActiveCategory] = useState<FilterCategory>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [focusNonce, setFocusNonce] = useState(0);
  const [routeFocusNonce, setRouteFocusNonce] = useState(0);
  const [tourFocusNonce, setTourFocusNonce] = useState(0);
  const [resetToken, setResetToken] = useState(0);
  const [activeJumpId, setActiveJumpId] = useState<string | null>(null);
  const [customFocusTarget, setCustomFocusTarget] = useState<{
    center: [number, number, number];
    offset?: [number, number, number];
    nonce: number;
  } | null>(null);

  const [directionsOpen, setDirectionsOpen] = useState(false);
  const [listOpen, setListOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [fromId, setFromId] = useState<string | null>(null);
  const [toId, setToId] = useState<string | null>(null);

  const [tourIndex, setTourIndex] = useState<number | null>(null);

  // Default to crisp 10:30 AM IST South Indian sunlight with Fog OFF by default
  const [timePreset, setTimePreset] = useState<TimePreset>("midday");
  const [istMinutes, setIstMinutes] = useState<number>(10 * 60 + 30);
  const [fogEnabled, setFogEnabled] = useState<boolean>(false);

  const [loadProgress, setLoadProgress] = useState(0);
  const [modelReady, setModelReady] = useState(false);
  const [devStats, setDevStats] = useState<DevPerfStats | null>(null);

  // Cartography debug overlay tools (?debug=1)
  const [debugSatelliteEnabled, setDebugSatelliteEnabled] = useState(false);
  const [debugSatelliteOpacity, setDebugSatelliteOpacity] = useState(0.85);
  const [debugSatelliteStatus, setDebugSatelliteStatus] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [debugGhostBuildings, setDebugGhostBuildings] = useState(false);
  const [debugShowPois, setDebugShowPois] = useState(false);
  const [debugTraceMode, setDebugTraceMode] = useState(false);
  const [tracedPoints, setTracedPoints] = useState<
    Array<[number, number, number]>
  >([]);
  const [tracedHoverPoint, setTracedHoverPoint] = useState<
    [number, number, number] | null
  >(null);
  const [topDownNonce, setTopDownNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      fetch("/data/campus_meta.json", { signal: controller.signal }).then(
        (res) => {
          if (!res.ok) {
            throw new Error(`Failed to load campus metadata (HTTP ${res.status})`);
          }
          return res.json() as Promise<CampusMeta>;
        },
      ),
      fetch("/data/walk_graph.json", { signal: controller.signal }).then(
        (res) => {
          if (!res.ok) {
            throw new Error(`Failed to load walk graph (HTTP ${res.status})`);
          }
          return res.json() as Promise<WalkGraph>;
        },
      ),
      fetch("/data/trees.json", { signal: controller.signal }).then(
        (res) => {
          if (!res.ok) {
            throw new Error(`Failed to load trees data (HTTP ${res.status})`);
          }
          return res.json() as Promise<TreesData>;
        },
      ),
      fetch("/data/streetlamps.json", { signal: controller.signal }).then(
        (res) =>
          res.ok ? (res.json() as Promise<StreetlampsData>) : null,
      ),
    ])
      .then(([campusData, graphData, treesJson, lampsJson]) => {
        setMeta(campusData);
        setWalkGraph(graphData);
        setTreesData(treesJson);
        setLampsData(lampsJson);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setMetaError(
          err instanceof Error ? err.message : "Failed to load campus data",
        );
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (timePreset !== "live") {
      return;
    }
    const syncId = window.setTimeout(() => {
      setIstMinutes(getCurrentIstMinutes());
    }, 0);
    const intervalId = window.setInterval(() => {
      setIstMinutes(getCurrentIstMinutes());
    }, 30_000);
    return () => {
      window.clearTimeout(syncId);
      window.clearInterval(intervalId);
    };
  }, [timePreset]);

  const lighting = useMemo(
    () => computeSolarLighting(istMinutes),
    [istMinutes],
  );

  const buildings = useMemo(() => meta?.buildings ?? [], [meta]);
  const inspectables = useMemo(() => meta?.inspectables ?? [], [meta]);

  const adjacency = useMemo(
    () => (walkGraph ? buildAdjacency(walkGraph) : null),
    [walkGraph],
  );

  const selectedBuilding = useMemo(
    () =>
      selectedId ? buildings.find((b) => b.id === selectedId) ?? null : null,
    [buildings, selectedId],
  );

  const fromBuilding = useMemo(
    () => (fromId ? buildings.find((b) => b.id === fromId) ?? null : null),
    [buildings, fromId],
  );

  const toBuilding = useMemo(
    () => (toId ? buildings.find((b) => b.id === toId) ?? null : null),
    [buildings, toId],
  );

  const activeTourStop =
    tourIndex !== null ? TOUR_STOPS[tourIndex] ?? null : null;

  const activeRoute = useMemo(() => {
    if (
      !directionsOpen ||
      activeTourStop ||
      !walkGraph ||
      !adjacency ||
      !fromBuilding ||
      !toBuilding ||
      fromBuilding.id === toBuilding.id
    ) {
      return null;
    }
    return findWalkingRoute(walkGraph, adjacency, fromBuilding, toBuilding);
  }, [
    directionsOpen,
    activeTourStop,
    walkGraph,
    adjacency,
    fromBuilding,
    toBuilding,
  ]);

  const handleSelectBuilding = useCallback((building: BuildingMeta) => {
    setTourIndex(null);
    setListOpen(false);
    setAboutOpen(false);
    setActiveJumpId(null);
    setCustomFocusTarget(null);
    setSelectedId(building.id);
    setFocusNonce((n) => n + 1);
  }, []);

  const handleCanvasSelect = useCallback(
    (id: string | null) => {
      if (tourIndex !== null) {
        return;
      }
      if (directionsOpen) {
        if (!id) {
          return;
        }
        if (!fromId) {
          setFromId(id);
        } else if (id !== fromId) {
          setToId(id);
        }
        return;
      }
      setListOpen(false);
      setAboutOpen(false);
      setActiveJumpId(null);
      setCustomFocusTarget(null);
      setSelectedId(id);
      if (id) {
        setFocusNonce((n) => n + 1);
      }
    },
    [tourIndex, directionsOpen, fromId],
  );

  const handleCategoryChange = useCallback(
    (nextCategory: FilterCategory) => {
      setActiveCategory(nextCategory);
      if (
        nextCategory !== "all" &&
        selectedBuilding &&
        selectedBuilding.category !== nextCategory
      ) {
        setSelectedId(null);
      }
    },
    [selectedBuilding],
  );

  const handleReady = useCallback(() => {
    setModelReady(true);
    setLoadProgress(100);
  }, []);

  const handleResetView = useCallback(() => {
    setSelectedId(null);
    setDebugSelected(null);
    setDebugTraceMode(false);
    setTracedPoints([]);
    setTracedHoverPoint(null);
    setActiveJumpId(null);
    setCustomFocusTarget(null);
    setDirectionsOpen(false);
    setListOpen(false);
    setAboutOpen(false);
    setTourIndex(null);
    setResetToken((n) => n + 1);
  }, []);

  const handleTraceClick = useCallback(
    (pt: { x: number; y: number; z: number }) => {
      setTracedPoints((prev) => [
        ...prev,
        [
          Number(pt.x.toFixed(2)),
          Number(pt.y.toFixed(2)),
          Number(pt.z.toFixed(2)),
        ],
      ]);
    },
    [],
  );

  const handleTraceHover = useCallback(
    (pt: { x: number; y: number; z: number } | null) => {
      if (!pt) {
        setTracedHoverPoint(null);
        return;
      }
      setTracedHoverPoint([
        Number(pt.x.toFixed(2)),
        Number(pt.y.toFixed(2)),
        Number(pt.z.toFixed(2)),
      ]);
    },
    [],
  );

  const handleRouteHere = useCallback(() => {
    if (!selectedBuilding) {
      return;
    }
    setTourIndex(null);
    setListOpen(false);
    setToId(selectedBuilding.id);
    if (fromId === selectedBuilding.id) {
      setFromId(null);
    }
    setSelectedId(null);
    setDirectionsOpen(true);
  }, [selectedBuilding, fromId]);

  const handleStartTour = useCallback(() => {
    setSelectedId(null);
    setDebugSelected(null);
    setActiveJumpId(null);
    setDirectionsOpen(false);
    setListOpen(false);
    setAboutOpen(false);
    setTourIndex(0);
    setTourFocusNonce((n) => n + 1);
  }, []);

  const handleQuickJump = useCallback(
    (item: QuickJumpItem) => {
      setTourIndex(null);
      setDirectionsOpen(false);
      setListOpen(false);
      setActiveCategory("all");
      setActiveJumpId(item.id);
      if (item.buildingId) {
        const found = buildings.find((b) => b.id === item.buildingId);
        if (found) {
          setCustomFocusTarget(null);
          setSelectedId(found.id);
          setFocusNonce((n) => n + 1);
        }
        return;
      }
      if (item.customTarget) {
        setSelectedId(null);
        setCustomFocusTarget({
          center: item.customTarget.center,
          offset: item.customTarget.offset,
          nonce: Date.now(),
        });
      }
    },
    [buildings],
  );

  const handleSelectPreset = useCallback(
    (preset: Exclude<TimePreset, "custom">) => {
      setTimePreset(preset);
      const found = TIME_PRESETS.find((p) => p.id === preset);
      if (preset === "live" || !found || found.minutes === null) {
        setIstMinutes(getCurrentIstMinutes());
      } else {
        setIstMinutes(found.minutes);
      }
    },
    [],
  );

  const handleChangeMinutes = useCallback((minutes: number) => {
    setTimePreset("custom");
    setIstMinutes(minutes);
  }, []);

  const canvasSelectedId = activeTourStop
    ? activeTourStop.buildingId
    : directionsOpen
      ? (toId ?? fromId)
      : selectedId;

  const hasBottomCardMobile = Boolean(
    activeTourStop || (!directionsOpen && !debugMode && selectedBuilding),
  );

  return (
    <main
      className="relative h-dvh w-screen overflow-hidden transition-colors duration-500"
      style={{ backgroundColor: lighting.skyColor }}
    >
      <CampusCanvas
        buildings={buildings}
        inspectables={inspectables}
        overturePois={meta?.overturePois}
        origin={meta?.origin}
        bbox={meta?.bbox}
        treesData={treesData}
        lampsData={lampsData}
        terrainBounds={meta?.terrainBounds}
        lighting={lighting}
        fogEnabled={fogEnabled}
        selectedId={canvasSelectedId}
        hoveredId={hoveredId}
        debugMode={debugMode}
        debugSatelliteEnabled={debugSatelliteEnabled}
        debugSatelliteOpacity={debugSatelliteOpacity}
        debugGhostBuildings={debugGhostBuildings}
        debugShowPois={debugShowPois}
        debugTraceMode={debugTraceMode}
        tracedPoints={tracedPoints}
        tracedHoverPoint={tracedHoverPoint}
        topDownNonce={topDownNonce}
        isTourActive={Boolean(activeTourStop)}
        debugSelected={debugSelected}
        debugHovered={debugHovered}
        activeCategory={
          directionsOpen || activeTourStop ? "all" : activeCategory
        }
        activeRoute={activeRoute}
        activeTourStop={activeTourStop}
        customFocusTarget={customFocusTarget}
        focusNonce={focusNonce}
        routeFocusNonce={routeFocusNonce}
        tourFocusNonce={tourFocusNonce}
        resetToken={resetToken}
        onHover={setHoveredId}
        onSelect={handleCanvasSelect}
        onSelectLandmark={handleSelectBuilding}
        onDebugHover={setDebugHovered}
        onDebugSelect={setDebugSelected}
        onTraceClick={handleTraceClick}
        onTraceHover={handleTraceHover}
        onSatelliteStatusChange={setDebugSatelliteStatus}
        onProgress={setLoadProgress}
        onReady={handleReady}
        onDevStats={
          process.env.NODE_ENV === "development" ? setDevStats : undefined
        }
      />

      {!activeTourStop &&
        (directionsOpen ? (
          <DirectionsPanel
            buildings={buildings}
            fromBuilding={fromBuilding}
            toBuilding={toBuilding}
            route={activeRoute}
            isNight={lighting.isNight}
            onSelectFrom={(b) => setFromId(b?.id ?? null)}
            onSelectTo={(b) => setToId(b?.id ?? null)}
            onSwap={() => {
              setFromId(toId);
              setToId(fromId);
            }}
            onFrameRoute={() => setRouteFocusNonce((n) => n + 1)}
            onClearRoute={() => {
              setFromId(null);
              setToId(null);
            }}
            onClose={() => setDirectionsOpen(false)}
          />
        ) : (
          <SearchBar
            buildings={buildings}
            query={searchQuery}
            activeCategory={activeCategory}
            isNight={lighting.isNight}
            onQueryChange={setSearchQuery}
            onCategoryChange={handleCategoryChange}
            onSelectBuilding={handleSelectBuilding}
            onOpenDirections={() => {
              if (selectedBuilding && !toId && !fromId) {
                setToId(selectedBuilding.id);
              }
              setSelectedId(null);
              setListOpen(false);
              setDirectionsOpen(true);
            }}
          />
        ))}

      <TopRightBar
        listOpen={listOpen}
        tourActive={Boolean(activeTourStop)}
        aboutOpen={aboutOpen}
        isNight={lighting.isNight}
        onResetView={handleResetView}
        onToggleList={() => {
          setAboutOpen(false);
          setListOpen((v) => !v);
        }}
        onToggleTour={() => {
          if (activeTourStop) {
            setTourIndex(null);
          } else {
            handleStartTour();
          }
        }}
        onToggleAbout={() => {
          setListOpen(false);
          setAboutOpen((v) => !v);
        }}
      />

      {listOpen && !activeTourStop && (
        <CampusListPanel
          buildings={buildings}
          selectedId={selectedId}
          isNight={lighting.isNight}
          onSelect={(b) => {
            setListOpen(false);
            setDirectionsOpen(false);
            setActiveJumpId(null);
            handleSelectBuilding(b);
          }}
          onClose={() => setListOpen(false)}
        />
      )}

      {!activeTourStop && !directionsOpen && !debugMode && selectedBuilding && (
        <BuildingInfoCard
          building={selectedBuilding}
          isNight={lighting.isNight}
          onClose={() => setSelectedId(null)}
          onFocus={() => setFocusNonce((n) => n + 1)}
          onRouteHere={handleRouteHere}
        />
      )}

      {debugMode && !activeTourStop && (
        <DebugInspectorOverlay
          selected={debugSelected}
          origin={meta?.origin ?? [10.9027, 76.9006]}
          overtureRelease={meta?.overtureRelease}
          unmatchedPoiCount={meta?.overturePois?.length ?? 0}
          isNight={lighting.isNight}
          satelliteEnabled={debugSatelliteEnabled}
          satelliteOpacity={debugSatelliteOpacity}
          satelliteStatus={debugSatelliteStatus}
          ghostBuildings={debugGhostBuildings}
          showPois={debugShowPois}
          traceMode={debugTraceMode}
          tracedPoints={tracedPoints}
          onCloseFeature={() => setDebugSelected(null)}
          onToggleSatellite={() => setDebugSatelliteEnabled((v) => !v)}
          onSatelliteOpacityChange={setDebugSatelliteOpacity}
          onToggleGhost={() => setDebugGhostBuildings((v) => !v)}
          onTopDownView={() => setTopDownNonce((n) => n + 1)}
          onTogglePois={() => setDebugShowPois((v) => !v)}
          onToggleTrace={() => {
            setDebugTraceMode((prev) => {
              const next = !prev;
              if (!next) {
                setTracedHoverPoint(null);
              }
              return next;
            });
          }}
          onUndoTracePoint={() => setTracedPoints((prev) => prev.slice(0, -1))}
          onClearTracePoints={() => setTracedPoints([])}
        />
      )}

      {activeTourStop && tourIndex !== null && (
        <TourOverlay
          stops={TOUR_STOPS}
          currentIndex={tourIndex}
          isNight={lighting.isNight}
          onSelectIndex={(idx) => {
            setTourIndex(idx);
            setTourFocusNonce((n) => n + 1);
          }}
          onExit={() => setTourIndex(null)}
        />
      )}

      <TimeOfDayControl
        preset={timePreset}
        minutesIst={istMinutes}
        lighting={lighting}
        fogEnabled={fogEnabled}
        hideOnMobile={hasBottomCardMobile}
        onSelectPreset={handleSelectPreset}
        onChangeMinutes={handleChangeMinutes}
        onToggleFog={setFogEnabled}
      />

      <QuickJumpBar
        activeJumpId={activeJumpId}
        isNight={lighting.isNight}
        onJump={handleQuickJump}
      />

      {aboutOpen && (
        <AboutModal
          buildingCount={meta?.counts.namedBuildings ?? buildings.filter((b) => b.isNamed).length}
          treeCount={treesData?.count ?? 0}
          lampCount={lampsData?.count ?? 0}
          isNight={lighting.isNight}
          onClose={() => setAboutOpen(false)}
        />
      )}

      {process.env.NODE_ENV === "development" && devStats && (
        <DevPerfBadge stats={devStats} isNight={lighting.isNight} />
      )}

      {metaError && (
        <div
          role="alert"
          className="fixed bottom-16 left-1/2 z-30 -translate-x-1/2 rounded-xl border border-red-900/20 bg-red-50/95 px-4 py-2 text-xs font-medium text-red-900 shadow-md backdrop-blur-md"
        >
          {metaError}
        </div>
      )}

      <LoadingOverlay
        progress={loadProgress}
        ready={modelReady}
        isNight={lighting.isNight}
      />
    </main>
  );
}
