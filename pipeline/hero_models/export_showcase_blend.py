"""Export an organized, standalone editable .blend showcase containing all Amrita Coimbatore hero landmarks."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

HERO_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = HERO_DIR.parent
for p in (str(PIPELINE_DIR), str(HERO_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_scene  # noqa: E402
import config  # noqa: E402
from hero_models import ab1_hero, ab2_hero, ab3_hero, asb_hero, campus_landmarks  # noqa: E402
from hero_models.geom_helpers import HERO_PALETTE, add_box_vc, srgb_hex_to_linear_rgba  # noqa: E402

SHOWCASE_BLEND_PATH = HERO_DIR / "amrita_heroes_showcase.blend"


def _make_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def _link_only(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    col.objects.link(obj)


def _create_obj_in_col(
    name: str,
    bm: bmesh.types.BMesh,
    mats: list[bpy.types.Material],
    col: bpy.types.Collection,
    loc: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name=name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name=name, object_data=mesh)
    obj.location = loc
    col.objects.link(obj)
    return obj


def export_showcase_blend(output_path: Path = SHOWCASE_BLEND_PATH) -> Path:
    """Build a standalone, neatly grouped .blend showcasing each Amrita Coimbatore hero landmark."""
    raw_osm = json.loads(config.RAW_OSM_PATH.read_text(encoding="utf-8"))
    elevation = json.loads(config.ELEVATION_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(config.OVERRIDES_PATH.read_text(encoding="utf-8"))
    overture_data = json.loads(config.OVERTURE_PATH.read_text(encoding="utf-8")) if config.OVERTURE_PATH.exists() else None
    campus_ctx = build_scene.terrain_utils.extract_campus_boundary_and_rail(raw_osm)

    datum_m = float(elevation["metadata"]["stats"]["origin_elevation_m"])
    terrain = build_scene.TerrainSurface(
        lats=elevation["lats"],
        lons=elevation["lons"],
        elevations=elevation["elevations"],
        datum_m=datum_m,
        raw_osm=raw_osm,
    )

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat_body = build_scene.make_vertex_color_material("HeroBody", roughness=0.72)
    mat_glass = build_scene.make_palette_material("WindowGlassLit", build_scene.PALETTE["window_glass"], roughness=0.14, metallic=0.25)

    features = raw_osm.get("features", [])
    osm_buildings = [f for f in features if f.get("properties", {}).get("layer") == "building"]
    records, _, _, _ = build_scene._prepare_building_records(osm_buildings, overrides, overture_data=overture_data)
    rec_by_id = {r["id"]: r for r in records}

    hero_specs = [
        ("Hero_AB1", build_scene.HERO_AB1_ID, "AB1_MainBuilding"),
        ("Hero_AB2_Skybridge", build_scene.HERO_AB2_ID, "AB2_AcademicBlock2"),
        ("Hero_AB3_MainGround", build_scene.HERO_AB3_ID, "AB3_SchoolOfComputing"),
        ("Hero_ASB", build_scene.HERO_ASB_ID, "ASB_SchoolOfBusiness"),
        ("Hero_CentralLibrary", build_scene.HERO_LIBRARY_ID, "CentralLibrary"),
        ("Hero_AmriteshwariHall", build_scene.HERO_AMRITESHWARI_ID, "AmriteshwariHall"),
        ("Hero_Shrine", build_scene.HERO_SHRINE_ID, "CampusShrine"),
        ("Hero_Workshops_West", build_scene.HERO_WORKSHOPS_WEST_ID, "ChemicalLabs_Foundry_Sheds"),
        ("Hero_Workshops_East", build_scene.HERO_WORKSHOPS_EAST_ID, "Lathe_Mechanical_Sheds"),
    ]
    collections: dict[str, bpy.types.Collection] = {
        cname: _make_collection(cname)
        for cname in [s[0] for s in hero_specs] + ["Hero_MainGate", "Hero_PoolComplex"]
    }

    # Build hero building geometries grouped into dedicated collections
    for col_name, fid, obj_name in hero_specs:
        rec = rec_by_id.get(fid)
        if not rec:
            continue
        rings = rec["rings"]
        outer_ring = rings[0]
        area_m2 = abs(build_scene.signed_area_2d(outer_ring))
        cat = str(rec["category"])
        floors, height_m = build_scene._compute_building_floors_and_height(cat, area_m2, rec)
        cx_b, cy_b = build_scene.ring_centroid_2d(outer_ring)
        zs = [terrain.sample(px, py) for px, py in outer_ring]
        z_bottom = min(zs) - build_scene.FOUNDATION_SINK_M
        z_base_ref = sum(zs) / len(zs)
        z_top = max(zs) + height_m
        cz_b = 0.5 * (z_bottom + z_top)

        bm = bmesh.new()
        col_layer = bm.loops.layers.color.new("Color")
        win_lit_bm = bmesh.new()
        win_dark_bm = bmesh.new()
        wall_hex = build_scene._tint_hex_for_id(build_scene.PALETTE.get(f"wall_{cat}", build_scene.PALETTE["wall_default"]), fid)
        roof_hex = build_scene.PALETTE["roof_hostel"] if cat == "hostel" else build_scene.PALETTE["roof_terracotta_top"]

        build_scene._append_amrita_building(
            bm=bm, col_layer=col_layer, win_lit_bm=win_lit_bm, win_dark_bm=win_dark_bm,
            fid=fid, rings=rings, offset_xyz=(cx_b, cy_b, cz_b),
            z_bottom=z_bottom, z_base_ref=z_base_ref, z_top=z_top,
            floors=floors, area_m2=area_m2, category=cat, terrain=terrain,
            wall_hex=wall_hex, roof_hex=roof_hex,
        )
        _create_obj_in_col(obj_name, bm, [mat_body], collections[col_name], (cx_b, cy_b, cz_b))
        for wb_name, wb_bm in ((f"{obj_name}_GlassLit", win_lit_bm), (f"{obj_name}_GlassDark", win_dark_bm)):
            if wb_bm.faces:
                _create_obj_in_col(wb_name, wb_bm, [mat_glass], collections[col_name], (0.0, 0.0, 0.0))
            else:
                wb_bm.free()

    # Skybridge portal inside Hero_AB2_Skybridge
    for br in overrides.get("bridges") or []:
        if br.get("id") == ab2_hero.__name__.split(".")[0] or br.get("id") == "bridge/ab2-library-skybridge":
            ax, ay = build_scene.latlon_to_blender_xy(float(br["from"][0]), float(br["from"][1]))
            bx, by = build_scene.latlon_to_blender_xy(float(br["to"][0]), float(br["to"][1]))
            mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
            z_g = max(terrain.sample(px, py) for px, py in ((ax, ay), (mx, my), (bx, by)))
            z_bot = z_g + float(br.get("bottomY", 4.5))
            z_top = z_bot + float(br.get("height", 3.4))
            cz = 0.5 * (z_bot + z_top)
            bm_s = bmesh.new()
            col_s = bm_s.loops.layers.color.new("Color")
            bm_sw = bmesh.new()
            ab2_hero.build_ab2_skybridge_hero(
                bm_s, col_s, bm_sw, ax, ay, bx, by, terrain, z_bot, z_top, float(br.get("width", 4.0)), (mx, my, cz),
            )
            _create_obj_in_col("AB2_Library_SkybridgePortal", bm_s, [mat_body], collections["Hero_AB2_Skybridge"], (mx, my, cz))
            if bm_sw.faces:
                _create_obj_in_col("AB2_Skybridge_Glass", bm_sw, [mat_glass], collections["Hero_AB2_Skybridge"])
            else:
                bm_sw.free()

    # Standalone Hero site accents grouped cleanly
    def _accent_col(col_name: str, obj_name: str, fn) -> None:
        bm_a = bmesh.new()
        col_a = bm_a.loops.layers.color.new("Color")
        fn(bm_a, col_a)
        if bm_a.faces:
            _create_obj_in_col(obj_name, bm_a, [mat_body], collections[col_name])
        else:
            bm_a.free()

    _accent_col("Hero_AB1", "AB1_LotusFountainPlaza", lambda bm_a, col_a: ab1_hero.append_ab1_fountain_plaza(bm_a, col_a, terrain))
    _accent_col("Hero_ASB", "ASB_StoneMedianPlanter", lambda bm_a, col_a: asb_hero.append_asb_driveway_planter(bm_a, col_a, terrain))
    _accent_col("Hero_MainGate", "MainGate_EntranceArchway", lambda bm_a, col_a: campus_landmarks.append_main_gate_archway(bm_a, col_a, terrain))

    pg_feat = next((f for f in features if f["id"] == build_scene.HERO_PLAYGROUND_ID), None)
    if pg_feat:
        pts = [build_scene.latlon_to_blender_xy(p[1], p[0]) for p in pg_feat["geometry"]["coordinates"][0][:-1]]
        gcx, gcy = sum(p[0] for p in pts) / 4.0, sum(p[1] for p in pts) / 4.0
        pang = math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0])
        _accent_col(
            "Hero_AB3_MainGround", "MainGround_BleachersAndGoals",
            lambda bm_a, col_a: ab3_hero.append_playground_bleachers_and_goals(bm_a, col_a, terrain, gcx, gcy, pang, None),
        )

    pool_feat = next((f for f in features if f["id"] == build_scene.HERO_POOL_WATER_ID), None)
    if pool_feat:
        p_pts = [build_scene.latlon_to_blender_xy(p[1], p[0]) for p in pool_feat["geometry"]["coordinates"][0][:-1]]
        pcx, pcy = sum(p[0] for p in p_pts) / 4.0, sum(p[1] for p in p_pts) / 4.0
        pz_d = terrain.sample(pcx, pcy) + 0.35

        def _build_pool_showcase(bm_a: bmesh.types.BMesh, col_a) -> None:
            c_deck = srgb_hex_to_linear_rgba(HERO_PALETTE["stucco_cream"])
            c_water = srgb_hex_to_linear_rgba("#1CB5D8")
            add_box_vc(bm_a, col_a, -183.2, 409.2, pz_d - 1.2, pz_d, 25.0, 44.0, c_deck, c_deck, rot_rad=0.062)
            add_box_vc(bm_a, col_a, -184.1, 405.0, pz_d - 0.1, pz_d + 0.08, 12.6, 25.0, c_water, c_water, rot_rad=0.062)
            campus_landmarks.append_pool_complex_hero(bm_a, col_a, terrain, p_pts, pz_d, pz_d + 0.08)

        _accent_col("Hero_PoolComplex", "OlympicPool_PavilionAndBleachers", _build_pool_showcase)

    # Lighting + overview Camera so opening the .blend shows a well-lit architectural layout immediately
    sun_data = bpy.data.lights.new("CampusSun", type="SUN")
    sun_data.energy = 3.2
    sun_obj = bpy.data.objects.new("CampusSun", sun_data)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(15.0), math.radians(-35.0))
    bpy.context.scene.collection.objects.link(sun_obj)

    cam_data = bpy.data.cameras.new("OverviewCam")
    cam_data.clip_end = 4000.0
    cam_obj = bpy.data.objects.new("OverviewCam", cam_data)
    cam_obj.location = (275.0, -355.0, 48.0)
    cam_obj.rotation_euler = (math.radians(65.0), 0.0, math.radians(28.0))
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.unit_settings.system = "METRIC"
    _link_only(sun_obj, bpy.context.scene.collection)
    _ = campus_ctx

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), compress=True)
    size_kb = output_path.stat().st_size / 1024.0
    print(f"Saved editable showcase .blend to {output_path} ({size_kb:.1f} KB)")
    return output_path


if __name__ == "__main__":
    export_showcase_blend()
