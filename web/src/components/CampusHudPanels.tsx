"use client";

import { useMemo } from "react";
import { Compass, Info, List, RotateCcw, X } from "lucide-react";
import { CATEGORY_META, type BuildingMeta } from "@/types/campus";

export interface QuickJumpItem {
  id: string;
  label: string;
  buildingId?: string;
  customTarget?: {
    center: [number, number, number];
    offset: [number, number, number];
  };
}

export const QUICK_JUMP_ITEMS: QuickJumpItem[] = [
  { id: "main-gate", label: "Main Gate", buildingId: "hero/main-gate" },
  { id: "ab1", label: "AB-1", buildingId: "way/380925364" },
  { id: "ab2", label: "AB-2", buildingId: "way/380702789" },
  { id: "ab3", label: "AB-3", buildingId: "way/380829415" },
  { id: "hostels", label: "Hostels", buildingId: "way/380925366" },
  {
    id: "sports-ground",
    label: "Sports Ground",
    customTarget: {
      center: [258.6, 4.0, -5.9],
      offset: [135, 118, 155],
    },
  },
];

interface TopRightBarProps {
  listOpen: boolean;
  tourActive: boolean;
  aboutOpen: boolean;
  isNight: boolean;
  onResetView: () => void;
  onToggleList: () => void;
  onToggleTour: () => void;
  onToggleAbout: () => void;
}

export function TopRightBar({
  listOpen,
  tourActive,
  aboutOpen,
  isNight,
  onResetView,
  onToggleList,
  onToggleTour,
  onToggleAbout,
}: TopRightBarProps) {
  const pillBase = `inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63]`;
  const inactiveCls = isNight
    ? "text-slate-200 hover:bg-slate-800 hover:text-white"
    : "text-slate-800 hover:bg-slate-900/6 hover:text-slate-950";
  const activeCls = "bg-[#1D5C63] text-white shadow-sm";

  return (
    <nav
      aria-label="Campus viewer controls"
      className={`fixed top-[6.25rem] right-3 z-20 flex items-center gap-1 rounded-xl border p-1 shadow-[0_8px_24px_-8px_rgba(15,23,42,0.2)] backdrop-blur-md sm:top-3 sm:right-3 ${
        isNight
          ? "border-slate-300/15 bg-slate-900/86"
          : "border-slate-900/12 bg-[#FAFBF9]/90"
      }`}
    >
      <button
        type="button"
        onClick={onResetView}
        className={`${pillBase} ${inactiveCls}`}
      >
        <RotateCcw className="h-3.5 w-3.5 opacity-75" />
        <span>Reset view</span>
      </button>

      <button
        type="button"
        aria-pressed={listOpen}
        onClick={onToggleList}
        className={`${pillBase} ${listOpen ? activeCls : inactiveCls}`}
      >
        <List className="h-3.5 w-3.5 opacity-80" />
        <span>List</span>
      </button>

      <button
        type="button"
        aria-pressed={tourActive}
        onClick={onToggleTour}
        className={`${pillBase} ${tourActive ? activeCls : inactiveCls}`}
      >
        <Compass className="h-3.5 w-3.5 opacity-80" />
        <span>Tour</span>
      </button>

      <button
        type="button"
        aria-pressed={aboutOpen}
        onClick={onToggleAbout}
        className={`${pillBase} ${aboutOpen ? activeCls : inactiveCls}`}
      >
        <Info className="h-3.5 w-3.5 opacity-80" />
        <span>About</span>
      </button>
    </nav>
  );
}

interface CampusListPanelProps {
  buildings: BuildingMeta[];
  selectedId: string | null;
  isNight: boolean;
  onSelect: (building: BuildingMeta) => void;
  onClose: () => void;
}

export function CampusListPanel({
  buildings,
  selectedId,
  isNight,
  onSelect,
  onClose,
}: CampusListPanelProps) {
  const named = useMemo(
    () =>
      buildings
        .filter((b) => b.isNamed)
        .sort((a, b) => a.name.localeCompare(b.name)),
    [buildings],
  );

  return (
    <aside
      aria-label="Campus buildings directory"
      className={`animate-panel-in fixed top-16 right-3 z-20 max-h-[min(420px,62vh)] w-[min(340px,calc(100vw-1.5rem))] overflow-y-auto rounded-2xl border p-3 shadow-[0_16px_38px_-10px_rgba(15,23,42,0.28)] backdrop-blur-md ${
        isNight
          ? "border-slate-300/15 bg-slate-900/92 text-slate-100"
          : "border-slate-900/12 bg-[#FAFBF9]/94 text-slate-900"
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold tracking-tight">
          Named Campus Landmarks ({named.length})
        </span>
        <button
          type="button"
          aria-label="Close building directory"
          onClick={onClose}
          className={`flex h-7 w-7 items-center justify-center rounded-lg border ${
            isNight
              ? "border-slate-300/15 bg-slate-800 text-slate-300 hover:text-white"
              : "border-slate-900/10 bg-white text-slate-600 hover:text-slate-950"
          }`}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="space-y-1">
        {named.map((b) => {
          const cat = CATEGORY_META[b.category];
          const isSelected = b.id === selectedId;
          return (
            <button
              key={b.id}
              type="button"
              onClick={() => onSelect(b)}
              className={`flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors ${
                isSelected
                  ? "bg-[#1D5C63] text-white"
                  : isNight
                    ? "text-slate-200 hover:bg-slate-800"
                    : "text-slate-800 hover:bg-slate-900/5"
              }`}
            >
              <span className="flex min-w-0 items-center gap-2">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: cat.dotColor }}
                />
                <span className="truncate font-medium">{b.name}</span>
              </span>
              <span className="shrink-0 font-mono text-[10px] opacity-75">
                {cat.label} · {b.floors}F
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

interface AboutModalProps {
  buildingCount: number;
  treeCount: number;
  lampCount: number;
  isNight: boolean;
  onClose: () => void;
}

export function AboutModal({
  buildingCount,
  treeCount,
  lampCount,
  isNight,
  onClose,
}: AboutModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="About Amrita 3D Campus Map"
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/35 p-4 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className={`animate-panel-in w-full max-w-md rounded-2xl border p-5 shadow-2xl backdrop-blur-md ${
          isNight
            ? "border-slate-300/15 bg-slate-900/95 text-slate-100"
            : "border-slate-900/12 bg-[#FAFBF9]/96 text-slate-900"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold tracking-tight">
              Amrita Vishwa Vidyapeetham · 3D Campus Map
            </h2>
            <p
              className={`mt-0.5 text-xs ${
                isNight ? "text-slate-400" : "text-slate-500"
              }`}
            >
              Ettimadai Campus, Coimbatore
            </p>
          </div>
          <button
            type="button"
            aria-label="Close about dialog"
            onClick={onClose}
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border ${
              isNight
                ? "border-slate-300/15 bg-slate-800 text-slate-300 hover:text-white"
                : "border-slate-900/10 bg-white text-slate-600 hover:text-slate-950"
            }`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p
          className={`mt-3 text-xs leading-relaxed ${
            isNight ? "text-slate-300" : "text-slate-700"
          }`}
        >
          Interactive 3D architectural maquette of the Ettimadai campus at the
          foothills of the Western Ghats, featuring hill-aware walking routes,
          real IST solar lighting, and curated fresher tour stops.
        </p>

        <div
          className={`mt-3 grid grid-cols-3 gap-2 rounded-xl border p-2.5 text-center font-mono text-[11px] ${
            isNight
              ? "border-slate-300/12 bg-slate-800/70"
              : "border-slate-900/8 bg-white/80"
          }`}
        >
          <div>
            <div className="text-sm font-semibold">{buildingCount}</div>
            <div className="opacity-65">Landmarks</div>
          </div>
          <div>
            <div className="text-sm font-semibold">{treeCount.toLocaleString()}</div>
            <div className="opacity-65">Trees</div>
          </div>
          <div>
            <div className="text-sm font-semibold">{lampCount}</div>
            <div className="opacity-65">Lamps</div>
          </div>
        </div>

        <div
          className={`mt-3 space-y-1 text-[11px] ${
            isNight ? "text-slate-400" : "text-slate-600"
          }`}
        >
          <p>
            <strong>Data:</strong> OpenStreetMap contributors & Open-Meteo Elevation
          </p>
          <p>
            <strong>Shortcuts:</strong> <code>Ctrl+K</code> or <code>/</code> to search,{" "}
            <code>?debug=1</code> for OSM Cartography Inspector
          </p>
        </div>
      </div>
    </div>
  );
}

interface QuickJumpBarProps {
  activeJumpId: string | null;
  isNight: boolean;
  onJump: (item: QuickJumpItem) => void;
}

export function QuickJumpBar({
  activeJumpId,
  isNight,
  onJump,
}: QuickJumpBarProps) {
  return (
    <nav
      aria-label="Quick campus landmarks"
      className={`fixed bottom-3 right-3 z-20 hidden max-w-[calc(100vw-1.5rem)] flex-wrap items-center gap-1 rounded-2xl border p-1 shadow-[0_10px_28px_-8px_rgba(15,23,42,0.22)] backdrop-blur-md md:flex ${
        isNight
          ? "border-slate-300/15 bg-slate-900/86"
          : "border-slate-900/12 bg-[#FAFBF9]/90"
      }`}
    >
      {QUICK_JUMP_ITEMS.map((item) => {
        const active = item.id === activeJumpId;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onJump(item)}
            className={`rounded-xl px-2.5 py-1.5 text-[11px] font-medium transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
              active
                ? "bg-[#1D5C63] text-white shadow-sm"
                : isNight
                  ? "text-slate-200 hover:bg-slate-800 hover:text-white"
                  : "text-slate-700 hover:bg-slate-900/6 hover:text-slate-950"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </nav>
  );
}
