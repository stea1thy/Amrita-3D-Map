"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Navigation, Search, X } from "lucide-react";
import { searchBuildings } from "@/lib/search";
import {
  CATEGORY_META,
  FILTER_PILLS,
  type BuildingMeta,
  type FilterCategory,
} from "@/types/campus";

interface SearchBarProps {
  buildings: BuildingMeta[];
  query: string;
  activeCategory: FilterCategory;
  isNight: boolean;
  onQueryChange: (q: string) => void;
  onCategoryChange: (cat: FilterCategory) => void;
  onSelectBuilding: (building: BuildingMeta) => void;
  onOpenDirections: () => void;
}

export default function SearchBar({
  buildings,
  query,
  activeCategory,
  isNight,
  onQueryChange,
  onCategoryChange,
  onSelectBuilding,
  onOpenDirections,
}: SearchBarProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIdx, setHighlightedIdx] = useState(0);

  const results = useMemo(
    () => searchBuildings(buildings, query, activeCategory, 12),
    [buildings, query, activeCategory],
  );

  // Global keyboard shortcut: '/' or Cmd/Ctrl+K focuses search
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
        return;
      }

      if (e.key === "/" && !isTyping) {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Close results dropdown on outside pointer down
  useEffect(() => {
    const onPointerDown = (e: PointerEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const activeIdx =
    results.length === 0 ? -1 : Math.min(highlightedIdx, results.length - 1);

  const commitSelection = (building: BuildingMeta) => {
    onSelectBuilding(building);
    setIsOpen(false);
    inputRef.current?.blur();
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
      }
      if (results.length > 0) {
        setHighlightedIdx((prev) => (prev + 1) % results.length);
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (results.length > 0) {
        setHighlightedIdx((prev) =>
          prev <= 0 ? results.length - 1 : prev - 1,
        );
      }
    } else if (e.key === "Enter" && isOpen && activeIdx >= 0) {
      e.preventDefault();
      commitSelection(results[activeIdx]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div
      ref={containerRef}
      className="fixed top-3 left-3 right-3 z-20 flex flex-col gap-2 sm:right-auto sm:w-[368px]"
    >
      {/* Search input row + Directions trigger */}
      <div className="flex items-center gap-2">
        <div
          className={`relative flex min-w-0 flex-1 items-center rounded-xl border shadow-[0_8px_24px_-8px_rgba(15,23,42,0.18)] backdrop-blur-md transition-[border-color,box-shadow] duration-150 focus-within:border-[#1D5C63]/55 focus-within:ring-2 focus-within:ring-[#1D5C63]/20 ${
            isNight
              ? "border-slate-300/15 bg-slate-900/86"
              : "border-slate-900/12 bg-[#FAFBF9]/88"
          }`}
        >
          <Search
            className={`pointer-events-none ml-3.5 h-4 w-4 shrink-0 ${
              isNight ? "text-slate-400" : "text-slate-500"
            }`}
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            type="search"
            role="combobox"
            value={query}
            aria-label="Search campus buildings"
            aria-autocomplete="list"
            aria-expanded={isOpen}
            aria-controls="campus-search-results"
            aria-activedescendant={
              isOpen && activeIdx >= 0
                ? `campus-result-${results[activeIdx].id}`
                : undefined
            }
            placeholder="Search buildings, blocks, hostels..."
            onFocus={() => setIsOpen(true)}
            onChange={(e) => {
              onQueryChange(e.target.value);
              setHighlightedIdx(0);
              setIsOpen(true);
            }}
            onKeyDown={handleInputKeyDown}
            className={`h-11 w-full bg-transparent px-3 text-sm focus:outline-none [&::-webkit-search-cancel-button]:hidden ${
              isNight
                ? "text-slate-100 placeholder:text-slate-400"
                : "text-slate-900 placeholder:text-slate-500"
            }`}
          />
          {query ? (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => {
                onQueryChange("");
                setHighlightedIdx(0);
                inputRef.current?.focus();
              }}
              className={`mr-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition-colors focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
                isNight
                  ? "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                  : "text-slate-500 hover:bg-slate-900/8 hover:text-slate-800"
              }`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          ) : (
            <kbd
              className={`mr-2.5 hidden shrink-0 rounded-md border px-1.5 py-0.5 font-mono text-[10px] font-medium sm:inline-block ${
                isNight
                  ? "border-slate-300/15 bg-slate-800 text-slate-300"
                  : "border-slate-900/12 bg-slate-900/5 text-slate-600"
              }`}
            >
              Ctrl K
            </kbd>
          )}
        </div>

        <button
          type="button"
          aria-label="Open walking directions"
          onClick={() => {
            setIsOpen(false);
            onOpenDirections();
          }}
          className={`inline-flex h-11 shrink-0 items-center gap-1.5 rounded-xl border px-3 text-xs font-medium shadow-[0_8px_24px_-8px_rgba(15,23,42,0.18)] backdrop-blur-md transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
            isNight
              ? "border-slate-300/15 bg-slate-900/86 text-slate-100 hover:bg-slate-800 hover:text-teal-300"
              : "border-slate-900/12 bg-[#FAFBF9]/88 text-slate-800 hover:bg-white hover:text-[#1D5C63]"
          }`}
        >
          <Navigation
            className={`h-3.5 w-3.5 ${isNight ? "text-teal-300" : "text-[#1D5C63]"}`}
          />
          <span className="hidden sm:inline">Directions</span>
        </button>
      </div>

      {/* Category filter pills */}
      <div
        role="group"
        aria-label="Filter buildings by category"
        className="scrollbar-none flex items-center gap-1.5 overflow-x-auto pb-0.5"
      >
        {FILTER_PILLS.map((pill) => {
          const active = activeCategory === pill.value;
          return (
            <button
              key={pill.value}
              type="button"
              aria-pressed={active}
              onClick={() => {
                onCategoryChange(pill.value);
                setHighlightedIdx(0);
              }}
              className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-[#1D5C63] ${
                active
                  ? "border-[#1D5C63] bg-[#1D5C63] text-white shadow-sm"
                  : isNight
                    ? "border-slate-300/15 bg-slate-900/80 text-slate-200 backdrop-blur-md hover:bg-slate-800"
                    : "border-slate-900/12 bg-[#FAFBF9]/85 text-slate-700 backdrop-blur-md hover:bg-white"
              }`}
            >
              {pill.label}
            </button>
          );
        })}
      </div>

      {/* Results dropdown */}
      {isOpen && (
        <div
          id="campus-search-results"
          role="listbox"
          aria-label="Building search results"
          className={`animate-panel-in max-h-[min(340px,52vh)] overflow-y-auto rounded-xl border p-1.5 shadow-[0_14px_34px_-10px_rgba(15,23,42,0.24)] backdrop-blur-md ${
            isNight
              ? "border-slate-300/15 bg-slate-900/94"
              : "border-slate-900/12 bg-[#FAFBF9]/94"
          }`}
        >
          {results.length === 0 ? (
            <div
              className={`px-3 py-5 text-center text-xs ${
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
                  id={`campus-result-${b.id}`}
                  type="button"
                  role="option"
                  aria-selected={isHighlighted}
                  onMouseEnter={() => setHighlightedIdx(idx)}
                  onClick={() => commitSelection(b)}
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
                  <div
                    className={`flex shrink-0 items-center gap-1.5 font-mono text-[11px] ${
                      isNight ? "text-slate-400" : "text-slate-500"
                    }`}
                  >
                    <span>{cat.label}</span>
                    <span aria-hidden="true">·</span>
                    <span>{b.floors}F</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
