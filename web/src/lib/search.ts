import type { BuildingMeta, FilterCategory } from "@/types/campus";

const STOPWORDS = new Set(["of", "and", "for", "the", "in", "at", "to"]);

const KNOWN_ALIAS_RULES: Array<[RegExp, string[]]> = [
  [/academic block\s*1/i, ["ab1", "ab-1", "soe", "engineering"]],
  [/academic block\s*2/i, ["ab2", "ab-2"]],
  [/academic block\s*3/i, ["ab3", "ab-3", "computing", "cse", "ai", "isl", "law"]],
  [/academic block\s*4/i, ["ab4", "ab-4"]],
  [/school of business/i, ["asb", "mba", "business"]],
  [/corporate and industry relations/i, ["cir", "placement", "placements"]],
  [/central library/i, ["cl", "lib", "library"]],
  [/amriteshwari hall/i, ["hall", "auditorium", "amriteshwari"]],
  [/automative|automotive/i, ["aartc", "automotive", "auto"]],
  [/aroyga|arogya/i, ["arogya", "aroyga", "gym"]],
  [/dhanlaxmi/i, ["bank", "atm", "dlb"]],
  [/agastya|agasthya/i, ["agastya", "agasthya"]],
  [/gautama|gauthama/i, ["gautama", "gauthama"]],
  [/maitheyi|maitreyi/i, ["maitreyi", "maitheyi"]],
  [/yagnavalkya/i, ["yb", "yagnavalkya"]],
  [/nachiketas/i, ["nb", "nachiketas"]],
  [/fabrication/i, ["fab", "workshop"]],
  [/guest house/i, ["gh", "guest"]],
];

export function getBuildingAliases(building: BuildingMeta): string[] {
  const aliases = new Set<string>();
  const lowerName = building.name.toLowerCase();

  for (const [pattern, extras] of KNOWN_ALIAS_RULES) {
    if (pattern.test(lowerName)) {
      for (const alias of extras) {
        aliases.add(alias);
      }
    }
  }

  // Build word-initial acronym (e.g., "Central Kitchen" -> "ck")
  const tokens = lowerName
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 0 && !STOPWORDS.has(t));

  if (tokens.length >= 2) {
    const acronym = tokens.map((t) => (/^\d+$/.test(t) ? t : t[0])).join("");
    if (acronym.length >= 2) {
      aliases.add(acronym);
    }
  }

  for (const tag of building.tags) {
    aliases.add(tag.toLowerCase());
  }
  for (const dept of building.departments) {
    aliases.add(dept.toLowerCase());
  }
  for (const place of building.places ?? []) {
    aliases.add(place.name.toLowerCase());
  }
  if (building.subtitle) {
    aliases.add(building.subtitle.toLowerCase());
  }

  return Array.from(aliases);
}

function fuzzySubsequenceScore(query: string, target: string): number {
  let qi = 0;
  let score = 0;
  let consecutive = 0;

  for (let ti = 0; ti < target.length && qi < query.length; ti++) {
    if (target[ti] === query[qi]) {
      qi++;
      consecutive++;
      const isBoundary = ti === 0 || /[\s\-_/]/.test(target[ti - 1]);
      score += 4 + Math.min(consecutive * 3, 12) + (isBoundary ? 5 : 0);
    } else {
      consecutive = 0;
    }
  }

  if (qi < query.length) {
    return 0;
  }

  const compactnessPenalty = Math.max(0, (target.length - query.length) * 0.2);
  return Math.max(15, Math.min(60, Math.round(score - compactnessPenalty)));
}

function scoreBuilding(building: BuildingMeta, normalizedQuery: string): number {
  const nameLower = building.name.toLowerCase();
  const aliases = getBuildingAliases(building);

  let best = 0;

  for (const alias of aliases) {
    if (alias === normalizedQuery) {
      best = Math.max(best, 100);
    } else if (alias.startsWith(normalizedQuery)) {
      best = Math.max(best, 92);
    } else if (alias.includes(normalizedQuery)) {
      best = Math.max(best, 72);
    }
  }

  if (nameLower === normalizedQuery) {
    best = Math.max(best, 100);
  } else if (nameLower.startsWith(normalizedQuery)) {
    best = Math.max(best, 94);
  } else if (nameLower.includes(normalizedQuery)) {
    best = Math.max(best, 84);
  }

  if (building.category.toLowerCase().includes(normalizedQuery)) {
    best = Math.max(best, 66);
  }

  if (best === 0) {
    const fuzzyName = fuzzySubsequenceScore(normalizedQuery, nameLower);
    best = Math.max(best, fuzzyName);
    for (const alias of aliases) {
      best = Math.max(best, fuzzySubsequenceScore(normalizedQuery, alias));
    }
  }

  if (best > 0 && building.isNamed) {
    best += 4;
  }

  return best;
}

export function searchBuildings(
  buildings: BuildingMeta[],
  query: string,
  category: FilterCategory,
  limit = 16,
): BuildingMeta[] {
  const filtered =
    category === "all"
      ? buildings
      : buildings.filter((b) => b.category === category);

  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return [...filtered]
      .sort((a, b) => {
        if (a.isNamed !== b.isNamed) {
          return a.isNamed ? -1 : 1;
        }
        return a.name.localeCompare(b.name);
      })
      .slice(0, limit);
  }

  const scored: Array<{ building: BuildingMeta; score: number }> = [];
  for (const building of filtered) {
    const score = scoreBuilding(building, normalized);
    if (score > 0) {
      scored.push({ building, score });
    }
  }

  scored.sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score;
    }
    if (a.building.isNamed !== b.building.isNamed) {
      return a.building.isNamed ? -1 : 1;
    }
    return a.building.name.localeCompare(b.building.name);
  });

  return scored.slice(0, limit).map((item) => item.building);
}
