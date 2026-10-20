# Kiba Park Phase 1 data pipeline and Three.js viewer

This phase reads the existing split OSM XML and GSI DEM PNGs without modifying the raw inputs. It writes a deduplicated, local-coordinate scene JSON and a static Three.js viewer. No paid service or runtime network access is required.

## Windows PowerShell

Run from the project root:

```powershell
python scripts\phase1\build_phase1_data.py
python scripts\fetch\verify_phase1_data.py
node scripts\phase1\build_viewer.mjs
python -m http.server 8765 --bind 127.0.0.1 --directory build
```

Open `http://127.0.0.1:8765/web/phase1-threejs/`. Stop the server with `Ctrl+C`.

Use `--source-root` and `--output-root` if the project is in a different location. Python 3.10+ and a modern browser with WebGL are recommended. The viewer loads only local files.

## Data and coordinates

- EPSG:6677 (JGD2011 / Japan Plane Rectangular CS IX); local origin matches the project's KPR coordinate definition.
- Three.js axes: `x=east (m)`, `y=T.P. elevation (m)`, `z=-north (m)`.
- GSI DEM 1A is sampled first; DEM 5A is used as fallback. No-data cells inside the park are marked red. Cells outside the park mask are omitted.
- OSM © OpenStreetMap contributors, ODbL 1.0. GSI elevation PNGs are retained as local input data. Three.js is vendored locally with its upstream `LICENSE`.
- The incorporated upstream project is [three.js](https://github.com/mrdoob/three.js), used for the browser renderer and orbit controls; its repository identifies the MIT license. The Blender GIS candidates were reviewed for later workflows; no paid add-on, account, or online elevation service is part of this build.

## Current build validation

The generated `data/processed/phase1_threejs/validation_report.json` records the per-run validation. The converter reports duplicate OSM IDs removed, tag conflicts, dangling node/relation references, all DEM tile decode counts, in-park terrain gaps, coordinate origin residual, and extracted feature counts.
