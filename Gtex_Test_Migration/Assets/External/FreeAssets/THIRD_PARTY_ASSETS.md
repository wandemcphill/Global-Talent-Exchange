# Third-Party Free Assets

Downloaded on: 2026-04-12

This folder contains free external assets imported for GTEX live/match presentation.
Keep this file updated if any asset here is replaced, removed, or moved.

## Models

### Stadium

- Asset: Soccer Field
- Source page: https://opengameart.org/content/soccer-field
- Download file: https://opengameart.org/sites/default/files/soccer_field.zip
- License: CC0
- Imported path: `Assets/External/FreeAssets/Models/Stadium/Soccer Field.fbx`
- Runtime mirror: `Assets/Resources/GTEX/FreeAssets/Stadium/SoccerField.fbx`
- Notes: Lightweight low-poly field with bleachers/seating. Suitable as a fallback or mobile-friendly stadium shell.

### Crowd characters

- Asset: Blocky Characters
- Source page: https://opengameart.org/content/blocky-characters
- Download file: https://opengameart.org/sites/default/files/kenney_blocky-characters_2.0.zip
- License: CC0
- Imported path: `Assets/External/FreeAssets/Models/Crowd`
- Runtime mirror: `Assets/Resources/GTEX/FreeAssets/Crowd/Characters`
- Notes: Package includes multiple formats and skins. For Unity, prefer the FBX set under `Assets/External/FreeAssets/Models/Crowd/Models/FBX format`.

## Audio

### Referee whistle

- Asset: Police short whistle
- Source page: https://mixkit.co/free-sound-effects/sports/
- Download file: https://assets.mixkit.co/active_storage/sfx/615/615.wav
- License: Mixkit Sound Effects Free License
- License page: https://mixkit.co/license/
- Imported path: `Assets/External/FreeAssets/Audio/mixkit_police_short_whistle.wav`
- Runtime mirror: `Assets/Resources/GTEX/FreeAssets/Audio/mixkit_police_short_whistle.wav`

### Crowd ambience

- Asset: Ambient sports crowd sound
- Source page: https://mixkit.co/free-sound-effects/sports/
- Download file: https://assets.mixkit.co/active_storage/sfx/2097/2097.wav
- License: Mixkit Sound Effects Free License
- License page: https://mixkit.co/license/
- Imported path: `Assets/External/FreeAssets/Audio/mixkit_ambient_sports_crowd.wav`
- Runtime mirror: `Assets/Resources/GTEX/FreeAssets/Audio/mixkit_ambient_sports_crowd.wav`

- Asset: Crowd at the stadium
- Source page: https://mixkit.co/free-sound-effects/sports/
- Download file: https://assets.mixkit.co/active_storage/sfx/2111/2111.wav
- License: Mixkit Sound Effects Free License
- License page: https://mixkit.co/license/
- Imported path: `Assets/External/FreeAssets/Audio/mixkit_crowd_at_the_stadium.wav`
- Runtime mirror: `Assets/Resources/GTEX/FreeAssets/Audio/mixkit_crowd_at_the_stadium.wav`

### Crowd cheer

- Asset: Huge crowd cheering victory
- Source page: https://mixkit.co/free-sound-effects/sports/
- Download file: https://assets.mixkit.co/active_storage/sfx/462/462.wav
- License: Mixkit Sound Effects Free License
- License page: https://mixkit.co/license/
- Imported path: `Assets/External/FreeAssets/Audio/mixkit_huge_crowd_cheering_victory.wav`
- Runtime mirror: `Assets/Resources/GTEX/FreeAssets/Audio/mixkit_huge_crowd_cheering_victory.wav`

## Integration notes

- These assets were added in an isolated `Assets/External/FreeAssets` tree to avoid colliding with existing GTEX art/audio.
- Runtime-loaded copies live under `Assets/Resources/GTEX/FreeAssets` so batch/player builds can load them through `Resources.Load`.
- The Kenney crowd pack already ships with an included `License.txt` confirming CC0.
- GTEX runtime integration now happens in `Assets/Code/GTEX/GtexStadiumAtmosphere.cs`.
- No prefabs, scenes, or addressables were authored in this pass.
- Review import settings in Unity before shipping, especially compression, mesh scaling, animation import, and audio load type.
