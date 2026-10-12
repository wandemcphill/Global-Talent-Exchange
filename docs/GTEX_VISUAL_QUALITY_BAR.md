# GTEX Visual Quality Bar

Status: **locked**

## Product bar

Matchday 3D must look and play at least like **Football Manager 23**:

- real 3D pitch and players
- ball travel with pass / shot / keeper action
- broadcast-style camera
- football movement from the original simulator systems

Not FIFA photorealism. Not Flutter canvas / 2.5D markers.

## Canonical visual runtime

| Surface | Role |
|---|---|
| Unity `Assets/Scenes/GTEX_OriginalVisualRuntime.unity` | **Only** FM23-class broadcast 3D path |
| `Assets/Code/GTEX/VisualBridge/` | Only GTEX → original-sim integration seam |
| Flutter match center 2D pitch | Tactical / phone companion only |
| `Gtex_MainScene` live transform playback | Legacy ship path until OVR replaces it |

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
