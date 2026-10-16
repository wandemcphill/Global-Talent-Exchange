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

    [switch]$SkipWebsocketVerify,

    [switch]$PayToView,

    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'

$root = 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE'
$unityConfigPath = Join-Path $root 'Gtex_Test_Migration\Assets\Resources\GTEX\match-config.json'
$bootstrapPath = Join-Path $root 'tmp\gtex_hosted_live_verification_bootstrap.json'

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $root ("tmp\gtex_{0}_hosted_live_verification_summary.json" -f $Profile)
}

$outputDirectory = Split-Path $OutputPath -Parent
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$arguments = @(
    'tools\provision_gtex_live_match.py',
    '--profile', $Profile,
    '--base-url', $BaseUrl,
    '--unity-config', $unityConfigPath,
    '--bootstrap-path', $bootstrapPath,
    '--dry-run'
)

if (-not [string]::IsNullOrWhiteSpace($UserAccessToken)) {
    $arguments += @('--user-access-token', $UserAccessToken)
}
elseif (-not [string]::IsNullOrWhiteSpace($UserEmail) -and -not [string]::IsNullOrWhiteSpace($UserPassword)) {
    $arguments += @('--user-email', $UserEmail, '--user-password', $UserPassword)
}
else {
    throw 'Hosted live verification requires either -UserAccessToken or both -UserEmail and -UserPassword.'
}

if (-not [string]::IsNullOrWhiteSpace($MatchId)) {
    $arguments += @('--match-id', $MatchId)
}
elseif ($AllowMatchGeneration.IsPresent) {
    $arguments += '--allow-match-generation'
}

if ($SkipWebsocketVerify.IsPresent) {
    $arguments += '--skip-websocket-verify'
}

if ($PayToView.IsPresent) {
    $arguments += '--pay-to-view'
}

$rawOutput = & python @arguments 2>&1
if ($LASTEXITCODE -ne 0) {
    throw ("Hosted live verification failed.`n" + ($rawOutput -join "`n"))
}

$jsonText = ($rawOutput -join "`n").Trim()
$provisionSummary = $jsonText | ConvertFrom-Json

$summary = [ordered]@{
    executed_at_utc = [DateTime]::UtcNow.ToString('o')
    profile = $Profile
    base_url = $BaseUrl
    verification_passed = $true
    verification_mode = 'hosted_live_contract'
    command = ('python ' + ($arguments -join ' '))
    summary = $provisionSummary
}

($summary | ConvertTo-Json -Depth 8) + "`n" | Set-Content -Path $OutputPath -Encoding UTF8

Write-Output ("SUMMARY_PATH={0}" -f $OutputPath)
Write-Output (($summary | ConvertTo-Json -Depth 8))
