"""Auto-discovery loader for modular hero landmark plugins in `pipeline/heroes/*.py`.

Contract for modular hero scripts (`pipeline/heroes/<landmark>.py`):
    def build_hero(context: dict[str, Any]) -> None:
        '''Append custom geometry or modify scene objects cleanly inside `context`.'''

Keys provided in `context`:
    - `terrain`: TerrainSurface with `.sample(x, y) -> float`
    - `overrides`: Parsed `pipeline/overrides.json` dict
    - `raw_osm`: Parsed `pipeline/data/raw_osm.json` dict
    - `mat_body`: Default vertex-colored building material
    - `mat_hero_accents`: Vertex-colored site-accent material
    - `mat_glass_lit`, `mat_glass_dark`: Window glass materials
    - `solid_colliders`: List of `(bbox, rings)` colliders avoided by `scatter_trees`
    - `courtyard_lawns`: List of CCW courtyard lawn polygons
    - `meta_buildings`, `inspectables`: Scene metadata lists
    - `flat_pad_heights`: Pre-computed terrace elevation map
    - `config`: `pipeline/config.py` module
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any


def discover_and_run_heroes(context: dict[str, Any]) -> list[str]:
    """Auto-discover and run all `pipeline/heroes/*.py` modules implementing `build_hero(context)`."""
    heroes_dir = Path(__file__).resolve().parent
    pipeline_dir = str(heroes_dir.parent)
    if pipeline_dir not in sys.path:
        sys.path.insert(0, pipeline_dir)

    executed: list[str] = []
    for mod_path in sorted(heroes_dir.glob("*.py")):
        if mod_path.name.startswith("_"):
            continue
        mod_name = f"heroes.{mod_path.stem}"
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, "build_hero", None) or getattr(mod, "build", None)
        if callable(fn):
            fn(context)
            executed.append(mod_path.stem)
    return executed


__all__ = ["discover_and_run_heroes"]
