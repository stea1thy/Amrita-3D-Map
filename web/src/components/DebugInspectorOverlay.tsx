"use client";

import { useMemo, useState } from "react";
import {
  ArrowDownToDot,
  Bug,
  Check,
  Copy,
  Eye,
  Loader2,
  MapPin,
  PenTool,
  RotateCcw,
  Satellite,
  Trash2,
  X,
} from "lucide-react";
import { localXZToLatLon } from "@/lib/debugPicking";
import { polygonAreaM2XZ, slugifyBuildingId } from "@/lib/satelliteTiles";
import type { BuildingCategory, InspectableFeature } from "@/types/campus";

interface DebugInspectorOverlayProps {
  selected: InspectableFeature | null;
  origin: [number, number];
  overtureRelease?: string;
  unmatchedPoiCount: number;
  isNight: boolean;
  satelliteEnabled: boolean;
  satelliteOpacity: number;
  satelliteStatus: "idle" | "loading" | "ready" | "error";
  ghostBuildings: boolean;
  showPois: boolean;
  traceMode: boolean;
  tracedPoints: Array<[number, number, number]>;
  onCloseFeature: () => void;
  onToggleSatellite: () => void;
  onSatelliteOpacityChange: (opacity: number) => void;
  onToggleGhost: () => void;
  onTopDownView: () => void;
  onTogglePois: () => void;
  onToggleTrace: () => void;
  onUndoTracePoint: () => void;
  onClearTracePoints: () => void;
}

const TRACE_CATEGORIES: BuildingCategory[] = [
  "academic",
  "hostel",
  "food",
  "sports",
  "admin",
  "landmark",
];

async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fallback below
  }
  try {
    const el = document.createElement("textarea");
    el.value = text;
    el.style.position = "fixed";
    el.style.opacity = "0";
    document.body.appendChild(el);
    el.focus();
    el.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}

export default function DebugInspectorOverlay({
  selected,
  origin,
  overtureRelease,
  unmatchedPoiCount,
  isNight,
  satelliteEnabled,
  satelliteOpacity,
  satelliteStatus,
  ghostBuildings,
  showPois,
  traceMode,
  tracedPoints,
  onCloseFeature,
  onToggleSatellite,
  onSatelliteOpacityChange,
  onToggleGhost,
  onTopDownView,
  onTogglePois,
  onToggleTrace,
  onUndoTracePoint,
  onClearTracePoints,
}: DebugInspectorOverlayProps) {
  const [copiedAction, setCopiedAction] = useState<
    "override" | "exclude" | "trace" | null
  >(null);

  const [traceName, setTraceName] = useState("Academic Block 4 (AB-4)");
  const [traceSubtitle, setTraceSubtitle] = useState("");
  const [traceCategory, setTraceCategory] =
    useState<BuildingCategory>("academic");
  const [traceFloors, setTraceFloors] = useState(3);
  const [traceTagsText, setTraceTagsText] = useState("AB4, AB-4");

  const handleCopy = async (
    kind: "override" | "exclude" | "trace",
    text: string,
  ) => {
    const ok = await copyText(text);
    if (ok) {
      setCopiedAction(kind);
      window.setTimeout(() => {
        setCopiedAction((prev) => (prev === kind ? null : prev));
      }, 1800);
    }
  };

  const buildOverrideSnippet = (feat: InspectableFeature) => {
    const entry = {
      name: feat.rawTags?.name || feat.name,
      category: feat.category,
      floors: Math.max(1, feat.floors || 1),
      tags: feat.tags.filter((t) => t !== feat.category),
    };
    return `"${feat.id}": ${JSON.stringify(entry, null, 2)}`;
  };

  const tracedXZ = useMemo(
    () => tracedPoints.map(([x, , z]): [number, number] => [x, z]),
    [tracedPoints],
  );

  const areaM2 = useMemo(
    () => Math.round(polygonAreaM2XZ(tracedXZ)),
    [tracedXZ],
  );

  const tracedSnippet = useMemo(() => {
    if (tracedPoints.length < 3) {
      return "";
    }
    const ring = tracedPoints.map(([x, , z]) =>
      localXZToLatLon(x, z, origin),
    );
    ring.push(ring[0]);
    const cleanName = traceName.trim() || "New Campus Building";
    const floors = Math.min(10, Math.max(1, Math.round(traceFloors || 1)));
    const parsedTags = traceTagsText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const payload: Record<string, unknown> = {
      id: slugifyBuildingId(cleanName),
      name: cleanName,
      category: traceCategory,
      floors,
      height_m: Number((floors * 3.6).toFixed(1)),
      tags: parsedTags,
      departments: [],
      footprint: ring,
    };
    if (traceSubtitle.trim()) {
      payload.subtitle = traceSubtitle.trim();
    }
    return JSON.stringify(payload, null, 2);
  }, [
    tracedPoints,
    origin,
    traceName,
    traceSubtitle,
    traceCategory,
    traceFloors,
    traceTagsText,
  ]);

  const rawEntries = selected
    ? Object.entries(selected.rawTags ?? {}).sort(([a], [b]) =>
        a.localeCompare(b),
      )
    : [];

  const toolBtnBase =
    "inline-flex h-7 items-center gap-1 rounded-lg border px-2 text-[11px] font-medium transition-colors";
  const toolInactive = isNight
    ? "border-slate-300/15 bg-slate-900/85 text-slate-200 hover:bg-slate-800"
    : "border-slate-900/12 bg-[#FAFBF9]/92 text-slate-700 hover:bg-white";
  const toolActive =
    "border-[#1D5C63] bg-[#1D5C63] text-white shadow-sm";

  return (
    <aside
      aria-label="Cartography debug inspector"
      className="fixed top-[9.25rem] right-3 z-30 flex flex-col items-end gap-2 sm:top-16"
    >
      <div
        className={`inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1 text-[11px] font-medium shadow-sm backdrop-blur-md ${
          isNight
            ? "border-amber-400/30 bg-slate-900/90 text-amber-200"
            : "border-amber-700/25 bg-amber-50/92 text-amber-950"
        }`}
      >
        <Bug className="h-3.5 w-3.5 text-amber-600" />
        <span className="font-mono">
          Cartography Inspector · ?debug=1
          {overtureRelease ? ` · Overture ${overtureRelease}` : ""}
        </span>
      </div>

      {/* Cartography Tools Toolbar */}
      <div
        className={`flex max-w-[min(356px,calc(100vw-1.5rem))] flex-col gap-1.5 rounded-2xl border p-2 shadow-sm backdrop-blur-md ${
          isNight
            ? "border-slate-300/18 bg-slate-950/90 text-slate-100"
            : "border-slate-900/12 bg-[#FAFBF9]/94 text-slate-800"
        }`}
      >
        <div className="flex flex-wrap items-center gap-1">
          <button
            type="button"
            aria-pressed={satelliteEnabled}
            onClick={onToggleSatellite}
            className={`${toolBtnBase} ${satelliteEnabled ? toolActive : toolInactive}`}
          >
            {satelliteStatus === "loading" ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Satellite className="h-3 w-3" />
            )}
            <span>Satellite</span>
          </button>

          <button
            type="button"
            aria-pressed={ghostBuildings}
            onClick={onToggleGhost}
            className={`${toolBtnBase} ${ghostBuildings ? toolActive : toolInactive}`}
          >
            <Eye className="h-3 w-3" />
            <span>Ghost 3D</span>
          </button>

          <button
            type="button"
            onClick={onTopDownView}
            className={`${toolBtnBase} ${toolInactive}`}
          >
            <ArrowDownToDot className="h-3 w-3" />
            <span>Top-Down</span>
          </button>

          {unmatchedPoiCount > 0 && (
            <button
              type="button"
              aria-pressed={showPois}
              onClick={onTogglePois}
              className={`${toolBtnBase} ${showPois ? toolActive : toolInactive}`}
            >
              <MapPin className="h-3 w-3" />
              <span>POIs ({unmatchedPoiCount})</span>
            </button>
          )}

          <button
            type="button"
            aria-pressed={traceMode}
            onClick={onToggleTrace}
            className={`${toolBtnBase} ${
              traceMode
                ? "border-cyan-600 bg-cyan-600 text-white shadow-sm"
                : toolInactive
            }`}
          >
            <PenTool className="h-3 w-3" />
            <span>Trace Footprint</span>
          </button>
        </div>

        {satelliteEnabled && (
          <div className="flex items-center justify-between gap-2 px-1 pt-0.5 text-[11px]">
            <span className="font-mono opacity-75">
              {satelliteStatus === "error"
                ? "Tile load failed"
                : satelliteStatus === "loading"
                  ? "Loading Esri tiles…"
                  : `Sat Opacity (${Math.round(satelliteOpacity * 100)}%)`}
            </span>
            <input
              type="range"
              min={25}
              max={100}
              step={5}
              value={Math.round(satelliteOpacity * 100)}
              aria-label="Satellite overlay opacity"
              onChange={(e) =>
                onSatelliteOpacityChange(Number(e.target.value) / 100)
              }
              className="h-1.5 w-32 accent-[#1D5C63]"
            />
          </div>
        )}
      </div>

      {traceMode ? (
        <div
          className={`animate-panel-in max-h-[calc(100dvh-14.5rem)] w-[min(356px,calc(100vw-1.5rem))] overflow-y-auto rounded-2xl border p-3.5 shadow-[0_16px_40px_-10px_rgba(15,23,42,0.34)] backdrop-blur-md ${
            isNight
              ? "border-cyan-400/25 bg-slate-950/92 text-slate-100"
              : "border-slate-900/15 bg-[#FAFBF9]/95 text-slate-900"
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="rounded bg-cyan-500/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase text-cyan-700 dark:text-cyan-300">
                  Polygon Tracer
                </span>
                <span className="font-mono text-[11px] opacity-80">
                  {tracedPoints.length} pts
                  {areaM2 > 0 ? ` · ${areaM2.toLocaleString()} m²` : ""}
                </span>
              </div>
              <p
                className={`mt-1 text-[11px] leading-snug ${
                  isNight ? "text-slate-300" : "text-slate-600"
                }`}
              >
                Click roof corners on the satellite map; drag to pan/zoom.
              </p>
            </div>
            <button
              type="button"
              aria-label="Exit footprint tracer"
              onClick={onToggleTrace}
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${
                isNight
                  ? "border-slate-300/15 bg-slate-800 text-slate-300 hover:text-white"
                  : "border-slate-900/10 bg-white text-slate-600 hover:text-slate-950"
              }`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs">
            <label className="col-span-2 flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase opacity-70">
                Building Name
              </span>
              <input
                type="text"
                value={traceName}
                onChange={(e) => setTraceName(e.target.value)}
                className={`h-8 rounded-lg border px-2 text-xs focus:outline-none ${
                  isNight
                    ? "border-slate-300/15 bg-slate-900 text-slate-100"
                    : "border-slate-900/12 bg-white text-slate-900"
                }`}
              />
            </label>

            <label className="col-span-2 flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase opacity-70">
                Subtitle (optional)
              </span>
              <input
                type="text"
                value={traceSubtitle}
                placeholder="e.g. School of Computing"
                onChange={(e) => setTraceSubtitle(e.target.value)}
                className={`h-8 rounded-lg border px-2 text-xs focus:outline-none ${
                  isNight
                    ? "border-slate-300/15 bg-slate-900 text-slate-100"
                    : "border-slate-900/12 bg-white text-slate-900"
                }`}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase opacity-70">
                Category
              </span>
              <select
                value={traceCategory}
                onChange={(e) =>
                  setTraceCategory(e.target.value as BuildingCategory)
                }
                className={`h-8 rounded-lg border px-2 text-xs focus:outline-none ${
                  isNight
                    ? "border-slate-300/15 bg-slate-900 text-slate-100"
                    : "border-slate-900/12 bg-white text-slate-900"
                }`}
              >
                {TRACE_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase opacity-70">
                Floors
              </span>
              <input
                type="number"
                min={1}
                max={10}
                value={traceFloors}
                onChange={(e) => setTraceFloors(Number(e.target.value))}
                className={`h-8 rounded-lg border px-2 text-xs focus:outline-none ${
                  isNight
                    ? "border-slate-300/15 bg-slate-900 text-slate-100"
                    : "border-slate-900/12 bg-white text-slate-900"
                }`}
              />
            </label>

            <label className="col-span-2 flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase opacity-70">
                Tags (comma-separated)
              </span>
              <input
                type="text"
                value={traceTagsText}
                onChange={(e) => setTraceTagsText(e.target.value)}
                className={`h-8 rounded-lg border px-2 text-xs focus:outline-none ${
                  isNight
                    ? "border-slate-300/15 bg-slate-900 text-slate-100"
                    : "border-slate-900/12 bg-white text-slate-900"
                }`}
              />
            </label>
          </div>

          <div className="mt-3 flex items-center gap-1.5">
            <button
              type="button"
              disabled={tracedPoints.length === 0}
              onClick={onUndoTracePoint}
              className={`inline-flex h-8 flex-1 items-center justify-center gap-1 rounded-lg border px-2.5 text-xs font-medium disabled:opacity-40 ${
                isNight
                  ? "border-slate-300/15 bg-slate-900 text-slate-200 hover:bg-slate-800"
                  : "border-slate-900/12 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Undo</span>
            </button>
            <button
              type="button"
              disabled={tracedPoints.length === 0}
              onClick={onClearTracePoints}
              className={`inline-flex h-8 flex-1 items-center justify-center gap-1 rounded-lg border px-2.5 text-xs font-medium disabled:opacity-40 ${
                isNight
                  ? "border-slate-300/15 bg-slate-900 text-slate-200 hover:bg-slate-800"
                  : "border-slate-900/12 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Clear</span>
            </button>
          </div>

          <button
            type="button"
            disabled={tracedPoints.length < 3}
            onClick={() => handleCopy("trace", tracedSnippet)}
            className="mt-2 inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-lg bg-[#1D5C63] px-3 text-xs font-medium text-white transition-colors hover:bg-[#174B51] disabled:cursor-not-allowed disabled:opacity-45"
          >
            {copiedAction === "trace" ? (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>Copied custom_buildings JSON!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy custom_buildings JSON</span>
              </>
            )}
          </button>
        </div>
      ) : selected ? (
        <div
          className={`animate-panel-in max-h-[calc(100dvh-14.5rem)] w-[min(356px,calc(100vw-1.5rem))] overflow-y-auto rounded-2xl border p-3.5 shadow-[0_16px_40px_-10px_rgba(15,23,42,0.34)] backdrop-blur-md ${
            isNight
              ? "border-slate-300/20 bg-slate-950/92 text-slate-100"
              : "border-slate-900/15 bg-[#FAFBF9]/95 text-slate-900"
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded bg-amber-500/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase text-amber-700 dark:text-amber-300">
                  {selected.kind}
                </span>
                {selected.source && (
                  <span className="rounded bg-teal-500/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase text-teal-700 dark:text-teal-300">
                    {selected.source}
                  </span>
                )}
                <span className="font-mono text-xs font-semibold text-[#1D5C63] dark:text-teal-300">
                  {selected.id}
                </span>
              </div>
              <h3 className="mt-1 truncate text-sm font-semibold">
                {selected.name}
              </h3>
              <p
                className={`truncate font-mono text-[11px] ${
                  isNight ? "text-slate-400" : "text-slate-500"
                }`}
              >
                mesh: {selected.meshName}
              </p>
            </div>

            <button
              type="button"
              aria-label="Close inspector details"
              onClick={onCloseFeature}
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${
                isNight
                  ? "border-slate-300/15 bg-slate-800 text-slate-300 hover:text-white"
                  : "border-slate-900/10 bg-white text-slate-600 hover:text-slate-950"
              }`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          <div
            className={`mt-2.5 grid grid-cols-2 gap-1.5 rounded-xl border p-2 font-mono text-[11px] ${
              isNight
                ? "border-slate-300/12 bg-slate-900/75"
                : "border-slate-900/10 bg-white/80"
            }`}
          >
            <div>
              <span className="opacity-60">floors: </span>
              <span className="font-semibold">{selected.floors}</span>
              <span className="opacity-60"> ({selected.heightM}m)</span>
            </div>
            <div>
              <span className="opacity-60">cat: </span>
              <span className="font-semibold">{selected.category}</span>
            </div>
            <div className="col-span-2">
              <span className="opacity-60">centroid: </span>
              <span>
                [{selected.latLon[0].toFixed(6)},{" "}
                {selected.latLon[1].toFixed(6)}]
              </span>
            </div>
          </div>

          {selected.places && selected.places.length > 0 && (
            <div className="mt-2.5">
              <div
                className={`mb-1 font-mono text-[10px] font-semibold uppercase tracking-wide ${
                  isNight ? "text-slate-400" : "text-slate-500"
                }`}
              >
                Snapped Overture Places
              </div>
              <div className="flex flex-wrap gap-1">
                {selected.places.map((pl) => (
                  <span
                    key={`${pl.name}-${pl.category}`}
                    className={`rounded-md border px-1.5 py-0.5 text-[11px] ${
                      isNight
                        ? "border-slate-300/15 bg-slate-900 text-slate-200"
                        : "border-slate-900/10 bg-white text-slate-800"
                    }`}
                  >
                    {pl.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="mt-2.5">
            <div
              className={`mb-1 font-mono text-[10px] font-semibold uppercase tracking-wide ${
                isNight ? "text-slate-400" : "text-slate-500"
              }`}
            >
              Source Tags
            </div>
            <div
              className={`space-y-1 rounded-xl border p-2 font-mono text-[11px] ${
                isNight
                  ? "border-slate-300/12 bg-slate-900/75"
                  : "border-slate-900/10 bg-white/80"
              }`}
            >
              {(["name", "building", "building:levels", "layer"] as const).map(
                (key) => (
                  <div key={key} className="flex justify-between gap-2">
                    <span className="shrink-0 opacity-60">{key}</span>
                    <span className="truncate text-right font-medium">
                      {selected.rawTags?.[key] ?? "(none)"}
                    </span>
                  </div>
                ),
              )}
              {rawEntries
                .filter(
                  ([k]) =>
                    k !== "name" &&
                    k !== "building" &&
                    k !== "building:levels" &&
                    k !== "layer",
                )
                .map(([key, val]) => (
                  <div
                    key={key}
                    className="flex justify-between gap-2 border-t border-current/10 pt-1"
                  >
                    <span className="shrink-0 opacity-60">{key}</span>
                    <span className="truncate text-right">{val}</span>
                  </div>
                ))}
            </div>
          </div>

          <div className="mt-3 grid grid-cols-1 gap-1.5">
            <button
              type="button"
              onClick={() =>
                handleCopy("override", buildOverrideSnippet(selected))
              }
              className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg bg-[#1D5C63] px-3 text-xs font-medium text-white transition-colors hover:bg-[#174B51]"
            >
              {copiedAction === "override" ? (
                <>
                  <Check className="h-3.5 w-3.5" />
                  <span>Copied Override JSON!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy Override Snippet</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => handleCopy("exclude", `"${selected.id}"`)}
              className={`inline-flex h-8 items-center justify-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors ${
                isNight
                  ? "border-red-400/30 bg-red-500/15 text-red-200 hover:bg-red-500/25"
                  : "border-red-700/25 bg-red-500/10 text-red-800 hover:bg-red-500/18"
              }`}
            >
              {copiedAction === "exclude" ? (
                <>
                  <Check className="h-3.5 w-3.5" />
                  <span>Copied Exclude ID!</span>
                </>
              ) : (
                <>
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Copy Exclude ID</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div
          className={`rounded-xl border px-2.5 py-1.5 text-[11px] shadow-sm backdrop-blur-md ${
            isNight
              ? "border-slate-300/15 bg-slate-900/82 text-slate-300"
              : "border-slate-900/10 bg-[#FAFBF9]/86 text-slate-600"
          }`}
        >
          Hover/click any building to inspect ID &amp; tags, or enable Satellite +
          Trace Footprint.
        </div>
      )}
    </aside>
  );
}
