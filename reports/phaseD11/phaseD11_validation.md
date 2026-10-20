# KIBA PARK DRIVE · Phase D1.1

Result: **PASS**

## Checks

- PASS · d1_unchanged_from_d11_baseline
- PASS · source_blend_hash_still_matches
- PASS · glb_identical_to_d1
- PASS · phase2c_nav_unchanged
- PASS · phase2b_terrain_and_roads_unchanged
- PASS · gltf_valid_and_contains_138_meshes
- PASS · contact_solver_reads_four_glb_wheel_nodes
- PASS · contact_solver_samples_road_triangles_and_dtm
- PASS · roundtrip_and_collision_logic_retained
- PASS · javascript_syntax_ok
- PASS · python_syntax_ok
- PASS · after_fix_browser_screenshots_saved
- PASS · browser_forward_reverse_turn_goal_test_recorded

## Wheel-contact method

For each frame, sample the actual two-triangle OSM A-course road surface at the four GLB-derived tire contact points; fit bus pitch, roll, and vertical position to those four heights. DEM grid height is also recorded for comparison.

- GLB SHA-256 unchanged from D1: `3a235439cb7ca539e8ebaad697ed6ad8bedfbf3d455a66e7b29899417a517457`.
- Source blend SHA-256 unchanged: `23b11189142e2cf09bf7fa94e6e1ecdab35388f3859d2603d370ef25e90eda2b`.
- D1 files, Phase 2J terrain/road elevations, and Phase 2C navigation remain unchanged.
- Browser screenshots:
- `d11_after_start.png`
- `d11_before.png`
- `d11_before_overview.png`
- `d11_midcourse.png`
- `d11_return.png`
- `d11_turnaround.png`

## Browser drive test

- A-course forward, steering, reverse, and GOAL were confirmed in the live browser.
- Maximum observed absolute tire-to-road residual: **3.0 cm**.
- FPS observed: **37.5–60.1** (mostly 60.1); draw calls **147–158**; triangles **615,344–617,170**; meshes **81**.
- Estimated road-to-DEM difference is shown per wheel in DEV HUD; DEM was not used to alter terrain or road geometry.
