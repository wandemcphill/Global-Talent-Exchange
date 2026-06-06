param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$BearerToken = '',

    [string]$OutputPath = '',

    [int]$TimeoutSeconds = 15,

    [int]$MaxLatencyMs = 2000,

    [switch]$IncludeOptionalMarket,

    [switch]$IncludeOptionalMatchCenter,

    [string]$MatchId = '',

    [switch]$VerifyMatchCenterRoutes,

    [string]$PythonPath = 'C:\Python314\python.exe'
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $OutputPath = Join-Path $root "tmp\staging_smoke_$stamp.json"
}

function Join-Url {
    param(
        [string]$RootUrl,
        [string]$Path
    )

    return $RootUrl.TrimEnd('/') + '/' + $Path.TrimStart('/')
}

function Invoke-SmokeRequest {
    param(
        [string]$Name,
        [string]$Path,
        [bool]$Required = $true
    )

    $url = Join-Url -RootUrl $BaseUrl -Path $Path
    $headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($BearerToken)) {
        $headers['Authorization'] = "Bearer $BearerToken"
    }

    $started = Get-Date
    try {
        $request = [System.Net.HttpWebRequest]::Create($url)
        $request.Method = 'GET'
        $request.Timeout = $TimeoutSeconds * 1000
        $request.ReadWriteTimeout = $TimeoutSeconds * 1000
        $request.KeepAlive = $false
        $request.UserAgent = 'gtex-staging-smoke/1.0'
        foreach ($header in $headers.GetEnumerator()) {
            $request.Headers[$header.Key] = $header.Value
        }

        $response = $request.GetResponse()
        try {
            $reader = [System.IO.StreamReader]::new($response.GetResponseStream())
            try {
                $body = $reader.ReadToEnd()
            } finally {
                $reader.Dispose()
            }
            $statusCode = [int]$response.StatusCode
        } finally {
            $response.Dispose()
        }

        $durationMs = [math]::Round(((Get-Date) - $started).TotalMilliseconds, 1)
        $passed = $statusCode -ge 200 -and $statusCode -lt 300 -and $durationMs -le $MaxLatencyMs

        return [ordered]@{
            name = $Name
            path = $Path
            url = $url
            required = $Required
            status_code = $statusCode
            latency_ms = $durationMs
            bytes = $body.Length
            result = if ($passed) { 'pass' } else { 'fail' }
            reason = if ($passed) { '' } else { "Expected 2xx and <= $MaxLatencyMs ms." }
        }
    } catch {
        $durationMs = [math]::Round(((Get-Date) - $started).TotalMilliseconds, 1)
        return [ordered]@{
            name = $Name
            path = $Path
            url = $url
            required = $Required
            status_code = 0
            latency_ms = $durationMs
            bytes = 0
            result = if ($Required) { 'fail' } else { 'blocked' }
            reason = $_.Exception.Message
        }
    }
}

$checks = New-Object System.Collections.Generic.List[object]

foreach ($item in @(
    @{ name = 'health'; path = '/health' },
    @{ name = 'readiness'; path = '/ready' },
    @{ name = 'version'; path = '/version' },
    @{ name = 'diagnostics'; path = '/diagnostics' }
)) {
    $checks.Add((Invoke-SmokeRequest -Name $item.name -Path $item.path -Required $true))
}

if ($IncludeOptionalMarket.IsPresent) {
    $checks.Add((Invoke-SmokeRequest -Name 'market_players' -Path '/api/market/players?limit=5' -Required $false))
}

if ($IncludeOptionalMatchCenter.IsPresent) {
    $checks.Add((Invoke-SmokeRequest -Name 'match_center_live_active' -Path '/api/matches/live/active' -Required $false))

    if ([string]::IsNullOrWhiteSpace($MatchId)) {
        $checks.Add([ordered]@{
            name = 'match_center_live_feed'
            path = '/api/match-viewer/{match_id}'
            url = ''
            required = $false
            status_code = 0
            latency_ms = 0
            bytes = 0
            result = 'blocked'
            reason = 'MatchId not provided; match-center smoke is intentionally blocked instead of inventing match truth.'
        })
    } else {
        $checks.Add((Invoke-SmokeRequest -Name 'match_center_viewer' -Path "/api/match-viewer/$MatchId" -Required $false))
        $checks.Add((Invoke-SmokeRequest -Name 'match_center_viewer_session' -Path "/api/match-viewer/$MatchId/session" -Required $false))
    }
}

$routeContract = [ordered]@{
    requested = [bool]$VerifyMatchCenterRoutes.IsPresent
    status = 'skipped'
    exit_code = $null
    output = ''
}

if ($VerifyMatchCenterRoutes.IsPresent) {
    $routeVerifier = Join-Path $root 'ops\render\verify_match_center_routes.py'
    if (-not (Test-Path $routeVerifier)) {
        $routeContract.status = 'fail'
        $routeContract.output = "Route verifier not found: $routeVerifier"
    } elseif (-not (Test-Path $PythonPath)) {
        $routeContract.status = 'fail'
        $routeContract.output = "PythonPath not found: $PythonPath"
    } else {
        $routeOutput = & $PythonPath $routeVerifier --url $BaseUrl --timeout-seconds $TimeoutSeconds 2>&1
        $routeContract.exit_code = $LASTEXITCODE
        $routeContract.output = ($routeOutput -join "`n")
        $routeContract.status = if ($LASTEXITCODE -eq 0) { 'pass' } else { 'fail' }
    }
}

$checkArray = [object[]]$checks.ToArray()
$requiredFailures = @($checkArray | Where-Object { $_.required -and $_.result -ne 'pass' })
$summary = [ordered]@{
    tool = 'invoke_gtex_staging_smoke'
    executed_at_utc = [DateTime]::UtcNow.ToString('o')
    base_url = $BaseUrl
    max_latency_ms = $MaxLatencyMs
    passed = [bool]($requiredFailures.Count -eq 0 -and $routeContract.status -ne 'fail')
    required_failure_count = $requiredFailures.Count
    check_count = $checkArray.Count
    route_contract = $routeContract
    checks = $checkArray
}

$outputDir = Split-Path $OutputPath -Parent
if (-not [string]::IsNullOrWhiteSpace($outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
(($summary | ConvertTo-Json -Depth 8) + "`n") | Set-Content -Path $OutputPath -Encoding UTF8

Write-Output ("STAGING_SMOKE_SUMMARY={0}" -f $OutputPath)
Write-Output (($summary | ConvertTo-Json -Depth 8))

if (-not $summary.passed) {
    exit 1
}
