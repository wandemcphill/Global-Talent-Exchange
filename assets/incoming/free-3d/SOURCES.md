# Free 3D assets staged for GTEX

Downloaded 9 Nov 2026. The stadium, the Poly Haven skies, and the baked Mixamo clips are wired into the React match. Raw downloads stay in this folder and are not committed.
Commercial use is allowed. Credit is not required. Keep this note with the files.

## Stadium

- File: `stadium/football-stadium.glb` (11,560,540 bytes)
- Source: https://www.innerscene.com/tools/library/3d-parts/football-stadium-f7b93967
- Licence: CC0 1.0, stated inside the GLB by Innerscene Corp
- Measured: 32,644 triangles, 19 meshes, 21 textures, 209.2 x 38.47 x 169.2 m
- Seats are a textured bowl (`Blue stadium seat rows`), not one mesh per chair
- The live match hides Grass, Pitch, Goals, Dugouts, Perimeter boards, and Roof trusses. The GTEX 105 x 68 pitch stays.

## Poly Haven lighting and surfaces

- Licence: CC0 1.0, https://polyhaven.com/license
- HDRIs, 2k: `polyhaven/hdr/`
  - overcast_industrial_courtyard
  - industrial_sunset_02
  - modern_buildings_night
  - concrete_tunnel
  - kloofendal_43d_clear_puresky
- 1k PBR maps: `polyhaven/textures/`
  - concrete_wall_001
  - concrete_floor_02
  - metal_plate
  - box_profile_metal_sheet
  - asphalt_01
  - corrugated_iron
- Each texture set has diffuse, normal, roughness, and ambient occlusion. Metal maps are included where Poly Haven publishes one.
- Poly Haven has no photographic glass texture in this set. Glass stays a material setting.

## Quaternius characters

- Zip: `quaternius/Universal Base Characters[Standard].zip` (128,968,391 bytes)
- Unpacked: `quaternius/universal-base-characters/`
- Source: https://quaternius.itch.io/universal-base-characters
- Licence file: `License_Standard.txt`, CC0 1.0
- The free zip contains Superhero male and female bodies, hair, and eyebrows.
- Regular and Teen bodies are in the paid Source pack, which was not downloaded.

## Quaternius animations

- Zip: `quaternius/Universal Animation Library[Standard].zip` (15,904,933 bytes)
- Unpacked: `quaternius/universal-animation-library/`
- Source: https://quaternius.itch.io/universal-animation-library
- Licence file: `License.txt`, CC0 1.0
- `UAL1_Standard.glb` has 43 generic clips. `UAL1_Standard_RM.glb` is the same set with root motion.
- These are idle, crouch, hit, and talk clips. They are not football contact moves.
- The larger Pro pack was not downloaded.

## Mixamo football clips

- Folder: `mixamo/` — 65 FBX files, 34,503,440 bytes
- Source: https://www.mixamo.com/ , exported 9 Nov 2026 on the X Bot character
- Licence: Adobe Mixamo. Commercial games are allowed. Do not redistribute the raw FBX files.
- Export settings: in place, no skin, 30 fps, FBX 2019 binary
- Every file starts with the Kaydara FBX Binary header
- Two Mixamo titles exist twice, so the second copy is numbered: `Juggling_Header_Of_A_Soccer_Ball_2.fbx` and `Goalkeeper_Left_Body_Block_2.fbx`
- Locomotion bridge: `Breathing_Idle.fbx`, `Walking_Forwards.fbx`, `Running_Forwards.fbx`
- Outfield set: spin, headers, tackles, falls, penalty, juggling, receive, idles, scissor, chip, throw-in, dribble, jog, and strafe
- Goalkeeper set: short and long placement, high and low catches, scoop, drop kick, diving saves, sidesteps, body blocks, throws, directing, and idle with and without the ball
- The raw FBX files stay here. The match plays the baked clip library at `frontend/react-shell/public/models/footballer/gtex_mixamo_clips.glb`.
- No further Mixamo titles were downloaded for the run-dribble, moving strike, standing tackle, or slumped reaction. Those four takes come from the Unity football FBX already in the repo, retargeted onto `mixamorig` bones with hip translation removed: `Gtex_Dribble_Run`, `Gtex_Strike`, `Gtex_Standing_Tackle`, `Gtex_Slump`. The rebaked library has 69 clips. Raw FBX was not copied into `mixamo/`.
- Goal celebration stays the existing Mixamo clip `Kicking_Up_A_Soccer_Ball`. The tunnel walk-off uses `Walking_Forwards`. The penalty clip `Male_Soccer_Penalty_Kick` plays only for a penalty. Contact phases for ball release are in `frontend/react-shell/src/lib/3d/broadcast/clipContact.json`.
- Licence reminder, also recorded in `frontend/react-shell/src/lib/3d/gifting/GIFTING_ASSET_LICENSES.md`: Adobe Mixamo allows commercial use. Do not redistribute the raw FBX.

## GT Mixamo footballer

- Source folder: `C:\Users\ayomc\Desktop\GT` (`MIXAMO RIG.glb` inside `MIXAMO+RIG.zip`)
- Copied to `frontend/react-shell/public/models/footballer/gtex_gt_mixamo_kit.glb`
- 65 joints named `mixamorig:Hips` and the rest of the Mixamo set, one skinned mesh, materials HEAD, TSHIRT, SHORT, HAND, LEG
- The kit file has no animation clips. Clips stay in `gtex_mixamo_clips.glb`.
- The 2D and 2.5D pitch samples `frontend/react-shell/public/models/footballer/atlas/` (body, kit, parts, and foot-anchor manifest). The procedural capsule atlas remains the fallback when that PNG is missing.

## Not downloaded

- Paid items were left for a later decision: the CGTrader player, the Player Motion 100-pack, and the Quaternius Source character pack.
