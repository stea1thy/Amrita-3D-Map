"""Headless Blender verification renderer for individual targets (`--target <name_or_id>`) or `overview`."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
import mathutils

PALM_SHADES = ("#3E663A", "#497141", "#355934", "#557A46")
CANOPY_SHADES = ("#2F5534", "#3E623B", "#4B693D", "#2A4A30")


def _hex_to_lin_rgba(hex_str: str) -> tuple[float, float, float, float]:
    c = hex_str.lstrip("#")
    r, g, b = (int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0)
    def _lin(u: float) -> float:
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    return (_lin(r), _lin(g), _lin(b), 1.0)


def _spawn_preview_trees(scene: bpy.types.Scene, cx: float, cy: float, max_dist: float) -> int:
    """Spawn temporary vertex-colored proxy trees from `trees.json` for QA screenshots."""
    if not config.TREES_JSON_PATH.exists():
        return 0
    trees_raw = json.loads(config.TREES_JSON_PATH.read_text(encoding="utf-8")).get("trees") or []
    max_d2 = max_dist * max_dist
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new("Color")

    c_trunk_palm = _hex_to_lin_rgba("#7E6449")
    c_trunk_canopy = _hex_to_lin_rgba("#6B513B")
    palm_cols = [_hex_to_lin_rgba(h) for h in PALM_SHADES]
    canopy_cols = [_hex_to_lin_rgba(h) for h in CANOPY_SHADES]

    def _emit_octa_blob(bx: float, by: float, bz: float, rx: float, ry: float, rz: float, rgba: tuple[float, float, float, float]) -> None:
        top = bm.verts.new((bx, by, bz + rz))
        bot = bm.verts.new((bx, by, bz - rz * 0.72))
        ring = []
        for i in range(6):
            ang = (2.0 * math.pi * i) / 6.0
            ring.append(bm.verts.new((bx + rx * math.cos(ang), by + ry * math.sin(ang), bz)))
        for i in range(6):
            j = (i + 1) % 6
            for tri in ((ring[i], ring[j], top), (ring[j], ring[i], bot)):
                f = bm.faces.new(tri)
                f.smooth = False
                for loop in f.loops:
                    loop[col_layer] = rgba

    def _add_trunk(bx: float, by: float, bz0: float, bz1: float, r: float, rgba: tuple[float, float, float, float]) -> None:
        b = [
            bm.verts.new((bx + r * math.cos(a), by + r * math.sin(a), bz0))
            for a in (0.0, 1.5708, 3.1416, 4.7124)
        ]
        rt = r * 0.65
        t = [
            bm.verts.new((bx + rt * math.cos(a), by + rt * math.sin(a), bz1))
            for a in (0.0, 1.5708, 3.1416, 4.7124)
        ]
        for i in range(4):
            j = (i + 1) % 4
            for tri in ((b[i], b[j], t[j]), (b[i], t[j], t[i])):
                f = bm.faces.new(tri)
                f.smooth = False
                for loop in f.loops:
                    loop[col_layer] = rgba

    count = 0
    for item in trees_raw:
        gx, gy, gz, sc, rot_y, ttype, shade = item
        bx, by, bz = float(gx), -float(gz), float(gy) - 0.15
        if (bx - cx) ** 2 + (by - cy) ** 2 > max_d2:
            continue
        sc_f = float(sc)
        shade_idx = int(shade) % 4
        if int(ttype) == 0:
            _add_trunk(bx, by, bz, bz + 7.6 * sc_f, 0.22 * sc_f, c_trunk_palm)
            pcol = palm_cols[shade_idx]
            cz = bz + 7.8 * sc_f
            _emit_octa_blob(bx, by, cz, 2.15 * sc_f, 2.15 * sc_f, 0.78 * sc_f, pcol)
        else:
            _add_trunk(bx, by, bz, bz + 2.8 * sc_f, 0.26 * sc_f, c_trunk_canopy)
            ccol = canopy_cols[shade_idx]
            ca, sa = math.cos(float(rot_y)), math.sin(float(rot_y))
            for rad, lx, lz, ly, sy in (
                (2.05, 0.0, 4.35, 0.0, 0.88),
                (1.52, 1.0, 3.65, 0.56, 0.92),
                (1.45, -0.92, 3.72, -0.62, 0.90),
            ):
                wx = bx + (lx * ca - ly * sa) * sc_f
                wy = by + (lx * sa + ly * ca) * sc_f
                wz = bz + lz * sc_f
                rxy = rad * sc_f
                _emit_octa_blob(wx, wy, wz, rxy, rxy, rad * sy * sc_f, ccol)
        count += 1

    if count == 0:
        bm.free()
        return 0

    mat = bpy.data.materials.new("QA_TreeMat")
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        vcol = nt.nodes.new(type="ShaderNodeVertexColor")
        vcol.layer_name = "Color"
        nt.links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.86
    mesh = bpy.data.meshes.new("QA_PreviewTrees")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new("QA_PreviewTrees", mesh)
    scene.collection.objects.link(obj)
    return count

PIPELINE_DIR = Path(__file__).resolve().parent
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

import config  # noqa: E402

BUILTIN_ALIASES: dict[str, str] = {
    "ab1": "way/380925364",
    "ab2": "way/380702789",
    "ab3": "way/380829415",
    "asb": "way/380829759",
    "library": "way/380702790",
    "centrallibrary": "way/380702790",
    "amriteshwari": "way/380925370",
    "canteen": "way/546394562",
    "maincanteen": "way/546394562",
    "shrine": "way/531394576",
    "maingate": "hero/main-gate",
    "securityoffice": "hero/security-office",
    "studentsparking": "hero/students-parking",
    "visitorparking": "hero/visitor-parking",
    "playground": "way/528938316",
    "mainground": "way/528938316",
    "mainsportsground": "way/528938316",
    "pool": "way/1210976885",
    "workshops": "way/380926299",
    "workshopswest": "way/380926299",
    "workshopseast": "way/380926300",
}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "target"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Render top & front QA screenshots for a campus target.")
    parser.add_argument("--target", required=True, help="Building name/ID (e.g. ab1, way/380925364) or 'overview'")
    parser.add_argument("--out-dir", type=Path, default=config.RENDERS_DIR, help="Output PNG directory")
    parser.add_argument(
        "--engine",
        default="BLENDER_EEVEE",
        choices=("BLENDER_EEVEE", "BLENDER_WORKBENCH", "CYCLES"),
        help="Preferred Blender render engine (falls back to CYCLES on headless GPU issues)",
    )
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=600)
    return parser.parse_args(argv)


def _world_bbox_from_object(obj: bpy.types.Object) -> tuple[float, float, float, float, float, float]:
    corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _resolve_target(target: str) -> tuple[str, tuple[float, float, float, float, float, float]]:
    meta = json.loads(config.CAMPUS_META_PATH.read_text(encoding="utf-8")) if config.CAMPUS_META_PATH.exists() else {}
    q_norm = _norm(target)

    if q_norm == "overview":
        tb = meta.get("terrainBounds") or {}
        if tb:
            min_x, max_x = float(tb.get("minX", -440.0)), float(tb.get("maxX", 460.0))
            min_y, max_y = -float(tb.get("maxZ", 420.0)), -float(tb.get("minZ", -480.0))
            min_z, max_z = float(tb.get("minY", -12.0)), min(60.0, float(tb.get("maxY", 45.0)))
            return ("Campus Overview", (min_x, max_x, min_y, max_y, min_z, max_z))
        return ("Campus Overview", (-440.0, 460.0, -420.0, 480.0, -10.0, 40.0))

    if q_norm == "maingate":
        return (
            "Amrita Main Gate, Security Office & Parking Zone",
            (-86.0, 48.0, -426.0, -300.0, -8.0, 12.0),
        )

    canonical_id = BUILTIN_ALIASES.get(q_norm)
    items: list[dict[str, Any]] = list(meta.get("buildings") or []) + list(meta.get("inspectables") or [])

    matched_item: dict[str, Any] | None = None
    if canonical_id:
        matched_item = next((it for it in items if str(it.get("id")) == canonical_id), None)

    if matched_item is None:
        for check_fn in (
            lambda it: str(it.get("id", "")).lower() == target.lower(),
            lambda it: str(it.get("meshName", "")).lower() == target.lower(),
            lambda it: _norm(str(it.get("name", ""))) == q_norm,
            lambda it: q_norm in _norm(str(it.get("name", ""))),
            lambda it: any(q_norm in _norm(str(t)) for t in (it.get("tags") or [])),
        ):
            matched_item = next((it for it in items if check_fn(it)), None)
            if matched_item is not None:
                break

    # Try direct Blender object match first (or via matched_item meshName)
    cand_obj: bpy.types.Object | None = None
    if canonical_id == "way/528938316":
        cand_obj = bpy.data.objects.get("GROUND_MainSports")
    if cand_obj is None and matched_item and matched_item.get("meshName"):
        cand_obj = bpy.data.objects.get(str(matched_item["meshName"]))
    if cand_obj is None:
        cand_obj = next(
            (o for o in bpy.data.objects if o.type == "MESH" and q_norm in _norm(o.name)),
            None,
        )

    if cand_obj is not None:
        label = str(matched_item.get("name")) if matched_item and matched_item.get("name") else cand_obj.name
        if canonical_id == "way/528938316" and label == cand_obj.name:
            label = "Amrita Main Sports Ground"
        return (label, _world_bbox_from_object(cand_obj))

    if matched_item is not None:
        c = matched_item.get("center") or [0.0, 0.0, 0.0]
        r = max(12.0, float(matched_item.get("boundingRadius") or 24.0))
        h = max(4.0, float(matched_item.get("heightM") or 8.0))
        bx, by, bz = float(c[0]), -float(c[2]), float(c[1])
        return (
            str(matched_item.get("name") or matched_item.get("id")),
            (bx - r, bx + r, by - r, by + r, bz - 0.5 * h, bz + 0.5 * h),
        )

    sample_names = [str(b.get("name")) for b in (meta.get("buildings") or [])[:12]]
    raise SystemExit(
        f"Target '{target}' not found in campus_meta.json or Blender scene. "
        f"Try 'overview', an OSM ID (e.g. way/380925364), or aliases {sorted(BUILTIN_ALIASES)} "
        f"or names like {sample_names}."
    )


def _setup_lighting_and_engine(scene: bpy.types.Scene, engine: str, width: int, height: int) -> None:
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    world = scene.world or bpy.data.worlds.new("QA_Sky")
    scene.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    if world.node_tree:
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs[0].default_value = (0.72, 0.84, 0.96, 1.0)
            bg.inputs[1].default_value = 0.85

    if not any(o.type == "LIGHT" for o in bpy.data.objects):
        sun_data = bpy.data.lights.new("QA_Sun", type="SUN")
        sun_data.energy = 3.0
        sun = bpy.data.objects.new("QA_Sun", sun_data)
        sun.rotation_euler = (0.72, 0.25, -0.75)
        scene.collection.objects.link(sun)

    scene.render.engine = engine
    if engine == "BLENDER_EEVEE":
        if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 16
    elif engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = 12
        scene.cycles.use_denoising = False


def _render_with_cam(
    scene: bpy.types.Scene,
    name: str,
    cam_type: str,
    loc: tuple[float, float, float],
    rot_euler: tuple[float, float, float],
    filepath: Path,
    ortho_scale: float = 100.0,
    lens: float = 34.0,
) -> None:
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = cam_type
    cam_data.clip_start = 0.5
    cam_data.clip_end = 6000.0
    if cam_type == "ORTHO":
        cam_data.ortho_scale = ortho_scale
    else:
        cam_data.lens = lens
    cam_obj = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_obj)
    cam_obj.location = loc
    cam_obj.rotation_euler = rot_euler
    scene.camera = cam_obj
    scene.render.filepath = str(filepath)
    try:
        bpy.ops.render.render(write_still=True)
    except Exception as exc:
        if scene.render.engine != "CYCLES":
            print(f"Render engine {scene.render.engine} failed ({exc}); falling back to CYCLES CPU...")
            scene.render.engine = "CYCLES"
            scene.cycles.device = "CPU"
            scene.cycles.samples = 12
            scene.cycles.use_denoising = False
            bpy.ops.render.render(write_still=True)
        else:
            raise


def main() -> None:
    args = _parse_args()
    out_dir: Path = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(args.target)

    label, (min_x, max_x, min_y, max_y, min_z, max_z) = _resolve_target(args.target)
    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)
    span_x = max(8.0, max_x - min_x)
    span_y = max(8.0, max_y - min_y)
    span_z = max(4.0, max_z - min_z)
    radius = max(12.0, 0.5 * math.hypot(span_x, span_y))

    scene = bpy.context.scene
    _setup_lighting_and_engine(scene, args.engine, args.width, args.height)

    is_overview = _norm(args.target) == "overview"
    tree_dist = 1400.0 if is_overview else max(160.0, radius * 2.6)
    tree_cnt = _spawn_preview_trees(scene, cx, cy, tree_dist)

    top_path = out_dir / f"{slug}_top.png"
    front_path = out_dir / f"{slug}_front.png"
    ortho_scale = max(span_x, span_y) * (1.05 if is_overview else 1.65)
    _render_with_cam(
        scene,
        "QA_Cam_Top",
        "ORTHO",
        (cx, cy, max_z + 320.0),
        (0.0, 0.0, 0.0),
        top_path,
        ortho_scale=ortho_scale,
    )

    if is_overview:
        front_loc = (cx + 120.0, min_y - 360.0, 290.0)
        front_target = (cx, cy + 40.0, 10.0)
        front_lens = 28.0
    elif _norm(args.target) in {"mainground", "mainsportsground", "playground"} or args.target.lower() == "way/528938316":
        d = max(72.0, radius * 1.95)
        front_loc = (cx - d * 0.42, cy - d * 0.92, max_z + d * 0.40)
        front_target = (cx + 4.0, cy, min_z + span_z * 0.35)
        front_lens = 34.0
    elif _norm(args.target) == "maingate":
        d = max(70.0, radius * 1.65)
        front_loc = (cx - d * 0.38, cy - d * 0.96, max_z + d * 0.44)
        front_target = (cx + 6.0, cy + 8.0, min_z + span_z * 0.32)
        front_lens = 34.0
    else:
        d = max(48.0, radius * 2.15)
        front_loc = (cx + d * 0.16, cy - d * 1.05, max_z + d * 0.44)
        front_target = (cx, cy, min_z + span_z * 0.45)
        front_lens = 34.0

    front_rot = (mathutils.Vector(front_target) - mathutils.Vector(front_loc)).to_track_quat("-Z", "Y").to_euler()
    _render_with_cam(
        scene,
        "QA_Cam_Front",
        "PERSP",
        front_loc,
        (front_rot.x, front_rot.y, front_rot.z),
        front_path,
        lens=front_lens,
    )

    print(
        f"Rendered '{label}' (span={span_x:.1f}x{span_y:.1f}x{span_z:.1f}m, trees={tree_cnt}, engine={scene.render.engine}):\n"
        f"  TOP  : {top_path}\n"
        f"  FRONT: {front_path}"
    )


if __name__ == "__main__":
    main()
