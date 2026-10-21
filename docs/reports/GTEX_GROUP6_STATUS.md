# GTEX Group 6 Status Ledger

## Repository lane

| Gate | Status | Evidence |
|---|---|---|
| Live frontend build requires API base URL | GREEN | `ops/render/build-frontend.sh` fails fast when `GTE_API_BASE_URL` is absent |
| KoraPay environment contract | GREEN | Production and Kubernetes templates contain secret, webhook secret, redirect and notification variables |
| Correct KoraPay webhook route | GREEN | `/integrations/payments/korapay/webhook` is the documented callback contract |
| Player-share buy compliance | GREEN | Buy route uses `get_current_trading_user` |
| Player-share sell compliance | GREEN | Sell route uses `get_current_trading_user` |
| Bulk player-share issuance policy & runner | GREEN | `backend/config/player_share_issuance.toml`, `backend/scripts/issue_player_share_markets.py`, and `backend/scripts/issue_player_share_markets_strict.py` exist |
| Hosted competition invites | GREEN | Invite router/tests exist |
| Admin runtime state | GREEN | `AdminRuntimeState` is the database-backed state source; legacy file state is reconciled/imported |
| Unity Windows CI gate (`P6-01`) | GREEN | Workflow is present in `ci-staging.yml` and `deploy-production.yml`, uses `BuildWindows64ProductionFromCommandLine`, and explicitly classifies Unity licensing failures (`docs/GTEX_P6_01_UNITY_WINDOWS_CI_GATE.md`) |
| Current-engine ownership & seam audit (`P6-02`) | GREEN | `GtexMatchController` keeps `LegacyBootstrap` default and routes runtime/atmosphere/scoreboard signals through GTEX seams (`docs/GTEX_P6_02_CURRENT_ENGINE_OWNERSHIP_AUDIT.md`) |
| Full-session Unity playback validation (`P6-03`) | GREEN | Kickoff-to-fulltime (`0'`–`90'`) harness and `Gtex3DFullSessionVerifier` committed and verified (`docs/GTEX_P6_03_FULL_SESSION_PLAYBACK_VALIDATION.md`) |
| Release-path no-debug-overlay audit (`P6-04`) | GREEN | `GtexLiveStartupOverlay` suppressed in `GTEX_PROD` builds and kinematic ball warnings resolved (`docs/GTEX_P6_04_RELEASE_PATH_AUDIT.md`) |
| 15-minute soak runner & deployed proof (`P6-05`) | GREEN | `tools/run_gtex_staging_soak.ps1` committed and 15-minute deployed production-path soak verified (`docs/GTEX_P6_05_STAGING_SOAK_RUN.md`) |
| Hosted live match generation verification (`P6-06`) | GREEN | `tools/run_gtex_hosted_live_verification.ps1` and `tools/provision_gtex_live_match.py` verified against deployed production lane (`docs/GTEX_P6_06_HOSTED_LIVE_VERIFICATION.md`) |
| GTEX live observability (`P6-07`) | GREEN | Prometheus counters, Grafana dashboard (`gtex-live-playback.json`), and alert rules (`gtex-alerts.yml`) committed and tested (`docs/GTEX_P6_07_LIVE_OBSERVABILITY.md`) |
| Live playback rollback runbook (`P6-08`) | GREEN | `ops/gtex-live-playback-rollback-runbook.md` documents triggers `R1`–`R5`, rollback order, and verification |
| Desktop & mobile render/content signoff (`P6-09`) | GREEN | `GtexRenderConfig`, `GtexRenderPipelineRepairTools` (`PC_RPAsset`/`Mobile_RPAsset`), `GtexLivePitchPresentation` occluder fix, and Android APK/`unityLibrary` export verified (`docs/GTEX_P6_09_RENDER_CONTENT_SIGNOFF.md`) |
| Runtime resilience verification (`P6-10`) | GREEN | `tools/run_gtex_live_resilience_smoke.ps1` and `tools/gtex_live_resilience_mock_server.py` verified for `4401` refresh, stale-transport reconnect, and terminal match (`docs/GTEX_P6_10_RUNTIME_RESILIENCE_VERIFICATION.md`) |
| P6 final gate review (`P6-11`) | GREEN | `docs/GTEX_P6_UNBLOCK_CHECKLIST.md` (`P6-01`–`P6-11` `PASSED`) and `docs/reports/GTEX_P6_PRODUCTION_GAP_BACKLOG.md` updated |
| Group 6 release audit | GREEN | Added to Quality Gates (`backend/scripts/audit_group6_production_readiness.py`) |
| Backup/restore rehearsal tooling | GREEN | Safe isolated-target helper added |
| Rollback preflight | GREEN | Migration-aware, non-destructive rollback helper added |
| Bounded soak tooling | GREEN | HTTP concurrency/latency harness added |

## Runtime lane

The following are deliberately **OPEN/BLOCKED**, because repository code cannot manufacture real production evidence:

1. Confirm the canonical deployed backend URL.
2. Confirm the bootstrap admin secret is in the real vault and injected into staging/production.
3. Execute real KoraPay staging checkout -> redirect -> webhook -> settlement with real credentials.
4. Import/publish/issue the approved 5000+ real-player cohort and verify it live.
5. Execute authenticated GTEX and hosted competition E2E flows in staging.
6. Run the 15-minute realtime/live-match soak on a dedicated staging host when healthy (`P6-05` accepted deployed production-path soak for current gate).
7. Run PostgreSQL wallet/treasury concurrency soak against staging.
8. Execute backup -> isolated restore rehearsal against the real staging database.
9. Execute controlled deployment rollback rehearsal.
10. Run Unity Windows batch build on a licensed self-hosted GitHub Actions runner and enforce branch protection on `main`.
11. Capture production monitoring/alert evidence from a live Grafana/Alertmanager instance.

## Launch rule

Do not convert an OPEN/BLOCKED runtime item to GREEN merely because the repository contains the corresponding code or test. Group 6 is fully launch-certified only after the runtime lane has real evidence for every mandatory item.

## CI synchronization

The Group 6 branch contains the latest certification fixes and P6 current-engine hardening verification (`P6-01` through `P6-11`). This ledger change intentionally triggers a fresh pull-request merge ref so Quality Gates evaluate the current branch head rather than an obsolete merge ref.
