# KIBA PARK DRIVE · Phase D1 validation

Result: **PASS**

## Checks

- PASS · source_blend_hash_matches_read_only_inspection
- PASS · source_blend_read_only_flag
- PASS · separate_gltf_exists_and_header_valid
- PASS · gltf_mesh_count_matches_inspection
- PASS · phase3a_copied_into_separate_d1
- PASS · course_a_24m_and_same_road
- PASS · course_a_nav_walkable_only
- PASS · course_a_not_bridge_or_stairs
- PASS · swept_body_inside_modeled_path
- PASS · swept_body_avoids_tree_trunks
- PASS · swept_body_avoids_osm_water_and_buildings
- PASS · max_course_grade_below_12pct
- PASS · all_bridge_run_nav_still_has_zero_walkable
- PASS · phase2c_nav_data_matches_source_and_phase3a
- PASS · javascript_syntax_ok
- PASS · python_syntax_ok
- PASS · browser_screenshot_saved

## Course A measured/modelled values

- OSM way 777288664; 24.00m route; modeled width 3.999m (inferred, unsurveyed).
- Tayo envelope 2.72m wide × 4.52m long; measured model wheelbase 2.40m; forward axis Blender −Y.
- Sampled plan radius ≥9.32m; estimated steering need 14.4° versus prototype max 16°.
- 2D swept-body lateral reserve in the modeled corridor: 0.362m; maximum sampled terrain grade 5.33%.
- The clearance is computed from a Phase 2B inferred road width, not an on-site measurement; the route is a gameplay prototype, not real-world access approval.

## Mode separation

- Bridge navigation remains 13 runs and 0 walkable bridge segments.
- The Phase 3A battle mode remains copied into D1 and uses its existing Phase 2C navigation; D1 driving is restricted to A test course.

## Incomplete

- B/C remain disabled. Their candidate ways have narrower modeled widths or review segments; no whole-vehicle swept-envelope validation has been performed.
- Tayo asset contains no steering-angle or turning-radius specification; runtime steering is an explicitly estimated prototype parameter.
- Browser and screenshot checks complete after playtest; performance figures must be sampled live in the same viewport.
