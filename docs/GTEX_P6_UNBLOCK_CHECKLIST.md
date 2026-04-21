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
| P6-01 | Make Unity Windows CI mandatory on `main` | `DO` | `UE`, `TL` | Configure the self-hosted Windows Unity runner. Confirm Unity license works under the runner account. Require the `unity-windows-build` job for merge and deploy. Repo-side workflow gating is implemented; remaining work is the live runner setup plus GitHub branch protection requirement. | Successful `unity-windows-build` run log, runner config note, PR protection screenshot or settings note, uploaded build log artifact. | A pull request cannot merge unless the Unity Windows build passes. The job runs on the real project and produces a clean build log. | The job is skipped, optional, flaky, or blocked by licensing or runner setup. | `IN PROGRESS` |
| P6-02 | Prove the current-engine path remains the default shipped runtime | `UE` | `TL` | Verify the default ownership path remains legacy bootstrap. Confirm controller-boundary mode is opt-in only. Audit recent GTEX integration changes for new direct legacy coupling. Code-level audit is committed, `GtexStadiumAtmosphere` now consumes controller-owned signals, and live-state fanout now routes through `GtexMatchController` instead of direct legacy events. | Short audit report, code references for default ownership path, grep or review summary of seam usage, signoff note from `TL`. | Default startup path uses the current engine. New GTEX integration code routes through GTEX-owned seams or existing adapters. | Default runtime ownership moved away from the current engine or fresh direct coupling was added without seam coverage. | `PASSED` |
| P6-03 | Capture full-session Unity playback validation | `QA` | `UE`, `BE` | Run a full live playback session on the current-engine path. Validate player motion, ball motion, camera stability, score/clock continuity, and scene stability from bootstrap through session end. | Validation report, timestamped video capture or screenshot set, Unity log, backend log, match id used for validation. | One full session completes with moving players, moving ball, stable camera, and no ownership regressions. | Session stalls, actors stop moving, camera breaks, score or clock drift is visible, or runtime ownership regresses. | `TODO` |
| P6-04 | Remove or suppress debug overlays in the shipped validation path | `UE` | `QA` | Confirm startup/debug overlays are not visible in release validation builds. Validate both development and release runtime behavior explicitly. Release-path entrypoints now use the production Windows build method, `GtexLiveStartupOverlay` is gated to editor or `GTEX_DEV` builds only, a clean local production batch build is proven through the Windows no-sleep wrapper, and authenticated live-playback capture now exists in the shipped player. Remaining work is a stronger motion capture pack plus a post-ball-cleanup production rerun after the Bee export hang is resolved. | Screenshot set from release validation, build mode note, code reference to overlay gating behavior, production build log showing `GTEX_PROD`, clean terminating batch-build log, player runtime log from release capture. | Release validation shows no debug overlays during live playback. | Any debug-only overlay appears in the shipped validation path. | `IN PROGRESS` |
| P6-05 | Add a committed 15-minute staging soak run | `QA` | `DO`, `UE`, `BE` | Define and run a 15-minute staging soak using the current-engine live playback path. Measure stability across the whole run, not only startup. Store the results in a committed report or release artifact. | Soak report with date, environment, match ids, logs, screenshots, and summary metrics. CI or scripted invocation for the soak where practical. | Staging completes a continuous 15-minute run with stable live playback and no unresolved high-severity defects. | No 15-minute run exists, the run aborts early, or critical defects remain unresolved. | `TODO` |
| P6-06 | Verify hosted live match generation after deploy | `BE` | `QA`, `DO` | Exercise `tools/provision_gtex_live_match.py` or equivalent post-deploy flow in staging. Validate match provisioning, access token issuance, refresh token issuance, live route access, and websocket bridge behavior. | Provisioning run log, match id, route verification output, websocket verification output, post-deploy report. | A deployed environment can provision a live match and feed Unity playback successfully end to end. | Provisioning fails, live access issuance fails, websocket verification fails, or the match cannot be consumed by Unity. | `TODO` |
| P6-07 | Harden GTEX-specific observability | `OP` | `BE`, `UE`, `TL` | Add GTEX-specific dashboards and alerts for stale state, websocket churn, auth refresh failures, live-match generation failures, and repeated reconnect degradation. Wire those alerts into the control tower docs and alert rules. | Dashboard export, alert rule diff, sample metrics or screenshots, operator note describing where each signal lives. | Operators can detect and diagnose the main P6 failure modes quickly using committed dashboards and alert rules. | Only generic platform alerts exist, or GTEX-specific live playback failure modes remain invisible. | `TODO` |
| P6-08 | Write rollback-ready operator workflows | `OP` | `DO`, `BE`, `UE` | Publish an operator runbook for live Unity playback covering provisioning, post-deploy verification, incident triage, rollback trigger, rollback steps, and post-rollback verification. Completed via `ops/gtex-live-playback-rollback-runbook.md`. | Committed runbook in `Docs/` or `ops/`, rollback checklist, named rollback trigger conditions. | There is a clear documented rollback path that an operator can execute without guessing. | Rollback exists only as tribal knowledge or deploy tooling without a verified procedure. | `PASSED` |
| P6-09 | Validate desktop and mobile render and content readiness | `UE` | `QA` | Validate shaders, materials, kits, stadium imports, and addressables on desktop and mobile targets. Confirm no content-specific regressions in live playback. | Validation checklist, screenshots or video on desktop and mobile, issue log for any content fixes. | Desktop and mobile render paths are signed off for the current-engine live playback lane. | Any critical content, shader, kit, stadium, or addressable issue remains unresolved. | `TODO` |
| P6-10 | Verify live runtime resilience under transport/auth failure modes | `BE` | `UE`, `QA` | Exercise stale transport, reconnect, token refresh, and terminal-match scenarios deliberately. Confirm the current-engine live path degrades cleanly and recovers where intended. | Test report with scenarios exercised, logs, match ids, and observed outcomes. | Stale transport, reconnect, auth refresh, and terminal-match behaviors are all explicitly verified and documented. | These behaviors are assumed rather than tested, or recovery is inconsistent. | `TODO` |
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
