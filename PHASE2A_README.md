# KIBA PARK REBUILD — Phase 2A

Phase 2A creates a separate terrain-and-path dataset and a Three.js viewer. Phase 1 and raw files are read-only inputs. Measured DEM heights remain unchanged; the 92 NoData vertices are separately tagged and interpolated from measured neighbors using inverse-distance weighting (power 2). The 143 Phase 1 path ways are clipped to the park boundary, split into 146 in-park runs, smoothed, and emitted as terrain-following ribbons.

## Regenerate on Windows PowerShell

From the `KIBA-REAL-CITY` project root in Windows PowerShell:

```powershell
python scripts\phase2a\build_phase2a_data.py --source-root 'C:\Users\hp\Desktop\KIBA-REAL-CITY'
python scripts\phase2a\verify_phase2a.py
node scripts\phase2a\build_phase2a_viewer.mjs
python -m http.server 8771 --bind 127.0.0.1 --directory .\build-phase2a
```

Open `http://127.0.0.1:8771/web/phase2a/`. Stop the server with Ctrl+C. Python uses only its standard library plus the existing Phase 1 builder; Node copies local vendored Three.js files. No paid services or network download are used.

## Diagnostics

`data/processed/phase2a/phase2a_report.json` records DEM NoData causes and coordinates, interpolation method and neighbor distances, measured-height difference, road widths/runs/triangles, terrain clearance, fallbacks, and terrain face counts. The browser HUD measures live FPS, draw calls, rendered triangles, and mesh count. The debug checkbox toggles interpolated vertices.

Terrain edge fallback samples are counted separately because path ribbons near the boundary may extend beyond the triangulated park surface. The reported 6 cm clearance is the emitted ribbon vertex offset at its terrain sample, not a physical field survey. Browser performance varies by hardware and browser.
