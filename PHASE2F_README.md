# KIBA PARK REBUILD Phase 2F

Phase 2F adds an isolated, render-only bridge-deck surface candidate to the Phase 2E viewer. It does not change Phase 2C movement/collision data.

## Regenerate and launch (Windows PowerShell)

Run in the clone root:

```powershell
$root = (Get-Location).Path
python (Join-Path $root 'scripts\phase2f\build_phase2f.py') --root $root
node (Join-Path $root 'scripts\phase2f\build_phase2f_viewer.mjs') $root
python (Join-Path $root 'scripts\phase2f\serve_phase2f.py')
```

Open `http://127.0.0.1:8779/web/phase2f/`. Use **上空視点**, **橋梁地上視点**, **橋梁側面**, and **ロボット視点**. Press **画面PNG保存** in each view to save into `screenshots\phase2f`. The isolated Phase 2E comparison copy is at `http://127.0.0.1:8779/web/phase2e-before/`.

After opening the viewer and capturing the listed screenshots, run:

```powershell
python (Join-Path $root 'scripts\phase2f\verify_phase2f.py') $root
python -m py_compile (Join-Path $root 'scripts\phase2f\build_phase2f.py') (Join-Path $root 'scripts\phase2f\verify_phase2f.py') (Join-Path $root 'scripts\phase2f\serve_phase2f.py')
node --check (Join-Path $root 'scripts\phase2f\build_phase2f_viewer.mjs')
```

## Output files

- Candidate surface data: `data\processed\phase2f\bridge_deck_candidate.json`
- Validation data: `reports\phase2f\phase2f_validation.json`
- Validation narrative: `reports\phase2f\phase2f_validation.md`
- Viewer build: `build-phase2f\web\phase2f`
- Comparison-only Phase 2E viewer copy: `build-phase2f\web\phase2e-before`
- Screenshots: `screenshots\phase2f`

The local server writes PNGs only to a short allowlist of Phase 2F filenames under that screenshot folder and binds to localhost.

## Evidence and limits

OSM way `33976871` is continuous through three OSM nodes; Phase 2C clips it into two in-park runs. The new amber segment only fills the visual 16.609m gap between those runs. Both its heights are interpolated estimates. The surface width is a 4m visual estimate; the 6cm offset separates it from the existing ribbon for rendering and does not represent physical clearance. The candidate is a surface mesh without structural underside or railings.

The mapped OSM way is about 174.289m, while the engineering archive reports 250m overall bridge length. Phase 2F displays about 149.445m of candidate deck (132.836m of existing clipped Phase 2C centerline plus the visual gap). About 100.555m of the documented overall bridge length remains unmodeled; the OSM portion outside Phase 2C's clipped runs is also omitted. No unsupported approach extension is generated.

G6.2 is included by Phase 2E's identity-transform visual hypothesis. Its scene metadata says Z-up while vertex layout looks Y-up, and no surveyed registration control was available. Bounding-box station overlap is a coarse overlap indicator, not a coordinate-accuracy result. The candidate is never enabled for robot collision or traversal.

All generation and browser viewing are local and use no paid service or API.
