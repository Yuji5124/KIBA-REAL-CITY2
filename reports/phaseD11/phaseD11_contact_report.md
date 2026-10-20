# KIBA PARK DRIVE Phase D1.1 — tire/ground contact

## Result

The live browser test completed the A-course outbound run, checkpoint turnaround, reverse return, and `GOAL · Aコース往復完了`. Four wheel contact values remained within **3.0 cm** of the rendered OSM road surface during the observed test. Steering input was applied while the bus was coasting at the mid-course sample.

## Cause and correction

Phase D1 positioned the bus from the route centerline height plus a fixed offset. On a sloped or cross-falling road patch, that does not place each tire over its local surface, so one end or side of the body could sink while another floated.

D1.1 reads the four wheel contact nodes from the existing GLB scene (`Wheel_FL`, `Wheel_FR`, `Wheel_RL`, `Wheel_RR`). Each frame it samples the visible OSM A-course road triangles at those four world positions, fits the bus vertical position, pitch, and roll to the sampled support plane, and retains a 12 mm clearance. The underlying terrain, road, navigation, and GLB are unchanged. DEM heights are shown alongside the road contact values as a difference diagnostic; the DEM is not used to edit either surface.

Model inspection: the GLB scene is approximately **4.52 m long × 2.72 m wide × 2.695 m high**, with **2.40 m wheelbase** and **1.72 m track**. The imported GLB uses local +Z as forward; the source Blender model used local −Y as forward before export. Wheel local offsets are FL (−0.86, 0, +1.17), FR (+0.86, 0, +1.17), RL (−0.86, 0, −1.23), RR (+0.86, 0, −1.23) metres, relative to the imported bus origin. Contacts are read after the GLB scene transforms, so the solver uses the displayed model's actual transformed wheel-node bounds.

For comparison, the offline D1 centerline-height placement analysis at the start estimated wheel residuals of FL **−3.8 cm**, FR **−2.4 cm**, RL **+2.1 cm**, and RR **+2.2 cm**. This is a pre-fix calculation, not a live browser measurement. D1.1's live start residuals are in the table below.

## Live browser readings

| Location / state | FL | FR | RL | RR | Pitch | Roll |
|---|---:|---:|---:|---:|---:|---:|
| Start | +0.9 cm | +1.5 cm | +1.5 cm | +0.9 cm | +1.3° | −0.3° |
| Mid-course after steering | +0.3 cm | +2.1 cm | +2.1 cm | +0.3 cm | +1.3° | −0.5° |
| Reverse, station 10.2 m | +3.0 cm | −0.6 cm | −0.6 cm | +3.0 cm | +0.4° | +1.2° |
| GOAL | +1.7 cm | +0.7 cm | +0.7 cm | +1.7 cm | +2.4° | −2.7° |

Negative residuals indicate a wheel sample just below the road support plane; the largest observed penetration is 0.6 cm. The positive values are clearance. This is a geometric wheel-contact fit, not a tire/suspension simulation.

At the start, displayed DEM differences were FL 10.7 cm, FR 13.9 cm, RL 9.4 cm, RR 8.6 cm. These represent an existing DEM-versus-rendered-road difference. No elevation correction was applied to terrain or roads.

## Render metrics observed in browser

- FPS: 37.5–60.1; readings were predominantly 60.1. The 37.5 reading was transient.
- Draw calls: 147–158.
- Triangles: 615,344–617,170.
- Meshes: 81.

## Screenshots

- Before: `screenshots/phaseD11/d11_before.png`
- After, start: `screenshots/phaseD11/d11_after_start.png`
- After, mid-course: `screenshots/phaseD11/d11_midcourse.png`
- After, turnaround: `screenshots/phaseD11/d11_turnaround.png`
- After, return/GOAL: `screenshots/phaseD11/d11_return.png`

The before/after captures are canvas captures; the live browser HUD and contact residuals were also inspected separately through the browser accessibility state.

## Integrity and verification

- Phase D1 app hash is unchanged from the D1.1 baseline.
- The original `Tayo_bus.blend` SHA-256 still matches Phase D1's inspection record.
- D1.1 GLB is byte-identical to D1's GLB.
- Phase 2C navigation JSON and Phase 2B terrain/road scene JSON are unchanged.
- The 13 bridge runs remain in their existing blocked/unverified state.
- The executable validation result is recorded in `phaseD11_validation.json` and `phaseD11_validation.md`.

## Regenerate and run (Windows PowerShell)

From `C:\Users\hp\Desktop\KIBA-REAL-CITY`:

```powershell
python .\scripts\phaseD1\build_phaseD1.py
python .\scripts\phaseD11\build_phaseD11.py
python -X utf8 .\scripts\phaseD11\verify_phaseD11.py
python .\scripts\phaseD11\serve_phaseD11.py
```

Open `http://127.0.0.1:8786/web/phaseD11/`. Stop the local server with `Ctrl+C` before rebuilding on Windows.
