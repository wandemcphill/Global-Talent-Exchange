# GTEX cinematic gifting — asset inventory and licence notes

The gift renderer now favours existing authored GLB assets. It does not generate substitute Eiffel towers, runways, crowns, crowds, trophy supports, player silhouettes, goal frames, or floating geometry when those models are missing.

## Authored assets reused from the existing GTEX product

| Gift scene | Existing model path |
| --- | --- |
| City / architecture reveal | `public/assets/showroom/royal_penthouse_box.glb` |
| Maracanã / stadium reveal | `public/assets/showroom/arena_imperiale_stadium.glb` |
| Golden stadium | `public/assets/showroom/golden_stadium.glb` |
| Private jet | `public/assets/showroom/sovereign_900x_jet.glb` |
| Superyacht | `public/assets/showroom/superyacht.glb` |
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

- The current city scene uses GTEX's existing royal penthouse architecture model. There is not yet a dedicated, authored Paris landmark / skyline model in the React public asset library.
- Dedicated boot and goalkeeper-glove hero models are not yet present in that library; those catalogue codes currently use the existing trophy-stage asset until proper models are commissioned or approved.
- The match scene uses the existing authored stadium, goal frame, football and Mixamo player. It intentionally does not invent a crowd made of capsule meshes or a goal net made from primitive geometry.

A missing model should be shown as a controlled loading/error state or replaced only by another approved, visually appropriate asset. Do not introduce placeholder cones, capsules, toruses, low-poly crowns, or fake landmarks to fill the gap.
