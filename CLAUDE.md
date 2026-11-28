# Amrita Campus 3D Map — Claude Code Workspace Rules

## Mandatory GitHub Sync Check (Before Starting Any Work)
- **Before making any file edits, running 3D builds, or starting any new task**, ALWAYS fetch from GitHub and verify whether the local workspace is on the latest `origin/main`:
  1. Run `git fetch origin`, `git status -sb`, `git branch -vv`, and `git log --oneline HEAD..origin/main`.
  2. **If behind `origin/main` or on an older/already-merged branch:** STOP and report the incoming commits/PRs to the user before editing anything.
     - If the working tree is clean on `main`, fast-forward cleanly (`git pull --ff-only origin main`).
     - If on an old/merged branch or if uncommitted local edits exist, ask the user before switching branches or merging so teammates' merged work and local edits (including any `.claude/worktrees/`) are never overwritten or lost.
  3. **Worktrees & Feature Branches:** When using a separate branch/worktree (e.g., `.claude/worktrees/`), rebase or merge the latest `origin/main` before building `web/public/models/campus.glb` or opening a Pull Request. Never overwrite teammates' merged `pipeline/` changes with a stale GLB.

## Follow All Project Rules in `GEMINI.md`
Follow every rule defined in [GEMINI.md](./GEMINI.md):
- **Hard Budgets (Fail-Fast):** Total triangles `<= 160,000`, `web/public/models/campus.glb` `<= 960 KB` (Draco-compressed), `<= 90` interactive `BLDG_*` objects. Always run `pipeline/.venv/Scripts/python.exe pipeline/verify_budget.py` after any 3D/material/override change.
- **Architectural Identity:** Keep models faithful to Amrita Vishwa Vidyapeetham, Coimbatore (Ettimadai) — warm cream/ivory stucco (`#EFE8DC`), flat weathered-concrete parapet roofs (`#B7B5AE`) with solar panels (`#2A3542`) and terracotta cornice trims (`#C27856`) where real buildings have them, open OSM inner courtyards, exact floor counts from `pipeline/overrides.json`, Shapely-merged roads, tropical foliage, and Bouluvampatty Western Ghats backdrop.
- **Modularity:** Put new custom landmark generators in `pipeline/heroes/<landmark>.py` (implementing `build_hero(context)`) instead of bloating `pipeline/build_scene.py`, and put metadata/floor/exclusion/road overrides in `pipeline/overrides.json`.
- **Mandatory Ground-Truth & Visual QA:** Before editing any building, fetch `pipeline/refs/<target>_sat.jpg` (`pipeline/fetch_ref_sat.py`) and verify Coimbatore/Ettimadai IRL photos (`pipeline/refs/<target>_irl.jpg`). Always verify edits with headless Blender renders (`pipeline/render_check.py`) before reporting completion.
