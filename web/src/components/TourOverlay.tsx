"use client";

import { useEffect } from "react";
import { ChevronLeft, ChevronRight, Compass, X } from "lucide-react";
import type { TourStop } from "@/data/tourStops";

interface TourOverlayProps {
  stops: TourStop[];
  currentIndex: number;
  isNight: boolean;
  onSelectIndex: (index: number) => void;
  onExit: () => void;
}

export default function TourOverlay({
  stops,
  currentIndex,
  isNight,
  onSelectIndex,
  onExit,
}: TourOverlayProps) {
  const stop = stops[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === stops.length - 1;

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable
      ) {
        return;
      }
      if (e.key === "ArrowRight" && !isLast) {
        e.preventDefault();
        onSelectIndex(currentIndex + 1);
      } else if (e.key === "ArrowLeft" && !isFirst) {
        e.preventDefault();
        onSelectIndex(currentIndex - 1);
      } else if (e.key === "Escape") {
        e.preventDefault();
        onExit();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentIndex, isFirst, isLast, onSelectIndex, onExit]);

  if (!stop) {
    return null;
  }

  return (
    <aside
      aria-label="Fresher Orientation Tour"
      className={`animate-panel-in fixed bottom-3 left-3 right-3 z-20 rounded-2xl border p-4 shadow-[0_16px_42px_-12px_rgba(15,23,42,0.3)] backdrop-blur-md md:bottom-4 md:left-1/2 md:right-auto md:w-[448px] md:-translate-x-1/2 ${
        isNight
          ? "border-slate-300/15 bg-slate-900/88 text-slate-100"
          : "border-slate-900/12 bg-[#FAFBF9]/92 text-slate-900"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${
              isNight
                ? "border-teal-400/30 bg-teal-400/15 text-teal-200"
                : "border-[#1D5C63]/25 bg-[#1D5C63]/10 text-[#1D5C63]"
            }`}
          >
            <Compass className="h-3 w-3" />
            <span>
              Stop {currentIndex + 1} of {stops.length}
            </span>
          </span>

          <div className="flex items-center gap-1" role="tablist" aria-label="Tour stops">
            {stops.map((s, idx) => {
              const active = idx === currentIndex;
              return (
                <button
                  key={s.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  aria-label={`Go to stop ${idx + 1}: ${s.title}`}
                  onClick={() => onSelectIndex(idx)}
                  className={`h-2 rounded-full transition-all duration-150 ${
                    active
                      ? isNight
                        ? "w-5 bg-teal-300"
                        : "w-5 bg-[#1D5C63]"
                      : isNight
                        ? "w-2 bg-slate-600 hover:bg-slate-400"
                        : "w-2 bg-slate-300 hover:bg-slate-400"
                  }`}
                />
              );
            })}
          </div>
        </div>

        <button
          type="button"
          aria-label="Exit orientation tour"
          onClick={onExit}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
            isNight
              ? "border-slate-300/15 bg-slate-800/80 text-slate-300 hover:bg-slate-700 hover:text-white"
              : "border-slate-900/10 bg-white/75 text-slate-600 hover:bg-white hover:text-slate-950"
          }`}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <h2 className="mt-2.5 text-base font-semibold leading-snug">
        {stop.title}
      </h2>
      <p
        className={`text-xs font-medium ${
          isNight ? "text-teal-300/90" : "text-[#1D5C63]"
        }`}
      >
        {stop.subtitle}
      </p>
      <p
        className={`mt-2 text-xs leading-relaxed ${
          isNight ? "text-slate-300" : "text-slate-700"
        }`}
      >
        {stop.narration}
      </p>

      <div
        className={`mt-3.5 flex items-center justify-between gap-2 border-t pt-3 ${
          isNight ? "border-slate-300/10" : "border-slate-900/8"
        }`}
      >
        <button
          type="button"
          disabled={isFirst}
          onClick={() => onSelectIndex(currentIndex - 1)}
          className={`inline-flex h-9 items-center gap-1 rounded-xl border px-3 text-xs font-medium transition-all duration-150 active:scale-[0.97] disabled:pointer-events-none disabled:opacity-40 ${
            isNight
              ? "border-slate-300/15 bg-slate-800/80 text-slate-200 hover:bg-slate-700"
              : "border-slate-900/12 bg-white/80 text-slate-800 hover:bg-white"
          }`}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          <span>Previous</span>
        </button>

        <button
          type="button"
          onClick={() => (isLast ? onExit() : onSelectIndex(currentIndex + 1))}
          className="inline-flex h-9 items-center gap-1 rounded-xl bg-[#1D5C63] px-3.5 text-xs font-medium text-white transition-all duration-150 hover:bg-[#174B51] active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63]"
        >
          <span>{isLast ? "Finish tour" : "Next stop"}</span>
          {!isLast && <ChevronRight className="h-3.5 w-3.5" />}
        </button>
      </div>
    </aside>
  );
}
