# GTEX 3D Campus Model Library Manifest (Phase 2.1 WebGL)

- **Coordinate System:** Right-handed `Y`-up (`+Y` vertical, `X`/`Z` horizontal campus grid).
- **Origin Point:** `center-bottom (0.0, 0.0, 0.0)` aligned to ground elevation `Y = 0`.
- **Scale Contract:** `1.0` scene unit = `1` authoritative backend grid tile (`24 × 18` campus grid).
- **Footprint Conformance:** All 28 models are strictly bounded within their `(W × D)` grid tile footprint with zero adjacent-tile overhang.
- **Master vs. Production Exports:** High-segment master files reside in `public/models/campus/masters/*.master.glb`; optimized runtime exports reside in `public/models/campus/*.glb`.

| Model Key | Category | Grid Footprint | BBox Span (X×Z×H) | Prod Vertices | Prod Triangles | PBR Materials | Prod Size |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `stadium_bowl_core` | `stadium_structures` | `6×5` | `5.68×4.68×2.063` | 5912 | 2872 | 10 | 166,640 B |
| `stadium_main` | `stadium_structures` | `6×5` | `5.68×4.68×2.063` | 6824 | 3328 | 11 | 191,956 B |
| `stadium_stand_expansion` | `stadium_structures` | `4×2` | `3.76×1.84×1.522` | 1324 | 648 | 7 | 41,020 B |
| `north_stand_expansion` | `stadium_structures` | `4×2` | `3.76×1.84×1.522` | 1716 | 816 | 7 | 51,436 B |
| `floodlight_pylon_array` | `stadium_structures` | `2×2` | `1.84×1.84×2.66` | 1572 | 772 | 7 | 47,704 B |
| `floodlight_tower` | `stadium_structures` | `2×2` | `1.84×1.84×2.66` | 1052 | 512 | 7 | 33,644 B |
| `vip_hospitality` | `club_headquarters` | `3×2` | `2.82×1.84×1.21` | 1172 | 540 | 5 | 35,240 B |
| `vip_skybox_concourse` | `club_headquarters` | `3×2` | `2.82×1.84×1.24` | 1544 | 744 | 7 | 46,840 B |
| `first_team_pitch_alpha` | `training_facilities` | `4×3` | `3.76×2.74×1.22` | 1340 | 652 | 8 | 42,092 B |
| `training_pitch` | `training_facilities` | `4×3` | `3.76×2.74×1.22` | 1364 | 664 | 9 | 43,440 B |
| `first_team_pitch_beta` | `training_facilities` | `4×3` | `3.72×2.765×1.03` | 1580 | 772 | 10 | 49,960 B |
| `high_performance_centre` | `training_facilities` | `3×3` | `2.82×2.82×1.135` | 1816 | 852 | 8 | 54,720 B |
| `indoor_training_arena` | `training_facilities` | `4×3` | `3.76×2.76×1.225` | 1968 | 984 | 10 | 60,564 B |
| `recovery_hydro_hub` | `medical_facilities` | `3×3` | `2.82×2.82×0.855` | 986 | 486 | 10 | 33,976 B |
| `elite_academy_complex` | `academy_buildings` | `4×3` | `3.76×2.76×1.255` | 2560 | 1252 | 10 | 76,388 B |
| `academy_complex` | `academy_buildings` | `4×3` | `3.76×2.76×1.255` | 2658 | 1294 | 10 | 78,976 B |
| `academy_youth_pitch` | `academy_buildings` | `4×3` | `3.72×2.74×1.075` | 1292 | 628 | 10 | 42,208 B |
| `club_hq_operations` | `club_headquarters` | `3×2` | `2.82×1.98×1.586` | 1966 | 918 | 8 | 58,724 B |
| `club_hq` | `club_headquarters` | `3×2` | `2.82×1.98×1.586` | 1840 | 864 | 8 | 55,344 B |
| `executive_fleet_terminal` | `club_headquarters` | `3×2` | `2.82×1.84×0.855` | 1034 | 510 | 8 | 33,920 B |
| `construction_crane_site` | `construction_equipment` | `3×3` | `2.74×2.74×2.812` | 956 | 436 | 8 | 31,560 B |
| `stage_1_site_prep` | `construction_equipment` | `3×3` | `2.72×2.72×0.34` | 746 | 366 | 9 | 26,760 B |
| `stage_2_groundworks` | `construction_equipment` | `3×3` | `2.72×2.72×0.545` | 732 | 352 | 6 | 24,240 B |
| `stage_3_foundations` | `construction_equipment` | `3×3` | `2.72×2.72×0.703` | 1026 | 506 | 7 | 32,936 B |
| `stage_4_structural` | `construction_equipment` | `3×3` | `2.78×2.72×2.532` | 1106 | 546 | 9 | 36,524 B |
| `stage_5_finishing` | `construction_equipment` | `3×3` | `2.72×2.72×1.639` | 1314 | 650 | 8 | 41,400 B |
| `campus_tree_cluster` | `landscaping` | `1×1` | `0.84×0.84×0.677` | 1561 | 669 | 4 | 44,628 B |
| `campus_road_plaza_segment` | `roads_infrastructure` | `1×1` | `0.96×0.96×0.25` | 270 | 126 | 6 | 11,852 B |
