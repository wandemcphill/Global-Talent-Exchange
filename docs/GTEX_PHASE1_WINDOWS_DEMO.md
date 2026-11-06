# GTEX Phase 1: Windows 3D Demonstration Runbook & Visual QA Package

This guide details the complete, reproducible Windows demonstration package for the GTEX Unity 3D match runtime (Phase 1 vertical slice). It documents the authoritative backend-driven render-sync architecture, prerequisite validation, deterministic match provisioning, standalone Unity player launch, and visual evidence capture protocols.

---

## 1. Non-Negotiable Engineering Protection Compliance

In strict compliance with the **GTEX Non-Negotiable Engineering Protection Policy**:
- **Player Universe Locked**: The canonical database of real players, regens, and legends remains untouched. No player records are inserted, modified, re-imported, backfilled, or merged.
- **No Synthetic Records**: Test fixtures use deterministic, non-persisted in-memory models or isolated development fixtures. No synthetic players are introduced into the real database.
- **No Duplicate Architecture**: Reuses the authoritative match engine (`tools/run_gtex_live_backend.py`), the canonical provisioning mechanisms (`tools/provision_gtex_live_match_windows.py` and `tools/provision_gtex_live_match.py`), and the existing Unity runtime scenes and shaders.
- **Evidence Integrity**: All demonstration evidence must be captured from a live, executing standalone Windows runtime session. No visual claims are made without verified physical recording or screenshots.

---

## 2. Exact Windows Prerequisites

To run and capture the demonstration on Windows:

| Requirement | Specification | Verification Command |
|---|---|---|
| **Operating System** | Windows 10 or Windows 11 64-bit (Build 19041+) | `[System.Environment]::OSVersion.Version` |
| **GPU & Display** | DirectX 11 or 12 capable GPU / integrated graphics (Intel HD Graphics 620+, NVIDIA, AMD) with active desktop session | `dxdiag /t tmp/dxdiag.txt` |
| **PowerShell** | Windows PowerShell 5.1 or PowerShell Core 7+ | `$PSVersionTable.PSVersion` |
| **Python** | Python 3.11 – 3.14 on `PATH` or at `.venv\Scripts\python.exe` | `python --version` |
| **Backend Dependencies** | Installed via repository root virtual environment | `pip list` or `uv pip list` |
| **Unity Editor (for rebuilds)** | **Unity 6 `6000.3.12f1`** (`6000.3.12f1 (fca03ac9b0d5)`) | Installed under `C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe` |
| **Network / Ports** | Port `8000` available for local FastAPI backend | `Test-NetConnection 127.0.0.1 -Port 8000` |
| **Standalone Build** | Windows player compiled under `Gtex_Test_Migration\Builds\WindowsProduction` | `Test-Path .\Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe` |

---

## 3. Unity Build Target, Scenes & Architecture

### Target & Version
- **Target Platform**: `StandaloneWindows64`
- **Unity Version**: `6000.3.12f1` (Revision `fca03ac9b0d5`)
- **Scripting Backend**: `Mono`
- **Quality Preset**: `PC` (Index 1)

### Scene Structure
The GTEX runtime architecture organizes scenes under `Gtex_Test_Migration/Assets/Scenes/`:
- **Production Match Scene**: `Assets/Scenes/Gtex_MainScene.unity` (Loaded automatically by `GtexSceneLoader` when in Production mode; contains the 3D stadium pitch, floodlights, camera rigs, and the authoritative `GtexMatchRuntime` controller).
- **Secondary Presentation Scene**: `Assets/Scenes/GTEX_OriginalVisualRuntime.unity` (Fallback/presentation review scene).
- **Starting Scene**: `Assets/Scenes/_StartingScene.unity` / `Assets/_StartingScene.unity` (Bootstrapper that initializes the GTEX environment and loads `Gtex_MainScene`).
- **Build Scene**: `Assets/Scenes/Gtex_BuildScene.unity` (Lightweight batch build harness).

Both `Assets/Scenes/Gtex_MainScene.unity` and `Assets/Scenes/GTEX_OriginalVisualRuntime.unity` are registered in `ProjectSettings/EditorBuildSettings.asset`.

---

## 4. Configuration Discovery & Bootstrap Architecture

The Unity player determines its operational mode through two primary configuration files:

### Primary Asset Config
Located at: `Gtex_Test_Migration/Assets/Resources/GTEX/match-config.json`
Format:
```json
{
  "enabled": true,
  "autoStartOnBoot": true,
  "runtimeMode": "live",
  "matchId": "",
  "environment": "local",
  "localBaseUrl": "http://127.0.0.1:8000",
  "productionBaseUrl": "https://gtex-api.onrender.com",
  "customBaseUrl": "",
  "liveAccessToken": "",
  "liveRefreshToken": "",
  "pollIntervalSeconds": 0.5,
  "maxRetryDelaySeconds": 12.0,
  "timeoutSeconds": 20,
  "homeTemplateTeam": "City",
  "awayTemplateTeam": "Royal",
  "homeTeamName": "",
  "awayTeamName": "",
  "dayTime": "Night",
  "preserveOriginalScenePresentation": false,
  "enableStadiumUpgrade": true,
  "showBroadcastScaffolding": false,
  "showCrowd": true,
  "stadiumVariant": "broadcast",
  "useOriginalMatchCamera": false,
  "verboseLogging": false,
  "enableRuntimeComparisonLogging": false,
  "showRuntimeDebugOverlay": false,
  "comparisonLogIntervalSeconds": 2.0,
  "stalePredictionSeconds": 0.25,
  "teleportDistance": 2.5,
  "continueClockWhenTransportStalls": false,
  "stalledClockAdvanceMinutesPerSecond": 0.0,
  "allowLocalSimulationInProductionScene": false,
  "use3DPlaybackForLocalSimulation": true,
  "stopReconnectAfterTerminal": true,
  "simulationTargetDurationMinutes": 15.0,
  "simulationEventCheckWindowMinutes": 1.0,
  "simulationBaseEventChancePerWindow": 0.42,
  "simulationRandomSeed": 1337
}
```

### Runtime Dynamic Bootstrap
Generated at match provisioning time:
- Primary location: `Gtex_Test_Migration/tmp/gtex-live-bootstrap.json`
- Standalone Player mirror: `Gtex_Test_Migration/Builds/WindowsProduction/tmp/gtex-live-bootstrap.json`

Format:
```json
{
  "profile": "local",
  "runtimeMode": "live",
  "environment": "local",
  "matchId": "<provisioned_match_id>",
  "baseUrl": "http://127.0.0.1:8000",
  "liveAccessToken": "<short_lived_jwt_token>",
  "liveRefreshToken": "<refresh_jwt_token>",
  "issuedAtUtc": "2026-11-06T12:00:00.000000Z",
  "bootstrapTtlSeconds": 900,
  "consumeOnLoad": false
}
```

When the Unity standalone player boots, `GtexMatchConfigLoader` reads this file, verifies TTL validity, and connects to the authoritative live stream.

---

## 5. One-Click Demonstration Launcher

The repository provides the automated PowerShell launcher:
`tools/GTEX_PHASE1_WINDOWS_DEMO.ps1`

### Running the Demo
Open a PowerShell console in the repository root and execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\GTEX_PHASE1_WINDOWS_DEMO.ps1 -LeaveUnityRunning
```

### Automated Steps Performed
1. **Prerequisite Resolution**: Automatically locates Python (`.venv` or `PATH`) and resolves the Windows standalone player executable under `Gtex_Test_Migration\Builds`.
2. **Safe Backend Start**: Verifies whether port `8000` is active. If not, spawns `tools/run_gtex_live_backend.py --profile local --port 8000` with logging to `tmp/gtex_live_backend_demo.log`.
3. **Deterministic Match Provisioning**: Checks for an existing active Infinite League fixture. If present, reuses it; otherwise, provisions a deterministic match via `tools/provision_gtex_live_match_windows.py`.
4. **Bootstrap Synchronization**: Generates and copies `gtex-live-bootstrap.json` directly into the player's runtime `tmp/` folder and exports `$env:GTEX_BOOTSTRAP_PATH`.
5. **Unity Launch**: Executes `GTEXMatch.exe` in 1280x720 windowed mode (`-popupwindow -screen-fullscreen 0 -screen-width 1280 -screen-height 720`) with dedicated logging to `tmp/gtex_windows_demo_player.log`.
6. **Graceful Teardown**: Intercepts shutdown signals and cleanly closes the Unity window and local backend processes unless `-LeaveUnityRunning` is specified.

---

## 6. Manual Execution Commands

If manual control over each component is desired:

### Step 1: Start Authoritative Backend
```powershell
python .\tools\run_gtex_live_backend.py --profile local --port 8000 --log-level info
```

### Step 2: Provision Authoritative Match
```powershell
python .\tools\provision_gtex_live_match_windows.py --profile local --base-url http://127.0.0.1:8000 --persist-access-token
```

### Step 3: Launch Unity Windows Player
```powershell
& ".\Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe" -popupwindow -screen-fullscreen 0 -screen-width 1280 -screen-height 720 -logFile "tmp\gtex_windows_demo_player.log"
```

---

## 7. Standalone Player Compilation (If Required)

If `GTEXMatch.exe` is missing from `Gtex_Test_Migration\Builds\WindowsProduction\`, compile it directly using Unity 6 batch mode:

### Option A: Using the Repository Build Helper
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_gtex_windows_production_build.ps1
```

### Option B: Direct Unity Command Line
```powershell
& "C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe" `
  -batchmode `
  -quit `
  -nographics `
  -buildTarget StandaloneWindows64 `
  -projectPath "Gtex_Test_Migration" `
  -executeMethod "FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64ProductionFromCommandLine" `
  -logFile "tmp\unity_windows_build.log"
```

*Note: Unity compilation requires approximately 8–15 minutes depending on CPU and disk performance. Progress can be monitored in `tmp\unity_windows_build.log`.*

---

## 8. Expected 75-Second Demonstration Timeline

During a 60–90 second demonstration run, observe the following chronological sequence:

| Timestamp | Visual Beat | Expected On-Screen Action |
|---|---|---|
| **00:00 – 00:08** | **Initialization & Kit Resolution** | Unity loads `Gtex_MainScene`, resolves the pitch coordinates (85m × 60m), and auto-selects contrasting kit colours (e.g. City Light vs Royal Dark) using `GtexKitContrastResolver`. |
| **00:08 – 00:15** | **Pre-Match Formation & Kickoff** | 22 humanoid player models take up canonical 4-3-3 tactical positions on either side of the center circle. Referee team is positioned. Striker places the ball at the center spot. |
| **00:15 – 00:30** | **Midfield Open Play & Passing** | Match clock starts. First pass is executed. Ball trajectory tracks between midfielders. Player controllers execute locomotion blend trees (idle $\to$ run $\to$ sprint). |
| **00:30 – 00:45** | **Attacking Build-up & Wing Play** | Offensive team advances into the final third. Wingers make overlapping runs; defenders shift laterally to maintain compact formation lines. |
| **00:45 – 00:55** | **Shot Attempt & Goalkeeper Action** | Striker enters the penalty box and unleashes a shot toward goal. Goalkeeper state machine triggers dive / deflection or catch animation. |
| **00:55 – 01:10** | **Goal Event, Celebration & Scoreboard** | Ball crosses the goal line. Headline notification overlay displays the scorer. Scorer triggers celebration state machine. Scoreboard UI increments (e.g., `1 - 0`). |
| **01:10 – 01:25** | **Broadcast Camera Transition & Replay** | Camera system switches from `TVBroadcast` to cinematic replay angle. `ReplayPlayer` triggers slow-motion playback at `0.35x` timescale. Stadium crowd models and floodlights frame the arena. |

---

## 9. Visual Evidence Capture Protocol

The operator must capture physical visual proof of the live runtime session.

### Video Recording Protocol
- **Target Duration**: 60 to 90 seconds (covering kickoff, play, goal, celebration, and replay).
- **Target Frame Rate**: 60 FPS (minimum 30 FPS) at 1280×720 or 1920×1080 resolution.
- **Recording Tool**:
  - Windows Xbox Game Bar: Press `Win + Alt + R` to start/stop recording.
  - Or OBS Studio configured for window capture of `GTEXMatch.exe`.
- **Storage**: Save recording locally (e.g., `evidence/gtex_phase1_windows_demo.mp4`).

### Eight Required Visual QA Screenshots
Capture screenshots at the designated moments using `Win + Shift + S` or the automated tool `tools/capture_gtex_player_session.ps1`:

1. `01_kickoff_formation.png`: Showing 22 players positioned on pitch before kickoff with tactical layout visible.
2. `02_tactical_spread.png`: Showing defensive and attacking lines spread across the pitch.
3. `03_midfield_passing.png`: Showing ball in transit between midfielders with locomotion animations.
4. `04_attacking_sequence.png`: Showing final third penetration with defenders tracking runners.
5. `05_shot_and_goalkeeper.png`: Showing shot trajectory and goalkeeper reaction/dive.
6. `06_goal_and_celebration.png`: Showing ball in net and player celebration animation state.
7. `07_scoreboard_update.png`: Showing the score update headline and scoreboard increment.
8. `08_broadcast_camera_and_stadium.png`: Showing cinematic camera angle, replay banner, and stadium crowd.

---

## 10. Verification of Stream & Performance

### Confirm Authoritative Render-Sync Stream
Inspect `tmp\gtex_windows_demo_player.log` to confirm that the build is receiving live backend WebSocket updates:
```text
[GTEX] Applied bootstrap payload from '...\tmp\gtex-live-bootstrap.json': runtimeMode, matchId, ...
[GTEX] Config loaded -> MatchId: match_fix_...
[GTEX] RuntimeMode -> LivePlayback
[GTEX] BaseUrl -> http://127.0.0.1:8000
[GTEX] Connecting WS: ws://127.0.0.1:8000/api/v2/ws/match/match_fix_...?format=unity
[GTEX] Live: 3.04' 0-0
```

### Verify Framerate (FPS)
- **Xbox Game Bar**: Press `Win + G`, pin the **Performance** widget, and monitor the FPS meter (target $\ge$ 60 FPS).
- **Unity Player Log**: Check for render loop stability and verify that Direct3D 11 / 12 device client initialized without frame stalls.

---

## 11. Troubleshooting & Diagnostics

| Symptom | Cause | Solution |
|---|---|---|
| `[GTEX] match-config.json NOT FOUND` | Asset file missing | Restore `Gtex_Test_Migration\Assets\Resources\GTEX\match-config.json`. |
| `WS failed, fallback to polling` | Backend not started or port blocked | Confirm backend is running at `http://127.0.0.1:8000` via `Test-NetConnection 127.0.0.1 -Port 8000`. |
| `Bootstrap file expired` | TTL ($>$ 900s) elapsed before launch | Re-run `tools/provision_gtex_live_match_windows.py` to issue a fresh JWT token. |
| `No Windows Unity build found` | Player has not been compiled | Follow Section 7 to compile `GTEXMatch.exe` using Unity 6. |
| Black screen or DirectX crash | Driver incompatibility | Update Intel/NVIDIA graphics driver; verify Direct3D 11 level in `dxdiag`. |

---

## 12. Artifact Locations Reference

- **Launcher Script**: [`tools/GTEX_PHASE1_WINDOWS_DEMO.ps1`](file:///tools/GTEX_PHASE1_WINDOWS_DEMO.ps1)
- **Common Launcher Helpers**: [`tools/GTEX_Launcher_Common.ps1`](file:///tools/GTEX_Launcher_Common.ps1)
- **Launcher Tests**: [`tools/GTEX_PHASE1_WINDOWS_DEMO.Tests.ps1`](file:///tools/GTEX_PHASE1_WINDOWS_DEMO.Tests.ps1)
- **Windows Live Provisioning**: [`tools/provision_gtex_live_match_windows.py`](file:///tools/provision_gtex_live_match_windows.py)
- **Authoritative Backend Runner**: [`tools/run_gtex_live_backend.py`](file:///tools/run_gtex_live_backend.py)
- **Unity Build Helper**: [`tools/run_gtex_windows_production_build.ps1`](file:///tools/run_gtex_windows_production_build.ps1)
- **Unity Player Log**: `tmp/gtex_windows_demo_player.log`
- **Backend Stdout**: `tmp/gtex_live_backend_demo.log`
- **Backend Stderr**: `tmp/gtex_live_backend_demo.err.log`
