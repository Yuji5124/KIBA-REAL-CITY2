# Phase D1 browser playtest

Local browser run at `http://127.0.0.1:8785/web/phaseD1/` visibly loaded the exported Tayo GLB over the park scene. W accelerated the bus, D steered during travel, the outbound checkpoint changed to RETURN, and S braked/reversed along the A test route. Returning to the start at zero speed displayed `GOAL · Aコース往復完了`.

The C camera toggle showed chase and elevated park views. The separate Phase 3A combat button restored the player/enemy HP HUD; an attack reduced enemy HP from 100 to 66. This verifies that D1 kept the copied combat mode separate from driving.

A manual steering/throttle run stayed on the A ribbon without triggering an off-road stop. This does not prove the safety stop against a deliberately forced off-road trajectory; static validation checks the bus footprint at sampled points along the modeled A corridor. B/C stay disabled. Phase 2C confirms all 13 bridge runs still contain zero walkable segments.

## Live render samples

| Browser state | FPS | Draw calls | Triangles | Meshes |
|---|---:|---:|---:|---:|
| Drive, chase/road view | 60.1 | 156 | 616,444 | 81 |
| Drive, moving | 60.1 | 155 | 616,254 | 81 |
| Battle, after attack | 60.1 | 143 | 542,412 | 81 |

Counts vary with view and vegetation LOD. These are viewport samples, not hardware-independent benchmark results.

## Screenshots

- `screenshots/phaseD1/d1_drive_start.png`
- `screenshots/phaseD1/d1_overview.png`
- `screenshots/phaseD1/d1_battle_mode.png`
