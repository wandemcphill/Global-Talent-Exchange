param(
    [int]$Port = 8879
)

$ErrorActionPreference = 'Stop'

$root = 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE'
$serverScript = Join-Path $root 'tools\gtex_live_full_session_mock_server.py'
$captureScript = Join-Path $root 'tools\capture_gtex_player_session.ps1'
$serverOut = Join-Path $root 'tmp\gtex_full_session_server.out.log'
$serverErr = Join-Path $root 'tmp\gtex_full_session_server.err.log'
$summaryFile = Join-Path $root 'tmp\gtex_full_session_summary.json'
$captureOutputDir = Join-Path $root 'tmp\gtex_full_session_capture'
$exe = Join-Path $root 'Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe'
$projectBootstrapPath = Join-Path $root 'Gtex_Test_Migration\tmp\gtex-live-bootstrap.json'
$sessionName = 'gtex_full_session_validation'
$matchId = 'live-full-session-test'
$accessToken = 'live-full-session-access-token' # pragma: allowlist secret
$refreshToken = 'live-full-session-refresh-token' # pragma: allowlist secret
$baseUrl = "http://127.0.0.1:$Port"

function Get-TailText {
    param(
        [string]$Path,
        [int]$Count = 60
    )

    if (Test-Path $Path) {
        return (Get-Content $Path -Tail $Count -ErrorAction SilentlyContinue) -join "`n"
    }

    return ''
}

function Stop-IfRunning {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process) {
        return
    }

    try {
        if (-not $Process.HasExited) {
            $Process.CloseMainWindow() | Out-Null
            Start-Sleep -Seconds 2
        }
    } catch {
    }

    try {
        if (-not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force
        }
    } catch {
    }

    try {
        $Process.WaitForExit(5000) | Out-Null
    } catch {
    }
}

function Remove-FileIfExists {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    for ($attempt = 0; $attempt -lt 8; $attempt++) {
        try {
            Remove-Item $Path -Force -Recurse
            return
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "Failed to remove path after retries: $Path"
}

function Wait-ForServerReady {
    param([System.Diagnostics.Process]$ServerProcess)

    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-WebRequest -Uri "$baseUrl/admin/reset" -Method Post -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            if ($ServerProcess.HasExited) {
                throw 'Full-session mock server exited before becoming ready.'
            }
        }
    }

    throw "Full-session mock server did not become ready on $baseUrl."
}

function Write-BootstrapFile {
    $payload = [ordered]@{
        profile = 'local'
        runtimeMode = 'live'
        environment = 'custom'
        matchId = $matchId
        baseUrl = $baseUrl
        liveAccessToken = $accessToken
        liveRefreshToken = $refreshToken
        issuedAtUtc = [DateTime]::UtcNow.ToString('o')
        bootstrapTtlSeconds = 900
        consumeOnLoad = $false
    }

    $bootstrapDir = Split-Path $projectBootstrapPath -Parent
    if (-not (Test-Path $bootstrapDir)) {
        New-Item -ItemType Directory -Path $bootstrapDir -Force | Out-Null
    }

    ($payload | ConvertTo-Json -Depth 4) + "`n" | Set-Content -Path $projectBootstrapPath -Encoding UTF8
}

function Test-TraceTimeline {
    param([string]$TraceText)

    $timeline = New-Object System.Collections.Generic.List[object]

    foreach ($line in ($TraceText -split "`r?`n")) {
        if ($line -notmatch '\| (phase|tick) \|') {
            continue
        }

        $match = [regex]::Match($line, 'minute=(?<minute>\d+(?:\.\d+)?) score=(?<home>\d+)-(?<away>\d+)')
        if (-not $match.Success) {
            continue
        }

        $timeline.Add(
            [pscustomobject]@{
                minute = [double]$match.Groups['minute'].Value
                home = [int]$match.Groups['home'].Value
                away = [int]$match.Groups['away'].Value
            }
        )
    }

    $clockNonDecreasing = $true
    $scoreNonDecreasing = $true
    for ($index = 1; $index -lt $timeline.Count; $index++) {
        if ($timeline[$index].minute + 0.001 -lt $timeline[$index - 1].minute) {
            $clockNonDecreasing = $false
        }
        if ($timeline[$index].home -lt $timeline[$index - 1].home -or $timeline[$index].away -lt $timeline[$index - 1].away) {
            $scoreNonDecreasing = $false
        }
    }

    return [pscustomobject]@{
        count = $timeline.Count
        first_minute = if ($timeline.Count -gt 0) { $timeline[0].minute } else { $null }
        last_minute = if ($timeline.Count -gt 0) { $timeline[$timeline.Count - 1].minute } else { $null }
        clock_non_decreasing = $clockNonDecreasing
        score_non_decreasing = $scoreNonDecreasing
        mid_session_seen = @($timeline | Where-Object { $_.minute -ge 45.0 }).Count -gt 0
        late_session_seen = @($timeline | Where-Object { $_.minute -ge 84.0 }).Count -gt 0
        fulltime_seen = @($timeline | Where-Object { $_.minute -ge 90.0 }).Count -gt 0
    }
}

function Get-CaptureValue {
    param(
        [string[]]$Lines,
        [string]$Key
    )

    $prefix = $Key + '='
    foreach ($line in $Lines) {
        if ($line.StartsWith($prefix)) {
            return $line.Substring($prefix.Length)
        }
    }

    return $null
}

function Copy-RuntimeTraceArtifact {
    param(
        [string]$ExePath,
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

function Wait-ForSessionCompletion {
    param(
        [System.Diagnostics.Process]$PlayerProcess,
        [int]$TimeoutSeconds = 120
    )

    $lastSummary = $null

    for ($elapsed = 0; $elapsed -lt $TimeoutSeconds; $elapsed++) {
        Start-Sleep -Seconds 1

        if ($null -ne $PlayerProcess) {
            try {
                $PlayerProcess.Refresh()
            } catch {
            }
        }

        try {
            $response = Invoke-WebRequest -Uri "$baseUrl/admin/session-summary" -UseBasicParsing -TimeoutSec 5
            $lastSummary = $response.Content | ConvertFrom-Json
            if ($lastSummary -and [bool]$lastSummary.final_frame_sent) {
                return [pscustomobject]@{
                    summary = $lastSummary
                    player_exited = ($null -ne $PlayerProcess -and $PlayerProcess.HasExited)
                    timed_out = $false
                }
            }
        } catch {
        }

        if ($null -ne $PlayerProcess -and $PlayerProcess.HasExited) {
            return [pscustomobject]@{
                summary = $lastSummary
                player_exited = $true
                timed_out = $false
            }
        }
    }

    if ($null -eq $lastSummary) {
        try {
            $response = Invoke-WebRequest -Uri "$baseUrl/admin/session-summary" -UseBasicParsing -TimeoutSec 5
            $lastSummary = $response.Content | ConvertFrom-Json
        } catch {
        }
    }

    return [pscustomobject]@{
        summary = $lastSummary
        player_exited = ($null -ne $PlayerProcess -and $PlayerProcess.HasExited)
        timed_out = $true
    }
}

foreach ($path in @($serverOut, $serverErr, $summaryFile, $projectBootstrapPath, $captureOutputDir)) {
    Remove-FileIfExists -Path $path
}

$server = $null

try {
    $server = Start-Process python -ArgumentList @('tools\gtex_live_full_session_mock_server.py', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory $root -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr -PassThru
    Wait-ForServerReady -ServerProcess $server
    Write-BootstrapFile

    $captureOutput = & $captureScript `
        -ExePath $exe `
        -OutputDir $captureOutputDir `
        -SessionName $sessionName `
        -InitialWaitSeconds 8 `
        -CaptureOffsetsSeconds @(10, 18, 26, 34, 42) `
        -WindowWaitSeconds 60 `
        -LeaveRunning

    $captureLines = @($captureOutput)
    $playerPidValue = Get-CaptureValue -Lines $captureLines -Key 'PID'
    $playerPid = if ([string]::IsNullOrWhiteSpace($playerPidValue)) { $null } else { [int]$playerPidValue }
    $playerLog = Get-CaptureValue -Lines $captureLines -Key 'PLAYER_LOG'
    $runtimeTrace = Get-CaptureValue -Lines $captureLines -Key 'RUNTIME_TRACE'
    $metadataPath = Get-CaptureValue -Lines $captureLines -Key 'METADATA'

    if ([string]::IsNullOrWhiteSpace($playerLog)) {
        $playerLog = Join-Path $captureOutputDir ($sessionName + '.player.log')
    }
    if ([string]::IsNullOrWhiteSpace($runtimeTrace)) {
        $runtimeTrace = Join-Path $captureOutputDir ($sessionName + '.runtime.log')
    }
    if ([string]::IsNullOrWhiteSpace($metadataPath)) {
        $metadataPath = Join-Path $captureOutputDir ($sessionName + '.metadata.txt')
    }

    $player = if ($null -ne $playerPid) { Get-Process -Id $playerPid -ErrorAction SilentlyContinue } else { $null }
    $sessionResult = Wait-ForSessionCompletion -PlayerProcess $player -TimeoutSeconds 120

    if ($null -ne $player) {
        Stop-IfRunning -Process $player
    }

    Start-Sleep -Seconds 2
    $null = Copy-RuntimeTraceArtifact -ExePath $exe -DestinationPath $runtimeTrace

    $screenshots = @(Get-ChildItem $captureOutputDir -Filter ($sessionName + '_t*.png') -ErrorAction SilentlyContinue | Sort-Object Name)

    $traceText = if (Test-Path $runtimeTrace) { Get-Content $runtimeTrace -Raw -ErrorAction SilentlyContinue } else { '' }
    $playerText = if (Test-Path $playerLog) { Get-Content $playerLog -Raw -ErrorAction SilentlyContinue } else { '' }
    $serverText = if (Test-Path $serverErr) { Get-Content $serverErr -Raw -ErrorAction SilentlyContinue } else { '' }
    $serverSummary = $sessionResult.summary
    if ($null -eq $serverSummary) {
        $serverSummaryResponse = Invoke-WebRequest -Uri "$baseUrl/admin/session-summary" -UseBasicParsing -TimeoutSec 5
        $serverSummary = $serverSummaryResponse.Content | ConvertFrom-Json
    }
    $traceTimeline = Test-TraceTimeline -TraceText $traceText

    $bootstrapSeen = $traceText -match 'scene bootstrap finished'
    $motionSeen = $traceText -match 'moving=(?!0\b)\d+'
    $ballMotionSeen = $traceText -match 'ballSpeed=(?!0(?:\.0+)?\b)[0-9.]+'
    $cameraSwitchCount = ([regex]::Matches($playerText, '\[CameraSystem\] Switch Camera:')).Count
    $serverReachedFulltime = [bool]$serverSummary.final_frame_sent
    $phaseSequence = @($serverSummary.phase_sequence)
    $scoreTimeline = @($serverSummary.score_timeline)
    $cameraPresetsSeen = @($serverSummary.camera_presets_seen)
    $screenshotsCaptured = $screenshots.Count -ge 5
    $linearKinematicWarningSeen = $playerText -match 'Setting linear velocity of a kinematic body is not supported'
    $angularKinematicWarningSeen = $playerText -match 'Setting angular velocity of a kinematic body is not supported'
    $playerExitedBeforeFulltime = [bool]$sessionResult.player_exited -and -not $serverReachedFulltime
    $cameraStable = ($cameraPresetsSeen -contains 'broadcast') -and
        ($cameraPresetsSeen -contains 'attack_push') -and
        ($cameraPresetsSeen -contains 'box_zoom') -and
        $traceText -notmatch '\| error \|' -and
        $traceText -notmatch 'bootstrap phase failed|scene bootstrap aborted|transport failure' -and
        $playerText -notmatch 'Exception'

    $passed = $bootstrapSeen -and
        $motionSeen -and
        $ballMotionSeen -and
        $cameraStable -and
        $traceTimeline.clock_non_decreasing -and
        $traceTimeline.score_non_decreasing -and
        $traceTimeline.mid_session_seen -and
        $traceTimeline.late_session_seen -and
        $traceTimeline.fulltime_seen -and
        $serverReachedFulltime -and
        ($phaseSequence -contains 'first_half') -and
        ($phaseSequence -contains 'halftime') -and
        ($phaseSequence -contains 'second_half') -and
        ($phaseSequence -contains 'fulltime') -and
        (($scoreTimeline -join ',') -eq '0-0,1-0,1-1,2-1') -and
        $screenshotsCaptured -and
        -not $linearKinematicWarningSeen -and
        -not $angularKinematicWarningSeen -and
        -not $playerExitedBeforeFulltime -and
        -not [bool]$sessionResult.timed_out

    $summary = [ordered]@{
        base_url = $baseUrl
        executable = $exe
        match_id = $matchId
        bootstrap_path = $projectBootstrapPath
        capture_output_dir = $captureOutputDir
        player_log = $playerLog
        runtime_trace = $runtimeTrace
        metadata_path = $metadataPath
        screenshot_paths = @($screenshots | ForEach-Object { $_.FullName })
        bootstrap_seen = $bootstrapSeen
        motion_seen = $motionSeen
        ball_motion_seen = $ballMotionSeen
        camera_switch_count = $cameraSwitchCount
        camera_presets_seen = $cameraPresetsSeen
        camera_stable = $cameraStable
        linear_kinematic_warning_seen = $linearKinematicWarningSeen
        angular_kinematic_warning_seen = $angularKinematicWarningSeen
        player_exited_before_fulltime = $playerExitedBeforeFulltime
        wait_timed_out = [bool]$sessionResult.timed_out
        trace_timeline = $traceTimeline
        server_summary = $serverSummary
        screenshots_captured = $screenshotsCaptured
        server_out_tail = Get-TailText -Path $serverOut
        server_err_tail = Get-TailText -Path $serverErr
        player_log_tail = Get-TailText -Path $playerLog
        runtime_trace_tail = Get-TailText -Path $runtimeTrace
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
        passed = $passed
    }

    $json = $summary | ConvertTo-Json -Depth 8
    Set-Content -Path $summaryFile -Value $json
    Write-Output $json

    if (-not $passed) {
        exit 1
    }
} finally {
    Stop-IfRunning -Process $server
}
