export type BuildingCategory =
  | "academic"
  | "hostel"
  | "food"
  | "sports"
  | "admin"
  | "landmark"
  | "default";

export type FilterCategory = "all" | "academic" | "hostel" | "food" | "sports";

export interface BuildingPlace {
  name: string;
  category: BuildingCategory;
  rawCategory?: string;
}

export interface OverturePoi {
  id: string;
  name: string;
  category: BuildingCategory;
  rawCategory?: string;
  confidence?: number | null;
  latLon: [number, number];
  position: [number, number, number];
}

export interface BuildingMeta {
  id: string;
  meshName: string;
  name: string;
  subtitle?: string;
  source?: "osm" | "overture" | "custom";
  isNamed: boolean;
  category: BuildingCategory;
  tags: string[];
  departments: string[];
  places?: BuildingPlace[];
  floors: number;
  heightM: number;
  center: [number, number, number];
  boundingRadius: number;
  nearestNodeId?: number;
  latLon?: [number, number];
  rawTags?: Record<string, string>;
}

export interface InspectableFeature {
  id: string;
  meshName: string;
  kind: "building" | "bridge" | "mesh";
  name: string;
  subtitle?: string;
  source?: "osm" | "overture" | "custom";
  isNamed: boolean;
  category: BuildingCategory;
  tags: string[];
  departments: string[];
  places?: BuildingPlace[];
  floors: number;
  heightM: number;
  center: [number, number, number];
  boundingRadius: number;
  latLon: [number, number];
  boundsXZ?: [number, number, number, number];
  footprintXZ?: Array<[number, number]>;
  rawTags: Record<string, string>;
}

export type WalkGraphNode = [number, number, number];

// [u, v, distM, timeUtoVS, timeVtoUS]
export type WalkGraphEdge = [number, number, number, number, number];

export interface WalkGraph {
  metadata: {
    nodeCount: number;
    edgeCount: number;
    units: string;
    toblerMaxSpeedMps: number;
    coordinateSpace: string;
  };
  nodes: WalkGraphNode[];
  edges: WalkGraphEdge[];
}

export interface RouteResult {
  fromId: string;
  toId: string;
  nodeIds: number[];
  points: WalkGraphNode[];
  distanceM: number;
  elevationGainM: number;
  elevationLossM: number;
  estimatedSeconds: number;
  estimatedMinutes: number;
  bounds: {
    center: [number, number, number];
    radius: number;
  };
}

// [x, y, z, scale, rotY, type (0=palm, 1=canopy), shade (0..3)]
export type TreePlacement = [number, number, number, number, number, 0 | 1, number];

export interface TreesData {
  count: number;
  format: string;
  types: string[];
  trees: TreePlacement[];
}

// [x, y, z, rotY]
export type StreetlampPlacement = [number, number, number, number];

export interface StreetlampsData {
  count: number;
  format: string;
  lamps: StreetlampPlacement[];
}

export interface TerrainBounds {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  minY: number;
  maxY: number;
}

export interface CampusMeta {
  origin: [number, number];
  bbox: [number, number, number, number];
  elevationDatumM: number;
  overtureRelease?: string;
  terrainBounds: TerrainBounds;
  counts: {
    buildings: number;
    namedBuildings: number;
    trees: number;
    bridges?: number;
    inspectables?: number;
    overtureBuildings?: number;
    overturePlaces?: number;
    unmatchedPois?: number;
  };
  buildings: BuildingMeta[];
  inspectables?: InspectableFeature[];
  overturePois?: OverturePoi[];
}

export const CATEGORY_META: Record<
  BuildingCategory,
  { label: string; dotColor: string; badgeClass: string }
> = {
  academic: {
    label: "Academic",
    dotColor: "#B39B7D",
    badgeClass: "bg-stone-500/12 text-stone-800 border-stone-500/25",
  },
  hostel: {
    label: "Hostel",
    dotColor: "#B58562",
    badgeClass: "bg-orange-900/10 text-orange-950 border-orange-900/20",
  },
  food: {
    label: "Food",
    dotColor: "#C87A32",
    badgeClass: "bg-amber-600/12 text-amber-950 border-amber-700/25",
  },
  sports: {
    label: "Sports",
    dotColor: "#4886A4",
    badgeClass: "bg-sky-700/12 text-sky-950 border-sky-700/25",
  },
  admin: {
    label: "Admin",
    dotColor: "#6B7C93",
    badgeClass: "bg-slate-600/12 text-slate-900 border-slate-600/25",
  },
  landmark: {
    label: "Landmark",
    dotColor: "#A67B35",
    badgeClass: "bg-yellow-700/12 text-yellow-950 border-yellow-700/25",
  },
  default: {
    label: "Campus",
    dotColor: "#858079",
    badgeClass: "bg-zinc-500/12 text-zinc-800 border-zinc-500/25",
  },
};

export const FILTER_PILLS: Array<{ value: FilterCategory; label: string }> = [
  { value: "all", label: "All" },
  { value: "academic", label: "Academic" },
  { value: "hostel", label: "Hostels" },
  { value: "food", label: "Food" },
  { value: "sports", label: "Sports" },
];
