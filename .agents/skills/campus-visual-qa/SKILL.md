---
name: campus-visual-qa
description: Runs an automated headless Blender build, budget check, target screenshot render, and Visual Critic subagent inspection loop. Use automatically after any edit to 3D campus geometry, buildings, roads, terrain, materials, or overrides.
---

# Campus 3D Visual QA Loop

Execute this automated **Reference Gathering → Build → Budget Check → Render → Visual Critic → Fix** loop before and after editing 3D buildings, hero landmarks, terrain, roads, bridges, foliage, materials, or `pipeline/overrides.json`.

## Step 0 — Gather & Verify Real References (BEFORE Editing Any Building)
Never guess or invent building geometry blindly. Before writing geometry code for `<target>`:

1. **0A — Satellite Ground Truth:**
   If `pipeline/refs/<target>_sat.jpg` does not already exist, fetch zoomed Esri World Imagery tiles covering `<target>` + 40m margin:
   ```powershell
   pipeline\.venv\Scripts\python.exe pipeline\fetch_ref_sat.py --target <target>
   ```
   Inspect `pipeline/refs/<target>_sat.jpg` directly to verify roof shape, solar panel layout, courtyard holes, adjacent roads, and entrance orientation.

2. **0B — Online IRL Photo Verification:**
   If `pipeline/refs/<target>_irl.jpg` does not exist (and the user did not already attach photos), invoke the **Browser Subagent** (`browser`) to search for verified exterior photos of:
   `"Amrita Vishwa Vidyapeetham Coimbatore Ettimadai <target>"`
   - Prioritize `amrita.edu/campus/coimbatore` and Google Maps / Street View exterior listings.
   - **Strict Campus Check:** Verify the photo is genuinely the **Coimbatore (Ettimadai)** campus (Western Ghats backdrop, Ettimadai architectural context). **NEVER** mix in photos from Amritapuri, Bengaluru, Kochi, or Faridabad campuses.
   - Save the clearest exterior reference screenshot to `pipeline/refs/<target>_irl.jpg` and cite its exact source URL in your notes/response.

3. **Fallback Rule:**
   If no verified Coimbatore (Ettimadai) exterior photo exists online (common for smaller hostels, canteens, or workshop sheds), do **NOT** hallucinate decorative architecture — model strictly from `pipeline/refs/<target>_sat.jpg`, `pipeline/overrides.json` floor counts, and the standard Ettimadai building palette, and let the user know if a phone photo would help refine facade details later.

## Step 1 — Headless Build & Fail-Fast Budget Check
1. Locate the installed Blender executable (Windows: `C:\Program Files\Blender Foundation\Blender*\blender.exe`).
2. Rebuild the full scene (saves `pipeline/debug_campus.blend` and exports `web/public/models/campus.glb` + `web/public/data/*.json`):
   ```powershell
   & "<blender.exe>" --background --python-exit-code 1 --python pipeline/build_scene.py
   ```
3. Run the budget gate (must pass `<= 150,000` triangles and `<= 900 KB` GLB):
   ```powershell
   pipeline\.venv\Scripts\python.exe pipeline\verify_budget.py
   ```
4. If roads, buildings, or `pipeline/overrides.json` changed, rebuild the walking graph:
   ```powershell
   pipeline\.venv\Scripts\python.exe pipeline\build_graph.py
   ```
   - If over budget, simplify geometry immediately before proceeding.

## Step 2 — Render Target Verification Views
Render orthographic top-down (`<target>_top.png`) and elevated 3/4 front (`<target>_front.png`) screenshots into `pipeline/renders/` from `pipeline/debug_campus.blend`:
```powershell
& "<blender.exe>" --background pipeline/debug_campus.blend --python-exit-code 1 --python pipeline/render_check.py -- --target <target>
```
- Also render `--target overview` when edits affect foliage balance, terrain, roads, multiple blocks, or the campus horizon.

## Step 3 — Visual Critic Subagent Inspection
1. Collect exact paths to:
   - `pipeline/renders/<target>_top.png` and `pipeline/renders/<target>_front.png` (plus `overview` PNGs if rendered),
   - `pipeline/refs/<target>_sat.jpg` and `pipeline/refs/<target>_irl.jpg` (when present) or user-attached photos, and
   - `GEMINI.md` architectural/budget rules.
2. Spawn a `research` subagent (`Role: "3D Visual Critic"`) to inspect both rendered PNGs side-by-side against the reference images and `GEMINI.md`:
   - Accurate footprint & open internal courtyards (no capped-over holes or nonexistent notches),
   - Correct roof shape/color, solar panels, floor count, entrance pavilion geometry, and facade palette,
   - Proportional, calm green foliage (clear sightlines & manicured lawns around plazas; no oversized neon blobs blocking facades),
   - Clean road/plaza/terrain contact with zero floating objects, clipping, z-fighting, or stray curbs/footpaths.
3. Require an explicit `PASS` or `FAIL` verdict with concrete coordinates/fixes if `FAIL`.

## Step 4 — Autonomous Fix Loop & Final Verification
- If the Visual Critic returns `FAIL`, apply the targeted fix in `pipeline/heroes/*.py`, `pipeline/hero_models/*.py`, `pipeline/overrides.json`, `pipeline/build_scene.py`, or `web/src/components/` and repeat **Steps 1–3** (max 3 iterations) until both `verify_budget.py` and the Visual Critic return `PASS`.
- If any files under `web/` were modified, run `npm --prefix web run lint` and `npm --prefix web run build` and confirm zero errors before reporting done.
