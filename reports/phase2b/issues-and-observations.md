# Phase 2B findings and remaining work

## Input and fallback classification

- The 1,793 Phase 2A road probes that used terrain fallback were reconstructed exactly: 132 probes lie outside the park boundary, and 1,661 lie in park polygons but their Phase 2A 8 m terrain triangles touch outside/unresolved source vertices. Coordinates and probe classes are in `road_terrain_diagnostics.json`.
- This separates boundary clipping from coarse triangulation contamination. No raw DEM/OSM input was edited.
- The former 0.655 m / 0.928 m transition on way `1525352522` has Phase 2A endpoint DEM1A 3x3 medians of 0.92 m and 0.91 m (difference −0.01 m). The old coarse-mesh transition is therefore not supported by the endpoint DEM medians; the 8 m mesh interpolation was the likely source of that spike.

## Phase 2B terrain and robot-route grade review

- Phase 2B maximum ground-route transition is way `261322457`, XY `[170.076, -181.382]` to `[169.752, -181.354]` metres, 0.325 m apart, height change +0.263 m (80.8%). Exact endpoint DEM1A 3x3 medians are both 1.93 m, while each 3x3 window spans 1.02–2.16 m. Nearby 1 m terrain lattice medians include 2.15 m and 1.02 m.
- The point-sample medians do not support the 0.263 m change by themselves, while the neighboring DEM-derived lattice values do. The steep transition is thus a local raster/triangulation sampling ambiguity; it cannot be called a surveyed real slope or definitively dismissed as DEM noise. We retained the source values and flagged this transition for higher-resolution survey/robot playtest.
- There are 86 short ground-route transitions above 20% grade and 17 above 35%. These are review counts at 0.5 m path sampling, not accessibility determinations. The top Phase 2B transition and raw endpoint windows are embedded in `phase2b_report.json`.
- Bridges are split out: 13 runs use an inferred linear deck between Phase 2A endpoint heights, with maximum sampled deck grade 6.0%. These values are not DEM measurements and are excluded from ground-contact clearance.
- Widths taper at the park/terrain boundary. 372 path stations were trimmed; generated ribbon station widths are 1.10–5.50 m. 22 outside/untriangulated sections were split or omitted (coordinates in `phase2b_report.json`) rather than extended past the boundary.
- Ground ribbon vertices follow the same piecewise planar terrain sampler with a 0.08 m render clearance: the generated-vertex gap measured 0.08 m at every sampled ground ribbon vertex. This avoids surface overlap/Z-fighting at those vertices, but is not a physics collision sweep between vertices.

## Browser performance and unresolved work

The local browser displayed all park terrain. Warm live HUD state was 60.0 FPS, 8 draw calls, 525,352 triangles, 8 meshes, DPR 1.0. Phase 2A was 60.1/54.3 FPS, 7 draw calls, 25,465 triangles, 6 meshes. The terrain detail increased triangles by 20.63×; the observed FPS remained near 60 on this workstation. Screenshot capture can momentarily display 0 FPS because it pauses the animation loop.

For a robot-ready collision surface, review the 86 high-grade transitions with source imagery or a higher-resolution elevation survey. A separate gameplay/collision heightfield can then apply a bounded slope filter while preserving `dem17_median3x3` and `idw_dem17_power2` source elevations as immutable render/measurement layers. Recheck with swept-volume collision tests and field observations before lowering those flags.
