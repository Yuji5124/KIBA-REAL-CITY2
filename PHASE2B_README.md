# KIBA PARK REBUILD — Phase 2B

Phase 2B output is isolated from Phase 1 and 2A. It uses read-only Phase 1/2A and raw OSM/DEM inputs. DEM values are copied into a 1 m scene mesh with source labels: `dem17_median3x3` (measured raster median) and `idw_dem17_power2` (derived fill for DEM NoData). No raw DEM pixel is edited. Bridge deck elevations are an inferred linear profile between Phase 2A bridge endpoints and are separated from ground-route grades.

## Rebuild (Windows PowerShell)

```powershell
$root = 'C:\Users\hp\Desktop\KIBA-REAL-CITY'
$phase2b = Join-Path $root 'scripts\phase2b'
Set-Location $root
python "$phase2b\analyze_phase2b.py" --source-root $root --output-root $root
python "$phase2b\build_phase2b.py" --source-root $root --output-root $root --spacing 1.0
python "$phase2b\verify_phase2b.py" --source-root $root
node "$phase2b\build_phase2b_viewer.mjs"
python -m http.server 8775 --bind 127.0.0.1 --directory "$root\build-phase2b"
```

Open `http://127.0.0.1:8775/web/phase2b/`. Use the checkbox to show/hide interpolated vertices. Orbit with left-drag, pan with right-drag, and zoom with the wheel. The server serves only the Phase 2B build directory. The viewer uses local Three.js files and no paid service.

## Interpretation

Road corridors are resampled at 0.5 m, Catmull–Rom centerlines are terrain-sampled, widths taper at the park/terrain boundary, and ground surfaces have a measured 0.08 m rendering clearance to reduce Z-fighting. Out-of-boundary sections are omitted and logged rather than extended. The 0.08 m offset is a render construction value; it is not an OSM or survey measurement. Abrupt local grades are retained and flagged for gameplay review rather than smoothed into altered measured terrain.
