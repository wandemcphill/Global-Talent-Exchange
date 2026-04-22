param(
    [ValidateSet('all', 'resilience', 'terminal')]
    [string]$Scenario = 'all',
    [int]$Port = 8878
)

$ErrorActionPreference = 'Stop'

$root = 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE'
$serverScript = Join-Path $root 'tools\gtex_live_resilience_mock_server.py'
$serverOut = Join-Path $root 'tmp\gtex_live_resilience_server.out.log'
$serverErr = Join-Path $root 'tmp\gtex_live_resilience_server.err.log'
$playerLog = Join-Path $root 'tmp\gtex_live_resilience_player.log'
$summaryFile = Join-Path $root 'tmp\gtex_live_resilience_summary.json'
$exe = Join-Path $root 'Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe'
$traceFile = Join-Path $root 'Gtex_Test_Migration\Builds\WindowsProduction\tmp\gtex_live_runtime_trace.log'
$bootstrapPath = Join-Path (Split-Path $exe -Parent) 'tmp\gtex-live-bootstrap.json'

$resilienceMatchId = 'live-resilience-test'
$terminalMatchId = 'live-terminal-test'
$initialAccessToken = 'live-resilience-access-token-0'
$refreshToken = 'live-resilience-refresh-token'
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
            Remove-Item $Path -Force
            return
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "Failed to remove file after retries: $Path"
}

function Reset-ScenarioState {
    Invoke-WebRequest -Uri "$baseUrl/admin/reset" -Method Post -UseBasicParsing -TimeoutSec 5 | Out-Null
}

function Wait-ForServerReady {
    $serverReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-WebRequest -Uri "$baseUrl/admin/reset" -Method Post -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $serverReady = $true
                break
            }
        } catch {
            if ($server.HasExited) {
                throw 'Resilience mock server exited before becoming ready.'
            }
        }
    }

    if (-not $serverReady) {
        throw "Resilience mock server did not become ready on $baseUrl."
    }
}

function Start-Player {
    param(
        [string]$MatchId
    )

    foreach ($path in @($playerLog, $traceFile)) {
        Remove-FileIfExists -Path $path
    }

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $exe
    $psi.WorkingDirectory = Split-Path $exe -Parent
    $psi.Arguments = "-logFile `"$playerLog`""
    $psi.UseShellExecute = $false
    $psi.Environment['GTEX_RUNTIME_MODE'] = 'live'
    $psi.Environment['GTEX_BOOTSTRAP_PATH'] = $bootstrapPath
    return [System.Diagnostics.Process]::Start($psi)
}

function Write-BootstrapFile {
    param(
        [string]$MatchId
    )

    $payload = [ordered]@{
        profile = 'local'
        runtimeMode = 'live'
        environment = 'custom'
        matchId = $MatchId
        baseUrl = $baseUrl
        liveAccessToken = $initialAccessToken
        liveRefreshToken = $refreshToken
        issuedAtUtc = [DateTime]::UtcNow.ToString('o')
        bootstrapTtlSeconds = 900
        consumeOnLoad = $false
    }

    $bootstrapDir = Split-Path $bootstrapPath -Parent
    if (-not (Test-Path $bootstrapDir)) {
        New-Item -ItemType Directory -Path $bootstrapDir -Force | Out-Null
    }

    ($payload | ConvertTo-Json -Depth 4) + "`n" | Set-Content -Path $bootstrapPath -Encoding UTF8
}

function Run-ResilienceScenario {
    Reset-ScenarioState
    $player = $null

    try {
        Write-BootstrapFile -MatchId $resilienceMatchId
        $player = Start-Player -MatchId $resilienceMatchId

        $bootstrapSeen = $false
        $refreshRequestSeen = $false
        $refreshSuccessSeen = $false
        $staleTransportSeen = $false
        $reconnectSeen = $false
        $steadyWebsocketSeen = $false

        for ($i = 0; $i -lt 160; $i++) {
            Start-Sleep -Milliseconds 500

            $traceText = if (Test-Path $traceFile) { Get-Content $traceFile -Raw -ErrorAction SilentlyContinue } else { '' }
            $playerText = if (Test-Path $playerLog) { Get-Content $playerLog -Raw -ErrorAction SilentlyContinue } else { '' }
            $serverText = if (Test-Path $serverErr) { Get-Content $serverErr -Raw -ErrorAction SilentlyContinue } else { '' }

            if ($traceText -match 'scene bootstrap finished') { $bootstrapSeen = $true }
            if ($serverText -match 'refresh request match=live-resilience-test') { $refreshRequestSeen = $true }
            if ($playerText -match 'Live access token refreshed successfully') { $refreshSuccessSeen = $true }
            if ($traceText -match 'Transport degraded\. Live state has gone stale') { $staleTransportSeen = $true }
            if ($serverText -match 'resilience websocket connect #3') { $reconnectSeen = $true }
            if ($serverText -match 'steady streaming after reconnect' -and $traceText -match 'transport=websocket ws=True') {
                $steadyWebsocketSeen = $true
            }

            if ($bootstrapSeen -and $refreshRequestSeen -and $refreshSuccessSeen -and $staleTransportSeen -and $reconnectSeen -and $steadyWebsocketSeen) {
                break
            }

            if ($player.HasExited -and $i -gt 10) {
                break
            }
        }

        return [ordered]@{
            name = 'resilience'
            match_id = $resilienceMatchId
            bootstrap_seen = $bootstrapSeen
            refresh_request_seen = $refreshRequestSeen
            refresh_success_seen = $refreshSuccessSeen
            stale_transport_seen = $staleTransportSeen
            reconnect_seen = $reconnectSeen
            steady_websocket_seen = $steadyWebsocketSeen
            passed = ($bootstrapSeen -and $refreshRequestSeen -and $refreshSuccessSeen -and $staleTransportSeen -and $reconnectSeen -and $steadyWebsocketSeen)
            trace_tail = Get-TailText -Path $traceFile
            player_log_tail = Get-TailText -Path $playerLog
            server_log_tail = Get-TailText -Path $serverErr
        }
    } finally {
        Stop-IfRunning -Process $player
    }
}

function Run-TerminalScenario {
    Reset-ScenarioState
    $player = $null

    try {
        Write-BootstrapFile -MatchId $terminalMatchId
        $player = Start-Player -MatchId $terminalMatchId

        $bootstrapSeen = $false
        $terminalWarningSeen = $false
        $terminalWebsocketSeen = $false

        for ($i = 0; $i -lt 80; $i++) {
            Start-Sleep -Milliseconds 500

            $traceText = if (Test-Path $traceFile) { Get-Content $traceFile -Raw -ErrorAction SilentlyContinue } else { '' }
            $playerText = if (Test-Path $playerLog) { Get-Content $playerLog -Raw -ErrorAction SilentlyContinue } else { '' }
            $serverText = if (Test-Path $serverErr) { Get-Content $serverErr -Raw -ErrorAction SilentlyContinue } else { '' }

            if ($traceText -match 'scene bootstrap finished') { $bootstrapSeen = $true }
            if ($playerText -match 'is already terminal') { $terminalWarningSeen = $true }
            if ($serverText -match 'terminal websocket final frame match=live-terminal-test') { $terminalWebsocketSeen = $true }

            if ($bootstrapSeen -and $terminalWarningSeen -and $terminalWebsocketSeen) {
                break
            }

            if ($player.HasExited -and $i -gt 10) {
                break
            }
        }

        return [ordered]@{
            name = 'terminal'
            match_id = $terminalMatchId
            bootstrap_seen = $bootstrapSeen
            terminal_warning_seen = $terminalWarningSeen
            terminal_websocket_seen = $terminalWebsocketSeen
            passed = ($bootstrapSeen -and $terminalWarningSeen -and $terminalWebsocketSeen)
            trace_tail = Get-TailText -Path $traceFile
            player_log_tail = Get-TailText -Path $playerLog
            server_log_tail = Get-TailText -Path $serverErr
        }
    } finally {
        Stop-IfRunning -Process $player
    }
}

foreach ($path in @($serverOut, $serverErr, $summaryFile, $bootstrapPath)) {
    Remove-FileIfExists -Path $path
}

$server = $null

try {
    $server = Start-Process python -ArgumentList @('tools\gtex_live_resilience_mock_server.py', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory $root -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr -PassThru
    Wait-ForServerReady

    $scenarios = @()
    if ($Scenario -in @('all', 'resilience')) {
        $scenarios += [pscustomobject](Run-ResilienceScenario)
    }

    if ($Scenario -in @('all', 'terminal')) {
        $scenarios += [pscustomobject](Run-TerminalScenario)
    }

    $summary = [ordered]@{
        base_url = $baseUrl
        executable = $exe
        bootstrap_path = $bootstrapPath
        scenarios = $scenarios
        passed = @($scenarios | Where-Object { -not $_.passed }).Count -eq 0
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
    }

    $json = $summary | ConvertTo-Json -Depth 6
    Set-Content -Path $summaryFile -Value $json
    Write-Output $json

    if (-not $summary.passed) {
        exit 1
    }
} finally {
    Stop-IfRunning -Process $server
}
