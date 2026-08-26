# GTEX 3D Phase 1 Vertical Slice - Asset Inventory & Origin / Licensing Report

## Asset Strategy Compliance
- Zero purchased assets were introduced during Phase 1.
- All visual, audio, shader, and stadium assets utilize existing project assets, procedural generation, standard Unity built-ins, or free/open-licensed assets.

---

## Asset Inventory

### 1. Stadium & Pitch Assets
- **`Resources/GTEX/FreeAssets/Stadium/SoccerField.fbx`**
  - **Origin:** Free open-license stadium geometry asset included in project template.
  - **License:** Free/Open-license (Royalty-Free).
  - **Usage:** Stadium structure and stands representation.
- **Procedural Pitch Markings & Turf:**
  - **Origin:** Generated procedurally in runtime via `GtexPitchZoneHelper` / `GtexStadiumAtmosphere`.
  - **License:** GTEX Original Code / Procedural.
- **`Resources/GTEX/Shaders/GtexFieldLineOverlay.shader`**
  - **Origin:** Custom Unity URP HLSL Shader written for GTEX.
  - **License:** GTEX Proprietary / Internal.

### 2. Player Models & Rigging
- **Humanoid Rigs & Outfield/Goalkeeper Meshes:**
  - **Origin:** Existing project player models under `Assets/Arts/` and `Assets/ThirdParty/`.
  - **License:** Royalty-Free / Project Internal.
  - **Animation Strategy:** Humanoid rig with Unity Mecanim animation blending (Idle, Walk, Jog, Sprint, Turning, Pass, Shoot, Tackle, Celebration).

### 3. Crowd Representation
- **`Resources/GTEX/FreeAssets/Crowd/Characters/character-a.fbx` through `character-r.fbx`**
  - **Origin:** Free low-poly crowd character pack.
  - **License:** Free/Open-license (Royalty-Free).
  - **Usage:** Animated crowd members in stadium stands with bobbing/cheering logic in `GtexStadiumAtmosphere.cs`.

### 4. Audio & SFX Assets
- **`mixkit_police_short_whistle.wav`**
  - **Origin:** Mixkit free audio library.
  - **License:** Mixkit Free License (Commercial & Non-Commercial Use Allowed).
  - **Usage:** Referee short whistle cues.
- **`mixkit_ambient_sports_crowd.wav`**
  - **Origin:** Mixkit free audio library.
  - **License:** Mixkit Free License.
  - **Usage:** Ambient background crowd loop.
- **`mixkit_crowd_at_the_stadium.wav`**
  - **Origin:** Mixkit free audio library.
  - **License:** Mixkit Free License.
  - **Usage:** Match event crowd accent loop.
- **`mixkit_huge_crowd_cheering_victory.wav`**
  - **Origin:** Mixkit free audio library.
  - **License:** Mixkit Free License.
  - **Usage:** Goal celebration and final whistle cheer SFX.

---

## Summary
No asset purchases were requested or required. All Phase 1 requirements were met cleanly within free and open-licensed asset parameters.
