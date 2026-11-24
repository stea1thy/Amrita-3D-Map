"use client";

interface LoadingOverlayProps {
  progress: number;
  ready: boolean;
  isNight?: boolean;
}

export default function LoadingOverlay({
  progress,
  ready,
  isNight = false,
}: LoadingOverlayProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress)));

  return (
    <div
      aria-live="polite"
      aria-hidden={ready}
      className={`fixed inset-0 z-30 flex items-center justify-center backdrop-blur-sm transition-opacity duration-300 ${
        isNight ? "bg-[#0D1B2A]/75" : "bg-[#DCE7F0]/75"
      } ${ready ? "pointer-events-none opacity-0" : "opacity-100"}`}
    >
      <div
        className={`w-[270px] rounded-2xl border px-5 py-4 shadow-[0_14px_34px_-10px_rgba(15,23,42,0.24)] backdrop-blur-md ${
          isNight
            ? "border-slate-300/15 bg-slate-900/90 text-slate-100"
            : "border-slate-900/10 bg-[#FAFBF9]/92 text-slate-900"
        }`}
      >
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm font-semibold tracking-tight">
            Amrita Campus 3D
          </span>
          <span
            className={`font-mono text-xs font-medium tabular-nums ${
              isNight ? "text-teal-300" : "text-[#1D5C63]"
            }`}
          >
            {pct}%
          </span>
        </div>
        <p
          className={`mt-1 text-xs ${
            isNight ? "text-slate-300" : "text-slate-600"
          }`}
        >
          Loading campus terrain and buildings
        </p>
        <div
          className={`mt-3 h-1.5 w-full overflow-hidden rounded-full ${
            isNight ? "bg-slate-700" : "bg-slate-900/10"
          }`}
        >
          <div
            className="h-full origin-left rounded-full bg-[#1D5C63] transition-transform duration-150 ease-out"
            style={{ transform: `scaleX(${Math.max(0.06, pct / 100)})` }}
          />
        </div>
      </div>
    </div>
  );
}
