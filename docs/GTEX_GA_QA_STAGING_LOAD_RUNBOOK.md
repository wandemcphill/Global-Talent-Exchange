# GTEX GA QA, Staging, And Load Runbook

Date: 2026-06-06

Scope: Thread 8 QA/staging/load harnesses. These tools are read-only against the app unless an operator manually performs a deploy rollback outside the scripts.

## Guardrails

- Use KoraPay and manual bank transfer only. There is no Paystack or crypto launch rail in this runbook.
- Do not test production Unity, native-3D, pseudo-3D, or monetized 3D routes.
- Missing match or market data is a blocked/degraded result, not a reason to invent fixture truth.
- Run from `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE` in PowerShell.

## Visual QA Screenshots

Capture desktop, tablet, and mobile screenshots with Microsoft Edge or Chrome headless:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\visual\capture_gtex_visual_qa.ps1 `
  -BaseUrl "https://<staging-web-host>" `
  -SettleSeconds 2 `
  -OutputDir ".\tmp\visual_qa_staging"
```

Optional route override:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\visual\capture_gtex_visual_qa.ps1 `
  -BaseUrl "https://<staging-web-host>" `
  -Routes "/", "/app/world", "/app/market", "/app/compete" `
  -Viewports "desktop=1440x900", "tablet=1024x1366", "mobile=390x844" `
  -OutputDir ".\tmp\visual_qa_market_compete"
```

Include match viewer only with an existing backend-authored match key:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\visual\capture_gtex_visual_qa.ps1 `
  -BaseUrl "https://<staging-web-host>" `
  -MatchKey "<existing-backend-authored-match-key>" `
  -RequireMatchViewer `
  -OutputDir ".\tmp\visual_qa_match_viewer"
```

Pass criteria:

- The command exits `0`.
- `visual_qa_manifest.json` reports `"passed": true`.
- Every route has `desktop`, `tablet`, and `mobile` PNGs.
- Each PNG is at least `5000` bytes and dimensions match the requested viewport.
- Manual reviewer confirms no production CTA or nav item exposes Unity/native-3D/pseudo-3D.
- Blocked/loading/syncing/degraded/error states are acceptable when backend data is absent.

Fail criteria:

- Browser missing, screenshot timeout, file smaller than threshold, blank/missing PNG, or any production 3D route/CTA visible.

## Staging Smoke

Run core read-only backend smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\staging\invoke_gtex_staging_smoke.ps1 `
  -BaseUrl "https://<staging-api-host>" `
  -VerifyMatchCenterRoutes `
  -OutputPath ".\tmp\staging_smoke.json"
```

Include optional market and match-center probes:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\staging\invoke_gtex_staging_smoke.ps1 `
  -BaseUrl "https://<staging-api-host>" `
  -IncludeOptionalMarket `
  -IncludeOptionalMatchCenter `
  -MatchId "<existing-backend-authored-match-id>" `
  -VerifyMatchCenterRoutes `
  -OutputPath ".\tmp\staging_smoke_match.json"
```

Pass criteria:

- Required endpoints `/health`, `/ready`, `/version`, and `/diagnostics` return `2xx`.
- When `-VerifyMatchCenterRoutes` is set, hosted OpenAPI exposes canonical 2D match-center routes and does not expose quarantined Unity/native/pseudo-3D route fragments.
- Required endpoint latency is `<= 2000 ms` by default.
- Optional market/match checks use mounted runtime paths such as `/api/market/players`, `/api/matches/live/active`, and `/api/match-viewer/{match_id}`; they may be `blocked` only when data is missing or no match id is supplied.

Fail criteria:

- Any required endpoint errors, times out, or exceeds the latency threshold.
- Optional match-center route returns fabricated/local truth instead of backend-authored payloads.

## Rollback Rehearsal

Compare current staging/prod candidate with the rollback candidate URL before a release window:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\staging\invoke_gtex_rollback_rehearsal.ps1 `
  -CurrentBaseUrl "https://<current-api-host>" `
  -RollbackBaseUrl "https://<previous-release-api-host>" `
  -CurrentReleaseId "<current-render-deploy-id-or-git-sha>" `
  -RollbackReleaseId "<known-good-render-deploy-id-or-git-sha>" `
  -VerifyMatchCenterRoutes `
  -OutputPath ".\tmp\rollback_rehearsal.json"
```

Pass criteria:

- Current and rollback candidate both pass `/health`, `/ready`, `/version`, and `/diagnostics`.
- Current and rollback candidate both pass canonical 2D match-center route verification when `-VerifyMatchCenterRoutes` is set.
- The generated JSON captures the manual Render rollback steps for the release captain.
- Release captain records current and rollback release identifiers before any manual rollback action.

Fail criteria:

- Either current or rollback candidate fails core smoke.
- No known previous successful deploy exists.

## Load And Perf Harness

Use the Python 3.14 runtime requested for this workspace:

```powershell
& C:\Python314\python.exe .\tools\load\gtex_load_probe.py `
  --base-url "https://<staging-api-host>" `
  --requests-per-endpoint 25 `
  --concurrency 5 `
  --output ".\tmp\gtex_load_probe_market.json"
```

Include match-center endpoints only with an existing backend-authored match:

```powershell
& C:\Python314\python.exe .\tools\load\gtex_load_probe.py `
  --base-url "https://<staging-api-host>" `
  --match-id "<existing-backend-authored-match-id>" `
  --require-match `
  --requests-per-endpoint 25 `
  --concurrency 5 `
  --max-p95-ms 1500 `
  --output ".\tmp\gtex_load_probe_match.json"
```

Optional websocket probe:

```powershell
& C:\Python314\python.exe .\tools\load\gtex_load_probe.py `
  --base-url "https://<staging-api-host>" `
  --websocket-url "wss://<staging-api-host>/ws/match/<match-id>" `
  --match-id "<existing-backend-authored-match-id>" `
  --require-match `
  --output ".\tmp\gtex_load_probe_ws.json"
```

Pass criteria:

- Required endpoint error rate is `<= 1%`.
- Required endpoint p95 latency is `<= 1500 ms` unless the release captain sets a stricter threshold.
- Concurrency stays `<= 32`.
- Match-center probes are required only when `--require-match` is set.
- Websocket probe is optional unless `--require-websocket` is set.

Fail criteria:

- Required endpoint p95 or error rate exceeds threshold.
- Required match id is missing.
- Required websocket probe cannot connect or cannot receive a first message.

## Evidence To Attach To Release Ticket

- Visual QA manifest and screenshot directory.
- Staging smoke JSON.
- Rollback rehearsal JSON.
- Load probe JSON and raw samples when captured.
- `git diff --check` output for Thread 8 paths.
- Manual reviewer notes for blocked/degraded screens.
