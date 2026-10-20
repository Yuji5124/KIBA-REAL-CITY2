# KIBA PARK REBUILD Phase 2D

Phase 2D adds low-poly trees, shrubs, grass tufts, and OSM groundcover areas to a separate viewer. The Phase 2B terrain and Phase 2C movement layer load unchanged. `mappedTrees` contains OSM point positions; `estimatedTrees` is explicitly divided by aerial-photo canopy heuristic and synthetic distribution inside OSM woodland polygons.

## Windows PowerShell

Run from the clone root (`C:\Users\hp\Desktop\KIBA-REAL-CITY`):

```powershell
$root = (Get-Location).Path
$phase2d = Join-Path $root 'scripts\phase2d'
python (Join-Path $root 'scripts\build_phase2d.py') `
  --source-root $root --output-root $root
python (Join-Path $phase2d 'verify_phase2d.py') $root
node (Join-Path $phase2d 'build_phase2d_viewer.mjs')
Set-Location (Join-Path $root 'build-phase2d')
python -m http.server 8777
```

Open `http://127.0.0.1:8777/web/phase2d/`. **ロボット視点** follows the proxy, **上空視点** shows the park and supports orbit/zoom, and **24m移動テスト** repeats the Phase 2C swept collision checks. Use `移動判定レイヤーを表示` to reveal the walkable/review/blocked overlays.

The tree batches use 4 low-poly shape/color variants, instancing, near/far geometry LOD (180 m / 520 m) and hide beyond 520 m. Grass tufts and shrubs also have view-distance cutoffs. The raw imagery tiles cover only a portion of the park; photo-derived candidates are heuristic estimates, not tree detections or measured positions.

For OSM attribution see the source data metadata: © OpenStreetMap contributors, ODbL 1.0. Aerial photos are existing GSI seamlessphoto tiles. No paid service or external API is used by the build or viewer.
