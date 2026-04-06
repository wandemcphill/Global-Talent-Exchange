# GTEX Unity Match Runtime

This folder adds a Unity-side runtime that consumes the existing Flutter `SCENE_SYNC` payload from `frontend/lib/models/match_3d_scene_graph.dart` and `frontend/lib/services/match_3d_bridge.dart`.

## What is included

- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchSceneBootstrap.cs`
  Creates the scene hierarchy at runtime if you drop a single `MatchSceneBootstrap` object into an empty scene.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchController.cs`
  Orchestrates scene sync, live-feed polling, event-triggered animation changes, camera focus, and replay recording.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/PlayerController.cs`
  Handles player interpolation, animator state changes, side colors, possession/highlight visuals.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/BallController.cs`
  Handles ball interpolation, shot orientation, and spin.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/CameraController.cs`
  Applies broadcast, tactical, and cinematic rigs from Flutter.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchOverlayController.cs`
  Draws the score, match clock, goal headline, and text event feed overlay.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/ReplayRecorder.cs`
  Records live runtime frames and prepares highlight clips.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/ReplayPlayer.cs`
  Rewinds, pauses, replays, loops, and supports slow motion.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/FlutterUnityBridge.cs`
  Entry point for JSON forwarded from the Flutter host/native shell.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchAPI.cs`
  Polling client for the backend live bridge at `/match/{id}/live`.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchLiveBridge.cs`
  Configurable backend to Unity poller that retries failures and keeps the last good state on screen.
- `unity/Assets/GtexMatch3D/Runtime/Scripts/MatchLiveModels.cs`
  Backend polling models: `MatchResponse`, `Event`, and `PlayerPosition`.

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
3. Add an empty root object named `MatchScene` and attach `MatchSceneBootstrap`.
4. Set `MatchController.backendBaseUrl` and `MatchController.matchId` if you want live-feed playback.
5. Press Play.

The bootstrapper will generate a plane pitch, a sphere ball, a camera rig, lighting, a text overlay, and a disabled player prototype used for cloning. In live-feed mode it also seeds 22 player capsules into a simple 4-3-3 vs 4-3-3 shape.

## Android SDK / External Tools

Unity Android builds depend on the Android Build Support module plus valid SDK, NDK, and JDK entries in `Edit > Preferences > External Tools`.

For the GTEX workspace on this machine:

- Flutter Android uses `C:\Users\ayomc\AppData\Local\Android\Sdk`
- `frontend/android/local.properties` already points `sdk.dir` there

If Unity is not using its bundled Android tools, point the Unity `Android SDK` field at that same SDK folder. The included editor helper `Assets/GtexMatch3D/Editor/GtexAndroidBuildTools.cs` can also copy `ANDROID_SDK_ROOT` or `ANDROID_HOME` into Unity's SDK preference when the current SDK path is missing.

## Build helpers

After importing the package into a real Unity project, use:

- `Tools > GTEX > Android > Configure SDK From Environment`
- `Tools > GTEX > Android > Validate External Tools`
- `Tools > GTEX > Android > Build APK`
- `Tools > GTEX > Android > Export Unity Library`

When the Unity project sits inside this GTEX repo layout, the Unity-library export defaults to `../frontend/android/unityExport`. Otherwise it falls back to the Unity project's own `Builds/Android/` folder.

## Live-feed playback

`MatchController` now supports a standalone polling mode for a basic Football Manager-style viewer.

- Primary path template: `/match/{id}/live`
- Fallback path template for this repo: `/api/match-engine/live-feed/{id}`
- Data source: `timeline_events`
- Supported visual beats:
  - `goal` / `goals` -> scorer animation, ball to goal, headline text
  - `shot` / `missed_chances` / `penalties` -> shot animation, ball toward goal
  - `assist` / `pass` -> pass animation, ball between two players

The live-feed path templates are serialized on `MatchController`, so you can point the scene at either the generic endpoint or the existing GTEX backend route without changing code.

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

## Direct backend polling

If you want Unity to talk to GTEX without going through the Flutter host bridge:

1. Add `MatchLiveBridge` to the same root object as `MatchSceneBootstrap`.
2. Set `matchId`.
3. Choose `Local`, `Production`, or `Custom` base URL in the inspector.
4. Leave polling at `1` second for the initial bridge.

`MatchLiveBridge` polls `GET /match/{matchId}/live`, retries with backoff on failures, and keeps rendering the last known good frame until the next successful response.

## GTEX Android integration

The Flutter/Android host now expects a Unity Android export under:

- `frontend/android/unityExport/unityLibrary`

Once that folder exists, Gradle conditionally includes `:unityLibrary` and GTEX launches Unity in a full-screen `UnityMatchActivity`.

Runtime flow:

- Flutter opens the native 3D session with `matchId` and `sessionId`
- Android launches Unity and forwards scene-sync JSON through `UnitySendMessage`
- Unity sends runtime events back into Android through `com.gtex.exchange.match3d.UnityBridgeCallback`
- `MatchController` stores the active `matchId` and ignores scene-sync frames for any other match

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
- No Unity compile/test pass was run here because this repo is not a full Unity project and the editor/runtime is not present in the workspace.
