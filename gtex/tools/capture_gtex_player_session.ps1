param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [string]$SessionName = "",

    [string]$PlayerLogPath = "",

    [int]$InitialWaitSeconds = 30,

    [int[]]$CaptureOffsetsSeconds = @(30, 60, 90),

    [int]$WindowWaitSeconds = 45,

    [switch]$LeaveRunning
)

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

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class Win32Capture
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@

function Resolve-SessionName {
    param([string]$Name)

    if (-not [string]::IsNullOrWhiteSpace($Name)) {
        return $Name.Trim()
    }

    return "gtex_player_session_{0}" -f (Get-Date -Format 'yyyyMMdd_HHmmss')
}

function Test-BitmapHasVisibleContent {
    param(
        [Parameter(Mandatory = $true)]
        [System.Drawing.Bitmap]$Bitmap
    )

    $sampleColumns = [Math]::Min(16, [Math]::Max(4, [Math]::Floor($Bitmap.Width / 64)))
    $sampleRows = [Math]::Min(12, [Math]::Max(4, [Math]::Floor($Bitmap.Height / 64)))
    $uniqueColors = New-Object 'System.Collections.Generic.HashSet[string]'
    $minLuma = [double]::PositiveInfinity
    $maxLuma = [double]::NegativeInfinity

    for ($column = 0; $column -lt $sampleColumns; $column += 1) {
        $x = [Math]::Min(
            $Bitmap.Width - 1,
            [Math]::Max(0, [Math]::Round(($column / [Math]::Max(1, $sampleColumns - 1)) * ($Bitmap.Width - 1))))

        for ($row = 0; $row -lt $sampleRows; $row += 1) {
            $y = [Math]::Min(
                $Bitmap.Height - 1,
                [Math]::Max(0, [Math]::Round(($row / [Math]::Max(1, $sampleRows - 1)) * ($Bitmap.Height - 1))))
            $pixel = $Bitmap.GetPixel($x, $y)
            $null = $uniqueColors.Add(("{0}-{1}-{2}" -f $pixel.R, $pixel.G, $pixel.B))
            $luma = ($pixel.R * 0.299) + ($pixel.G * 0.587) + ($pixel.B * 0.114)
            $minLuma = [Math]::Min($minLuma, $luma)
            $maxLuma = [Math]::Max($maxLuma, $luma)
        }
    }

    return $uniqueColors.Count -ge 10 -or ($maxLuma - $minLuma) -ge 14
}

function Test-ImageFileHasVisibleContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $false
    }

    $bitmap = $null
    try {
        $bitmap = [System.Drawing.Bitmap]::FromFile($Path)
        return Test-BitmapHasVisibleContent -Bitmap $bitmap
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $bitmap) {
            $bitmap.Dispose()
        }
    }
}

function Wait-ForInternalCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [int]$TimeoutSeconds = 8
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-ImageFileHasVisibleContent -Path $Path) {
            return $true
        }

        Start-Sleep -Milliseconds 250
    }

    return (Test-ImageFileHasVisibleContent -Path $Path)
}

function Copy-WindowFromScreen {
    param(
        [Parameter(Mandatory = $true)]
        [System.Drawing.Graphics]$Graphics,

        [Parameter(Mandatory = $true)]
        [Win32Capture+RECT]$Rect,

        [Parameter(Mandatory = $true)]
        [System.Drawing.Size]$BitmapSize
    )

    $Graphics.CopyFromScreen($Rect.Left, $Rect.Top, 0, 0, $BitmapSize)
}

function Capture-WindowImage {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process,

        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $Process.Refresh()
    if ($Process.HasExited -or $Process.MainWindowHandle -eq 0) {
        return $false
    }

    [Win32Capture]::ShowWindow($Process.MainWindowHandle, 5) | Out-Null
    [Win32Capture]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 800

    $rect = New-Object Win32Capture+RECT
    if (-not [Win32Capture]::GetWindowRect($Process.MainWindowHandle, [ref]$rect)) {
        return $false
    }

    $width = [Math]::Max(1, $rect.Right - $rect.Left)
    $height = [Math]::Max(1, $rect.Bottom - $rect.Top)

    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $captured = $false
    try {
        $printed = $false
        $hdc = [IntPtr]::Zero
        try {
            $hdc = $graphics.GetHdc()
            $printed = [Win32Capture]::PrintWindow($Process.MainWindowHandle, $hdc, 2)
        }
        finally {
            if ($hdc -ne [IntPtr]::Zero) {
                $graphics.ReleaseHdc($hdc)
            }
        }

        if ($printed) {
            $captured = Test-BitmapHasVisibleContent -Bitmap $bitmap
        }

        if (-not $captured) {
            Start-Sleep -Milliseconds 150
            Copy-WindowFromScreen -Graphics $graphics -Rect $rect -BitmapSize $bitmap.Size
            $captured = Test-BitmapHasVisibleContent -Bitmap $bitmap
        }

        if (-not $captured -and $printed) {
            Start-Sleep -Milliseconds 350
            [Win32Capture]::ShowWindow($Process.MainWindowHandle, 9) | Out-Null
            [Win32Capture]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
            Start-Sleep -Milliseconds 350
            Copy-WindowFromScreen -Graphics $graphics -Rect $rect -BitmapSize $bitmap.Size
            $captured = Test-BitmapHasVisibleContent -Bitmap $bitmap
        }

        if ($captured) {
            $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
        }
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }

    if (-not $captured -and (Test-Path $Path)) {
        Remove-Item $Path -Force -ErrorAction SilentlyContinue
    }

    return $captured
}

function Resolve-FallbackPlayerLog {
    param(
        [Parameter(Mandatory = $true)]
        [datetime]$LaunchTime
    )

    $localLowPath = Join-Path $env:USERPROFILE 'AppData\LocalLow'
    if (-not (Test-Path $localLowPath)) {
        return $null
    }

    $cutoff = $LaunchTime.AddMinutes(-2)
    $candidates = Get-ChildItem $localLowPath -Recurse -Filter 'Player.log' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $cutoff } |
        Sort-Object LastWriteTime -Descending

    if ($candidates.Count -eq 0) {
        return $null
    }

    return $candidates[0].FullName
}

function Copy-RuntimeTraceArtifact {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExePath,

        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    $runtimeDirectory = Split-Path $ExePath -Parent
    $runtimeTracePath = Join-Path (Join-Path $runtimeDirectory 'tmp') 'gtex_live_runtime_trace.log'
    if (-not (Test-Path $runtimeTracePath)) {
        return $null
    }

    Copy-Item -Path $runtimeTracePath -Destination $DestinationPath -Force
    return $runtimeTracePath
}

function Get-RuntimeTraceArtifactPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExePath
    )

    $runtimeDirectory = Split-Path $ExePath -Parent
    return (Join-Path (Join-Path $runtimeDirectory 'tmp') 'gtex_live_runtime_trace.log')
}

function Remove-PathIfExists {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path $Path)) {
        return
    }

    for ($attempt = 0; $attempt -lt 8; $attempt++) {
        try {
            Remove-Item -Path $Path -Force -ErrorAction Stop
            return
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
}

function Sync-CaptureRecordsFromDisk {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.Generic.List[object]]$Records
    )

    foreach ($record in $Records) {
        if (Test-ImageFileHasVisibleContent -Path $record.path) {
            $record.captured = $true
            if ($record.method -eq 'none') {
                $record.method = 'internal'
            }
        }
    }
}

function Copy-BootstrapArtifact {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExePath
    )

    $repoRoot = Split-Path $PSScriptRoot -Parent
    $sourceBootstrapPath = Join-Path (Join-Path (Join-Path $repoRoot 'Gtex_Test_Migration') 'tmp') 'gtex-live-bootstrap.json'
    if (-not (Test-Path $sourceBootstrapPath)) {
        return $null
    }

    $runtimeDirectory = Split-Path $ExePath -Parent
    $runtimeBootstrapDirectory = Join-Path $runtimeDirectory 'tmp'
    [System.IO.Directory]::CreateDirectory($runtimeBootstrapDirectory) | Out-Null

    $runtimeBootstrapPath = Join-Path $runtimeBootstrapDirectory 'gtex-live-bootstrap.json'
    Copy-Item -Path $sourceBootstrapPath -Destination $runtimeBootstrapPath -Force
    return $runtimeBootstrapPath
}

$resolvedSessionName = Resolve-SessionName -Name $SessionName
[System.IO.Directory]::CreateDirectory($OutputDir) | Out-Null

if ([string]::IsNullOrWhiteSpace($PlayerLogPath)) {
    $PlayerLogPath = Join-Path $OutputDir ($resolvedSessionName + '.player.log')
}

if (Test-Path $PlayerLogPath) {
    Remove-Item $PlayerLogPath -Force
}

$captureOffsets = @($CaptureOffsetsSeconds | Sort-Object)
$metadataPath = Join-Path $OutputDir ($resolvedSessionName + '.metadata.txt')
$runtimeTracePath = Join-Path $OutputDir ($resolvedSessionName + '.runtime.log')
$runtimeTraceArtifactPath = Get-RuntimeTraceArtifactPath -ExePath $ExePath
$runtimeBootstrapPath = Copy-BootstrapArtifact -ExePath $ExePath
$runtimeBootstrapSource = if ([string]::IsNullOrWhiteSpace($runtimeBootstrapPath)) { 'missing' } else { 'project_tmp' }

$args = @(
    '-popupwindow',
    '-screen-fullscreen', '0',
    '-screen-width', '1280',
    '-screen-height', '720',
    '-logFile', $PlayerLogPath
)

$previousCaptureOutputDirectory = $env:GTEX_CAPTURE_OUTPUT_DIR
$previousCaptureSessionName = $env:GTEX_CAPTURE_SESSION_NAME
$previousCaptureOffsets = $env:GTEX_CAPTURE_OFFSETS_SECONDS
$env:GTEX_CAPTURE_OUTPUT_DIR = $OutputDir
$env:GTEX_CAPTURE_SESSION_NAME = $resolvedSessionName
$env:GTEX_CAPTURE_OFFSETS_SECONDS = ($captureOffsets -join ',')

$process = $null
try {
    Remove-PathIfExists -Path $runtimeTraceArtifactPath
    Remove-PathIfExists -Path $runtimeTracePath

    $process = Start-Process -FilePath $ExePath -ArgumentList $args -PassThru
    $launchTime = Get-Date

    Start-Sleep -Seconds $InitialWaitSeconds

    $windowDeadline = (Get-Date).AddSeconds($WindowWaitSeconds)
    do {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
    } while ((Get-Date) -lt $windowDeadline -and -not $process.HasExited -and $process.MainWindowHandle -eq 0)

    $captureRecords = New-Object System.Collections.Generic.List[object]

    foreach ($offset in $captureOffsets) {
        $targetTime = $launchTime.AddSeconds($offset)
        while ((Get-Date) -lt $targetTime -and -not $process.HasExited) {
            Start-Sleep -Milliseconds 500
            $process.Refresh()
        }

        $capturePath = Join-Path $OutputDir ("{0}_t{1:D4}s.png" -f $resolvedSessionName, $offset)
        $captured = Wait-ForInternalCapture -Path $capturePath
        $captureMethod = 'internal'

        if (-not $captured) {
            $captured = Capture-WindowImage -Process $process -Path $capturePath
            $captureMethod = if ($captured) { 'window' } else { 'none' }
        }

        $captureRecords.Add(
            [pscustomobject]@{
                offset = $offset
                captured = $captured
                method = $captureMethod
                path = $capturePath
            })
    }

    $process.Refresh()
    $playerLogSource = 'redirected'

    if (-not $LeaveRunning) {
        if (-not $process.HasExited) {
            $null = $process.CloseMainWindow()
            Start-Sleep -Seconds 3
            $process.Refresh()
        }

        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
            Start-Sleep -Seconds 2
            $process.Refresh()
        }
    }

    if (-not (Test-Path $PlayerLogPath)) {
        $fallbackPlayerLog = Resolve-FallbackPlayerLog -LaunchTime $launchTime
        if (-not [string]::IsNullOrWhiteSpace($fallbackPlayerLog) -and (Test-Path $fallbackPlayerLog)) {
            Copy-Item -Path $fallbackPlayerLog -Destination $PlayerLogPath -Force
            $playerLogSource = "fallback:$fallbackPlayerLog"
        }
        else {
            $playerLogSource = 'missing'
        }
    }

    $runtimeTraceSource = Copy-RuntimeTraceArtifact -ExePath $ExePath -DestinationPath $runtimeTracePath
    if ([string]::IsNullOrWhiteSpace($runtimeTraceSource)) {
        $runtimeTraceSource = 'missing'
    }
    elseif ((Get-Item $runtimeTraceSource).LastWriteTimeUtc -lt $launchTime.ToUniversalTime()) {
        $runtimeTraceSource = "stale:$runtimeTraceSource"
    }

    Sync-CaptureRecordsFromDisk -Records $captureRecords

    $captureResultLines = @(
        $captureRecords | ForEach-Object {
            "offset={0}; captured={1}; method={2}; path={3}" -f $_.offset, $_.captured, $_.method, $_.path
        }
    )

    $metadata = @(
        ("session={0}" -f $resolvedSessionName),
        ("pid={0}" -f $process.Id),
        ("title={0}" -f $process.MainWindowTitle),
        ("handle={0}" -f $process.MainWindowHandle),
        ("exited={0}" -f $process.HasExited),
        ("exit_code={0}" -f $(if ($process.HasExited) { $process.ExitCode } else { '' })),
        ("launch_time_utc={0}" -f $launchTime.ToUniversalTime().ToString('o')),
        ("player_log={0}" -f $PlayerLogPath),
        ("player_log_source={0}" -f $playerLogSource),
        ("runtime_bootstrap={0}" -f $runtimeBootstrapPath),
        ("runtime_bootstrap_source={0}" -f $runtimeBootstrapSource),
        ("runtime_trace={0}" -f $runtimeTracePath),
        ("runtime_trace_source={0}" -f $runtimeTraceSource),
        ("leave_running={0}" -f $LeaveRunning.IsPresent)
    )

    $metadata += $captureResultLines
    Set-Content -Path $metadataPath -Value $metadata

    Write-Output ("SESSION={0}" -f $resolvedSessionName)
    Write-Output ("PID={0}" -f $process.Id)
    Write-Output ("EXITED={0}" -f $process.HasExited)
    Write-Output ("TITLE={0}" -f $process.MainWindowTitle)
    Write-Output ("HANDLE={0}" -f $process.MainWindowHandle)
    Write-Output ("EXIT_CODE={0}" -f $(if ($process.HasExited) { $process.ExitCode } else { '' }))
    Write-Output ("LAUNCH_TIME_UTC={0}" -f $launchTime.ToUniversalTime().ToString('o'))
    Write-Output ("PLAYER_LOG={0}" -f $PlayerLogPath)
    Write-Output ("PLAYER_LOG_SOURCE={0}" -f $playerLogSource)
    Write-Output ("RUNTIME_BOOTSTRAP={0}" -f $runtimeBootstrapPath)
    Write-Output ("RUNTIME_BOOTSTRAP_SOURCE={0}" -f $runtimeBootstrapSource)
    Write-Output ("RUNTIME_TRACE={0}" -f $runtimeTracePath)
    Write-Output ("RUNTIME_TRACE_SOURCE={0}" -f $runtimeTraceSource)
    Write-Output ("METADATA={0}" -f $metadataPath)
    $captureResultLines | ForEach-Object { Write-Output $_ }
}
finally {
    if ($null -eq $previousCaptureOutputDirectory) {
        Remove-Item Env:GTEX_CAPTURE_OUTPUT_DIR -ErrorAction SilentlyContinue
    }
    else {
        $env:GTEX_CAPTURE_OUTPUT_DIR = $previousCaptureOutputDirectory
    }

    if ($null -eq $previousCaptureSessionName) {
        Remove-Item Env:GTEX_CAPTURE_SESSION_NAME -ErrorAction SilentlyContinue
    }
    else {
        $env:GTEX_CAPTURE_SESSION_NAME = $previousCaptureSessionName
    }

    if ($null -eq $previousCaptureOffsets) {
        Remove-Item Env:GTEX_CAPTURE_OFFSETS_SECONDS -ErrorAction SilentlyContinue
    }
    else {
        $env:GTEX_CAPTURE_OFFSETS_SECONDS = $previousCaptureOffsets
    }

}
