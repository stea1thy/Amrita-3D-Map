# Amrita Campus 3D Map

Interactive 3D campus map for **Amrita Vishwa Vidyapeetham, Coimbatore (Ettimadai)**.

## Tech Stack & Architecture

```text
pipeline/ (Python 3 + Blender 5.3 headless) ──► web/ (Next.js 16 + React Three Fiber)
```

- **3D & Geospatial Pipeline (`pipeline/`)**: Python (`requests`, `shapely`, `numpy`, `duckdb`) + headless Blender 5.3 ingests OpenStreetMap, Overture Maps, and elevation DEM data, builds `web/public/models/campus.glb` (Draco-compressed, `<= 160,000` tris, `<= 960 KB`), and exports `web/public/data/*.json` (`campus_meta.json`, `walk_graph.json`, `trees.json`, `streetlamps.json`).
- **Frontend Viewer (`web/`)**: Next.js 16 App Router, TypeScript, React Three Fiber, Three.js, and Tailwind CSS v4.
- **No Blender needed for frontend/data work**: Pre-built `web/public/models/campus.glb` and `web/public/data/*.json` are committed directly to Git.

---

## Quickstart for Teammates (No Blender Required)

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

Useful frontend checks before opening a PR:
```bash
npm --prefix web run lint
npm --prefix web run build
```

### `?debug=1` Inspector & Satellite Tracer Mode

Open [http://localhost:3000/?debug=1](http://localhost:3000/?debug=1) to turn on the campus QA toolkit:
- **Inspect structures**: Click any building, bridge, or sports area to see its OSM/Overture ID, floor count, dimensions, and copy ready-to-paste `pipeline/overrides.json` snippets (`rename_or_retag`, `exclude_ids`, `bridges`).
- **Satellite comparison**: Toggle **Satellite** (Esri World Imagery overlay + opacity slider), **Top-Down** camera, **Ghost** buildings, and unmatched **POIs**.
- **Trace missing buildings**: Toggle **Trace** mode, click footprint corners directly over the satellite imagery, fill in metadata, and copy a ready-to-paste `custom_buildings` entry for `pipeline/overrides.json`.

---

## Folder Ownership Split (Prevent Merge Conflicts)

Each teammate owns distinct folders/files so parallel branches rarely touch the same code:

| Role | Owned Paths | Notes |
| --- | --- | --- |
| **3D Pipeline Lead** | `pipeline/build_scene.py`, `pipeline/hero_models/`, `web/public/models/campus.glb` *(plus supporting geometry scripts: `pipeline/merge_roads.py`, `pipeline/terrain_utils.py`, `pipeline/verify_budget.py`)* | Only the 3D Pipeline Lead should rebuild and commit binary `campus.glb`. |
| **Frontend** | `web/src/**` *(excluding `web/src/data/tourStops.ts`)* | R3F scene, UI panels, search, directions UI, debug inspector. |
| **Campus Data & Routing** | `pipeline/overrides.json`, `pipeline/build_graph.py`, `web/src/data/tourStops.ts` *(and `web/public/data/walk_graph.json` when routing changes)* | Building metadata, floor counts, skybridges, tour stops, walking graph. |

---

## Git Workflow (Copy-Paste)

**Rule:** Never push directly to `main`. Always branch off `main` and open a Pull Request.

```bash
# 1. Sync main before starting work
git checkout main
git pull origin main

# 2. Create a feature branch (use prefixes: feat/, data/, 3d/, fix/)
git checkout -b feat/your-task-name

# 3. Check what changed, stage only your files, and commit
git status
git add <your-files>
git commit -m "feat: concise summary of your change"

# 4. Push your branch and open a Pull Request to main on GitHub
git push -u origin feat/your-task-name
```

---

## Rebuilding the 3D Scene (3D Pipeline Lead Only)

```powershell
# One-time Python environment setup
python -m venv pipeline\.venv
pipeline\.venv\Scripts\pip.exe install -r pipeline\requirements.txt

# Optional: refresh geospatial source data
pipeline\.venv\Scripts\python.exe pipeline\fetch_osm.py
pipeline\.venv\Scripts\python.exe pipeline\fetch_overture.py
pipeline\.venv\Scripts\python.exe pipeline\fetch_elevation.py

# Rebuild GLB, verify budget (<= 160k tris, <= 960 KB), and rebuild walk graph
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" --background --python-exit-code 1 --python pipeline/build_scene.py
pipeline\.venv\Scripts\python.exe pipeline\verify_budget.py
pipeline\.venv\Scripts\python.exe pipeline\build_graph.py
```
