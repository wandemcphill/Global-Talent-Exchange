# GTEX Visual Quality Bar

> **Browser Launch Match vs. Desktop Unity 3D Runtime (2026-11-14):**
> - **Browser Launch Match (Canonical Web App):** The React WebGL 2D orthographic pitch in `frontend/react-shell/src/match2d` (`OrthographicPitch.tsx`, `Pitch2DView.tsx`, `matchStateAdapter.ts`, `playerRig.ts`) is the canonical browser launch match experience, driven by authoritative backend snapshots and spectator WebSocket streams. Perspective Three.js 3D (`MatchPitchLiveScene`) is an optional mode behind `match_3d_gameplay`.
> - **Desktop Unity 3D Runtime:** The sections below govern the standalone Unity desktop engine (`Gtex_Test_Migration` / `GTEX_OriginalVisualRuntime`), where `GTEX_OriginalVisualRuntime` + `VisualBridge` is the canonical FM23-class 3D desktop path.

Status: **locked**

## Product bar (Unity Desktop 3D Runtime)

Matchday 3D in the Unity desktop runtime must look and play at least like **Football Manager 23**:

- real 3D pitch and players
- ball travel with pass / shot / keeper action
- broadcast-style camera
- football movement from the original simulator systems

Not FIFA photorealism. Not Flutter canvas / 2.5D markers.

## Canonical visual runtime matrix

| Surface | Role |
|---|---|
| React WebGL 2D (`frontend/react-shell/src/match2d`) | **Canonical browser launch match** (orthographic WebGL pitch, procedural sprites, tactical/spatial overlays, Canvas 2D fallback) |
| Unity `Assets/Scenes/GTEX_OriginalVisualRuntime.unity` | **Only** FM23-class broadcast 3D desktop path |
| `Assets/Code/GTEX/VisualBridge/` | Only GTEX → original-sim Unity integration seam |
| Flutter match center 2D pitch | Tactical / phone companion only |
| `Gtex_MainScene` live transform playback | Legacy Unity ship path until OVR replaces it |

## Rules

1. Do not ship 2.5D / pseudo-3D as the product match visual.
2. Do not drive OVR with per-frame `DrivePlayers` / `DriveBall` transform playback.
3. Prefer native original-simulator football AI for visual quality (`NativeAutonomousPlay`).
4. Use high-level visual commands only when GTEX must author outcomes (goals, score, scripted acceptance).
5. Keep `GtexScoreAuthority` as the single score source.
6. Preserve Windows batchmode build stability.

## How to open the quality bar scene

1. Open Unity project `Gtex_Test_Migration` (Editor `6000.3.12f1`).
2. Open `Assets/Scenes/GTEX_OriginalVisualRuntime.unity`.
3. Confirm `GtexVisualMatchDirector` is present.
4. Press Play — original simulator camera, players, ball, and AI should run.
5. Optional: set `GTEX_RUNTIME_MODE=original-visual` or use `Resources/GTEX/match-config.original-visual.json` values when bootstrapping outside the scene override.

## Verification

Run **Tools → GTEX → Runtime → Verify Original Visual Runtime** in the Unity Editor, or invoke `FStudio.GTEX.Editor.GtexOriginalVisualRuntimeVerifier.VerifyFromCommandLine` with Unity `-batchmode`, `-projectPath`, and a `-logFile`. The verifier exits the Editor when finished; do not add `-quit` or `-nographics`.

```text
Unity.exe -batchmode -projectPath <Gtex_Test_Migration> -executeMethod FStudio.GTEX.Editor.GtexOriginalVisualRuntimeVerifier.VerifyFromCommandLine -logFile <verifier-log-path>
```

The verifier runs four sections:

- **A. Editor no-backend:** confirms the original visual scene boots and advances without a backend.
- **B. Scripted replay:** checks the wide-cross/save and central-buildup/goal sequences, command ordering, reset-after-goal, and score change.
- **C. Local sim feed:** checks the original visual runtime against the local simulation feed.
- **D. Live backend feed:** checks a scripted local HTTP feed, expected match commands and score, and isolation from the legacy live/simulation runtime hosts.

Reports are written to `Gtex_Test_Migration/tmp/original-visual-runtime-verification/<stamp>/report.md`, with screenshots and console output alongside the report.

## Acceptance for visual quality

- Kickoff looks like the original football simulator, not sliding puppets
- Pass, dribble, shot, and keeper saves use original APIs / AI
- Camera follows broadcast football, not a fixed top-down board
- No Flutter 2.5D demo route remains in the product app

## Anti-fight seams (must hold in Play mode)

1. `MatchManager.SetExternalPlayback(true)` is refused in OVR
2. `GtexOriginalVisualIsolationGuard` disables live `GtexMatchRuntime` in OVR
3. Native AI goals promote into `GtexScoreAuthority` (no second scoreboard writer)
4. Command-driven scoring does not double-count native `GoalEvent` increments
5. `scriptOnPitchEvents` stays `false` for the FM23 look path
