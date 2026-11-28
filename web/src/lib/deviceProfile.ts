"use client";

import { useSyncExternalStore } from "react";

/** Render settings. Touch devices get a lighter profile so the map stays usable on phones. */
export interface RenderProfile {
  dpr: [number, number];
  shadowMapSize: number;
  simpleTrees: boolean;
}

const DESKTOP: RenderProfile = { dpr: [1, 1], shadowMapSize: 1024, simpleTrees: true };
const HANDHELD: RenderProfile = { dpr: [1, 1], shadowMapSize: 512, simpleTrees: true };
const HANDHELD_QUERY = "(pointer: coarse)";

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(HANDHELD_QUERY);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

export function useRenderProfile(): RenderProfile {
  const handheld = useSyncExternalStore(
    subscribe,
    () => window.matchMedia(HANDHELD_QUERY).matches,
    () => false,
  );
  return handheld ? HANDHELD : DESKTOP;
}
