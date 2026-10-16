GTEX Unity Repro Notes
======================

Unity version
- 6000.3.12f1

Render pipeline
- URP
- Evidence:
  - Gtex_Test_Migration/ProjectSettings/QualitySettings.asset has customRenderPipeline set
  - Gtex_Test_Migration/ProjectSettings/GraphicsSettings.asset has URP global settings mapped

Packages / runtime systems in use
- Cinemachine: not found in Packages/manifest.json or Assets/Code usage
- NavMeshAgent: package com.unity.ai.navigation is present, but no NavMeshAgent runtime usage was found in Assets/Code
- Rigidbody: yes
  - MatchEngine/Ball/Ball.cs
  - MatchEngine/Players/PlayerController/CodeBasedController.cs
- Animator root motion: no explicit applyRootMotion / OnAnimatorMove usage found; movement appears code-driven
- DOTS / ECS: not found

Exact scene to open
- Gtex_Test_Migration/Assets/Scenes/Gtex_MainScene.unity

2-3 steps to reproduce
1. Open Gtex_Test_Migration/Assets/Scenes/Gtex_MainScene.unity in Unity 6000.3.12f1.
2. From the repo root, run:
   powershell -ExecutionPolicy Bypass -File tools/run_gtex_full_session_validation.ps1
3. Let the shipped Windows player complete the mocked full session, then inspect:
   - tmp/gtex_full_session_summary.json
   - tmp/gtex_full_session_capture/gtex_full_session_validation.runtime.log
   - tmp/gtex_full_session_capture/gtex_full_session_validation.gif

Scripts that seem to own the main systems

Match clock / score
- Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs
  - consumes MatchResponse.clockMinute / homeScore / awayScore
  - calls GtexMatchController.MatchManagerAdapter.ApplyExternalLiveState(...)
- Gtex_Test_Migration/Assets/Code/MatchEngine/MatchManager.cs
  - ApplyExternalLiveState(float clockMinute, int homeScore, int awayScore, MatchStatus matchStatus)
  - stores minutes, homeTeamScore, awayTeamScore

Player movement
- Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs
  - primary live-state consumer and external playback driver
- Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexLegacyPlayerHandle.cs
  - applies external animator state and instant position / rotation to bound legacy players
- Gtex_Test_Migration/Assets/Code/MatchEngine/Players/PlayerController/CodeBasedController.cs
  - low-level transform / rigidbody controller used by players

Ball movement
- Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs
  - computes live ball intent and calls GtexMatchController.BallAdapter.ApplyExternalState(...)
- Gtex_Test_Migration/Assets/Code/MatchEngine/Ball/Ball.cs
  - owns ball rigidbody state and external playback application

Camera
- Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs
  - ApplyLiveCameraPreset(...) maps cameraPreset from MatchResponse
- Gtex_Test_Migration/Assets/Code/MatchEngine/Camera/CameraSystem.cs
  - owns actual SwitchCamera(...) behavior and smoothing
- Gtex_Test_Migration/Assets/Code/MatchEngine/MatchManager.cs
  - ApplyExternalPlaybackCamera() forces Broadcast on external playback start

Console errors / warnings seen
- No hard exceptions were recorded in the latest full-session validation run.
- Current repeatable warning/noise:
  - repeated transport warnings after fulltime in tmp/gtex_full_session_capture/gtex_full_session_validation.runtime.log
  - message: WS closed by remote peer (1000): fulltime. reconnect=True
- Earlier smoke logs also showed repeated:
  - "No callbacks found for typeof FStudio.MatchEngine.Events.MatchCameraActiveEvent"
  - source: tmp/gtex_live_player_smoke.log

Expected vs actual
- Expected:
  - live playback should bootstrap, run from kickoff to fulltime, then settle cleanly once the terminal frame is reached
  - no repeated reconnect attempts after the match is already fulltime
- Actual:
  - the current-engine live path now does complete a full mocked session with moving players, moving ball, score progression, and camera preset changes
  - after the terminal fulltime frame is applied, the runtime still retries websocket reconnects and logs repeated fulltime transport warnings until shutdown

Attached visual
- GIF created from the latest captured full-session checkpoints:
  - tmp/gtex_full_session_capture/gtex_full_session_validation.gif
- Source screenshots:
  - tmp/gtex_full_session_capture/gtex_full_session_validation_t0012s.png
  - tmp/gtex_full_session_capture/gtex_full_session_validation_t0024s.png
  - tmp/gtex_full_session_capture/gtex_full_session_validation_t0042s.png
