param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string[]]$Routes = @(
        '/',
        '/app/world',
        '/app/market',
        '/app/club',
        '/app/compete',
        '/app/capital',
        '/app/community',
        '/app/creator',
        '/app/admin'
    ),

    [string]$OutputDir = '',

    [string]$BrowserPath = '',

    [int]$MinBytes = 5000,

    [int]$TimeoutSeconds = 30,

    [string[]]$Viewports = @('desktop=1440x900', 'tablet=1024x1366', 'mobile=390x844'),

    [int]$SettleSeconds = 2,

    [string]$MatchKey = '',

    [switch]$RequireMatchViewer
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $OutputDir = Join-Path $root "tmp\visual_qa_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path

function Parse-Viewport {
    param([string]$Definition)

    if ($Definition -notmatch '^([A-Za-z0-9_.-]+)=([0-9]+)x([0-9]+)$') {
        throw "Invalid viewport '$Definition'. Expected name=WIDTHxHEIGHT, for example desktop=1440x900."
    }

    return [pscustomobject]@{
        name = $Matches[1]
        width = [int]$Matches[2]
        height = [int]$Matches[3]
    }
}

$viewportRecords = @($Viewports | ForEach-Object { Parse-Viewport -Definition $_ })

if ($RequireMatchViewer.IsPresent -and [string]::IsNullOrWhiteSpace($MatchKey)) {
    throw '-RequireMatchViewer requires -MatchKey for an existing backend-authored match.'
}

if (-not [string]::IsNullOrWhiteSpace($MatchKey)) {
    $Routes += "/matches/viewer/$MatchKey"
}

function Resolve-BrowserPath {
    param([string]$RequestedPath)

    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        if (-not (Test-Path $RequestedPath)) {
            throw "BrowserPath does not exist: $RequestedPath"
        }
        return (Resolve-Path $RequestedPath).Path
    }

    $candidates = @(
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    )

    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    foreach ($name in @('msedge.exe', 'chrome.exe', 'chromium.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $command.Source
        }
    }

    throw 'No supported browser found. Install Microsoft Edge or Chrome, or pass -BrowserPath.'
}

function Join-Url {
    param(
        [string]$RootUrl,
        [string]$Route
    )

    $trimmedRoot = $RootUrl.TrimEnd('/')
    if ([string]::IsNullOrWhiteSpace($Route) -or $Route -eq '/') {
        return $trimmedRoot + '/'
    }

    return $trimmedRoot + '/' + $Route.TrimStart('/')
}

function Get-SafeRouteName {
    param([string]$Route)

    if ([string]::IsNullOrWhiteSpace($Route) -or $Route -eq '/') {
        return 'root'
    }

    $safe = $Route.Trim('/').Replace('/', '_')
    $safe = $safe -replace '[^A-Za-z0-9_.-]', '_'
    if ([string]::IsNullOrWhiteSpace($safe)) {
        return 'root'
    }
    return $safe
}

function Read-PngDimensions {
    param([string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 24) {
        throw "PNG file is too small to read dimensions: $Path"
    }

    $signature = [byte[]](137, 80, 78, 71, 13, 10, 26, 10)
    for ($index = 0; $index -lt $signature.Length; $index++) {
        if ($bytes[$index] -ne $signature[$index]) {
            throw "File is not a PNG screenshot: $Path"
        }
    }

    $widthBytes = [byte[]]($bytes[16], $bytes[17], $bytes[18], $bytes[19])
    $heightBytes = [byte[]]($bytes[20], $bytes[21], $bytes[22], $bytes[23])
    if ([BitConverter]::IsLittleEndian) {
        [Array]::Reverse($widthBytes)
        [Array]::Reverse($heightBytes)
    }

    $width = [BitConverter]::ToInt32($widthBytes, 0)
    $height = [BitConverter]::ToInt32($heightBytes, 0)
    return [ordered]@{ width = $width; height = $height }
}

$browser = Resolve-BrowserPath -RequestedPath $BrowserPath
$results = New-Object System.Collections.Generic.List[object]

foreach ($route in $Routes) {
    foreach ($viewport in $viewportRecords) {
        $viewportName = [string]$viewport.name
        $viewportWidth = [int]$viewport.width
        $viewportHeight = [int]$viewport.height
        $routeName = Get-SafeRouteName -Route $route
        $fileName = "{0}_{1}_{2}x{3}.png" -f $routeName, $viewportName, $viewportWidth, $viewportHeight
        $screenshotPath = Join-Path $OutputDir $fileName
        $browserErrorPath = Join-Path $OutputDir ($fileName + '.browser.err.log')
        $url = Join-Url -RootUrl $BaseUrl -Route $route
        $userDataDir = Join-Path $OutputDir ("browser_profile_{0}_{1}" -f $routeName, $viewportName)

        $arguments = @(
            '--headless',
            '--disable-gpu',
            '--hide-scrollbars',
            '--no-first-run',
            '--no-default-browser-check',
            "--user-data-dir=$userDataDir",
            "--window-size=$viewportWidth,$viewportHeight",
            "--screenshot=$screenshotPath",
            $url
        )

        $startedAt = Get-Date
        if ($SettleSeconds -gt 0) {
            Start-Sleep -Seconds $SettleSeconds
        }
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $browserOutput = @(& $browser @arguments 2>&1)
            $browserExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        if ($null -eq $browserExitCode) {
            $browserExitCode = 0
        }
        if ($browserOutput.Count -gt 0) {
            ($browserOutput -join "`n") | Set-Content -Path $browserErrorPath -Encoding UTF8
        } else {
            '' | Set-Content -Path $browserErrorPath -Encoding UTF8
        }

        $exists = Test-Path $screenshotPath
        $length = if ($exists) { (Get-Item $screenshotPath).Length } else { 0 }
        $dimensions = if ($exists) { Read-PngDimensions -Path $screenshotPath } else { [ordered]@{ width = 0; height = 0 } }
        $dimensionsMatch = $dimensions.width -eq $viewportWidth -and $dimensions.height -eq $viewportHeight
        $passed = $browserExitCode -eq 0 -and $exists -and $length -ge $MinBytes -and $dimensionsMatch

        $results.Add([ordered]@{
            route = $route
            url = $url
            viewport = $viewportName
            expected_width = $viewportWidth
            expected_height = $viewportHeight
            png_width = $dimensions.width
            png_height = $dimensions.height
            screenshot = $screenshotPath
            bytes = $length
            dimensions_match = [bool]$dimensionsMatch
            browser_error_log = $browserErrorPath
            duration_ms = [math]::Round(((Get-Date) - $startedAt).TotalMilliseconds, 1)
            exit_code = $browserExitCode
            passed = [bool]$passed
        })
    }
}

$resultArray = [object[]]$results.ToArray()
$summary = [ordered]@{
    tool = 'capture_gtex_visual_qa'
    executed_at_utc = [DateTime]::UtcNow.ToString('o')
    base_url = $BaseUrl
    output_dir = (Resolve-Path $OutputDir).Path
    browser = $browser
    min_bytes = $MinBytes
    route_count = $Routes.Count
    viewport_count = $viewportRecords.Count
    screenshot_count = $resultArray.Count
    passed = [bool](-not @($resultArray | Where-Object { -not $_.passed }))
    results = $resultArray
}

$manifestPath = Join-Path $OutputDir 'visual_qa_manifest.json'
(($summary | ConvertTo-Json -Depth 8) + "`n") | Set-Content -Path $manifestPath -Encoding UTF8

Write-Output ("VISUAL_QA_MANIFEST={0}" -f $manifestPath)
Write-Output (($summary | ConvertTo-Json -Depth 8))

if (-not $summary.passed) {
    exit 1
}
