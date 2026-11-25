# Amrita Campus 3D Map — Workspace Rules

## Hard Budgets (Fail-Fast)
- Never consider a 3D build complete if total triangles exceed **150,000**, `web/public/models/campus.glb` exceeds **900 KB** (Draco-compressed), or draw calls regress severely (baseline ~50 primitives, `<= 90` interactive `BLDG_*` objects).
- Always run `pipeline/verify_budget.py` after any geometry, terrain, road, or material change.

## Architectural Identity (Amrita Coimbatore / Ettimadai)
- Keep buildings faithful to the real campus architecture: warm cream/ivory stucco walls (`#EFE8DC`), flat weathered-concrete parapet roofs (`#B7B5AE`) with dark solar panel arrays (`#2A3542`) and warm terracotta cornice trims (`#C27856`) on multi-wing blocks (use pitched roofs only where real photos show them, e.g., AB-1 entrance pediment, AB-2 gable roofs, octagonal pavilion).
- Preserve open internal OSM/multipolygon courtyards (never cap over holes), exact floor counts and exclusions in `pipeline/overrides.json`, Shapely-merged roads, lush Ettimadai tropical palms/canopy groves, and the Bouluvampatty Western Ghats mountain backdrop.
- Never revert to generic bright-red-capped boxes or continuous jet-black window stripes.

## Modularity
- Put new custom landmark generators in `pipeline/heroes/<landmark>.py` (implementing `build_hero(context)` — auto-discovered by `pipeline/build_scene.py`) or manual `.glb` assets in `pipeline/hero_models/` instead of bloating `pipeline/build_scene.py`.
- Put metadata renames, floor count overrides, exclusions, custom buildings, bridges, and custom roads in `pipeline/overrides.json`.

## Mandatory Reference Ground-Truth & Autonomous Visual Loop
- **Before writing or modifying geometry for any building**, execute **Step 0** of the `campus-visual-qa` skill:
  - **0A (Satellite Ground Truth):** Ensure `pipeline/refs/<target>_sat.jpg` exists (run `pipeline/.venv/Scripts/python.exe pipeline/fetch_ref_sat.py --target <target>` if missing).
  - **0B (Online IRL Photo Verification):** If `pipeline/refs/<target>_irl.jpg` is missing, use the **Browser Subagent** (`/browser`) to search for verified exterior photos of `"Amrita Vishwa Vidyapeetham Coimbatore Ettimadai <target>"` (prioritizing `amrita.edu/campus/coimbatore` and Google Maps / Street View listings).
  - **Strict Campus Check:** Confirm every photo is genuinely the **Coimbatore (Ettimadai)** campus — NEVER mix in photos from Amritapuri, Bengaluru, Kochi, or Faridabad campuses. Save the clearest exterior reference to `pipeline/refs/<target>_irl.jpg` and cite the source URL.
  - **Fallback Rule:** If no verified Ettimadai exterior photo exists online, do NOT hallucinate wild architecture — model strictly from `<target>_sat.jpg`, `pipeline/overrides.json` floor counts, and the Ettimadai building palette, and ask the user if they can provide a phone photo.
- Whenever modifying any 3D geometry, buildings, roads, bridges, terrain, materials, foliage, or `pipeline/overrides.json`, ALWAYS execute the full `campus-visual-qa` loop (`Step 0 → Build → Budget Check → Render → Visual Critic Subagent → Fix`, up to 3 iterations) before reporting completion — never deliver unverified blind 3D edits.
