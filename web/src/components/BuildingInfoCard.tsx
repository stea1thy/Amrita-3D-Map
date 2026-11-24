"use client";

import { Building2, Crosshair, Layers, Navigation, X } from "lucide-react";
import { CATEGORY_META, type BuildingMeta } from "@/types/campus";

interface BuildingInfoCardProps {
  building: BuildingMeta;
  isNight: boolean;
  onClose: () => void;
  onFocus: () => void;
  onRouteHere: () => void;
}

export default function BuildingInfoCard({
  building,
  isNight,
  onClose,
  onFocus,
  onRouteHere,
}: BuildingInfoCardProps) {
  const cat = CATEGORY_META[building.category];
  const visibleTags = building.tags.filter(
    (t) => t.toLowerCase() !== building.category.toLowerCase(),
  );

  return (
    <aside
      aria-label={`Details for ${building.name}`}
      className={`animate-panel-in fixed bottom-3 left-3 right-3 z-20 rounded-2xl border p-4 shadow-[0_14px_38px_-10px_rgba(15,23,42,0.26)] backdrop-blur-md md:bottom-24 md:left-3 md:right-auto md:w-[368px] ${
        isNight
          ? "border-slate-300/15 bg-slate-900/90 text-slate-100"
          : "border-slate-900/12 bg-[#FAFBF9]/92 text-slate-900"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${
              isNight
                ? "border-slate-300/20 bg-slate-800/80 text-slate-200"
                : cat.badgeClass
            }`}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: cat.dotColor }}
            />
            {cat.label}
          </span>
          <h2 className="mt-2 text-base font-semibold leading-snug">
            {building.name}
          </h2>
          {building.subtitle && (
            <p
              className={`mt-0.5 text-xs ${
                isNight ? "text-slate-300" : "text-slate-600"
              }`}
            >
              {building.subtitle}
            </p>
          )}
        </div>

        <button
          type="button"
          aria-label="Close building details"
          onClick={onClose}
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
            isNight
              ? "border-slate-300/15 bg-slate-800/75 text-slate-300 hover:bg-slate-700 hover:text-white"
              : "border-slate-900/10 bg-white/70 text-slate-600 hover:bg-white hover:text-slate-950"
          }`}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div
        className={`mt-3 flex flex-wrap items-center gap-4 border-t pt-3 text-xs ${
          isNight
            ? "border-slate-300/10 text-slate-300"
            : "border-slate-900/8 text-slate-700"
        }`}
      >
        <span className="inline-flex items-center gap-1.5 font-medium">
          <Layers className="h-3.5 w-3.5 opacity-70" />
          <span>
            {building.floors} {building.floors === 1 ? "floor" : "floors"}
          </span>
        </span>
        <span className="inline-flex items-center gap-1.5 font-mono opacity-85">
          <Building2 className="h-3.5 w-3.5 opacity-70" />
          <span>~{Math.round(building.heightM)} m</span>
        </span>
      </div>

      {building.departments.length > 0 && (
        <div
          className={`mt-2.5 text-xs ${
            isNight ? "text-slate-300" : "text-slate-700"
          }`}
        >
          <span className="font-medium">Departments: </span>
          <span>{building.departments.join(", ")}</span>
        </div>
      )}

      {building.places && building.places.length > 0 && (
        <div className="mt-2.5">
          <div
            className={`mb-1 text-[11px] font-medium ${
              isNight ? "text-slate-400" : "text-slate-600"
            }`}
          >
            Places &amp; Facilities
          </div>
          <div className="flex flex-wrap gap-1.5">
            {building.places.map((place) => {
              const pCat = CATEGORY_META[place.category] ?? CATEGORY_META.default;
              return (
                <span
                  key={`${place.name}-${place.category}`}
                  className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] ${
                    isNight
                      ? "border-slate-300/15 bg-slate-800/80 text-slate-200"
                      : "border-slate-900/10 bg-white/80 text-slate-800"
                  }`}
                >
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: pCat.dotColor }}
                  />
                  <span>{place.name}</span>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {visibleTags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {visibleTags.map((tag) => (
            <span
              key={tag}
              className={`rounded-md border px-2 py-0.5 font-mono text-[11px] ${
                isNight
                  ? "border-slate-300/15 bg-slate-800/75 text-slate-300"
                  : "border-slate-900/10 bg-slate-900/[0.04] text-slate-700"
              }`}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div
        className={`mt-3.5 flex items-center justify-between gap-2 border-t pt-3 ${
          isNight ? "border-slate-300/10" : "border-slate-900/8"
        }`}
      >
        <span
          className={`min-w-0 truncate font-mono text-[11px] ${
            isNight ? "text-slate-400" : "text-slate-500"
          }`}
        >
          {building.id}
        </span>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={onRouteHere}
            className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-medium transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
              isNight
                ? "border-teal-400/35 bg-teal-400/15 text-teal-200 hover:bg-teal-400/25"
                : "border-[#1D5C63]/30 bg-[#1D5C63]/10 text-[#1D5C63] hover:bg-[#1D5C63]/18"
            }`}
          >
            <Navigation className="h-3.5 w-3.5" />
            <span>Route here</span>
          </button>
          <button
            type="button"
            onClick={onFocus}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-[#1D5C63] px-3 text-xs font-medium text-white transition-all duration-150 hover:bg-[#174B51] active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63]"
          >
            <Crosshair className="h-3.5 w-3.5" />
            <span>Focus view</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
