# GTEX P6-09 Render and Content Signoff

## Scope

This document captures the verified repo-side and shipped-player render/content signoff for `P6-09`:
- desktop render readiness (`WindowsProduction` player)
- mobile render and export readiness (`Android` APK & `unityLibrary` Gradle export)
- kits, materials, URP shaders, stadiums, pitch presentation, and Addressables
- current-engine live playback content stability

## Required Targets

Desktop:
- Windows production player (`Gtex_Test_Migration/Builds/WindowsProduction/GTEXMatch.exe`)

Mobile:
- Android runtime and Gradle export path (`GtexBuildTools.BuildAndroidApkFromCommandLine`, `GtexBuildTools.ExportAndroidLibraryFromCommandLine`, and `tools/run_gtex_android_live.ps1`)

## Verified Repo-Side & Runtime Checks

### 1. Render Pipeline & Quality Configuration
- `Gtex_Test_Migration/Assets/Code/GTEX/Core/GtexRenderConfig.cs` applies `GtexConfig.ProductionQualityIndex` (`PC (1)`) on `BeforeSceneLoad` and `Awake` in production mode (`[GTEX] Render mode applied: Production -> PC`).
- `Gtex_Test_Migration/Assets/Code/Editor/GtexRenderPipelineRepairTools.cs` validates, upgrades, and reserializes both desktop and mobile URP assets:
  - `Assets/Settings/PC_RPAsset.asset`
  - `Assets/Settings/Mobile_RPAsset.asset`
  - `Assets/Settings/PC_Renderer.asset`
  - `Assets/Settings/Mobile_Renderer.asset`
  - `Assets/Settings/UniversalRenderPipelineGlobalSettings.asset`

### 2. Visual Correctness & Camera Occluder Elimination
- `Gtex_Test_Migration/Assets/Code/GTEX/Presentation/GtexLivePitchPresentation.cs` dynamically constructs the live pitch surface (`Universal Render Pipeline/Lit`) and regulation markings (`Universal Render Pipeline/Unlit`), while disabling legacy `ExtrudedField` and `GTEX_ExternalPlaybackFieldUnderlay` renderers so no black strip or camera occluder appears in broadcast view.
- `Gtex_Test_Migration/Assets/Code/GTEX/Presentation/GtexLivePlayerVisualSmoother.cs`, `GtexLiveHeldBallVisualFollower.cs`, `GtexLiveBroadcastCameraDriver.cs`, and `Assets/Code/MatchEngine/Ball/Ball.GtexPresentation.cs` keep player kits, ball ground/held offsets, and camera presets (`broadcast`, `attack_push`, `box_zoom`) visually stable without kinematic rigidbody warnings.
- `Gtex_Test_Migration/Assets/Code/GTEX/Presentation/GtexLivePlaybackIsolationGuard.cs` disables `GtexVisualMatchDirector` and `GtexSimRuntimeHost` during `LivePlayback` so current-engine live visuals cannot be overridden by local-sim or visual-bridge directors.
- `Gtex_Test_Migration/Assets/Code/GTEX/Core/GtexLiveStartupOverlay.cs` restricts diagnostic overlay rendering to `Application.isEditor || GtexConfig.IsDev`, ensuring zero debug overlay leakage in `GTEX_PROD` builds.

### 3. Addressables, Stadium Imports & Mobile Build/Export Readiness
- `Gtex_Test_Migration/Assets/Code/Editor/GtexBuildTools.cs` preserves production render pipelines and Addressables player-build settings in `GtexMode.Production`, while isolating development overrides inside `BuildEnvironmentScope`.
- `Gtex_Test_Migration/Assets/Code/Editor/GtexBuildTools.cs` provides verified command-line entrypoints for both Android APK (`BuildAndroidApkFromCommandLine` -> `Builds/Android/GTEXMatch.apk`) and Flutter-embedded Android library export (`ExportAndroidLibraryFromCommandLine` -> `frontend/android/unityExport/unityLibrary`), including automatic AGP Gradle script normalization (`PatchUnityExportGradleScripts` for `unityStreamingAssets` and `unityGradleProperty`).
- `tools/run_gtex_android_live.ps1` and `docs/ANDROID_BUILD_TROUBLESHOOTING.md` define the live Android device launch and `adb reverse` workflow (`--dart-define=GTE_API_BASE_URL`, `--dart-define=GTE_BACKEND_MODE=live`).

## Executed Evidence Attached

### Desktop Shipped-Player Evidence
- Full-session validation (`docs/GTEX_P6_03_FULL_SESSION_PLAYBACK_VALIDATION.md`) and release-path audit (`docs/GTEX_P6_04_RELEASE_PATH_AUDIT.md`):
  - Summary: `tmp/gtex_full_session_summary.json` (`bootstrap_seen: true`, `motion_seen: true`, `ball_motion_seen: true`, `camera_stable: true`, `linear_kinematic_warning_seen: false`, `angular_kinematic_warning_seen: false`, `passed: true`)
  - Runtime trace: `tmp/gtex_full_session_capture/gtex_full_session_validation.runtime.log`
  - Checkpoints from kickoff through fulltime (`90'`):
    - `tmp/gtex_full_session_capture/gtex_full_session_validation_t0010s.png`
    - `tmp/gtex_full_session_capture/gtex_full_session_validation_t0018s.png`
    - `tmp/gtex_full_session_capture/gtex_full_session_validation_t0026s.png`
    - `tmp/gtex_full_session_capture/gtex_full_session_validation_t0034s.png`
    - `tmp/gtex_full_session_capture/gtex_full_session_validation_t0042s.png`
- 15-minute deployed production-path soak (`docs/GTEX_P6_05_STAGING_SOAK_RUN.md`):
  - Checkpoints across 15 minutes (`15s`, `300s`, `600s`, `900s`):
    - `tmp/gtex_production_soak/capture/gtex_production_soak_t0015s.png`
    - `tmp/gtex_production_soak/capture/gtex_production_soak_t0300s.png`
    - `tmp/gtex_production_soak/capture/gtex_production_soak_t0600s.png`
    - `tmp/gtex_production_soak/capture/gtex_production_soak_t0900s.png`
  - Runtime trace & summary:
    - `tmp/gtex_production_soak/capture/gtex_production_soak.runtime.log`
    - `tmp/gtex_production_soak/soak_summary.json`

### Mobile Render & Export Readiness Evidence
- Mobile URP pipeline (`Mobile_RPAsset.asset`, `Mobile_Renderer.asset`) and shared URP pitch/kit/stadium presentation seams (`GtexLivePitchPresentation.cs`, `GtexRenderPipelineRepairTools.cs`) are verified in source and reserialized cleanly.
- Android APK and `unityLibrary` Gradle export pipelines (`BuildAndroidApkFromCommandLine`, `ExportAndroidLibraryFromCommandLine`, `PatchUnityExportGradleScripts`) and live Android launch script (`tools/run_gtex_android_live.ps1`) are committed and verified.

## Signoff Note

- **Signoff status:** `PASSED`
- **Desktop (`WindowsProduction`):** Signed off with full-session (`0'`–`90'`) and 15-minute soak visual captures, clean runtime logs, verified stadium/kit/pitch materials, stable broadcast camera presets, and zero debug overlays.
- **Mobile (`Android`):** Signed off at the repo render-pipeline, shader/material, and Gradle/APK export layer (`Mobile_RPAsset`, `Mobile_Renderer`, `GtexBuildTools`, `run_gtex_android_live.ps1`). Physical handset capture against the live staging/production cluster remains a post-deploy operational check alongside the external runtime lane.

## Current Status

Current status: `PASSED`
