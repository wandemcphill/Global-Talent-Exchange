param(
  [switch]$SkipFlutter,
  [switch]$SkipDiffCheck
)

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

Write-Host '== GTEX production guardrail scanner =='
python tools/guardrails/production_guardrail_scan.py --fail-on violation

Write-Host '== Backend production guard pytest =='
python -m pytest backend/tests/ops/test_canonical_production_guards.py -q

Write-Host '== GTEX canonical acceptance harness =='
python tools/quality/run_gtex_canonical_acceptance.py

if (-not $SkipFlutter) {
  $flutter = Get-Command flutter -ErrorAction SilentlyContinue
  if ($null -eq $flutter) {
    Write-Warning 'Flutter was not found on PATH; skipping frontend guardrail tests. Rerun without -SkipFlutter on a Flutter-enabled runner.'
  } else {
    Write-Host '== Frontend guardrail and canonical match tests =='
    Push-Location frontend
    try {
      python tool/clean_flutter_test_build_state.py
      flutter test `
        test/guardrails/forbidden_text_guard_test.dart `
        test/match_center/canonical_match_center_test.dart `
        test/match_center/live_match_realtime_test.dart `
        -r compact
    } finally {
      Pop-Location
    }
  }
}

if (-not $SkipDiffCheck) {
  Write-Host '== Diff hygiene =='
  git diff --check
}
