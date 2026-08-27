# GTEX Phase 1: Windows 3D Demo & Visual QA

This guide runs the GTEX Unity Windows player against the authoritative local backend and provisions a real live-match session before Unity starts.

## Prerequisites

- Windows 10/11 64-bit
- Python available on PATH or `.venv\Scripts\python.exe`
- Backend dependencies installed
- A Windows Unity standalone build under `Gtex_Test_Migration\Builds`
- Unity 6 `6000.3.12f1` for rebuilding the player

The launcher accepts an explicit executable path, otherwise it searches in this order:

1. `GTEXMatch.exe`
2. `Gtex_Test_Migration.exe`
3. the first `.exe` found under `Gtex_Test_Migration\Builds`

This matches the current Windows build produced during Phase 1 validation.

## One-click run

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\GTEX_PHASE1_WINDOWS_DEMO.ps1 -LeaveUnityRunning
```

The launcher will:

1. Resolve Python and the Unity executable.
2. Start `tools/run_gtex_live_backend.py --profile local --port 8000` when port 8000 is not already listening.
3. Run `tools/provision_gtex_live_match.py --profile local --base-url http://127.0.0.1:8000 --persist-access-token`.
4. Launch the standalone Unity player at 1280x720.
5. Leave the player running when `-LeaveUnityRunning` is supplied.

The provisioning step must succeed before Unity is launched.

## Manual run

Start the backend:

```powershell
python .\tools\run_gtex_live_backend.py --profile local --port 8000
```

In another PowerShell window:

```powershell
python .\tools\provision_gtex_live_match.py --profile local --base-url http://127.0.0.1:8000 --persist-access-token
```

Then launch the actual build, for example:

```powershell
& ".\Gtex_Test_Migration\Builds\WindowsProduction\Gtex_Test_Migration.exe"
```

## Evidence capture

Once the Unity window is visible:

- Video: `Win + Alt + R`
- Screenshot: `Win + Shift + S`

Capture at least:

- kickoff / 22-player formation
- open play / locomotion
- attack and goalkeeper action
- goal / celebration / scoreboard
- replay camera
- stadium atmosphere

Keep the player running long enough to observe real backend-driven events. Do not use screenshots of the Unity Editor as Phase 1 visual evidence.

## Logs

The launcher writes the Unity player log to:

```text
.tmp\gtex_windows_demo_player.log
```

and the backend log to:

```text
tmp\gtex_live_backend_demo.log
```

Unity's normal standalone `Player.log` is also available under the Windows `%USERPROFILE%\AppData\LocalLow` tree.
