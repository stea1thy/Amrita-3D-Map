"""Verify triangle count and file size budgets for exported campus GLB."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from typing import Any

try:
    from . import config
except ImportError:
    import config

GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK_TYPE = 0x4E4F534A


def parse_glb_json(glb_path: Path) -> dict[str, Any]:
    """Read and decode the JSON chunk from a binary glTF (.glb) file."""
    raw = glb_path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f"File too small to be a valid GLB: {glb_path}")

    magic, version, total_length = struct.unpack("<4sII", raw[:12])
    if magic != GLB_MAGIC or version != 2:
        raise ValueError(f"Invalid GLB header (magic={magic!r}, version={version}): {glb_path}")
    if total_length > len(raw):
        raise ValueError(f"Truncated GLB file ({len(raw)} < {total_length}): {glb_path}")

    offset = 12
    while offset + 8 <= len(raw):
        chunk_len, chunk_type = struct.unpack("<II", raw[offset : offset + 8])
        chunk_start = offset + 8
        chunk_end = chunk_start + chunk_len
        if chunk_end > len(raw):
            raise ValueError(f"Truncated GLB chunk at offset {offset}")
        if chunk_type == GLB_JSON_CHUNK_TYPE:
            return json.loads(raw[chunk_start:chunk_end].decode("utf-8"))
        offset = chunk_end

    raise ValueError(f"No JSON chunk found in GLB: {glb_path}")


def _primitive_triangles(prim: dict[str, Any], accessors: list[dict[str, Any]]) -> int:
    """Compute triangle count for a single glTF mesh primitive."""
    mode = prim.get("mode", 4)  # 4 == TRIANGLES
    if "indices" in prim:
        count = int(accessors[prim["indices"]]["count"])
    elif "POSITION" in prim.get("attributes", {}):
        count = int(accessors[prim["attributes"]["POSITION"]]["count"])
    else:
        return 0

    if mode == 4:
        return count // 3
    if mode in (5, 6):  # TRIANGLE_STRIP / TRIANGLE_FAN
        return max(0, count - 2)
    return 0


def classify_node_category(name: str) -> str:
    """Map a glTF node name to a budget reporting category."""
    if name.startswith("TERRAIN_") or name.startswith("GROUND_") or name.startswith("STATIC_H"):
        return "terrain"
    if (
        name.startswith("BLDG_")
        or name.startswith("BRIDGE_")
        or name.startswith("STATIC_B")
        or name.startswith("STATIC_W")
    ):
        return "buildings"
    if name.startswith("ROADS_") or name.startswith("RAILWAY_"):
        return "roads"
    if name.startswith("TREES_"):
        return "trees"
    return "other"


def verify_glb(
    glb_path: Path = config.CAMPUS_GLB_PATH,
    max_triangles: int = config.MAX_TRIANGLES,
    max_bytes: int = config.MAX_GLB_BYTES,
) -> tuple[bool, dict[str, Any]]:
    """Inspect a GLB file, print category breakdown, and check triangle & size budgets."""
    if not glb_path.exists():
        print(f"Budget check FAIL: file not found: {glb_path}")
        return False, {"error": f"File not found: {glb_path}"}

    size_bytes = glb_path.stat().st_size
    size_kb = size_bytes / 1024.0
    gltf = parse_glb_json(glb_path)

    accessors = gltf.get("accessors", [])
    meshes = gltf.get("meshes", [])
    nodes = gltf.get("nodes", [])
    scenes = gltf.get("scenes", [])

    mesh_tris: list[int] = [
        sum(_primitive_triangles(prim, accessors) for prim in mesh.get("primitives", []))
        for mesh in meshes
    ]
    mesh_prims: list[int] = [len(mesh.get("primitives", [])) for mesh in meshes]

    categories: dict[str, int] = {
        "terrain": 0,
        "buildings": 0,
        "roads": 0,
        "trees": 0,
        "other": 0,
    }
    object_counts: dict[str, int] = {k: 0 for k in categories}
    primitive_counts: dict[str, int] = {k: 0 for k in categories}

    def walk_node(node_idx: int) -> None:
        if node_idx < 0 or node_idx >= len(nodes):
            return
        node = nodes[node_idx]
        if "mesh" in node:
            mesh_idx = int(node["mesh"])
            tris = mesh_tris[mesh_idx] if 0 <= mesh_idx < len(mesh_tris) else 0
            prims = mesh_prims[mesh_idx] if 0 <= mesh_idx < len(mesh_prims) else 0
            node_name = node.get("name") or (
                meshes[mesh_idx].get("name", "") if 0 <= mesh_idx < len(meshes) else ""
            )
            cat = classify_node_category(node_name)
            categories[cat] += tris
            object_counts[cat] += 1
            primitive_counts[cat] += prims
        for child_idx in node.get("children", []):
            walk_node(int(child_idx))

    if scenes:
        scene_idx = int(gltf.get("scene", 0))
        root_nodes = scenes[scene_idx].get("nodes", []) if 0 <= scene_idx < len(scenes) else []
        for idx in root_nodes:
            walk_node(int(idx))
    else:
        for idx in range(len(nodes)):
            walk_node(idx)

    total_triangles = sum(categories.values())
    total_primitives = sum(primitive_counts.values())
    extensions = set(gltf.get("extensionsUsed", [])) | set(gltf.get("extensionsRequired", []))
    draco_enabled = "KHR_draco_mesh_compression" in extensions

    failures: list[str] = []
    if total_triangles > max_triangles:
        failures.append(f"triangles {total_triangles:,} > {max_triangles:,}")
    if size_bytes > max_bytes:
        failures.append(f"size {size_kb:.1f} KB ({size_bytes} B) > {max_bytes / 1024.0:.1f} KB ({max_bytes} B)")

    passed = len(failures) == 0

    print("=== Campus 3D Budget Verification ===")
    print(f"File: {glb_path}")
    print(f"Draco compression: {'enabled' if draco_enabled else 'NOT DETECTED'}")
    print("Triangle breakdown by category:")
    for cat in ("terrain", "buildings", "roads", "trees", "other"):
        if cat == "other" and categories[cat] == 0:
            continue
        print(
            f"  {cat:<10s}: {categories[cat]:>8,d} tris "
            f"({object_counts[cat]} nodes, {primitive_counts[cat]} primitives)"
        )
    print(f"  {'TOTAL':<10s}: {total_triangles:>8,d} / {max_triangles:,d} tris ({total_primitives} draw primitives)")
    print(f"File size   : {size_kb:8.1f} / {max_bytes / 1024.0:.1f} KB ({size_bytes:,d} bytes)")
    if passed:
        print("Budget check: PASS")
    else:
        print(f"Budget check: FAIL ({'; '.join(failures)})")

    report = {
        "passed": passed,
        "glb_path": str(glb_path),
        "size_bytes": size_bytes,
        "size_kb": round(size_kb, 2),
        "max_bytes": max_bytes,
        "total_triangles": total_triangles,
        "total_primitives": total_primitives,
        "max_triangles": max_triangles,
        "categories": categories,
        "object_counts": object_counts,
        "primitive_counts": primitive_counts,
        "draco_enabled": draco_enabled,
        "failures": failures,
    }
    return passed, report


def main() -> None:
    """CLI entrypoint for standalone budget verification."""
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else config.CAMPUS_GLB_PATH
    passed, _ = verify_glb(target)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
