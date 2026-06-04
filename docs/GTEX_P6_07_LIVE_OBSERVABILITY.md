# GTEX P6-07 Live Observability Hardening

## Scope

This document closes the repo-side work for `P6-07`:
- GTEX-specific live match center metrics
- GTEX-specific dashboards
- GTEX-specific alert rules
- operator references for the main current-engine failure modes

This item is about committed operator visibility, not just generic platform telemetry.

## Added Signals

The backend metrics layer now emits GTEX live match center counters for:
- Legacy match runtime access issuance and refresh outcomes via `gtex_legacy_match_runtime_access_total`
- Legacy match runtime payload bridge outcomes via `gtex_legacy_match_runtime_payload_total`
- Legacy match runtime websocket lifecycle events via `gtex_legacy_match_runtime_websocket_events_total`
- generated live-match bootstrap outcomes via `gtex_legacy_match_runtime_generated_match_total`

Code references:
- metrics definitions: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\backend\app\observability\metrics.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/observability/metrics.py>)
- access/payload instrumentation: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\backend\app\live_matches\router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/live_matches/router.py>)
- websocket churn / stale-state instrumentation: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\backend\app\api_v1\router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/api_v1/router.py>)

## Failure Modes Covered

The committed signals now cover the P6 live failure modes directly:
- stale state:
  - `gtex_legacy_match_runtime_websocket_events_total{event="stale_state",result="detected"}`
- websocket churn / reconnect degradation:
  - `gtex_legacy_match_runtime_websocket_events_total{event="accepted",result="success"}`
  - `gtex_legacy_match_runtime_websocket_events_total{event="closed",result!="terminal"}`
  - `gtex_legacy_match_runtime_websocket_events_total{event="reject",...}`
- auth refresh failures:
  - `gtex_legacy_match_runtime_access_total{action="refresh",result!="success"}`
- live-match generation failures:
  - `gtex_legacy_match_runtime_generated_match_total{result="missing_stream"}`
- payload bridge failures:
  - `gtex_legacy_match_runtime_payload_total{transport=...,result=~"unavailable|error|not_found"}`

## Dashboard Export

Committed dashboard export:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\ops\observability\grafana\dashboards\gtex-live-match-center.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/ops/observability/grafana/dashboards/gtex-live-match-center.json>)

The dashboard includes:
- Legacy runtime access failure stat
- Legacy runtime refresh failure stat
- stale-state detection stat
- generated match bootstrap failure stat
- Legacy runtime access/refresh outcome time series
- websocket churn and payload outcome time series

## Alert Rules

Committed Prometheus alert rules:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\ops\observability\prometheus\rules\gtex-alerts.yml](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/ops/observability/prometheus/rules/gtex-alerts.yml>)

Added GTEX live alerts:
- `GTexLegacyMatchRuntimeRefreshFailuresHigh`
- `GTexLegacyMatchRuntimePayloadFailuresHigh`
- `GTexLegacyMatchRuntimeStaleStateDetected`
- `GTexLegacyMatchRuntimeWebsocketRejectsHigh`
- `GTexLegacyMatchRuntimeReconnectChurnHigh`
- `GTexLegacyMatchRuntimeGenerationFailuresHigh`

## Operator Notes

Primary operator surfaces:
- general stack instructions: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\ops\observability\README.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/ops/observability/README.md>)
- rollback/triage runbook: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\ops\gtex-live-match-center-rollback-runbook.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/ops/gtex-live-match-center-rollback-runbook.md>)

Recommended triage sequence when an alert fires:
1. Check `gtex-live-match-center.json` for whether the issue is access, payload, websocket churn, or generated-match bootstrap.
2. If access/refresh failures are rising, run the hosted verification lane in [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_hosted_live_verification.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_hosted_live_verification.ps1>).
3. If websocket churn or stale-state alerts are firing, compare the dashboard to the player/runtime evidence from the full-session and resilience lanes.
4. If generated-match failures are rising, verify infinite-league stream bootstrap before escalating to a player/runtime incident.

## Verification

Pinned by tests:
- metrics coverage: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\backend\tests\observability\test_metrics.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/tests/observability/test_metrics.py>)
- dashboard / alert coverage: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\backend\tests\observability\test_monitoring_dashboard.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/tests/observability/test_monitoring_dashboard.py>)

## Current Status

Current status: `PASSED`

What remains outside this item:
- loading the dashboard into a live Grafana instance
- routing alerts to the production/staging operator channel
- collecting live screenshots from a running control tower instance when operationally convenient
