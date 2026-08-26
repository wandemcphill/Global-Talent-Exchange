# GTEX Phase 1: One-Click Windows 3D Demo & Visual QA Guide

This guide describes how to run the **authoritative real GTEX Unity 3D match engine** locally on Windows, provision live backend-driven match payloads, and capture visual evidence (screenshots and video recordings).

---

## 1. Prerequisites

Before executing the launcher script, ensure the following setup on Windows:

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **PowerShell**: PowerShell 5.1+ or PowerShell Core 7+.
3. **Python**: Python 3.10+ installed and accessible in `PATH` (or configured inside a `.venv` at root).
4. **Backend Dependencies**: Ensure required Python packages (`fastapi`, `uvicorn`, `httpx`, `websockets`, `pydantic`) are installed.
   ```powershell
   uv venv .venv
   uv pip install -r backend/requirements.txt
   ```
5. **Unity Standalone Windows Build**:
   - Path check: `Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe` or `Gtex_Test_Migration\Builds\Windows\GTEXMatch.exe`.

---

## 2. Windows Unity 6000.3.12f1 Build Instructions

If `GTEXMatch.exe` is **not present**, you must generate the standalone executable first.

### Option A: Automated PowerShell Build Script (Recommended)
Run the automated batch build tool in PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_gtex_windows_production_build.ps1 -UnityExe "C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe"
```

### Option B: Unity Editor GUI
1. Open the project folder `Gtex_Test_Migration` in **Unity 6000.3.12f1**.
2. From the menu bar, navigate to:
   `Tools > GTEX > Build > Windows x64 (Production)`
3. Save the built executable under `Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe`.

---

## 3. One-Click Demo Execution

Run the one-click demo launcher script in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\GTEX_PHASE1_WINDOWS_DEMO.ps1
```

### What the script automates:
1. **Prerequisite Check**: Validates Python executable and required packages (`httpx`, `websockets`, `uvicorn`, `fastapi`).
2. **Build Detection**: Finds the compiled `GTEXMatch.exe` standalone player.
3. **Backend Startup**: Starts the real GTEX backend on `http://127.0.0.1:8000` (`tools/run_gtex_live_backend.py`).
4. **Live Match Provisioning**: Executes `tools/provision_gtex_live_match.py` to select/generate an active infinite-league match, issue spectator credentials, and generate `match-config.json` & `tmp/gtex-live-bootstrap.json`.
5. **3D Runtime Launch**: Spawns `GTEXMatch.exe` in windowed mode (`1280x720`).
6. **Clean Shutdown**: Closes Unity and terminates the local backend process upon pressing Enter or Ctrl+C.

---

## 4. Expected 60–90 Second Visual Sequence Guide

When the Unity 3D player launches, observe the following visual progression driven by real backend WebSocket frames:

| Time | Phase | Visual Expectation |
|---|---|---|
| **00:00 – 00:15** | **Initialization & Loading** | Stadium, pitch, lighting, camera rigs, and HUD elements render. Runtime bootstrap connects to `http://127.0.0.1:8000` via WebSocket. |
| **00:15 – 00:45** | **Kick-Off & Positioning** | Home and Away 3D player models spawn in formation. Match clock starts advancing. Real-time pitch positions update according to backend render-sync payloads. |
| **00:45 – 00:90** | **Live Match Flow & Events** | Active ball movement, passing sequences, event callouts (tackles/shots), real-time score HUD updates, and live commentary stream synchronization. |

---

## 5. Capturing Visual Evidence

### Method A: Automated Session & Screenshot Capture
Run the automated visual session recorder PowerShell tool:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\capture_gtex_player_session.ps1 -ExePath .\Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe -OutputDir .\tmp\gtex_captures
```
This tool captures window screenshots at defined offsets (e.g. 30s, 60s, 90s) and exports player logs & metadata into `.\tmp\gtex_captures`.

### Method B: Manual Recording & Screenshots
- **Video Recording**:
  - **Xbox Game Bar**: Press `Win + Alt + R` to start/stop screen recording while the Unity 3D window is focused.
  - **OBS Studio**: Capture window `GTEXMatch.exe`.
- **Screenshots**:
  - **Snipping Tool / Snip & Sketch**: Press `Win + Shift + S`.
  - Save output images to `docs/images/` or submit them with QA signoff reports.

---

## 6. Logs & Diagnostics

- **Unity Player Log**: `tmp\gtex_windows_demo_player.log` or `%USERPROFILE%\AppData\LocalLow\FStudio\GTEX\Player.log`
- **GTEX 3D Runtime Trace Log**: `Gtex_Test_Migration\tmp\gtex_live_runtime_trace.log`
- **Backend Server Log**: `tmp\gtex_live_backend_demo.log`
- **Backend Health Check**: `http://127.0.0.1:8000/health`
