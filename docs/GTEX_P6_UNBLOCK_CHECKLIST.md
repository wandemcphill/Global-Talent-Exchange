# GTEX P6 Unblock Checklist

## Purpose

This checklist defines the concrete work required to move `P6` from `READY` to `COMPLETE` and unblock `P7`.

Source of truth:
- `GTEX_TASKS.md`
- `GTEX_PHASED_PROMPTS.md`

This is an execution checklist, not a design note. `P7` stays blocked until every required item below is marked passed with evidence attached.

## Exit Rule

`P6` is complete only when all of the following are true:
- the current-engine ship path is the verified default runtime
- Unity Windows batch build is a real gate on `main`
- hosted live playback is verified end to end after deploy
- staging passes a 15-minute soak run
- production has GTEX-specific observability and rollback-ready operator workflows
- Unity playback completes a full session with moving players, moving ball, stable camera, and no debug overlays

## Owner Roles

- `TL` = GTEX technical lead
- `UE` = Unity and engine owner
- `BE` = backend live-match owner
- `DO` = DevOps and CI owner
- `QA` = release and validation owner
- `OP` = operations and incident owner

## Status Values

- `TODO`
- `IN PROGRESS`
- `BLOCKED`
- `PASSED`
- `FAILED`

## Execution Checklist

| ID | Work Item | Primary Owner | Supporting Owners | Required Actions | Proof Artifacts | Pass Criteria | Fail Criteria | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P6-01 | Make Unity Windows CI mandatory on `main` | `DO` | `UE`, `TL` | Configure the self-hosted Windows Unity runner. Confirm Unity license works under the runner account. Require the `unity-windows-build` job for merge and deploy. Repo-side workflow wiring is now always-on in `.github/workflows/ci-staging.yml`, and the remaining work is the live runner setup plus GitHub branch protection requirement. See `docs/GTEX_P6_01_UNITY_WINDOWS_CI_GATE.md`. | Successful `unity-windows-build` run log, runner config note, PR protection screenshot or settings note, uploaded build log artifact. | A pull request cannot merge unless the Unity Windows build passes. The job runs on the real project and produces a clean build log. | The job is skipped, optional, flaky, or blocked by licensing or runner setup. | `IN PROGRESS` |
| P6-02 | Prove the current-engine path remains the default shipped runtime | `UE` | `TL` | Verify the default ownership path remains legacy bootstrap. Confirm controller-boundary mode is opt-in only. Audit recent GTEX integration changes for new direct legacy coupling. Code-level audit is committed, `GtexStadiumAtmosphere` now consumes controller-owned signals, and live-state fanout now routes through `GtexMatchController` instead of direct legacy events. | Short audit report, code references for default ownership path, grep or review summary of seam usage, signoff note from `TL`. | Default startup path uses the current engine. New GTEX integration code routes through GTEX-owned seams or existing adapters. | Default runtime ownership moved away from the current engine or fresh direct coupling was added without seam coverage. | `PASSED` |
| P6-03 | Capture full-session Unity playback validation | `QA` | `UE`, `BE` | Run a full live playback session on the current-engine path. Validate player motion, ball motion, camera stability, score/clock continuity, and scene stability from bootstrap through session end. Completed with the committed harness in `tools/run_gtex_full_session_validation.ps1` and `tools/gtex_live_full_session_mock_server.py`, plus executed evidence in `docs/GTEX_P6_03_FULL_SESSION_PLAYBACK_VALIDATION.md`. | Validation report, timestamped video capture or screenshot set, Unity log, backend log, match id used for validation. | One full session completes with moving players, moving ball, stable camera, and no ownership regressions. | Session stalls, actors stop moving, camera breaks, score or clock drift is visible, or runtime ownership regresses. | `PASSED` |
| P6-04 | Remove or suppress debug overlays in the shipped validation path | `UE` | `QA` | Confirm startup/debug overlays are not visible in release validation builds. Validate both development and release runtime behavior explicitly. Completed with the production Windows build lane, overlay gating in `GtexLiveStartupOverlay`, corrected full-session release capture in `tools/run_gtex_full_session_validation.ps1`, and refreshed shipped-player evidence in `docs/GTEX_P6_04_RELEASE_PATH_AUDIT.md`. | Screenshot set from release validation, build mode note, code reference to overlay gating behavior, production build log showing `GTEX_PROD`, clean terminating batch-build log, player runtime log from release capture. | Release validation shows no debug overlays during live playback. | Any debug-only overlay appears in the shipped validation path. | `PASSED` |
| P6-05 | Add a committed 15-minute staging soak run | `QA` | `DO`, `UE`, `BE` | Define and run a 15-minute staging soak using the current-engine live playback path. Measure stability across the whole run, not only startup. Repo-side soak tooling is now committed via `tools/run_gtex_staging_soak.ps1`, with the execution lane documented in `docs/GTEX_P6_05_STAGING_SOAK_RUN.md`. A production-path 15-minute capture set now exists as pre-staging evidence, but the remaining work is still to execute the soak against staging and retain the resulting staging artifact set. | Soak report with date, environment, match ids, logs, screenshots, and summary metrics. CI or scripted invocation for the soak where practical. | Staging completes a continuous 15-minute run with stable live playback and no unresolved high-severity defects. | No 15-minute run exists, the run aborts early, or critical defects remain unresolved. | `IN PROGRESS` |
| P6-06 | Verify hosted live match generation after deploy | `BE` | `QA`, `DO` | Exercise `tools/provision_gtex_live_match.py` or equivalent post-deploy flow in staging. Validate match provisioning, access token issuance, refresh token issuance, live route access, and websocket bridge behavior. This is now executed and documented in `docs/GTEX_P6_06_HOSTED_LIVE_VERIFICATION.md`, with a saved production hosted-verification summary proving deployed live access issuance, payload hydration, and websocket advancement. | Provisioning run log, match id, route verification output, websocket verification output, post-deploy report. | A deployed environment can provision a live match and feed Unity playback successfully end to end. | Provisioning fails, live access issuance fails, websocket verification fails, or the match cannot be consumed by Unity. | `PASSED` |
| P6-07 | Harden GTEX-specific observability | `OP` | `BE`, `UE`, `TL` | Add GTEX-specific dashboards and alerts for stale state, websocket churn, auth refresh failures, live-match generation failures, and repeated reconnect degradation. This is now committed through live-route metrics in `backend/app/observability/metrics.py`, route instrumentation in `backend/app/live_matches/router.py` and `backend/app/api_v1/router.py`, dashboard export `ops/observability/grafana/dashboards/gtex-live-playback.json`, alert rules in `ops/observability/prometheus/rules/gtex-alerts.yml`, and the operator note in `docs/GTEX_P6_07_LIVE_OBSERVABILITY.md`. | Dashboard export, alert rule diff, sample metrics or screenshots, operator note describing where each signal lives. | Operators can detect and diagnose the main P6 failure modes quickly using committed dashboards and alert rules. | Only generic platform alerts exist, or GTEX-specific live playback failure modes remain invisible. | `PASSED` |
| P6-08 | Write rollback-ready operator workflows | `OP` | `DO`, `BE`, `UE` | Publish an operator runbook for live Unity playback covering provisioning, post-deploy verification, incident triage, rollback trigger, rollback steps, and post-rollback verification. Completed via `ops/gtex-live-playback-rollback-runbook.md`. | Committed runbook in `Docs/` or `ops/`, rollback checklist, named rollback trigger conditions. | There is a clear documented rollback path that an operator can execute without guessing. | Rollback exists only as tribal knowledge or deploy tooling without a verified procedure. | `PASSED` |
| P6-09 | Validate desktop and mobile render and content readiness | `UE` | `QA` | Validate shaders, materials, kits, stadium imports, and addressables on desktop and mobile targets. Confirm no content-specific regressions in live playback. The signoff checklist and evidence requirements are now documented in `docs/GTEX_P6_09_RENDER_CONTENT_SIGNOFF.md`; the remaining work is the actual desktop/mobile evidence capture and signoff note. | Validation checklist, screenshots or video on desktop and mobile, issue log for any content fixes. | Desktop and mobile render paths are signed off for the current-engine live playback lane. | Any critical content, shader, kit, stadium, or addressable issue remains unresolved. | `IN PROGRESS` |
| P6-10 | Verify live runtime resilience under transport/auth failure modes | `BE` | `UE`, `QA` | Exercise stale transport, reconnect, token refresh, and terminal-match scenarios deliberately. Confirm the current-engine live path degrades cleanly and recovers where intended. Completed with the committed harness in `tools/run_gtex_live_resilience_smoke.ps1` and `tools/gtex_live_resilience_mock_server.py`, plus the executed evidence recorded in `docs/GTEX_P6_10_RUNTIME_RESILIENCE_VERIFICATION.md`. | Test report with scenarios exercised, logs, match ids, and observed outcomes. | Stale transport, reconnect, auth refresh, and terminal-match behaviors are all explicitly verified and documented. | These behaviors are assumed rather than tested, or recovery is inconsistent. | `PASSED` |
| P6-11 | Freeze proof and update the phase gate | `TL` | `UE`, `BE`, `DO`, `QA`, `OP` | Review all evidence above. Record a go or no-go decision for `P6`. If all items pass, update `GTEX_TASKS.md` from `P6 READY` to `P6 COMPLETE`. | Final gate review note, checklist snapshot, diff updating `GTEX_TASKS.md`. | All required items are passed and the project gate is updated. | Evidence is incomplete, contradictory, or unresolved blockers remain. | `TODO` |

## Recommended Execution Order

1. `P6-01` Unity Windows CI mandatory gate
2. `P6-02` current-engine ownership and seam audit
3. `P6-06` hosted live match generation after deploy
4. `P6-10` runtime resilience verification
5. `P6-03` full-session Unity playback validation
6. `P6-04` no-debug-overlay release proof
7. `P6-09` desktop and mobile render and content signoff
8. `P6-07` GTEX-specific observability
9. `P6-08` rollback-ready runbook
10. `P6-05` 15-minute staging soak
11. `P6-11` final gate review and phase update

## Required Evidence Pack For P7 Unblock

Before `P7` can start, the technical lead should be able to point to one evidence pack containing:
- Unity Windows CI proof
- current-engine ownership audit
- full-session Unity playback validation
- no-debug-overlay release validation
- post-deploy live provisioning and websocket verification
- resilience verification for reconnect, stale transport, auth refresh, and terminal-match cases
- desktop and mobile render/content signoff
- GTEX-specific dashboards and alert rules
- rollback runbook
- 15-minute staging soak report
- final `P6` go decision

## Decision Rule

- `UNBLOCK P7`: only if every required item above is `PASSED`
- `KEEP P7 BLOCKED`: if even one required item remains `TODO`, `IN PROGRESS`, `BLOCKED`, or `FAILED`
