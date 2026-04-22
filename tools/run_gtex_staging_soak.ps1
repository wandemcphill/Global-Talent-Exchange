param(
    [ValidateSet('staging', 'production')]
    [string]$Profile = 'staging',

    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$UserEmail = '',

    [string]$UserPassword = '',

    [string]$UserAccessToken = '',

    [string]$MatchId = '',

    [switch]$AllowMatchGeneration,

    [switch]$PayToView,

    [int]$DurationMinutes = 15,

    [string]$OutputDir = '',

    [string]$ExePath = 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe'
)

$ErrorActionPreference = 'Stop'

$root = 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE'
$captureScript = Join-Path $root 'tools\capture_gtex_player_session.ps1'
$unityConfigPath = Join-Path $root 'Gtex_Test_Migration\Assets\Resources\GTEX\match-config.json'
$bootstrapPath = Join-Path $root 'Gtex_Test_Migration\tmp\gtex-live-bootstrap.json'

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $root ("tmp\gtex_{0}_soak" -f $Profile)
}

[System.IO.Directory]::CreateDirectory($OutputDir) | Out-Null

$provisionSummaryPath = Join-Path $OutputDir 'provision_summary.json'
$soakSummaryPath = Join-Path $OutputDir 'soak_summary.json'
$captureOutputDir = Join-Path $OutputDir 'capture'
$sessionName = ("gtex_{0}_soak" -f $Profile)

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
}

$provisionArgs = @(
    'tools\provision_gtex_live_match.py',
    '--profile', $Profile,
    '--base-url', $BaseUrl,
    '--unity-config', $unityConfigPath,
    '--bootstrap-path', $bootstrapPath,
    '--keep-bootstrap-file',
    '--persist-access-token'
)

if (-not [string]::IsNullOrWhiteSpace($UserAccessToken)) {
    $provisionArgs += @('--user-access-token', $UserAccessToken)
}
elseif (-not [string]::IsNullOrWhiteSpace($UserEmail) -and -not [string]::IsNullOrWhiteSpace($UserPassword)) {
    $provisionArgs += @('--user-email', $UserEmail, '--user-password', $UserPassword)
}
else {
    throw 'Staging soak requires either -UserAccessToken or both -UserEmail and -UserPassword.'
}

if (-not [string]::IsNullOrWhiteSpace($MatchId)) {
    $provisionArgs += @('--match-id', $MatchId)
}
elseif ($AllowMatchGeneration.IsPresent) {
    $provisionArgs += '--allow-match-generation'
}

if ($PayToView.IsPresent) {
    $provisionArgs += '--pay-to-view'
}

$provisionOutput = & python @provisionArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    throw ("Staging soak provisioning failed.`n" + ($provisionOutput -join "`n"))
}

$provisionSummary = (($provisionOutput -join "`n").Trim()) | ConvertFrom-Json
(($provisionSummary | ConvertTo-Json -Depth 8) + "`n") | Set-Content -Path $provisionSummaryPath -Encoding UTF8

$durationSeconds = [Math]::Max(60, $DurationMinutes * 60)
$captureOffsets = @(15, [Math]::Min(300, $durationSeconds), [Math]::Min(600, $durationSeconds), $durationSeconds) | Sort-Object -Unique

$captureOutput = & $captureScript `
    -ExePath $ExePath `
    -OutputDir $captureOutputDir `
    -SessionName $sessionName `
    -InitialWaitSeconds 12 `
    -CaptureOffsetsSeconds $captureOffsets `
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
$endedEarly = $false
$start = Get-Date

for ($elapsed = 0; $elapsed -lt $durationSeconds; $elapsed++) {
    Start-Sleep -Seconds 1
    if ($null -eq $player) {
        continue
    }
    try {
        $player.Refresh()
        if ($player.HasExited) {
            $endedEarly = $true
            break
        }
    } catch {
        $endedEarly = $true
        break
    }
}

if ($null -ne $player) {
    Stop-IfRunning -Process $player
}

Start-Sleep -Seconds 2

$traceText = if (Test-Path $runtimeTrace) { Get-Content $runtimeTrace -Raw -ErrorAction SilentlyContinue } else { '' }
$playerText = if (Test-Path $playerLog) { Get-Content $playerLog -Raw -ErrorAction SilentlyContinue } else { '' }
$screenshots = @(Get-ChildItem $captureOutputDir -Filter ($sessionName + '_t*.png') -ErrorAction SilentlyContinue | Sort-Object Name)

$motionSeen = $traceText -match 'moving=(?!0\b)\d+'
$ballMotionSeen = $traceText -match 'ballSpeed=(?!0(?:\.0+)?\b)[0-9.]+'
$runtimeErrorSeen = $traceText -match '\| error \|'
$playerExceptionSeen = $playerText -match 'Exception'
$playerSurvivedTarget = -not $endedEarly

$summary = [ordered]@{
    executed_at_utc = [DateTime]::UtcNow.ToString('o')
    profile = $Profile
    base_url = $BaseUrl
    duration_minutes = $DurationMinutes
    duration_seconds = $durationSeconds
    elapsed_seconds = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    player_survived_target_duration = $playerSurvivedTarget
    motion_seen = [bool]$motionSeen
    ball_motion_seen = [bool]$ballMotionSeen
    runtime_error_seen = [bool]$runtimeErrorSeen
    player_exception_seen = [bool]$playerExceptionSeen
    screenshot_count = $screenshots.Count
    provision_summary_path = $provisionSummaryPath
    player_log = $playerLog
    runtime_trace = $runtimeTrace
    metadata = $metadataPath
    screenshots = @($screenshots | ForEach-Object { $_.FullName })
    passed = [bool](
        $playerSurvivedTarget -and
        $motionSeen -and
        $ballMotionSeen -and
        -not $runtimeErrorSeen -and
        -not $playerExceptionSeen
    )
}

(($summary | ConvertTo-Json -Depth 8) + "`n") | Set-Content -Path $soakSummaryPath -Encoding UTF8

Write-Output ("SUMMARY_PATH={0}" -f $soakSummaryPath)
Write-Output (($summary | ConvertTo-Json -Depth 8))
