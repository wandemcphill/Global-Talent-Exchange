<#
.SYNOPSIS
    One-click launcher for the GTEX Phase 1 Windows 3D vertical slice demo.
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

function Resolve-PythonExecutable {
    param([string]$ExplicitPath)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (Test-Path $ExplicitPath) { return (Get-Item $ExplicitPath).FullName }
        throw "Specified Python executable not found: $ExplicitPath"
    }
    $candidates = @(
        (Join-Path $repoRoot ".venv\Scripts\python.exe"),
        (Join-Path $repoRoot ".venv\bin\python"),
        "python.exe",
        "python"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate -ErrorAction SilentlyContinue) { return (Get-Item $candidate).FullName }
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $cmd) { return $cmd.Source }
    }
    throw "Python executable not found."
}

function Resolve-UnityExecutable {
    param([string]$ExplicitPath)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (Test-Path $ExplicitPath) { return (Get-Item $ExplicitPath).FullName }
        throw "Specified Unity executable not found: $ExplicitPath"
    }
    $buildsDir = Join-Path $repoRoot "Gtex_Test_Migration\Builds"
    if (-not (Test-Path $buildsDir)) { return $null }
    $preferredNames = @("GTEXMatch.exe", "Gtex_Test_Migration.exe")
    foreach ($name in $preferredNames) {
        $candidate = Get-ChildItem -Path $buildsDir -Recurse -Filter $name -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $candidate) { return $candidate.FullName }
    }
    $fallback = Get-ChildItem -Path $buildsDir -Recurse -Filter "*.exe" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $fallback) { return $fallback.FullName }
    return $null
}

function Test-BackendPort {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(500, $false)
        if ($connected) {
            $client.EndConnect($async)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch { return $false }
}

$python = Resolve-PythonExecutable -ExplicitPath $PythonExe
$exe = Resolve-UnityExecutable -ExplicitPath $ExePath
if ($null -eq $exe) {
    throw "No Windows Unity build found under Gtex_Test_Migration\Builds. Build the standalone player first."
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " GTEX Phase 1 - Windows 3D Demo" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Python: $python" -ForegroundColor Green
Write-Host "Unity:  $exe" -ForegroundColor Green

$baseUrl = "http://127.0.0.1:$BackendPort"
$backend = $null
$startedBackend = $false
$unity = $null

try {
    if (Test-BackendPort -Port $BackendPort) {
        Write-Host "[+] Backend already running at $baseUrl" -ForegroundColor Green
    } else {
        $backendLog = Join-Path $repoRoot "tmp\gtex_live_backend_demo.log"
        New-Item -ItemType Directory -Force -Path (Split-Path $backendLog -Parent) | Out-Null
        $backendArgs = @((Join-Path $repoRoot "tools\run_gtex_live_backend.py"), "--profile", "local", "--port", $BackendPort, "--log-level", "info")
        $backend = Start-Process -FilePath $python -ArgumentList $backendArgs -WorkingDirectory $repoRoot -RedirectStandardOutput $backendLog -RedirectStandardError $backendLog -PassThru
        $startedBackend = $true
        $ready = $false
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep -Milliseconds 500
            if (Test-BackendPort -Port $BackendPort) { $ready = $true; break }
            if ($backend.HasExited) { throw "GTEX backend exited with code $($backend.ExitCode). See $backendLog" }
        }
        if (-not $ready) { throw "Timed out waiting for GTEX backend on port $BackendPort." }
        Write-Host "[+] Backend started (PID $($backend.Id))" -ForegroundColor Green
    }

    Write-Host "[*] Provisioning authoritative GTEX live match..." -ForegroundColor Yellow
    & $python (Join-Path $repoRoot "tools\provision_gtex_live_match.py") --profile local --base-url $baseUrl --persist-access-token
    if ($LASTEXITCODE -ne 0) { throw "Live match provisioning failed with exit code $LASTEXITCODE." }
    Write-Host "[+] Live match provisioned; Unity bootstrap/config updated." -ForegroundColor Green

    $playerLog = Join-Path $repoRoot "tmp\gtex_windows_demo_player.log"
    New-Item -ItemType Directory -Force -Path (Split-Path $playerLog -Parent) | Out-Null
    $unityArgs = @("-popupwindow", "-screen-fullscreen", "0", "-screen-width", "1280", "-screen-height", "720", "-logFile", $playerLog)
    Write-Host "[*] Launching 3D player..." -ForegroundColor Yellow
    $unity = Start-Process -FilePath $exe -ArgumentList $unityArgs -WorkingDirectory (Split-Path $exe -Parent) -PassThru

    Write-Host "[+] GTEX 3D player launched. PID=$($unity.Id)" -ForegroundColor Green
    Write-Host "    Recording: Win+Alt+R" -ForegroundColor Yellow
    Write-Host "    Screenshot: Win+Shift+S" -ForegroundColor Yellow
    Write-Host "    Player log: $playerLog" -ForegroundColor Gray

    if ($LeaveUnityRunning.IsPresent) {
        Write-Host "[+] Leaving Unity running." -ForegroundColor Green
    } else {
        Write-Host "[*] Press ENTER to stop the demo." -ForegroundColor Yellow
        [void](Read-Host)
    }
}
finally {
    if (-not $LeaveUnityRunning.IsPresent -and $null -ne $unity -and -not $unity.HasExited) {
        try { $unity.CloseMainWindow() | Out-Null } catch {}
        Start-Sleep -Seconds 2
        if (-not $unity.HasExited) { Stop-Process -Id $unity.Id -Force -ErrorAction SilentlyContinue }
    }
    if ($startedBackend -and -not $KeepBackendRunning.IsPresent -and $null -ne $backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}
