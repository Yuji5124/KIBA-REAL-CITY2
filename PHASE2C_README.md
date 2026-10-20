# KIBA PARK REBUILD Phase 2C

Phase 2C adds a separate robot navigation/collision ribbon over the Phase 2B scene. Its bounded DEM reconciliation does not alter the render terrain or raw inputs. Bridges are separate review-only decks; mapped steps, water crossings, out-of-bound geometry, narrow corridors, and unresolved terrain gaps are blocked.

## Windows PowerShell

Run from the clone root (`C:\Users\hp\Desktop\KIBA-REAL-CITY`):

```powershell
$root = (Get-Location).Path
$phase2c = Join-Path $root 'scripts\phase2c'
python (Join-Path $root 'scripts\build_phase2c.py') `
  --source-root $root --output-root $root
python (Join-Path $phase2c 'verify_phase2c.py')
node (Join-Path $phase2c 'build_phase2c_viewer.mjs')
Set-Location (Join-Path $root 'build-phase2c')
python -m http.server 8776
```

Open `http://127.0.0.1:8776/web/phase2c/`. Use the **移動テスト** button for the swept robot test, WASD/arrow keys for manual motion, and **移動面デバッグ** to toggle status overlays. To rebuild after changing the source, stop the HTTP server with Ctrl+C and rerun the build commands from the clone root.

## Coordinate and safety rules

- Coordinates use the Phase 2B EPSG:6677 local metre frame (`+Y` up).
- Ground navigation heights follow the Phase 2B terrain plus a per-station DEM1A adjustment capped at 0.12 m and one constrained smoothing pass.
- The 13 bridge runs use Phase 2B endpoint interpolation as inferred deck height and remain review-only.
- Mapped stairways and the 22 omitted/missing segments are not traversable; the missing segments never create connecting geometry.
- The browser proxy uses a 0.28 m radius, 0.65 m body height, 0.16 m step limit, 2 m/s speed, and 0.08 m movement probes. Review zones are traversable but counted separately.

This prototype uses sampled ribbon collision checks rather than a full rigid-body physics engine. Inspect bridge heights and review-colored sections against survey data before production gameplay use.
