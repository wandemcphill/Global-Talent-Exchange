param(
  [string]$LiveUrl = "",
  [string]$DiffBase = "HEAD",
  [string]$DiffHead = "",
  [switch]$StrictDiff,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "quality\run_gtex_canonical_acceptance.py"
$arguments = @($scriptPath)

if ($LiveUrl.Trim().Length -gt 0) {
  $arguments += @("--live-url", $LiveUrl)
}

if ($DiffBase.Trim().Length -gt 0) {
  $arguments += @("--diff-base", $DiffBase)
} else {
  $arguments += @("--diff-base", "")
}

if ($DiffHead.Trim().Length -gt 0) {
  $arguments += @("--diff-head", $DiffHead)
}

if ($StrictDiff.IsPresent) {
  $arguments += "--strict-diff"
}

if ($Json.IsPresent) {
  $arguments += "--json"
}

python @arguments
exit $LASTEXITCODE
