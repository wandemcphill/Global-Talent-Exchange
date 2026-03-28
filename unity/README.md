# GTEX Unity Match Runtime

This folder adds a Unity-side runtime that consumes the existing Flutter `SCENE_SYNC` payload from `frontend/lib/models/match_3d_scene_graph.dart` and `frontend/lib/services/match_3d_bridge.dart`.

## What is included

- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchSceneBootstrap.cs`
  Creates the scene hierarchy at runtime if you drop a single `MatchSceneBootstrap` object into an empty scene.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchController.cs`
  Orchestrates scene sync, event-triggered animation changes, camera focus, and replay recording.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/PlayerController.cs`
  Handles player interpolation, animator state changes, side colors, possession/highlight visuals.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/BallController.cs`
  Handles ball interpolation, shot orientation, and spin.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/CameraController.cs`
  Applies broadcast, tactical, and cinematic rigs from Flutter.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/ReplayRecorder.cs`
  Records live runtime frames and prepares highlight clips.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/ReplayPlayer.cs`
  Rewinds, pauses, replays, loops, and supports slow motion.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/FlutterUnityBridge.cs`
  Entry point for JSON forwarded from the Flutter host/native shell.

## Scene shape

At runtime the bootstrapper creates:

```text
MatchScene
|- Pitch
|- Ball
|- Players
|- Cameras
|- Lighting
`- MatchController
```

If you already have authored prefabs, you can keep the same hierarchy and replace the generated primitives with your own meshes.

## Unity setup

1. Copy `unity/Assets/GtexMatch3D` into your Unity project `Assets/` folder.
2. Create a new empty scene.
3. Add an empty root object named `MatchScene`.
4. Add `MatchSceneBootstrap` to that root object.
5. Press Play once.

The bootstrapper will generate a plane pitch, a sphere ball, a camera rig, lighting, and a disabled player prototype used for cloning.

## Flutter to Unity handoff

The Flutter app already builds a payload with:

- `type: "SCENE_SYNC"`
- `camera`
- `action`
- `entities`
- optional `matchEvent`

Unity expects that payload as JSON and exposes:

- `FlutterUnityBridge.HandleMessage(string json)`
- `FlutterUnityBridge.HandleSceneSync(string json)`
- `FlutterUnityBridge.HandleMatchEvent(string json)`

### Recommended host bridge

From the native shell that embeds both Flutter and Unity:

1. Receive the `Map<String, dynamic>` from the Flutter `MethodChannel`.
2. Encode it to JSON.
3. Forward it into Unity with a direct bridge call or `UnitySendMessage`.

Example target:

```csharp
bridgeGameObject.SendMessage("HandleSceneSync", jsonPayload);
```

## Motion-capture pipeline

Use Humanoid rigs and keep the runtime state names aligned with the default bindings in `PlayerController`.

### Recommended clip set

- `idle`
- `run`
- `sprint`
- `receive`
- `pass`
- `shoot`
- `tackle`
- `celebrate`
- `intercept`
- `recover`

### Import flow

1. Download clips from Mixamo.
2. Clean root motion and scale in Blender.
3. Export FBX.
4. In Unity, set `Rig -> Humanoid`.
5. Create an Animator Controller with states matching the names above, or change the `animationBindings` array on `PlayerController`.
6. Add a movement blend tree driven by a `speed` float if you want finer locomotion.

The runtime will set:

- `speed` float, if present
- `highlighted` bool, if present
- `hasPossession` bool, if present

## Replay behavior

`ReplayRecorder` stores player, ball, and camera state every synced frame. On `goal`, `save`, and `miss`, it buffers a highlight window and hands a finished clip to `ReplayPlayer`.

Available controls on `ReplayPlayer`:

- `Play(ReplayClip clip, bool loop, float playbackSpeed, bool slowMotion)`
- `Pause()`
- `Resume()`
- `Stop()`
- `Rewind()`
- `SetPlaybackSpeed(float value)`
- `SetSlowMotion(bool enabled)`

With `useGlobalTimeScale` enabled, slow motion applies `Time.timeScale = 0.35`.

## Notes

- The generated scene uses primitives only; replace them with authored assets once your Unity project is wired.
- The runtime is schema-aligned to the current Flutter scene graph contract rather than inventing a second event format.
- No Unity compile/test pass was run here because this repo is not a Unity project and the editor/runtime is not present in the workspace.
