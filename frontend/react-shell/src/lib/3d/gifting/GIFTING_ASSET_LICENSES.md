# GTEX cinematic gifting — asset inventory and licence notes

The gift renderer now favours existing authored GLB assets. It does not generate substitute Eiffel towers, runways, crowns, crowds, trophy supports, player silhouettes, goal frames, or floating geometry when those models are missing.

## Authored assets reused from the existing GTEX product

| Gift scene | Existing model path |
| --- | --- |
| City / architecture reveal | `public/assets/showroom/royal_penthouse_box.glb` |
| Maracanã / stadium reveal | `public/assets/showroom/arena_imperiale_stadium.glb` |
| Golden stadium | `public/assets/showroom/golden_stadium.glb` |
| Private jet | `public/assets/showroom/sovereign_900x_jet.glb` |
| Gulfstream jet | `public/assets/showroom/gulfstream_g700_exec_jet.glb` |
| Superyacht | `public/assets/showroom/superyacht.glb` |
| Team coach / bus | `public/assets/showroom/vanguard_xii_coach.glb` |
| Executive SUV | `public/assets/showroom/executive_suv.glb` |
| Hypercar | `public/assets/showroom/veloce_gt9_hypercar.glb` |
| Performance campus / facility | `public/assets/showroom/apex_performance_campus.glb` |
| Award / trophy | `public/assets/showroom/trophy_plinth.glb` |
| Crown / watch | `public/assets/showroom/chronos_tourbillon_watch.glb` |
| Match stadium | `public/models/match/football-stadium.glb` |
| Goal frame | `public/models/match/goal_frame.glb` |
| Match ball | `public/models/match/football_pbr.glb` |
| Footballer rig and kit | `public/models/footballer/gtex_home_kit_mixamo.glb` |
| Footballer animation clips | `public/models/footballer/gtex_mixamo_clips.glb` |

These are existing GTEX product assets, not new external models introduced by this code change. Their authoritative licence/provenance records remain with the original asset packages and must be retained there; this inventory does not make a new licence claim for those showroom GLBs.

## Environment lighting

The gift renderer loads existing environment maps for image-based lighting and metallic reflections:

- `public/textures/env/modern_buildings_night_2k.hdr` — city and award scenes.
- `public/textures/env/kloofendal_43d_clear_puresky_2k.hdr` — private jet and yacht scenes.
- `public/textures/env/stadium_01_1k.hdr` — football and stadium scenes.

The Poly Haven environment assets are CC0 1.0. Poly Haven licence: https://polyhaven.com/license. Additional source manifest: `assets/incoming/free-3d/SOURCES.md`.

## Mixamo animation licence

The footballer rig/kit and baked Mixamo clips are based on Adobe Mixamo exports. Adobe's Mixamo terms allow use in commercial games; raw FBX downloads are not redistributed. The source manifest is `assets/incoming/free-3d/SOURCES.md`.

## Known asset gaps — do not fake these with primitives

- City-specific landmark/skyline models for Paris, New York, Rio, Lagos, Tokyo and Dubai are not yet present in the React public asset library. Those gift codes use a clean atmospheric reveal rather than pretending the generic royal-penthouse model is a landmark. The royal-penthouse GLB is reserved for a penthouse/property gift.
- Dedicated crown, golden-boot and goalkeeper-glove hero models are not yet present. Those gifts currently use a clean, asset-free cinematic light/particle reveal and lower-third; they do not borrow a trophy or watch model.
- Player-card and tactics-board catalogue gifts also use the restrained atmosphere treatment until proper authored art is available.
- The Chronos Tourbillon watch gift uses its matching watch model. A generic crown/tactics gift does not.
- The match scene uses the existing authored stadium, goal frame, football and Mixamo player. It intentionally does not invent a crowd made of capsule meshes or a goal net made from primitive geometry.

A missing model should be shown as a controlled loading/error state or replaced only by another approved, visually appropriate asset. Do not introduce placeholder cones, capsules, toruses, low-poly crowns, or fake landmarks to fill the gap.
