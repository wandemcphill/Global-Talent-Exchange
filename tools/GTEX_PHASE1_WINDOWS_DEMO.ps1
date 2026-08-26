<#
.SYNOPSIS
    One-click launcher for the GTEX Phase 1 Windows 3D Vertical Slice Demo.

.DESCRIPTION
    Automates prerequisite validation, backend startup, live match provisioning,
    match-config discovery, and Unity 3D executable launch on Windows. Provides clean
    shutdown of backend services when complete.

.EXAMPLE
    .\tools\GTEX_PHASE1_WINDOWS_DEMO.ps1
#>

[CmdletBinding()]
param(
    [string]$PythonExe = "",
    [string]$ExePath = "",
    [int]$BackendPort = 8000,
    [switch]$KeepBackendRunning,
    [switch]$LeaveUnityRunning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Normalize-ProcessPathEnvironment {
    $pathValue = [System.Environment]::GetEnvironmentVariable('Path', 'Process')
    if ([string]::IsNullOrWhiteSpace($pathValue)) {
        $pathValue = [System.Environment]::GetEnvironmentVariable('PATH', 'Process')
    }

    if (-not [string]::IsNullOrWhiteSpace($pathValue)) {
        [System.Environment]::SetEnvironmentVariable('Path', $pathValue, 'Process')
    }

    [System.Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
}

Normalize-ProcessPathEnvironment

Write-Host "========================================================================" -ForegroundColor Cyans
Write-Host "       GTEX Phase 1: One-Click Windows 3D Demo Launcher                 " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Resolve Python Executable
function Resolve-PythonExecutable {
    param([string]$ExplicitPath)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (Test-Path $ExplicitPath) {
            return (Get-Item $ExplicitPath).FullName
        }
        throw "Specified Python executable not found: $ExplicitPath"
    }

    $candidatePaths = @(
        (Join-Path $repoRoot ".venv\Scripts\python.exe"),
        (Join-Path $repoRoot ".venv\bin\python"),
        "python.exe",
        "python"
    )

    foreach ($candidate in $candidatePaths) {
        if (Test-Path $candidate -ErrorAction SilentlyContinue) {
            return (Get-Item $candidate).FullName
        }
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            return $cmd.Source
        }
    }

    throw "Python executable not found. Ensure Python is installed or a virtualenv exists at .venv."
}

$resolvedPython = Resolve-PythonExecutable -ExplicitPath $PythonExe
Write-Host "[+] Python Executable: $resolvedPython" -ForegroundColor Green

# 2. Check Python dependencies
Write-Host "[*] Validating Python backend dependencies..." -ForegroundColor Yellow
$checkScript = "import httpx, websockets, uvicorn, fastapi; print('OK')"
$pyCheck = Start-Process -FilePath $resolvedPython -ArgumentList "-c `"$checkScript`"" -NoNewWindow -PassThru -Wait
if ($pyCheck.ExitCode -ne 0) {
    Write-Host "[!] Missing required Python backend packages (httpx, websockets, uvicorn, fastapi)." -ForegroundColor Red
    Write-Host "    Run the following command to install dependencies:" -ForegroundColor Red
    Write-Host "    uv venv .venv; uv pip install -r backend/requirements.txt" -ForegroundColor Yellow
    throw "Backend dependencies missing."
}
Write-Host "[+] Backend Python dependencies verified." -ForegroundColor Green

# 3. Resolve Unity Executable
function Resolve-UnityExecutable {
    param([string]$ExplicitPath)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (Test-Path $ExplicitPath) {
            return (Get-Item $ExplicitPath).FullName
        }
        throw "Specified Unity executable not found: $ExplicitPath"
    }

    $buildsDir = Join-Path (Join-Path $repoRoot "Gtex_Test_Migration") "Builds"
    if (Test-Path $buildsDir) {
        $candidates = Get-ChildItem -Path $buildsDir -Recurse -Filter "GTEXMatch.exe" -ErrorAction SilentlyContinue
        if ($candidates.Count -gt 0) {
            return $candidates[0].FullName
        }
    }

    return $null
}

$resolvedExe = Resolve-UnityExecutable -ExplicitPath $ExePath

if ($null -eq $resolvedExe) {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Red
    Write-Host " [!] NO WINDOWS UNITY STANDALONE BUILD DETECTED                        " -ForegroundColor Red
    Write-Host "========================================================================" -ForegroundColor Red
    Write-Host " Expected executable location: Gtex_Test_Migration\Builds\...\GTEXMatch.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host " To build the Windows 3D Standalone executable, execute either:" -ForegroundColor White
    Write-Host ""
    Write-Host " Option A (Automated PowerShell Build Script):" -ForegroundColor Cyan
    Write-Host " powershell -ExecutionPolicy Bypass -File .\tools\run_gtex_windows_production_build.ps1 -UnityExe `"C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe`"" -ForegroundColor Yellow
    Write-Host ""
    Write-Host " Option B (Unity Editor Menu):" -ForegroundColor Cyan
    Write-Host " Open Gtex_Test_Migration in Unity 6000.3.12f1 and select:" -ForegroundColor White
    Write-Host "   Tools > GTEX > Build > Windows x64 (Production)" -ForegroundColor Yellow
    Write-Host "========================================================================" -ForegroundColor Red
    Write-Host ""
    throw "Windows Unity Standalone build not found. Please build the standalone player first."
}

Write-Host "[+] Unity Executable: $resolvedExe" -ForegroundColor Green

# 4. Check / Start Backend Process
$baseUrl = "http://127.0.0.1:$BackendPort"
$backendProcess = $null
$startedBackend = $false

function Test-BackendPort {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $wait = $asyncResult.AsyncWaitHandle.WaitOne(500, $false)
        if ($wait) {
            $client.EndConnect($asyncResult)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    }
    catch {
        return $false
    }
}

if (Test-BackendPort -Port $BackendPort) {
    Write-Host "[+] GTEX Backend is already running on port $BackendPort ($baseUrl)." -ForegroundColor Green
} else {
    Write-Host "[*] Starting GTEX Live Backend on port $BackendPort..." -ForegroundColor Yellow
    $backendLog = Join-Path $repoRoot "tmp\gtex_live_backend_demo.log"
    [System.IO.Directory]::CreateDirectory((Split-Path $backendLog -Parent)) | Out-Null

    $backendScript = Join-Path $repoRoot "tools\run_gtex_live_backend.py"
    $backendArgs = "$backendScript --profile local --port $BackendPort"

    $backendProcess = Start-Process -FilePath $resolvedPython -ArgumentList $backendArgs -NoNewWindow -PassThru
    $startedBackend = $true

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-BackendPort -Port $BackendPort) {
            $ready = $true
            break
        }
        if ($backendProcess.HasExited) {
            throw "GTEX Backend process exited unexpectedly with code $($backendProcess.ExitCode)."
        }
    }

    if (-not $ready) {
        throw "Timed out waiting for GTEX Backend to bind to port $BackendPort."
    }

    Write-Host "[+] GTEX Backend started successfully (PID: $($backendProcess.Id))." -ForegroundColor Green
}

# 5. Provision Real GTEX Live Match
Write-Host "[*] Provisioning real GTEX live match..." -ForegroundColor Yellow
$provisionScript = Join-Path $repoRoot "tools\provision_gtex_live_match.py"
$provisionArgs = "$provisionScript --profile local --base-url $baseUrl --persist-access-token"

$provisionProcess = Start-Process -FilePath $resolvedPython -ArgumentList $provisionArgs -NoNewWindow -PassThru -Wait
if ($provisionProcess.ExitCode -ne 0) {
    throw "Match provisioning failed with exit code $($provisionProcess.ExitCode)."
}
Write-Host "[+] Real GTEX live match provisioned and match-config/bootstrap updated." -ForegroundColor Green

# 6. Launch Unity 3D Windows Player
Write-Host "[*] Launching GTEX 3D Unity Windows Player..." -ForegroundColor Yellow
$playerLog = Join-Path $repoRoot "tmp\gtex_windows_demo_player.log"
[System.IO.Directory]::CreateDirectory((Split-Path $playerLog -Parent)) | Out-Null

$unityArgs = @(
    "-popupwindow",
    "-screen-fullscreen", "0",
    "-screen-width", "1280",
    "-screen-height", "720",
    "-logFile", $playerLog
)

$unityProcess = Start-Process -FilePath $resolvedExe -ArgumentList $unityArgs -PassThru

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "               GTEX 3D DEMO RUNNING SUCCESSFULLY                        " -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host " Unity PID:            $($unityProcess.Id)" -ForegroundColor White
Write-Host " Unity Executable:     $resolvedExe" -ForegroundColor White
Write-Host " Backend Base URL:     $baseUrl" -ForegroundColor White
Write-Host " Unity Player Log:     $playerLog" -ForegroundColor White
Write-Host " Runtime Trace Log:    $repoRoot\Gtex_Test_Migration\tmp\gtex_live_runtime_trace.log" -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host " EXPECTED 60-90 SECOND VISUAL SEQUENCE GUIDE:                          " -ForegroundColor Yellow
Write-Host "  1. [00-15s] Startup & Loading: Stadium assets & 3D match view initialize." -ForegroundColor White
Write-Host "  2. [15-45s] Kick-Off & Positioning: 3D player models move based on WS payloads." -ForegroundColor White
Write-Host "  3. [45-90s] Match Flow & Events: Real-time ball physics, passes & commentary sync." -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host " HOW TO RECORD VISUAL EVIDENCE:                                        " -ForegroundColor Yellow
Write-Host "  - Windows Game Bar: Press Win + Alt + R to start/stop video recording." -ForegroundColor White
Write-Host "  - Snipping Tool:   Press Win + Shift + S or open Snipping Tool for screenshots." -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

try {
    if (-not $LeaveUnityRunning.IsPresent) {
        Write-Host "[*] Press ENTER or Ctrl+C to stop demo and shut down background services..." -ForegroundColor Yellow
        $null = Read-Host
    } else {
        Write-Host "[+] Demo left running as requested (-LeaveUnityRunning)." -ForegroundColor Green
    }
}
finally {
    if (-not $LeaveUnityRunning.IsPresent -and $null -ne $unityProcess -and -not $unityProcess.HasExited) {
        Write-Host "[*] Closing Unity 3D Player..." -ForegroundColor Yellow
        $null = $unityProcess.CloseMainWindow()
        Start-Sleep -Seconds 2
        if (-not $unityProcess.HasExited) {
            Stop-Process -Id $unityProcess.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Host "[+] Unity 3D Player stopped." -ForegroundColor Green
    }

    if ($startedBackend -and -not $KeepBackendRunning.IsPresent -and $null -ne $backendProcess -and -not $backendProcess.HasExited) {
        Write-Host "[*] Stopping GTEX Live Backend (PID: $($backendProcess.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[+] GTEX Live Backend stopped." -ForegroundColor Green
    }
}
