# Phase 2F validation report

## Scope and preservation

Phase 2F was created in its own `data/processed/phase2f`, `reports/phase2f`, `scripts/phase2f`, `build-phase2f`, and `screenshots/phase2f` paths. The existing raw OSM/DEM, Phase 1–2E outputs, G6.2 source, KIBA-REAL-CITY-main, and Blender scenes were read-only. No Blender MCP operation was available in this session, so the bridge surface was built as a separate Three.js mesh. The new deck group is rendered independently and is not referenced by the robot navigation or collision functions.

## Geometry and coordinate checks

OSM way `33976871` contains three continuous nodes and measures 174.289m in the Phase 1 EPSG:6677 project frame. Phase 2C provides two clipped runs: 319 segments and 132.836m of centerline. The run endpoints around the park-boundary exclusion are `[79.289, 2.616, -186.457]` and `[78.065, 2.140, -203.021]` in the project-local Three.js convention (X east, Y estimated elevation, Z negative north). Their direct distance is 16.609m, matching the Phase 2B reported 16.616m gap within 7mm of rounding/sampling. This is a park-boundary clipping gap, not a broken raw OSM way.

The candidate adds a visual amber span across that interval. It uses linear interpolation between the adjacent Phase 2C estimated endpoint heights: 2.616m to 2.140m, a -0.476m change (about 2.87% over 16.609m). Both values are estimated bridge heights, not measured bridge deck elevations. All other candidate segments follow the unchanged Phase 2C centerline and estimated elevations. A 0.06m rendering offset is used to prevent surface overlap; it is not structural clearance.

The candidate shows 149.445m in total: the existing clipped 132.836m plus the gap. The full OSM way includes roughly 24.844m outside the Phase 2C displayed runs, which is left out because there is no validated terrain or robot navigation surface there. Japan Concrete Institute's archive reports 250m overall length and 96.95m maximum span. Therefore another 100.555m of the documented overall structure is outside this candidate and remains unresolved. The candidate width of 4.0m is a visual working estimate, not a surveyed or locally tagged width. The surface mesh contains 640 top triangles in two rendered groups (mapped surface and amber gap); it has no underside, railing, joints, or independently validated foundations.

The G6.2 GLB bounds are X 73.868–89.600m, Y 0–60m, Z -236.018–-47.979m. About 76.18% of Phase 2C center-start stations fall inside the GLB's X/Z bounding rectangle. This is only a rough footprint overlap check. The Phase 2E identity placement remains a visual hypothesis: its scene metadata axis conflicts with vertex layout and no survey control point validates position, orientation, or elevation. The existing Phase 2E report notes 27 visual-only meshes and no deck mesh. Phase 2F leaves those meshes untouched.

## Robot and rendering checks

The 24.0m browser movement test passed with 326 swept probes on OSM way `777288664`. It still reports stairs BLOCK, slopes over 35% BLOCK, omitted gap BLOCK, and boundary BLOCK. The bridge deck candidate remained outside the spatial navigation index. The dedicated OSM bridge gap records in Phase 2C remain `status=blocked` and `autoConnected=false`; the data verifier checks that the gap has no Phase 2C bridge segment across its midpoint. The movement test does not claim that a robot crossed the bridge.

The in-app browser at `http://127.0.0.1:8779/web/phase2f/` rendered the top, bridge, side, and robot views. A one-second top-view HUD sample showed:

| View | FPS | Draw calls | Triangles | Meshes |
|---|---:|---:|---:|---:|
| Phase 2E comparison | 60.1 | 53 | 599,740 | 51 |
| Phase 2F candidate | 60.1 | 55 | 600,380 | 53 |
| Change | 0.0 | +2 | +640 | +2 |

FPS varies with hardware, browser scheduling, camera, and vegetation LOD. It is an observed browser reading, not a stable benchmark.

Saved PNGs are actual WebGL canvas captures from the browser:

- `screenshots/phase2f/phase2e_before_top.png`
- `screenshots/phase2f/phase2f_top.png`
- `screenshots/phase2f/phase2f_bridge.png`
- `screenshots/phase2f/phase2f_side.png`
- `screenshots/phase2f/phase2f_robot.png`

## Unresolved before traversal

1. Survey control points are needed to settle G6.2 origin, axis, rotation, scale, and deck elevations.
2. The full documented 250m alignment needs route geometry beyond OSM way 33976871; its branches and approaches cannot be inferred safely from the present data alone.
3. The 4m width and linearly interpolated gap profile need measurements or authoritative design drawings.
4. Deck thickness, parapets/railings, drainage, expansion joints, structural supports, collision shape, and clearance over road/water are absent.
5. Bridge approaches must be connected to verified ground paths with continuous game-grade slope and step checks. The current gap stays blocked in the robot graph.

## External references

- [Japan Concrete Institute archive: Kiba Park Bridge](https://www.jci-net.or.jp/photo_60/archive/detail_db.php?id=168&page=6) — completed 1991, 250m overall, maximum span 96.95m, two-span continuous prestressed-concrete cable-stayed bridge.
- [Tokyo Metropolitan Park Association: Kiba Park](https://www.tokyo-park.or.jp/park/kiba/index.html) — park layout and bridge context.
- [Tokyo Metropolitan Park Association: barrier-free park map](https://www.tokyo-park.or.jp/park/kiba/assets/files/kiba_bf.pdf) — bridge and district context.
- [Kiba Park bridge photograph (CC BY-SA 4.0)](https://commons.wikimedia.org/wiki/File:Kiba_Park_bridge_view.jpg) — visual reference only, not a dimensional survey.
