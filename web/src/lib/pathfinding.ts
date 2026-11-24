import type {
  BuildingMeta,
  RouteResult,
  WalkGraph,
  WalkGraphNode,
} from "@/types/campus";

export interface AdjacencyEdge {
  to: number;
  distM: number;
  timeS: number;
}

export type AdjacencyList = AdjacencyEdge[][];

interface HeapNode {
  id: number;
  f: number;
}

class MinHeap {
  private items: HeapNode[] = [];

  get size(): number {
    return this.items.length;
  }

  push(item: HeapNode): void {
    this.items.push(item);
    let idx = this.items.length - 1;
    while (idx > 0) {
      const parent = (idx - 1) >> 1;
      if (this.items[parent].f <= this.items[idx].f) {
        break;
      }
      const tmp = this.items[parent];
      this.items[parent] = this.items[idx];
      this.items[idx] = tmp;
      idx = parent;
    }
  }

  pop(): HeapNode | undefined {
    const n = this.items.length;
    if (n === 0) {
      return undefined;
    }
    const top = this.items[0];
    const last = this.items.pop()!;
    if (n > 1) {
      this.items[0] = last;
      let idx = 0;
      const len = this.items.length;
      while (true) {
        const left = idx * 2 + 1;
        const right = left + 1;
        let smallest = idx;
        if (left < len && this.items[left].f < this.items[smallest].f) {
          smallest = left;
        }
        if (right < len && this.items[right].f < this.items[smallest].f) {
          smallest = right;
        }
        if (smallest === idx) {
          break;
        }
        const tmp = this.items[idx];
        this.items[idx] = this.items[smallest];
        this.items[smallest] = tmp;
        idx = smallest;
      }
    }
    return top;
  }
}

export function buildAdjacency(graph: WalkGraph): AdjacencyList {
  const adj: AdjacencyList = Array.from(
    { length: graph.nodes.length },
    () => [],
  );
  for (const [u, v, distM, timeUV, timeVU] of graph.edges) {
    if (u >= 0 && u < adj.length && v >= 0 && v < adj.length) {
      adj[u].push({ to: v, distM, timeS: timeUV });
      adj[v].push({ to: u, distM, timeS: timeVU });
    }
  }
  return adj;
}

// Admissible Euclidean + climb lower bound in seconds for Tobler's hiking function
function heuristicSeconds(a: WalkGraphNode, b: WalkGraphNode): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const dz = b[2] - a[2];
  const dist3d = Math.hypot(dx, dy, dz);
  const tDist = dist3d / (6.0 / 3.6);
  const tClimb = dy > 0 ? dy * 6.5 : 0;
  return Math.max(tDist, tClimb);
}

function findNearestNodeId(
  nodes: WalkGraphNode[],
  center: [number, number, number],
): number {
  let bestId = 0;
  let bestD2 = Infinity;
  const [cx, , cz] = center;
  for (let i = 0; i < nodes.length; i++) {
    const dx = nodes[i][0] - cx;
    const dz = nodes[i][2] - cz;
    const d2 = dx * dx + dz * dz;
    if (d2 < bestD2) {
      bestD2 = d2;
      bestId = i;
    }
  }
  return bestId;
}

function computeRouteBounds(points: WalkGraphNode[]): {
  center: [number, number, number];
  radius: number;
} {
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;

  for (const [px, py, pz] of points) {
    if (px < minX) minX = px;
    if (py < minY) minY = py;
    if (pz < minZ) minZ = pz;
    if (px > maxX) maxX = px;
    if (py > maxY) maxY = py;
    if (pz > maxZ) maxZ = pz;
  }

  const cx = 0.5 * (minX + maxX);
  const cy = 0.5 * (minY + maxY);
  const cz = 0.5 * (minZ + maxZ);
  const radius = Math.max(25, Math.hypot(maxX - cx, maxY - cy, maxZ - cz));
  return { center: [cx, cy, cz], radius };
}

export function findWalkingRoute(
  graph: WalkGraph,
  adj: AdjacencyList,
  fromBuilding: BuildingMeta,
  toBuilding: BuildingMeta,
): RouteResult | null {
  const { nodes } = graph;
  if (nodes.length === 0) {
    return null;
  }

  const startId =
    typeof fromBuilding.nearestNodeId === "number" &&
    fromBuilding.nearestNodeId >= 0 &&
    fromBuilding.nearestNodeId < nodes.length
      ? fromBuilding.nearestNodeId
      : findNearestNodeId(nodes, fromBuilding.center);

  const goalId =
    typeof toBuilding.nearestNodeId === "number" &&
    toBuilding.nearestNodeId >= 0 &&
    toBuilding.nearestNodeId < nodes.length
      ? toBuilding.nearestNodeId
      : findNearestNodeId(nodes, toBuilding.center);

  if (startId === goalId) {
    const node = nodes[startId];
    const pStart: WalkGraphNode = [
      fromBuilding.center[0],
      node[1],
      fromBuilding.center[2],
    ];
    const pGoal: WalkGraphNode = [
      toBuilding.center[0],
      node[1],
      toBuilding.center[2],
    ];
    const dist = Math.hypot(pGoal[0] - pStart[0], pGoal[2] - pStart[2]);
    const points: WalkGraphNode[] =
      dist >= 0.5 ? [pStart, pGoal] : [node, [node[0] + 0.5, node[1], node[2]]];
    const estS = dist / 1.4;
    return {
      fromId: fromBuilding.id,
      toId: toBuilding.id,
      nodeIds: [startId],
      points,
      distanceM: Math.round(dist),
      elevationGainM: 0,
      elevationLossM: 0,
      estimatedSeconds: Math.round(estS),
      estimatedMinutes: Math.max(1, Math.round(estS / 60)),
      bounds: computeRouteBounds(points),
    };
  }

  const n = nodes.length;
  const gScore = new Float64Array(n).fill(Infinity);
  const cameFrom = new Int32Array(n).fill(-1);
  const closed = new Uint8Array(n);

  gScore[startId] = 0;
  const open = new MinHeap();
  open.push({ id: startId, f: heuristicSeconds(nodes[startId], nodes[goalId]) });

  let found = false;
  while (open.size > 0) {
    const curr = open.pop()!;
    const u = curr.id;
    if (closed[u]) {
      continue;
    }
    if (u === goalId) {
      found = true;
      break;
    }
    closed[u] = 1;

    const neighbors = adj[u];
    for (let i = 0; i < neighbors.length; i++) {
      const edge = neighbors[i];
      if (closed[edge.to]) {
        continue;
      }
      const tentativeG = gScore[u] + edge.timeS;
      if (tentativeG < gScore[edge.to]) {
        cameFrom[edge.to] = u;
        gScore[edge.to] = tentativeG;
        const f = tentativeG + heuristicSeconds(nodes[edge.to], nodes[goalId]);
        open.push({ id: edge.to, f });
      }
    }
  }

  if (!found) {
    return null;
  }

  const nodeIds: number[] = [];
  let cursor = goalId;
  while (cursor !== -1) {
    nodeIds.push(cursor);
    cursor = cameFrom[cursor];
  }
  nodeIds.reverse();

  const points: WalkGraphNode[] = nodeIds.map((id) => nodes[id]);
  let distanceM = 0;
  let elevationGainM = 0;
  let elevationLossM = 0;

  for (let i = 1; i < nodeIds.length; i++) {
    const u = nodeIds[i - 1];
    const v = nodeIds[i];
    const edge = adj[u].find((e) => e.to === v);
    if (edge) {
      distanceM += edge.distM;
    } else {
      const [x1, y1, z1] = nodes[u];
      const [x2, y2, z2] = nodes[v];
      distanceM += Math.hypot(x2 - x1, y2 - y1, z2 - z1);
    }
    const dy = nodes[v][1] - nodes[u][1];
    if (dy > 0) {
      elevationGainM += dy;
    } else {
      elevationLossM += -dy;
    }
  }

  const estimatedSeconds = gScore[goalId];
  return {
    fromId: fromBuilding.id,
    toId: toBuilding.id,
    nodeIds,
    points,
    distanceM: Math.round(distanceM),
    elevationGainM: Math.round(elevationGainM * 10) / 10,
    elevationLossM: Math.round(elevationLossM * 10) / 10,
    estimatedSeconds: Math.round(estimatedSeconds),
    estimatedMinutes: Math.max(1, Math.round(estimatedSeconds / 60)),
    bounds: computeRouteBounds(points),
  };
}
