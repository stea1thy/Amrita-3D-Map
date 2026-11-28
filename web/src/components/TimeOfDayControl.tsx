"use client";

import { Moon, Sun, Sunrise, Sunset } from "lucide-react";
import {
  TIME_PRESETS,
  formatIstMinutes,
  type SolarLightingState,
  type TimePreset,
} from "@/lib/solar";

interface TimeOfDayControlProps {
  preset: TimePreset;
  minutesIst: number;
  lighting: SolarLightingState;
  fogEnabled: boolean;
  shadowsEnabled?: boolean;
  hideOnMobile: boolean;
  onSelectPreset: (preset: Exclude<TimePreset, "custom">) => void;
  onChangeMinutes: (minutes: number) => void;
  onToggleFog: (enabled: boolean) => void;
  onToggleShadows?: (enabled: boolean) => void;
}

export default function TimeOfDayControl({
  preset,
  minutesIst,
  lighting,
  fogEnabled,
  shadowsEnabled = false,
  hideOnMobile,
  onSelectPreset,
  onChangeMinutes,
  onToggleFog,
  onToggleShadows,
}: TimeOfDayControlProps) {
  const { isNight, altitudeDeg } = lighting;

  const renderSolarIcon = () => {
    if (isNight) {
      return <Moon className="h-3.5 w-3.5 text-amber-300" />;
    }
    if (altitudeDeg < 15 && minutesIst < 720) {
      return <Sunrise className="h-3.5 w-3.5 text-amber-600" />;
    }
    if (altitudeDeg < 15 && minutesIst >= 720) {
      return <Sunset className="h-3.5 w-3.5 text-orange-600" />;
    }
    return <Sun className="h-3.5 w-3.5 text-amber-500" />;
  };

  return (
    <section
      aria-label="Lighting and atmosphere controls"
      className={`fixed bottom-3 left-3 z-20 max-w-[calc(100vw-1.5rem)] rounded-2xl border px-3 py-2 shadow-[0_10px_28px_-8px_rgba(15,23,42,0.22)] backdrop-blur-md ${
        hideOnMobile ? "hidden md:block" : "block"
      } ${
        isNight
          ? "border-slate-300/15 bg-slate-900/86 text-slate-100"
          : "border-slate-900/12 bg-[#FAFBF9]/90 text-slate-900"
      }`}
    >
      <div className="flex flex-wrap items-center gap-1">
        {TIME_PRESETS.map((item) => {
          const active = preset === item.id;
          return (
            <button
              key={item.id}
              type="button"
              aria-pressed={active}
              onClick={() => onSelectPreset(item.id)}
              className={`rounded-lg px-2 py-1 text-[11px] font-medium transition-all duration-150 active:scale-[0.97] ${
                active
                  ? "bg-[#1D5C63] text-white shadow-sm"
                  : isNight
                    ? "text-slate-300 hover:bg-slate-800 hover:text-white"
                    : "text-slate-700 hover:bg-slate-900/6 hover:text-slate-950"
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      <div className="mt-1.5 flex items-center gap-2.5">
        <div className="flex shrink-0 items-center gap-1.5 font-mono text-[11px] tabular-nums">
          {renderSolarIcon()}
          <span>{formatIstMinutes(minutesIst)}</span>
        </div>

        <input
          type="range"
          min={0}
          max={1435}
          step={5}
          value={minutesIst}
          aria-label="Time of day in IST"
          onChange={(e) => onChangeMinutes(Number(e.target.value))}
          className="h-1.5 w-28 cursor-pointer accent-[#1D5C63] sm:w-36"
        />

        <label
          className={`flex shrink-0 cursor-pointer items-center gap-1.5 border-l pl-2.5 text-[11px] font-medium select-none ${
            isNight
              ? "border-slate-300/15 text-slate-200"
              : "border-slate-900/12 text-slate-700"
          }`}
        >
          <input
            type="checkbox"
            checked={fogEnabled}
            onChange={(e) => onToggleFog(e.target.checked)}
            className="h-3.5 w-3.5 cursor-pointer rounded accent-[#1D5C63]"
          />
          <span>Fog</span>
        </label>

        {onToggleShadows && (
          <label
            className={`flex shrink-0 cursor-pointer items-center gap-1.5 border-l pl-2.5 text-[11px] font-medium select-none ${
              isNight
                ? "border-slate-300/15 text-slate-200"
                : "border-slate-900/12 text-slate-700"
            }`}
          >
            <input
              type="checkbox"
              checked={shadowsEnabled}
              onChange={(e) => onToggleShadows(e.target.checked)}
              className="h-3.5 w-3.5 cursor-pointer rounded accent-[#1D5C63]"
            />
            <span>Shadows</span>
          </label>
        )}
      </div>
    </section>
  );
}
