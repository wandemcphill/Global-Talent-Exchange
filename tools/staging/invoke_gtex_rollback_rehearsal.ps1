param(
    [Parameter(Mandatory = $true)]
    [string]$CurrentBaseUrl,

    [Parameter(Mandatory = $true)]
    [string]$RollbackBaseUrl,

    [string]$BearerToken = '',

    [string]$OutputPath = '',

    [int]$TimeoutSeconds = 15,

    [int]$MaxLatencyMs = 2500,

    [string]$CurrentReleaseId = '',

    [string]$RollbackReleaseId = '',

    [switch]$VerifyMatchCenterRoutes,

    [string]$PythonPath = 'C:\Python314\python.exe'
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $OutputPath = Join-Path $root "tmp\rollback_rehearsal_$stamp.json"
}

function Join-Url {
    param(
        [string]$RootUrl,
        [string]$Path
    )

    return $RootUrl.TrimEnd('/') + '/' + $Path.TrimStart('/')
}

function Invoke-ReadOnlyCheck {
    param(
        [string]$BaseUrl,
        [string]$Name,
        [string]$Path
    )

    $headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($BearerToken)) {
        $headers['Authorization'] = "Bearer $BearerToken"
    }

    $url = Join-Url -RootUrl $BaseUrl -Path $Path
    $started = Get-Date
    try {
        $request = [System.Net.HttpWebRequest]::Create($url)
        $request.Method = 'GET'
        $request.Timeout = $TimeoutSeconds * 1000
        $request.ReadWriteTimeout = $TimeoutSeconds * 1000
        $request.KeepAlive = $false
        $request.UserAgent = 'gtex-rollback-rehearsal/1.0'
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
            status_code = $statusCode
            latency_ms = $durationMs
            bytes = ([string]$body).Length
            passed = [bool]$passed
            reason = if ($passed) { '' } else { "Expected 2xx and <= $MaxLatencyMs ms." }
        }
    } catch {
        return [ordered]@{
            name = $Name
            path = $Path
            url = $url
            status_code = 0
            latency_ms = [math]::Round(((Get-Date) - $started).TotalMilliseconds, 1)
            bytes = 0
            passed = $false
            reason = $_.Exception.Message
        }
    }
}

function Invoke-SmokeSet {
    param([string]$BaseUrl)

    $checks = New-Object System.Collections.Generic.List[object]
    foreach ($item in @(
        @{ name = 'health'; path = '/health' },
        @{ name = 'readiness'; path = '/ready' },
        @{ name = 'version'; path = '/version' },
        @{ name = 'diagnostics'; path = '/diagnostics' }
    )) {
        $checks.Add((Invoke-ReadOnlyCheck -BaseUrl $BaseUrl -Name $item.name -Path $item.path))
    }

    return [object[]]$checks.ToArray()
}

function Invoke-RouteContract {
    param([string]$BaseUrl)

    if (-not $VerifyMatchCenterRoutes.IsPresent) {
        return [ordered]@{
            requested = $false
            status = 'skipped'
            exit_code = $null
            output = ''
        }
    }

    $routeVerifier = Join-Path $root 'ops\render\verify_match_center_routes.py'
    if (-not (Test-Path $routeVerifier)) {
        return [ordered]@{
            requested = $true
            status = 'fail'
            exit_code = $null
            output = "Route verifier not found: $routeVerifier"
        }
    }
    if (-not (Test-Path $PythonPath)) {
        return [ordered]@{
            requested = $true
            status = 'fail'
            exit_code = $null
            output = "PythonPath not found: $PythonPath"
        }
    }

    $routeOutput = & $PythonPath $routeVerifier --url $BaseUrl --timeout-seconds $TimeoutSeconds 2>&1
    return [ordered]@{
        requested = $true
        status = if ($LASTEXITCODE -eq 0) { 'pass' } else { 'fail' }
        exit_code = $LASTEXITCODE
        output = ($routeOutput -join "`n")
    }
}

$currentChecks = Invoke-SmokeSet -BaseUrl $CurrentBaseUrl
$rollbackChecks = Invoke-SmokeSet -BaseUrl $RollbackBaseUrl
$currentRouteContract = Invoke-RouteContract -BaseUrl $CurrentBaseUrl
$rollbackRouteContract = Invoke-RouteContract -BaseUrl $RollbackBaseUrl
$currentPassed = -not @($currentChecks | Where-Object { -not $_.passed })
$rollbackPassed = -not @($rollbackChecks | Where-Object { -not $_.passed })
$currentRoutePassed = [bool]($currentRouteContract.status -ne 'fail')
$rollbackRoutePassed = [bool]($rollbackRouteContract.status -ne 'fail')

$summary = [ordered]@{
    tool = 'invoke_gtex_rollback_rehearsal'
    executed_at_utc = [DateTime]::UtcNow.ToString('o')
    current_base_url = $CurrentBaseUrl
    rollback_base_url = $RollbackBaseUrl
    current_release_id = $CurrentReleaseId
    rollback_release_id = $RollbackReleaseId
    passed = [bool]($currentPassed -and $rollbackPassed -and $currentRoutePassed -and $rollbackRoutePassed)
    current_passed = [bool]$currentPassed
    rollback_candidate_passed = [bool]$rollbackPassed
    current_route_contract = $currentRouteContract
    rollback_route_contract = $rollbackRouteContract
    rehearsal_steps = @(
        'Confirm current release health/readiness/version/diagnostics are green.',
        'Confirm rollback candidate health/readiness/version/diagnostics are green.',
        'Record current and rollback release identifiers from Render before any manual deploy action.',
        'If current release fails production smoke, use Render rollback/redeploy previous successful deploy.',
        'Run staging smoke against the post-rollback URL before reopening traffic or announcing recovery.'
    )
    current_checks = [object[]]$currentChecks
    rollback_checks = [object[]]$rollbackChecks
}

$outputDir = Split-Path $OutputPath -Parent
if (-not [string]::IsNullOrWhiteSpace($outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
(($summary | ConvertTo-Json -Depth 8) + "`n") | Set-Content -Path $OutputPath -Encoding UTF8

Write-Output ("ROLLBACK_REHEARSAL_SUMMARY={0}" -f $OutputPath)
Write-Output (($summary | ConvertTo-Json -Depth 8))

if (-not $summary.passed) {
    exit 1
}
