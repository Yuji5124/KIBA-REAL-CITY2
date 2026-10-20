# KIBA PARK REBUILD Phase 2E

Phase 2E adds the existing G6.2 pylon and cable model as a visual-only layer in an isolated copy of the Phase 2D viewer. Phase 2C's navigation data is copied unchanged. The 13 bridge runs stay review/blocked; the GLB never participates in collision or movement checks.

## Windows PowerShell

Run from the clone root (`C:\Users\hp\Desktop\KIBA-REAL-CITY`). The source GLB is read from the sibling `KIBA-REAL-CITY-main` project and is never modified. The generated copy has unrelated secret metadata removed.

```powershell
$root = (Get-Location).Path
$g62 = 'C:\Users\hp\Desktop\KIBA-REAL-CITY-main\output\Kiba_Park_Ohashi_G6.2_visual_details.glb'
$phase2e = Join-Path $root 'scripts\phase2e'
python (Join-Path $root 'scripts\build_phase2e.py') `
  --source-root $root --output-root $root --g62-glb $g62
python (Join-Path $phase2e 'verify_phase2e.py') $root
node (Join-Path $phase2e 'build_phase2e_viewer.mjs')
Set-Location (Join-Path $root 'build-phase2e')
python -m http.server 8778
```

Open `http://127.0.0.1:8778/web/phase2e/`. The page provides **上空視点**, **橋梁地上視点**, **ロボット視点**, and the existing 24 m movement check.

## Registration limits

The GLB reports EPSG:6677 and the same projected local origin as Phase 2B. Its mesh coordinates are already Y-up and align with the Phase 2B local metre positions, so the candidate viewer transform is identity (0 m translation, 0° rotation, 1× scale). However, the GLB scene metadata describes Z-up axes, which conflicts with its mesh layout. Treat this as a visual registration pending a surveyed control-point check.

For reporting projected coordinates, Phase 2B uses `E = E0 + X` and `N = N0 - Z`. The two pylon centers therefore convert to approximately `(-2226.318, -35974.717)` and `(-2214.318, -35974.717)` in EPSG:6677; these are transformed model positions, not survey measurements.

The GLB contains two pylons, one crossbeam, and 24 simplified stays (27 meshes, 356 triangles); it contains no deck surface. OSM way `33976871` has two Phase 2C ribbons totaling 132.90 m with a 16.62 m gap, and their inferred Y elevations range from 1.568 to 4.940 m. The model's cable geometry spans 188.04 m in plan and overlaps 76.01% of the ribbon stations by its bounding rectangle. Because there is no modeled deck to sample, deck-height agreement cannot be confirmed. The Phase 2C ribbon remains inferred and review-only.

The matching G6.2 `.blend` was not present in the source output folder; the existing GLB was inspected directly. The viewer is offline after build and uses no paid API or service. OSM and GSI attribution remain in the Phase 2D source data.
