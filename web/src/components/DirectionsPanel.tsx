"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpDown,
  Clock,
  Maximize2,
  Route,
  TrendingUp,
  X,
} from "lucide-react";
import { searchBuildings } from "@/lib/search";
import {
  CATEGORY_META,
  type BuildingMeta,
  type RouteResult,
} from "@/types/campus";

interface DirectionsPanelProps {
  buildings: BuildingMeta[];
  fromBuilding: BuildingMeta | null;
  toBuilding: BuildingMeta | null;
  route: RouteResult | null;
  isNight: boolean;
  onSelectFrom: (building: BuildingMeta | null) => void;
  onSelectTo: (building: BuildingMeta | null) => void;
  onSwap: () => void;
  onFrameRoute: () => void;
  onClearRoute: () => void;
  onClose: () => void;
}

type ActiveField = "from" | "to" | null;

function formatDistance(meters: number): string {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(2)} km`;
  }
  return `${Math.round(meters)} m`;
}

function formatDuration(seconds: number, minutes: number): string {
  if (seconds < 45) {
    return "< 1 min";
  }
  return `${minutes} min`;
}

export default function DirectionsPanel({
  buildings,
  fromBuilding,
  toBuilding,
  route,
  isNight,
  onSelectFrom,
  onSelectTo,
  onSwap,
  onFrameRoute,
  onClearRoute,
  onClose,
}: DirectionsPanelProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [activeField, setActiveField] = useState<ActiveField>(null);
  const [fieldQuery, setFieldQuery] = useState("");
  const [highlightedIdx, setHighlightedIdx] = useState(0);

  const results = useMemo(() => {
    if (!activeField) {
      return [];
    }
    return searchBuildings(buildings, fieldQuery, "all", 10);
  }, [buildings, activeField, fieldQuery]);

  useEffect(() => {
    const onPointerDown = (e: PointerEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setActiveField(null);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const activeIdx =
    results.length === 0 ? -1 : Math.min(highlightedIdx, results.length - 1);

  const commitPick = (building: BuildingMeta) => {
    if (activeField === "from") {
      onSelectFrom(building);
    } else if (activeField === "to") {
      onSelectTo(building);
    }
    setActiveField(null);
    setFieldQuery("");
  };

  const handleFieldKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && results.length > 0) {
      e.preventDefault();
      setHighlightedIdx((prev) => (prev + 1) % results.length);
    } else if (e.key === "ArrowUp" && results.length > 0) {
      e.preventDefault();
      setHighlightedIdx((prev) =>
        prev <= 0 ? results.length - 1 : prev - 1,
      );
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      commitPick(results[activeIdx]);
    } else if (e.key === "Escape") {
      setActiveField(null);
      setFieldQuery("");
    }
  };

  return (
    <div
      ref={containerRef}
      className="animate-panel-in fixed top-3 left-3 right-3 z-20 flex flex-col gap-2 sm:right-auto sm:w-[368px]"
    >
      <div
        className={`rounded-2xl border p-3.5 shadow-[0_14px_34px_-10px_rgba(15,23,42,0.24)] backdrop-blur-md ${
          isNight
            ? "border-slate-300/15 bg-slate-900/90 text-slate-100"
            : "border-slate-900/12 bg-[#FAFBF9]/92 text-slate-900"
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-tight">
            Walking directions
          </h2>
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Swap start and destination"
              onClick={onSwap}
              className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
                isNight
                  ? "border-slate-300/15 bg-slate-800/75 text-slate-300 hover:bg-slate-700 hover:text-white"
                  : "border-slate-900/10 bg-white/75 text-slate-600 hover:bg-white hover:text-slate-950"
              }`}
            >
              <ArrowUpDown className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              aria-label="Close directions"
              onClick={onClose}
              className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
                isNight
                  ? "border-slate-300/15 bg-slate-800/75 text-slate-300 hover:bg-slate-700 hover:text-white"
                  : "border-slate-900/10 bg-white/75 text-slate-600 hover:bg-white hover:text-slate-950"
              }`}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* From & To inputs */}
        <div className="mt-2.5 flex flex-col gap-2">
          {/* From input */}
          <div
            className={`relative flex items-center rounded-xl border focus-within:border-[#0F766E]/60 focus-within:ring-2 focus-within:ring-[#0F766E]/15 ${
              isNight
                ? "border-slate-300/15 bg-slate-800/75"
                : "border-slate-900/12 bg-white/80"
            }`}
          >
            <span
              className="ml-3 h-2.5 w-2.5 shrink-0 rounded-full bg-[#0F766E]"
              aria-hidden="true"
            />
            <input
              type="text"
              aria-label="Starting building"
              value={activeField === "from" ? fieldQuery : (fromBuilding?.name ?? "")}
              placeholder={
                fromBuilding ? fromBuilding.name : "Choose starting building..."
              }
              onFocus={() => {
                setActiveField("from");
                setFieldQuery("");
                setHighlightedIdx(0);
              }}
              onChange={(e) => {
                setFieldQuery(e.target.value);
                setHighlightedIdx(0);
              }}
              onKeyDown={handleFieldKeyDown}
              className={`h-10 w-full bg-transparent px-2.5 text-sm focus:outline-none ${
                isNight
                  ? "text-slate-100 placeholder:text-slate-400"
                  : "text-slate-900 placeholder:text-slate-500"
              }`}
            />
            {fromBuilding && (
              <button
                type="button"
                aria-label="Clear starting building"
                onClick={() => {
                  onSelectFrom(null);
                  setFieldQuery("");
                }}
                className={`mr-1.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
                  isNight
                    ? "text-slate-400 hover:bg-slate-700 hover:text-white"
                    : "text-slate-500 hover:bg-slate-900/8 hover:text-slate-800"
                }`}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* To input */}
          <div
            className={`relative flex items-center rounded-xl border focus-within:border-[#D97706]/60 focus-within:ring-2 focus-within:ring-[#D97706]/15 ${
              isNight
                ? "border-slate-300/15 bg-slate-800/75"
                : "border-slate-900/12 bg-white/80"
            }`}
          >
            <span
              className="ml-3 h-2.5 w-2.5 shrink-0 rounded-full bg-[#D97706]"
              aria-hidden="true"
            />
            <input
              type="text"
              aria-label="Destination building"
              value={activeField === "to" ? fieldQuery : (toBuilding?.name ?? "")}
              placeholder={
                toBuilding ? toBuilding.name : "Choose destination building..."
              }
              onFocus={() => {
                setActiveField("to");
                setFieldQuery("");
                setHighlightedIdx(0);
              }}
              onChange={(e) => {
                setFieldQuery(e.target.value);
                setHighlightedIdx(0);
              }}
              onKeyDown={handleFieldKeyDown}
              className={`h-10 w-full bg-transparent px-2.5 text-sm focus:outline-none ${
                isNight
                  ? "text-slate-100 placeholder:text-slate-400"
                  : "text-slate-900 placeholder:text-slate-500"
              }`}
            />
            {toBuilding && (
              <button
                type="button"
                aria-label="Clear destination building"
                onClick={() => {
                  onSelectTo(null);
                  setFieldQuery("");
                }}
                className={`mr-1.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
                  isNight
                    ? "text-slate-400 hover:bg-slate-700 hover:text-white"
                    : "text-slate-500 hover:bg-slate-900/8 hover:text-slate-800"
                }`}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Route summary or helper prompt */}
        {route ? (
          <div
            className={`mt-3 border-t pt-3 ${
              isNight ? "border-slate-300/10" : "border-slate-900/8"
            }`}
          >
            <div className="grid grid-cols-3 gap-2">
              <div
                className={`rounded-xl border px-2.5 py-2 ${
                  isNight
                    ? "border-slate-300/12 bg-slate-800/70"
                    : "border-slate-900/8 bg-white/70"
                }`}
              >
                <div
                  className={`flex items-center gap-1 text-[11px] font-medium ${
                    isNight ? "text-slate-400" : "text-slate-500"
                  }`}
                >
                  <Clock className="h-3 w-3 text-[#14B8A6]" />
                  <span>Walk</span>
                </div>
                <div className="mt-0.5 font-mono text-sm font-semibold tabular-nums">
                  {formatDuration(route.estimatedSeconds, route.estimatedMinutes)}
                </div>
              </div>

              <div
                className={`rounded-xl border px-2.5 py-2 ${
                  isNight
                    ? "border-slate-300/12 bg-slate-800/70"
                    : "border-slate-900/8 bg-white/70"
                }`}
              >
                <div
                  className={`flex items-center gap-1 text-[11px] font-medium ${
                    isNight ? "text-slate-400" : "text-slate-500"
                  }`}
                >
                  <Route className="h-3 w-3 opacity-80" />
                  <span>Distance</span>
                </div>
                <div className="mt-0.5 font-mono text-sm font-semibold tabular-nums">
                  {formatDistance(route.distanceM)}
                </div>
              </div>

              <div
                className={`rounded-xl border px-2.5 py-2 ${
                  isNight
                    ? "border-slate-300/12 bg-slate-800/70"
                    : "border-slate-900/8 bg-white/70"
                }`}
              >
                <div
                  className={`flex items-center gap-1 text-[11px] font-medium ${
                    isNight ? "text-slate-400" : "text-slate-500"
                  }`}
                >
                  <TrendingUp className="h-3 w-3 text-[#F59E0B]" />
                  <span>Climb</span>
                </div>
                <div className="mt-0.5 font-mono text-sm font-semibold tabular-nums">
                  +{Math.round(route.elevationGainM)} m
                </div>
              </div>
            </div>

            <div className="mt-2.5 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={onClearRoute}
                className={`h-8 rounded-lg border px-2.5 text-xs font-medium transition-colors ${
                  isNight
                    ? "border-slate-300/15 bg-slate-800/75 text-slate-300 hover:bg-slate-700 hover:text-white"
                    : "border-slate-900/12 bg-white/75 text-slate-700 hover:bg-white hover:text-slate-950"
                }`}
              >
                Clear
              </button>
              <button
                type="button"
                onClick={onFrameRoute}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-[#1D5C63] px-3 text-xs font-medium text-white transition-all duration-150 hover:bg-[#174B51] active:scale-[0.97]"
              >
                <Maximize2 className="h-3.5 w-3.5" />
                <span>Frame route</span>
              </button>
            </div>
          </div>
        ) : (
          <p
            className={`mt-2.5 text-xs ${
              isNight ? "text-slate-400" : "text-slate-600"
            }`}
          >
            {fromBuilding && toBuilding && fromBuilding.id === toBuilding.id
              ? "Choose two different buildings to compute a route."
              : "Pick two buildings above or click them on the 3D map."}
          </p>
        )}
      </div>

      {/* Picker dropdown */}
      {activeField && (
        <div
          role="listbox"
          aria-label={
            activeField === "from"
              ? "Starting building options"
              : "Destination building options"
          }
          className={`animate-panel-in max-h-[min(300px,46vh)] overflow-y-auto rounded-xl border p-1.5 shadow-[0_14px_34px_-10px_rgba(15,23,42,0.26)] backdrop-blur-md ${
            isNight
              ? "border-slate-300/15 bg-slate-900/95"
              : "border-slate-900/12 bg-[#FAFBF9]/95"
          }`}
        >
          {results.length === 0 ? (
            <div
              className={`px-3 py-4 text-center text-xs ${
                isNight ? "text-slate-400" : "text-slate-600"
              }`}
            >
              No matching campus buildings found.
            </div>
          ) : (
            results.map((b, idx) => {
              const cat = CATEGORY_META[b.category];
              const isHighlighted = idx === activeIdx;
              return (
                <button
                  key={b.id}
                  type="button"
                  role="option"
                  aria-selected={isHighlighted}
                  onMouseEnter={() => setHighlightedIdx(idx)}
                  onClick={() => commitPick(b)}
                  className={`flex w-full items-center justify-between gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors ${
                    isHighlighted
                      ? isNight
                        ? "bg-teal-400/15 text-white"
                        : "bg-[#1D5C63]/10 text-slate-950"
                      : isNight
                        ? "text-slate-200 hover:bg-slate-800"
                        : "text-slate-800 hover:bg-slate-900/5"
                  }`}
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-black/10"
                      style={{ backgroundColor: cat.dotColor }}
                    />
                    <span className="truncate text-sm font-medium">
                      {b.name}
                    </span>
                  </div>
                  <span
                    className={`shrink-0 font-mono text-[11px] ${
                      isNight ? "text-slate-400" : "text-slate-500"
                    }`}
                  >
                    {cat.label}
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
