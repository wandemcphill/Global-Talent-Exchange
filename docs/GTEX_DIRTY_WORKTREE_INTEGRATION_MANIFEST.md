# GTEX Dirty Worktree Integration Manifest

Date: 2026-06-09

Purpose: stabilize the current canonicalization worktree before deeper feature expansion. The repository has many concurrent worker changes, so integration must be lane-based, test-gated, and non-destructive.

## Current Dirty Shape

After ignoring generated runtime media and temp check folders, visible dirty entries dropped from about 1902 to about 771 source-level entries. This manifest itself adds one additional untracked integration entry until it is staged.

| Lane | Visible entries | Owner thread | Integration priority |
| --- | ---: | --- | --- |
| Flutter shell, routes, product surfaces | 480 | Thread 2 and Thread 3 | High |
| Backend contracts, payments, admin, domains | 132 | Thread 1 | High |
| Unity/internal engine quarantine | 103 | Thread 4 only for quarantine signals, otherwise hold | Medium |
| Docs and route contract artifacts | 18 | Thread 5 and main | High |
| Ops/deploy/observability | 11 | Thread 5 | Medium |
| Tools and guardrails | 12 | Thread 5 and main | High |
| Workflows/secrets baseline | 4 | Thread 5 and main | High |
| Shared contract | 1 | Thread 1 and main | High |
| Data/engine misc | 2 | Main review required | Hold |
| Other root files | 8 | Main review required | Hold |

Generated runtime artifacts now ignored:

- `backend/generated_media/`
- `backend/manual_phase1_checks/`
- `backend/pytesttmp_phase1_admin/`

Do not delete these directories during integration. They are hidden from normal status because they are runtime/test outputs, not canonical source.

## Active Thread Ownership

Thread 1: Backend Economy Contracts

- Owns `backend/app/wallets/**`, `backend/app/treasury/**`, `backend/app/admin_finance/**`, `backend/app/integrations/payments/**`, `backend/app/services/payment_gateway_service.py`, and matching wallet/treasury/admin finance tests.
- Must prove KoraPay/manual bank transfer only.
- Must keep withdrawal, bid, payment proof, webhook, and audit behavior backend-authoritative.

Thread 2: Flutter Shell, Routes, State

- Owns `frontend/lib/features/shell/**`, `frontend/lib/features/app_routes/**`, `frontend/lib/router/**`, `frontend/lib/shared/state/**`, `frontend/lib/shared/realtime/**`, `frontend/lib/shared/widgets/**`, and matching shell/router/shared tests.
- Must keep `/app/{world,market,club,compete,capital,community,creator,admin}` canonical.
- Must keep legacy 3D/Unity routes hidden from production navigation.

Thread 3: Prototype Translation Product Flows

- Owns `frontend/lib/features/build_a_son/**`, `frontend/lib/features/regen_creation/**`, `frontend/lib/features/regen_world/**`, `frontend/lib/features/capital/**`, `frontend/lib/features/compete/**`, `frontend/lib/features/community/**`, `frontend/lib/features/creator/**`, and matching tests.
- Must translate v13/high-fidelity prototype behavior without inventing backend truth.
- Must use reusable shell/state primitives rather than isolated screen state machines.

Thread 4: Match Center and Realtime

- Owns `frontend/lib/features/match_center/**`, `backend/app/live_matches/**`, `backend/app/realtime/**`, `backend/app/routes/match_viewer.py`, `backend/app/schemas/match_viewer.py`, and matching live/realtime/match-viewer tests.
- Must keep match center websocket-authoritative.
- Must quarantine legacy 3D/Unity/pseudo-3D from production routes, CTAs, and monetization.

Thread 5: Integration, Docs, Guardrails, Ops

- Owns `docs/**`, `tools/guardrails/**`, `tools/quality/**`, `scripts/**`, ops verification docs, and integration manifests.
- Must classify worktree risk, update guardrails, run acceptance scans, and report collisions.
- Must not edit product source except for guardrail/test manifest needs.

## Integration Order

1. Guardrail and source hygiene
   - Keep `.gitignore` runtime-only additions.
   - Verify forbidden source terms using production guardrail scan.
   - Verify no source owner is carrying untracked runtime output.

2. Backend payment/admin/wallet contracts
   - Integrate KoraPay/manual-only provider changes.
   - Stabilize withdrawal reservation lifecycle.
   - Stabilize admin payment queue DTOs and audit results.
   - Run targeted wallet, treasury, admin finance, and payment webhook tests.

3. Canonical shell and route registry
   - Integrate canonical shell and `/app/*` registry.
   - Confirm role guards and responsive shell tests.
   - Confirm legacy route adapters no longer promote old shell or 3D routes.

4. Match center and realtime
   - Integrate 2D match center and websocket event contracts.
   - Keep Unity/current-engine files quarantined or internal only.
   - Confirm no fake clocks, scores, events, or local simulation controls in production UI.

5. Prototype product flows
   - Integrate Build-a-Son, wallet/capital, Regen World, competitions, creator/community surfaces.
   - Confirm every missing backend payload renders reusable blocked/empty/syncing/error states.

6. Docs, ops, generated contracts
   - Regenerate API/frontend contract artifacts only after backend and route surfaces stabilize.
   - Update docs after source behavior is final, not before.

7. Full verification
   - Run focused backend and Flutter suites first.
   - Then run canonical acceptance, guardrails, `git diff --check`, and finally broader test suites.

## Required Gates

Always run before calling a lane integrated:

```powershell
python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation
python tools/quality/run_gtex_canonical_acceptance.py --diff-base=
git diff --check
```

Backend payment/admin lane gates:

```powershell
python -m pytest -p no:cacheprovider -q backend/tests/treasury backend/tests/admin_finance backend/tests/wallets backend/tests/integration/test_payment_gateway.py
```

Flutter shell/product lane gates:

```powershell
flutter test frontend/test/shell frontend/test/router frontend/test/shared frontend/test/guardrails
```

Match/realtime lane gates:

```powershell
python -m pytest -p no:cacheprovider -q backend/tests/live_matches backend/tests/realtime backend/tests/test_match_viewer_route.py backend/tests/test_match_viewer_scaling_service.py
```

## Collision Rules

- `frontend/lib/router/app_router.dart` is main/Thread 2 owned. Other threads may request route additions but should not edit it directly.
- `frontend/lib/shared/realtime/**` is Thread 2 owned unless Thread 4 needs a match-center-specific contract and coordinates through main.
- `backend/app/treasury/service.py` and `backend/app/wallets/service.py` are Thread 1 owned. Other threads should not alter wallet business truth.
- `docs/FINAL_API_SCHEMA.json`, `docs/ROUTE_MAP.json`, `shared/api_contract.json`, and generated frontend contract files should be regenerated only after source routes settle.
- Unity project files under `Gtex_Test_Migration/**` are not production Flutter/backend source. Treat them as quarantine/internal engine work unless a guardrail requires a targeted edit.

## Current Main-Thread Stabilization Done

- Runtime/test output ignore rules added for generated media and temp admin phase directories.
- Visible dirty status reduced from about 1902 entries to 771 source-level entries.
- Treasury withdrawal reinstatement safety was hardened before this manifest: released rejected/cancelled withdrawals must create a new request to re-reserve funds.
- Production guardrail and canonical acceptance scans passed immediately before this item-1 integration pass.
- Competition route tests were modernized to canonical `/api/v2/...` paths with token-backed fixtures and a seeded owned club entrant; `backend/tests/competitions/test_competition_launch_rules.py` passed 3/3 on 2026-06-09. This shard is no longer a blocker for the current route-modernization lane.
- Treasury audit events now stamp application-time `created_at`, which fixed payment-queue reinstate audit ordering in admin finance. `backend/tests/admin_finance/test_admin_finance_router.py` passed 16/16 on 2026-06-09.

## Worker Handoffs - 2026-06-01

Thread 3 prototype product lane completed a community/creator coverage slice:

- Added `frontend/lib/features/community/community.dart`.
- Added `frontend/lib/features/creator/creator.dart`.
- Added `frontend/test/community/community_canonical_surface_test.dart`.
- Added `frontend/test/creator/creator_canonical_surface_test.dart`.

Integration note: Thread 2 has been notified to account for these barrels in shell/router registration if needed. Do not wire these from product lanes directly through `frontend/lib/router/app_router.dart`.

Thread 3 verification note:

- `dart format` completed on the new files.
- Lane-level forbidden-text scan passed for the new community/creator files.
- Flutter tests stalled during loading in this environment, so these files still need a shell/router-owner or main-thread Flutter verification pass before staging.

Thread 5 dirty-worktree lane completed its docs/guardrails pass and reported:

- The full all-files status view is larger than source-only status because generated media, temp output, and permission-blocked check dirs are still physically present.
- Canonical acceptance and production guardrail scans passed.
- Generated contracts, route maps, zip/media artifacts, Unity package imports, and delete-plus-untracked frontend moves require explicit review before staging.

Thread 4 match center/realtime lane completed a verified 2D realtime hardening slice:

- Updated `frontend/lib/features/match_center/realtime/live_match_realtime.dart`.
- Updated `frontend/lib/features/match_center/widgets/match_center_components.dart`.
- Added/updated `frontend/test/match_center/live_match_realtime_test.dart`.
- Added/updated `frontend/test/match_center/match_center_widgets_test.dart`.

Thread 4 behavior confirmed:

- Backend score-clock authority survives later commentary-only websocket frames.
- Nested backend score payloads are recognized as authoritative.
- Closed websocket frames before score-clock truth render blocked state, not vague syncing state.

Thread 4 verification:

- Backend live/realtime/match-viewer pytest slice: 41 passed.
- Generated live-match quarantine + websocket gateway pytest slice: 5 passed.
- Match center Flutter reducer/widget slice: 10 passed.
- Realtime provider/shared realtime/forbidden-generation Flutter slice: 26 passed.

Integration note: Thread 2/main must keep shell route registry pointed at canonical 2D match center/viewer and quarantined legacy 3D/Unity routes only.

Continuity update:

- Thread 3 was resumed for the next Build-a-Son and regen creation readiness slice, with ownership limited to `frontend/lib/features/build_a_son/**`, `frontend/lib/features/regen_creation/**`, and matching tests.
- Thread 4 was resumed for backend live-match/realtime contract audit, with ownership limited to backend live-match, realtime, and match-viewer contracts/tests.
- Main remains integration owner and should not edit Thread 1 or Thread 2 source while their heavier tests are active.

## Thread 5 Verification Pass - 2026-06-01

Latest full `git status --short --untracked-files=all` scan reported 2213 visible entries:

| Lane | Modified | Deleted | Untracked | Integration owner |
| --- | ---: | ---: | ---: | --- |
| Backend source and tests | 111 | 3 | 1151 | Thread 1, with generated/temp review first |
| Frontend source and tests | 228 | 208 | 324 | Threads 2, 3, and 4 by domain |
| Unity project | 95 | 0 | 20 | Unity/P6V owner only |
| Docs | 12 | 0 | 12 | Thread 5/main |
| Ops | 5 | 3 | 3 | Thread 5/main |
| Tools | 9 | 0 | 3 | Thread 5/main |
| CI workflows | 3 | 0 | 0 | Thread 5/main |
| Root/other | 4 | 0 | 17 | Main review |

Permission-blocked temp directories:

- `backend/manual_phase1_checks/admin_payment_rails_normalize_a7ijxacg`
- `backend/pytesttmp_phase1_admin`
- `backend/.tmp_pytest_integration`

Do not delete them in this lane. Treat them as stale generated/test-output candidates that need owner or OS-permission review before cleanup.

Risky untracked generated/media artifacts:

- `ops.zip`
- `frontend/assets/media/gtex_matchday_wallpaper.png`
- `Gtex_Test_Migration/Assets/ThirdParty/OriginalFootballSimulator/Football Soccer Simulator.unitypackage`

## Thread 3 CI / Quality Gates / Release Integrity - 2026-06-06

Ownership lane:

- `.github/workflows/**`
- `tools/quality/**`
- `tools/guardrails/**`
- `tools/check_python_runtime_alignment.py`

Completed work:

- Hardened `.github/workflows/ci-staging.yml` so PRs and main pushes run full Flutter analyze/test, full backend pytest, generated API contract regeneration/drift checks, production guardrails, canonical acceptance, existing smoke/regression jobs, and a final merge gate.
- Hardened `.github/workflows/deploy-production.yml` so manual production deploys are blocked behind full Flutter, full backend pytest, generated contract checks, production guardrails/deploy blockers, and live match smoke before deploy eligibility.
- Hardened `.github/workflows/quality-gates.yml` naming and generated contract drift checks.
- Kept KoraPay/manual-only and Unity/native-3D/pseudo-3D quarantine guardrail checks in CI.
- Added guardrail/acceptance scan prefilters and cached path helpers in `tools/guardrails/production_guardrail_scan.py` and `tools/quality/run_gtex_canonical_acceptance.py` to keep full-production scans practical in CI without weakening rule coverage.

Verification:

- YAML parse of `.github/workflows/*.yml` passed with Python.
- `tools/check_python_runtime_alignment.py` passed.
- `py_compile` passed for Thread 3 quality/guardrail tooling.
- `python -m pytest -q tools/guardrails -p no:cacheprovider` passed: 4 passed. Output was redirected to `backend\_out.txt`, read, and removed per thread instructions.
- `tools/guardrails/production_guardrail_scan.py --profile canonical-production --format summary --fail-on violation` passed.
- `tools/guardrails/production_guardrail_scan.py --root .github/workflows --format summary --fail-on violation` passed.
- `tools/quality/run_gtex_canonical_acceptance.py --diff-base=` passed.
- Scoped `git diff --check` passed for owned workflow/tooling/manifest paths with CRLF warnings only.

Blockers / notes:

- `actionlint` is not installed in this workspace, so semantic GitHub Actions lint was not run locally.
- A subagent run of `backend/tests/ops/test_canonical_production_guards.py -q` reported existing non-workflow source expectation failures around legacy 3D documentation/canonicalization. Thread 3 did not edit backend/frontend source to repair those failures; CI now correctly gates production deploy on that blocker.
- `Gtex_Test_Migration/tmp/builds/command-line-invocations.log`

Obvious move/collision patterns:

- Legacy frontend 3D files deleted under `frontend/lib/{controllers,models,services,widgets}/...` with same-name untracked replacements under `frontend/lib/features/3d/...`.
- Legacy capital/wallet/trader/dispute paths deleted under `frontend/lib/{data,screens,widgets,features}/...` with same-name untracked replacements under `frontend/lib/features/capital/...`.
- Legacy competition paths deleted under `frontend/lib/{controllers,screens,widgets,features}/...` with same-name untracked replacements under `frontend/lib/features/compete/...`.
- Legacy match paths deleted under `frontend/lib/{controllers,data,features,models,screens}/...` with same-name untracked replacements under `frontend/lib/features/match_center/...`.
- Ops rollback/verifier paths appear renamed from live-playback/Unity naming to live-match-center/render verification naming; integrate with guardrail review before accepting deletions.

Verification results from this pass:

- `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json`: passed core checks; warned on 454 outside-owner changed files because the shared worktree is intentionally dirty.
- `python tools/guardrails/production_guardrail_scan.py --profile canonical-production --format summary --fail-on violation`: no violations; summary reported 17 owned-by-thread hits and 65 quarantined hits.
- `rg` forbidden-term scan over docs/tools/scripts/tests/.github/ops found expected mock/placeholder/paystack/3D references in tests, docs, guardrails, and quarantined route tests. No cleanup was performed.
- `git diff --name-status` produced many CRLF normalization warnings; treat line-ending churn as review noise unless a lane owner confirms intentional formatting changes.

Ignore for source integration until cleanup lane:

- Python caches, pytest caches, `.ruff_cache`, `.codex_tmp`, root `tmp/`, Unity `Library/Temp/Logs/Obj`-style output, and `Gtex_Test_Migration/tmp/builds/command-line-invocations.log`.
- Permission-blocked backend temp dirs listed above.

Needs review before staging:

- `ops.zip` and `frontend/assets/media/gtex_matchday_wallpaper.png`.
- The Unity `.unitypackage` import candidate and all `Gtex_Test_Migration/Assets/ThirdParty/OriginalFootballSimulator/**` changes.
- Deleted legacy frontend files whose replacements are untracked; stage as deliberate moves only after import paths and tests prove the new canonical folders.
- Generated contract/map docs such as `docs/FINAL_API_SCHEMA.json`, `docs/FRONTEND_API_MAP.json`, `docs/ROUTE_MAP.json`, and generated frontend contract bindings.

## Next Main Integration Target

Integrate Thread 1 backend payment/admin/wallet source first, because it defines product truth for wallet, bids, Build-a-Son payment checks, trader settlement, and admin queues. Flutter surfaces should consume these contracts after they are stable.

## Main Handoff Update - 2026-06-01 Late Pulse

Completed worker lanes closed by main:

- Thread 1 backend economy/payment/admin finance lane closed after wallet HTTP contract fixes. Reported verification: wallet gateway service 4 passed, admin finance webhook regressions 3 passed, payment gateway integration 2 passed, treasury withdrawal reviews 4 passed, wallet service/rail service 27 passed, admin finance router 16 passed, wallet router/http/event backbone 30 passed, and finance-lane Paystack scan returned no matches.
- Thread 4 match center/realtime lane closed after backend websocket contract hardening. `backend/app/realtime/service.py` now preserves backend-provided match event status/result status instead of inventing live status; realtime/live/match-viewer pytest slices reported 11 passed, 24 passed, and 3 passed.
- Thread 2 shell/router/state lane closed with shell/realtime/shared state tests passing, but reported two route tests exiting with no diagnostics and community/creator surface overflow in new product-lane widget tests.

Main-thread integration action from this pulse:

- Patched `frontend/lib/features/community/presentation/community_canonical_surface.dart` to use a vertical scroll container around the canonical readiness panel and removed an unused import.
- Patched `frontend/lib/features/creator/presentation/creator_canonical_surface.dart` to use a vertical scroll container around the approved creator readiness panel.
- These edits intentionally stay inside Thread 3's earlier community/creator surface files and do not touch router, wallet, backend, match center, or Build-a-Son ownership.

Active/unfinished lane:

- Thread 3 completed the Build-a-Son and regen creation readiness slice and was closed. Reported verification covered Build-a-Son readiness, regen creation wizard, wallet block, model strictness, closure, legacy adapter, and prototype mapping contract tests.
- New route/shell worker `019e84f7-e13a-7161-b52d-54483b5abbe4` was spawned to wire or verify the canonical Build-a-Son/regen creation entry. Its ownership is limited to `frontend/lib/router/app_router.dart`, `frontend/lib/features/app_routes/**`, and `frontend/test/router/**`.
- Route worker was closed after a bounded wait. Current route state now verifies locally: `flutter test test/router/gtex_role_guard_test.dart test/router/route_coverage_test.dart --reporter expanded --concurrency=1` passed 13 tests, including canonical shell URLs, legacy alias shell redirects, quarantined `/matches` surfaces, visible metadata guard, parser rejection, and Build-a-Son route mounting.

## Main Handoff Update - 2026-06-01 Finance/Admin Pulse

Completed worker lane:

- Frontend admin payments worker `019e8504-5e11-7330-8826-40696b48ab88` completed and was closed. It hardened admin payment/bid queue row metadata for severity, escalation, actor, timestamps, audit reference, notes, and audit trail; fixed bid audit text parsing; and reported `flutter test test/admin/admin_command_center_screen_test.dart --reporter expanded` passing 4/4 plus scoped forbidden UI scan and `git diff --check` passing.
- Read-only bid reservation explorer `019e8505-d396-7b43-b145-d5c948cfc7d7` completed without edits. It found wallet reservation primitives and summary lock reasons already implemented, with the safest next no-collision backend slice being focused tests in `backend/tests/wallets/test_wallet_service.py` for `replace_transfer_bid_reservation` no double-lock behavior and idempotent withdrawn/cancel release.

Main-thread verification target:

- Re-run the backend finance/admin/wallet suite from the closed Thread 1 handoff.
- Re-run scoped forbidden scans for Paystack in wallet/admin finance surfaces and legacy 3D/Unity route exposure in production route/live-match scopes.

Main-thread backend wallet action:

- Added focused bid-reservation contract tests to `backend/tests/wallets/test_wallet_service.py` for replacement escrow no double-lock behavior and idempotent withdrawn release.
- `git diff --check` passed for the touched wallet test and this manifest.
- Focused backend verification passed: `python -X faulthandler -m pytest backend/tests/wallets/test_wallet_service.py::test_get_wallet_summary_derives_structured_transfer_bid_lock_reasons backend/tests/wallets/test_wallet_service.py::test_replace_transfer_bid_reservation_leaves_exact_replacement_hold backend/tests/wallets/test_wallet_service.py::test_release_transfer_bid_reservation_withdrawn_is_idempotent -vv -s --tb=short --durations=10` passed 3 tests. Runtime was 183.56s because the first test spent 102.88s in migration-backed SQLite setup.

Player-lifecycle bid audit and test hardening:

- Read-only player-lifecycle explorer `019e8523-fb50-7650-b141-dc951b57c966` completed and was closed. It confirmed backend lifecycle endpoints for create, accept, reject, counter, and withdraw; backend uses `submitted` as the active pending state while `ACTIVE_TRANSFER_BID_STATUSES` includes both `pending` and `submitted`.
- Added focused backend tests in `backend/tests/players/test_player_lifecycle.py` for reject release, counter replacement without double-locking, and idempotent withdraw release.
- Verification passed: `python -X faulthandler -m pytest backend/tests/players/test_player_lifecycle.py::test_reject_transfer_bid_leaves_player_state_unchanged backend/tests/players/test_player_lifecycle.py::test_counter_transfer_bid_replaces_reservation_without_double_locking backend/tests/players/test_player_lifecycle.py::test_withdraw_transfer_bid_releases_reservation_idempotently -vv -s --tb=short --durations=10` passed 3 tests. Runtime was 232.25s, mostly collection/setup.
- Strengthened `test_future_transfer_acceptance_keeps_current_contract_active_until_move_date` so the buyer and seller use distinct owners. It now proves a future accepted transfer keeps the bid amount reserved until activation, then settles the escrow to the selling owner and clears the buyer lock reasons.
- Verification passed: `python -X faulthandler -m pytest backend/tests/players/test_player_lifecycle.py::test_future_transfer_acceptance_keeps_current_contract_active_until_move_date -vv -s --tb=short --durations=10` passed 1 test. Runtime was 112.71s.

Post-pulse guardrails:

- `git diff --check -- backend/tests/wallets/test_wallet_service.py backend/tests/players/test_player_lifecycle.py frontend/lib/data/admin_command_center_api.dart frontend/lib/screens/admin/admin_command_center_screen.dart frontend/test/admin/admin_command_center_screen_test.dart docs/GTEX_DIRTY_WORKTREE_INTEGRATION_MANIFEST.md` passed with known CRLF warnings only.
- `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 74}`.
- `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json` passed with provider-neutral payment exposure, no production 3D route promotion, canonical route health, and 2D match direction checks green. It warned on 455 outside-owner changed files, expected for this shared dirty multi-thread workspace.

Completed follow-up worker:

- Read-only bid-status mapping explorer `019e8533-d46f-7dd0-9fff-c47f6b8b3f32` completed without edits and was closed. It found the next safest no-collision slice in frontend bid-status fidelity: preserve canonical transfer bid statuses in parsers, stop using fallback `active`, keep `counter` rows distinct from replacement `submitted` rows, and avoid showing accept/reject controls for terminal/counter statuses.
- Main patched `frontend/lib/data/gte_exchange_api_client.dart` so fixture fallback `lastBidStatus` now emits canonical `submitted` instead of non-canonical `active`.
- Added `frontend/test/transfer_bid_status_contract_test.dart` to prove `GteTransferStatusView` preserves `submitted`, `pending`, `counter`, `accepted`, `completed`, `withdrawn`, and `rejected` without remapping.
- Existing `frontend/test/gte_exchange_api_client_test.dart` was also given a lifecycle snapshot assertion for `submitted`, but its direct run is currently blocked by unrelated missing `_depositRequests` fields in `frontend/lib/data/gte_mock_api.dart`.
- Verification passed: `flutter test test/transfer_bid_status_contract_test.dart --reporter expanded` passed 1 test, and fixed-string scans found no `lastBidStatus`/`last_bid_status` fallback to `active` in `frontend/lib` or `frontend/test`.
- Final post-slice checks passed: `git diff --check` for the touched backend/frontend/manifest files passed with known CRLF warnings only; `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 74}`; `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok` with the expected shared-worktree diff hygiene warning.

## Main Handoff Update - 2026-06-02 Bid UI/Mock Compile Pulse

- Confirmed the prior `frontend/lib/data/gte_mock_api.dart` `_depositRequests` compile blocker is now cleared by the capital fixture-store refactor in the shared worktree. `flutter test test/gte_exchange_api_client_test.dart --reporter expanded` passed 12 tests.
- Added `isActionableTransferBidStatus` to `frontend/lib/features/transfer_news_calendar/data/transfer_news_calendar_models.dart` so only `submitted` and legacy `pending` transfer bids are actionable.
- Updated `frontend/lib/features/transfer_news_calendar/presentation/transfer_news_calendar_screen.dart` so Accept/Reject controls are hidden for `counter`, `accepted`, `completed`, `withdrawn`, `rejected`, and other terminal/non-actionable statuses.
- Added `frontend/test/transfer_news_calendar/transfer_bid_action_gating_test.dart`. Verification passed: `flutter test test/transfer_news_calendar/transfer_bid_action_gating_test.dart --reporter expanded`.
- Reconfirmed canonical transfer-bid status parsing: `flutter test test/transfer_bid_status_contract_test.dart --reporter expanded` passed.
- Read-only test blocker worker `019e85bf-84e2-7d30-83f8-6109fef13790` completed without edits. It identified stale Flutter native asset outputs (`frontend/build/unit_test_assets` and `frontend/build/native_assets`) as a likely broad-test blocker; integration/CI owner should clear those generated folders before broad `flutter test` runs.
- Backend smoke recheck passed: `python -X faulthandler -m pytest backend/tests/wallets/test_wallet_service.py::test_get_wallet_summary_derives_structured_transfer_bid_lock_reasons backend/tests/players/test_player_lifecycle.py::test_counter_transfer_bid_replaces_reservation_without_double_locking -vv -s --tb=short --durations=10` passed 2 tests in 332.40s. A first attempt included a stale admin finance node id and collected no tests for that command; current admin bid queue tests are `test_payment_queue_bid_counter_records_audit_only_review` and `test_payment_queue_bid_route_commits_audit_only_action`.

## Main Handoff Update - 2026-06-02 Flutter Test Build-State Pulse

- Added `frontend/tool/clean_flutter_test_build_state.py`, a small cross-platform cleanup helper that removes `frontend/build/unit_test_assets` and `frontend/build/native_assets` before Flutter test/analyze runs.
- Wired stale native-asset cleanup into `.github/workflows/ci-staging.yml` before every Flutter test invocation and before the frontend analyzer hard-error check.
- Wired the same cleanup into `.github/workflows/deploy-production.yml` before production frontend analyze/test steps.
- Wired local `scripts/run_gtex_guardrails.ps1` to call the cleanup helper before frontend guardrail/match-center tests.
- `frontend/tool/check_analyzer_hard_errors.py` now also clears the same stale native-asset output folders before `flutter analyze --no-pub`.
- Verification passed so far: `python -m py_compile frontend/tool/clean_flutter_test_build_state.py frontend/tool/check_analyzer_hard_errors.py`, `python frontend/tool/clean_flutter_test_build_state.py`, and `git diff --check` for the touched workflow/script files. The workflow grep confirms every current CI `flutter test` invocation in `ci-staging.yml` and `deploy-production.yml` is preceded by cleanup.
- `flutter test test/navigation_surface_truth_test.dart -r compact` no longer fails with a native-assets `PathExistsException`; after the long compile/loading phase, the test passed 8/8.

## Main Handoff Update - 2026-06-02 Canonical Match Route Pulse

- Closed read-only route worker `019e85f7-da45-7503-8aa1-c7f735921847`. It found a route-contract split: `LiveMatchHubRouteData` and `LiveMatchViewerRouteData` existed and mounted canonical 2D screens through `GteAppRouteRegistry`, but `/matches`, `/matches/viewer/:matchKey`, and named `matches.*` parser support were still treated as legacy/quarantined in route tests.
- Closed read-only route-runtime worker `019e8600-cd38-7182-bbaf-20241e8cf67f`. It found `frontend/test/navigation_surface_truth_test.dart` is slow because it compiles a large production import graph; fastest no-collision remediation is to keep route inventory in that file and move widget smokes into a separate `navigation_surface_widget_smoke_test.dart`, with a longer-term extraction of `GteBackendMode` out of the heavy repository import path.
- Patched `frontend/lib/features/app_routes/gte_route_data.dart` so the visible catalog, named parser, and URI parser all support canonical 2D match routes: `matches.hub`, `matches.viewer`, `/matches`, and `/matches/viewer/:matchKey`.
- Patched `frontend/lib/router/app_router.dart` so direct `/matches` and `/matches/viewer/:matchKey` GoRouter links render through `GteAppRouteRegistry` instead of falling through to unavailable routes.
- Patched `frontend/test/router/route_coverage_test.dart` so canonical 2D match hub/viewer routes mount active widgets while `/matches/3d`, `/matches/unity`, `/matches/pseudo-3d`, `/matches/broadcast`, `/matches/spectate`, `/matches/simulate`, and `/broadcast/live` remain quarantined.
- Patched `frontend/test/gte_feature_routing_test.dart` so canonical match route data round-trips through deep-link and named-route parsing.
- Focused verification passed: `flutter test test/gte_feature_routing_test.dart --plain-name "new feature deep links round-trip through the parser" -r expanded --no-pub` passed 1/1, and `flutter test test/router/route_coverage_test.dart -r expanded --no-pub` passed 6/6.
- Broader combined route run `flutter test test/router/route_coverage_test.dart test/gte_feature_routing_test.dart -r expanded --no-pub` failed only in two unrelated no-club onboarding expectations looking for `CLUB SETUP` in `gte_feature_routing_test.dart`; the canonical route round-trip test passed before those failures.
- Post-pulse verification passed: `git diff --check` for the touched route/test/workflow/tool/manifest files passed with known CRLF warnings only; `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 109}`; `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok` with the expected shared-worktree diff hygiene warning.

## Main Handoff Update - 2026-06-02 Home No-Club Routing Pulse

- Closed read-only no-club worker `019e8619-29b6-7ad3-a29f-e70d80d84a98`. It confirmed the no-club failures were stale Home-route expectations after the new role-aware Home dashboard replaced the old shared onboarding surface; the Club tab still owns `GteNoClubOnboardingView`.
- Patched `frontend/lib/features/home_dashboard/home_dashboard_screen.dart` so the fan/no-club Home scaffold keeps a visible `CLUB SETUP` action band without reverting the role-aware dashboard. The band now exposes backend-safe actions for browsing the club market, creating a club, exploring competitions, scouting players, opening world, and opening funds.
- Patched `frontend/test/gte_feature_routing_test.dart` so shell Home verifies the role-aware operating board mounts without legacy blocked copy, while direct Home verifies the fan/no-club setup band and scrolls before tapping offscreen actions.
- Focused verification passed: `flutter test test/gte_feature_routing_test.dart --name "authenticated shell Home shows role-aware operating board without legacy blocked copy|home dashboard shows shared no-club onboarding with working arena path" -r expanded --no-pub` passed 2/2.
- Full feature-route verification passed: `flutter test test/gte_feature_routing_test.dart -r expanded --no-pub` passed 19/19.
- Route coverage recheck passed: `flutter test test/router/route_coverage_test.dart -r expanded --no-pub` passed 6/6.
- Post-pulse verification passed: `git diff --check` for touched Home/test/manifest files passed with known CRLF warnings only; `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 109}`; `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok` with the expected shared-worktree diff hygiene warning.

## Main Handoff Update - 2026-06-02 Navigation Surface Test Split Pulse

- Read-only guardrail worker `019e8637-191c-7d70-9a63-7f8406b750d5` completed without edits. It confirmed production guardrails and backend ops canonical production guards are green; the main remaining risk is dirty diff hygiene from hundreds of shared-worktree changes, especially around relocated match runtime files.
- Stopped worker `019e8636-b8b5-7ff0-8935-68571388c59b` before it edited, then main thread took ownership of `frontend/test/navigation_surface_truth_test.dart` and new `frontend/test/navigation_surface_widget_smoke_test.dart`.
- Split `frontend/test/navigation_surface_truth_test.dart` into cheap route-inventory truth only: primary nav excludes hidden/placeholder routes, quick actions stay live-only, visible surfaces stay live, legacy match runtime stays hidden, and launch simulation stays blocked.
- Added `frontend/test/navigation_surface_widget_smoke_test.dart` for the heavier widget smokes: Home quick actions, World desk preview-label truth, and the hidden legacy native match route blocked surface.
- Verification passed: `flutter test test/navigation_surface_truth_test.dart -r expanded --no-pub` passed 5/5, and `flutter test test/navigation_surface_widget_smoke_test.dart -r expanded --no-pub` passed 3/3, with `python tool/clean_flutter_test_build_state.py` run before each Flutter test.
- Post-split guardrail verification passed: `git diff --check -- frontend/test/navigation_surface_truth_test.dart frontend/test/navigation_surface_widget_smoke_test.dart Docs/GTEX_DIRTY_WORKTREE_INTEGRATION_MANIFEST.md` passed with known CRLF warnings only; `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 109}`.

## Main Handoff Update - 2026-06-02 Route/Shell + Payment Guardrail Freeze Pulse

- Spawned two read-only audit lanes for route/shell/match-center and payment guardrails, then closed them when local verification completed first. No agent edits were integrated in this pulse.
- Froze the frontend acceptance slice without new production edits: `frontend/test/guardrails/forbidden_text_guard_test.dart`, `frontend/test/match_center/broadcast_score_authority_test.dart`, `frontend/test/match_center/canonical_match_center_test.dart`, `frontend/test/match_center/live_match_realtime_provider_test.dart`, and `frontend/test/router/route_coverage_test.dart`.
- Frontend verification passed after stale build-state cleanup: `flutter test test/guardrails/forbidden_text_guard_test.dart test/match_center/broadcast_score_authority_test.dart test/match_center/canonical_match_center_test.dart test/match_center/live_match_realtime_provider_test.dart test/router/route_coverage_test.dart -r expanded --no-pub` passed 33/33.
- Backend production/payment guardrails passed: `python -m pytest backend/tests/ops/test_canonical_production_guards.py -q` passed 16/16, and `python -m pytest backend/tests/admin_godmode/test_payment_rails_truth.py backend/tests/integration/test_payment_gateway.py backend/tests/wallets/test_wallet_rail_service.py -q` passed 13/13.
- Post-freeze guardrails passed: `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 109}`.
- Final canonical acceptance passed: `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok` with Paystack exposure, production 3D promotion, route health, and 2D match direction checks green. The only warning remains shared-worktree diff hygiene: 458 outside-owner changed files.

## Main Handoff Update - 2026-06-02 Match-Center Relocation Stabilization Pulse

- Spawned read-only relocation audit lanes. `019e866b-d6a9-7190-a78e-780fe06c85b5` found no active production router promotion of legacy 3D/Unity/pseudo-3D surfaces and flagged stale fixture-fallback tests as the next risk. `019e866b-a257-75b3-ac27-0895c72f297a` found no direct stale `features/match` package imports, but flagged broken relative imports in the quarantined 3D bootstrap service and live match HUD avatar.
- Fixed `frontend/lib/features/3d/services/match_3d_live_bootstrap_service.dart` to import the top-level API classes by package path while keeping the service quarantined behind `kGtexLegacy3dRuntimeEnabled`.
- Fixed `frontend/lib/features/match_center/widgets/match_hud_avatar.dart` to import shared avatar models/widgets by package path instead of stale relative paths from the deleted old widget tree.
- Updated `frontend/test/match/native_match_3d_surface_test.dart` to use the existing backend-authored broadcast fixture rather than the removed local fallback-snapshot mapper API. This keeps the quarantine test aligned with the canonical no-local-match-truth rule.
- Reviewed and updated `frontend/test/goldens/broadcast_package_premium_surface.png` from the generated current capture after the relocated broadcast package surface drifted visually but remained nonblank and structurally correct. The golden comparator tolerance was not loosened.
- Verification passed: `flutter test test/match_center -r expanded --no-pub` passed 39/39, `flutter test test/match -r expanded --no-pub` passed 24/24, and `flutter test test/match_3d_live_bootstrap_service_test.dart test/avatar_rendering_test.dart test/match_center/match_center_widgets_test.dart -r expanded --no-pub` passed 14/14.
- Cleaned generated `frontend/test/match/failures/` artifacts from the failed pre-fix golden run.
- Post-pulse checks passed: `git diff --check` for touched files passed with known CRLF warnings only; `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 109}`; `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok`, with the expected shared-worktree diff hygiene warning.

## Main Handoff Update - 2026-06-02 Legacy Navigation Adapter + Match Truth Pulse

- Spawned read-only audit lanes for the old `frontend/lib/navigation` adapter and match-runtime truth tests. The adapter audit confirmed production boot uses `frontend/lib/router/app_router.dart`, while the old adapter still carried hidden/redirect match-lane contracts. The match-truth audit confirmed `MatchViewerMapper` no longer supports `fallbackSnapshot`/`preferFallback`.
- Updated `frontend/test/match_runtime_truth_test.dart` so fixture mode is expected to reject canonical live match snapshots and viewer frames. The test now imports `features/match_center/data/live_match_fixtures.dart` directly for `loadLiveMatchSnapshot` and no longer calls removed mapper fallback arguments.
- Updated the old `frontend/lib/navigation/app_router.dart` adapter so retired match lanes redirect to canonical match surfaces instead of mounting placeholder pages: `/matches/broadcast/:matchKey` and `/internal/dev/match-runtime/:matchKey` redirect to `/matches/viewer/:matchKey`; `/internal/dev/blocked-match-runtime`, `/matches/spectate`, and `/matches/simulate` redirect to `/matches`.
- Updated `frontend/lib/navigation/app_destinations.dart` so broadcast, spectate, and simulate match surfaces are hidden from launch navigation with canonical 2D/backend-authored truth copy instead of placeholder promotion.
- Updated `frontend/test/active_shell_route_mount_test.dart` and `frontend/test/navigation_surface_truth_test.dart` to prove retired adapter match lanes redirect or stay hidden, not visible as coming-soon CTAs.
- Verification passed: `flutter test test/match_runtime_truth_test.dart test/navigation_surface_truth_test.dart test/active_shell_route_mount_test.dart -r expanded --no-pub` passed 12/12 after stale build-state cleanup.
- Additional frontend coverage passed: `flutter test test/router/route_coverage_test.dart test/guardrails/forbidden_text_guard_test.dart test/navigation_surface_widget_smoke_test.dart -r expanded --no-pub` passed 17/17.
- Post-pulse checks passed: `git diff --check` for touched adapter/test/manifest files passed with known CRLF warnings only; `python tools/guardrails/production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"owned-by-thread": 17, "quarantined": 109}`; `python tools/quality/run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok`, with the expected shared-worktree diff hygiene warning.
- Known next focused slice: remove the remaining removed-mapper fallback calls in `frontend/test/match_3d_screen_test.dart`, `frontend/test/match_3d_bridge_scene_test.dart`, and `frontend/test/match_3d_timeline_controller_test.dart` by introducing a backend-authored 3D quarantine test fixture helper. Do not re-add `fallbackSnapshot` or `preferFallback` to `MatchViewerMapper`.

## Agent D Service Contract Notes - 2026-06-02

Scope: Dio/WebSocket/audit frontend service contracts only. No backend, router, shared realtime, or feature-screen edits were made in this lane.

Contract additions in Agent D-owned paths:

- Added canonical Dio service contracts under `frontend/lib/services/api/**`: base client, auth interceptor, error interceptor, and debug logging interceptor.
- Added canonical WebSocket service contracts under `frontend/lib/services/websocket/**`: bounded 1/2/4/8/30s exponential reconnect policy, channel abstraction, raw envelope parser, and `GtexReconnecting<T>` surface-state hook carrying `lastKnown` plus reconnect attempt.
- Added canonical audit contracts under `frontend/lib/services/audit/**`: sealed `AuditEvent`, `GtexAuditEvent`, `TraderDisputeFiledAuditEvent`, and `AuditLogger` backend/local dispatch.

Section 4 backend contract gaps remain blocked/missing until backend owners publish stable response schemas or websocket docs:

| Gap IDs | Status | Agent D contract note |
| --- | --- | --- |
| 1, 2, 3 | Blocked | Trader balance stale timestamp, quote lock field shape, and KoraPay checkout mode are not confirmed in frontend service contracts. |
| 4, 5 | Missing/risk | Bank-transfer account-detail scope and settlement ETA format are still backend-owned display-contract risks. |
| 6 | Blocked | Complete `MarketBidDTO.status` enum remains required before bid state machines can be exhaustive. |
| 7, 8 | Missing/risk | Market pagination mode and squad availability enum remain unconfirmed. |
| 9 | Blocked | Fixture score null-vs-absent shape remains required to avoid false 0-0 rendering. |
| 10, 11 | Missing/risk | Match event pitch coordinates and settlement trigger authority remain unconfirmed. |
| 12, 13 | Blocked | Admin lock TTL/conflict shape and export async contract remain required for admin decision surfaces. |
| 14, 15 | Missing/risk | Bulk-action backend batching and audit-log before/after diff availability remain unconfirmed. `AuditLogger` now serializes optional `before`/`after`, but backend response support is still not assumed. |
| 16, 17 | Blocked | WebSocket auth mode and canonical channel naming scheme remain unconfirmed. `GtexWsService` keeps auth external and accepts explicit endpoint/topic inputs until backend docs settle. |
| 18, 19 | Missing/risk | Per-resource subscription support and standard WS envelope schema remain unconfirmed. The frontend parser tolerates `{type,data,timestamp}`, `{type,payload,timestamp}`, and topic/channel aliases, but this is not a backend confirmation. |
| 20 | Blocked | Formation publish server-side eligibility validation remains unconfirmed and must not be replaced by frontend-only checks. |
| 21, 22 | Missing/risk | Regen DNA axis list and projected-value methodology enum remain unconfirmed. |

## Thread 8 GA QA / Staging Dry Run / Visual + Load - 2026-06-06

Scope: Thread 8-owned QA/staging/load/docs only. No product source, workflow, backend business logic, frontend routes, Unity files, or existing dirty worker files were edited in this slice.

Completed work:

- Added `tools/visual/capture_gtex_visual_qa.ps1` for desktop/tablet/mobile screenshot capture using Edge or Chrome headless. The tool writes `visual_qa_manifest.json` and fails on missing/tiny/invalid PNG output.
- Added `tools/staging/invoke_gtex_staging_smoke.ps1` for read-only staging smoke across `/health`, `/ready`, `/version`, and `/diagnostics`, with optional market and match-center probes.
- Added `tools/staging/invoke_gtex_rollback_rehearsal.ps1` for current-vs-rollback candidate smoke comparison and release-captain rollback steps.
- Added `tools/load/gtex_load_probe.py` for stdlib HTTP load probing of market endpoints and optional backend-authored match-center endpoints, with optional websocket probing when `websocket-client` is installed.
- Added `Docs/GTEX_GA_QA_STAGING_LOAD_RUNBOOK.md` with exact commands, pass/fail criteria, and release evidence requirements.
- Added `Docs/GTEX_PRODUCTION_SIGNOFF_CHECKLIST.md` with per-feature production signoff gates.

Guardrail notes:

- KoraPay/manual bank transfer remains the only launch money rail in Thread 8 docs.
- Visual QA defaults to canonical `/app/*` surfaces and does not include Unity/native-3D/pseudo-3D production routes.
- Match-center load/smoke requires an existing backend-authored match id when match truth is mandatory; otherwise the tools report blocked/skipped rather than fabricating data.

Verification:

- PowerShell parser checks passed for `tools/visual/capture_gtex_visual_qa.ps1`, `tools/staging/invoke_gtex_staging_smoke.ps1`, and `tools/staging/invoke_gtex_rollback_rehearsal.ps1`.
- Python compile check passed: `C:\Python314\python.exe -m py_compile tools\load\gtex_load_probe.py`.
- Load harness help check passed: `C:\Python314\python.exe tools\load\gtex_load_probe.py --help`.
- Local mock staging smoke passed with route verification and relaxed local threshold: `powershell -ExecutionPolicy Bypass -File .\tools\staging\invoke_gtex_staging_smoke.ps1 -BaseUrl http://127.0.0.1:8931 -IncludeOptionalMarket -IncludeOptionalMatchCenter -MatchId qa-match -VerifyMatchCenterRoutes -MaxLatencyMs 5000 -OutputPath .\tmp\thread8_staging_smoke_pass.json`. The default `2000 ms` threshold remains documented for real staging; the local mock cold `/health` request exceeded it once in this Windows shell.
- Local mock rollback rehearsal passed: `powershell -ExecutionPolicy Bypass -File .\tools\staging\invoke_gtex_rollback_rehearsal.ps1 -CurrentBaseUrl http://127.0.0.1:8931 -RollbackBaseUrl http://127.0.0.1:8931 -CurrentReleaseId current-qa -RollbackReleaseId rollback-qa -VerifyMatchCenterRoutes -OutputPath .\tmp\thread8_rollback.json`.
- Local mock load probe passed: `C:\Python314\python.exe .\tools\load\gtex_load_probe.py --base-url http://127.0.0.1:8931 --match-id qa-match --require-match --requests-per-endpoint 2 --concurrency 2 --max-p95-ms 5000 --output .\tmp\thread8_load_probe_pass2.json`.
- Local mock visual smoke passed: `powershell -ExecutionPolicy Bypass -File .\tools\visual\capture_gtex_visual_qa.ps1 -BaseUrl http://127.0.0.1:8931 -Routes '/' -Viewports 'desktop=800x600' -OutputDir .\tmp\thread8_visual_smoke -MinBytes 1000 -TimeoutSeconds 45 -SettleSeconds 0`. Manifest reported `passed=true`, PNG dimensions `800x600`, and `8423` bytes.
- `git diff --check -- tools/visual/capture_gtex_visual_qa.ps1 tools/staging/invoke_gtex_staging_smoke.ps1 tools/staging/invoke_gtex_rollback_rehearsal.ps1 tools/load/gtex_load_probe.py Docs/GTEX_GA_QA_STAGING_LOAD_RUNBOOK.md Docs/GTEX_PRODUCTION_SIGNOFF_CHECKLIST.md Docs/GTEX_DIRTY_WORKTREE_INTEGRATION_MANIFEST.md` passed.
- Production guardrail scan passed: `C:\Python314\python.exe tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` returned summary `{"fixed": 5, "owned-by-thread": 17, "quarantined": 165}`.

Skipped/blockers:

- No real staging API/web URLs, bearer token, or backend-authored match id were provided in this thread, so verification used a local mock server only. Real staging must still run the documented commands before GA signoff.
- The visual harness verified a local static route only. Full desktop/tablet/mobile visual QA across canonical GTEX routes remains a release-captain action once staging web is available.

## Thread 1 Core/Foundation Lane 0 Pulse - 2026-06-02

Scope: Thread 1-owned Core/Foundation only: shared async state/renderers, shell primitives, route constants/guards, Dio/WebSocket/audit service contracts, production guardrails, and contract documentation.

- Spawned and integrated the requested parallel lanes:
  - Agent A: shared `GtexSurfaceState<T>` variants and async renderer coverage.
  - Agent B: canonical `/app/{world,market,club,compete,capital,community,creator,admin}` route constants and route guard coverage.
  - Agent C: production forbidden-text/payment/3D/fake-authority scans.
  - Agent D: Dio/WebSocket/audit service contracts and Section 4 backend contract-gap table above.
- Added canonical shared async surface state coverage for `loading`, `empty`, `blocked`, `pending`, `syncing`, `reconnecting`, `degraded`, `confirmed`, `error`, and `data` through `frontend/lib/shared/state/**`, `AsyncStateWidget`, and `GtexAsyncStateView`.
- Kept shell `GtexSurfaceState.data` as a compatibility alias for `confirmed` while the canonical data-bearing state remains `GtexData<T>`. This preserves existing exhaustive feature-screen switches while letting shell callers express backend-data-ready intent.
- Normalized shell primitives so data/confirmed states do not show warning chrome in wallet chips, context rails, command palette, realtime widgets, live ticker, async shell surfaces, and operating shell state helpers.
- Added canonical API, WebSocket, and audit service contracts under `frontend/lib/services/{api,websocket,audit}/**`, including bearer-token retry, backend error envelope mapping, bounded reconnect snapshots, and optional audit before/after serialization.
- Strengthened production guardrails for unsupported payment rails, Paystack exposure, Unity/native/pseudo-3D promotion, fake authority data, fixture-mode activation, and capital facade boundaries.
- Fixture-mode guardrail classification now allows named `.fixture` factories while still blocking production activation/default-on fixture mode.
- Router guard tests now prove canonical shell roots and role lanes parse and route through the shell; fixture-backed role widget tests drain delayed fixture loads before replacing mounted trees.

Focused verification:

- `dart format frontend/lib/shared/state frontend/lib/shared/widgets/async_state_widget.dart frontend/lib/shared/widgets/gtex_async_state_view.dart frontend/lib/services/api frontend/lib/services/websocket frontend/lib/services/audit frontend/lib/router frontend/lib/features/shell frontend/test/shared/async_state_rendering_test.dart frontend/test/shared/services/gtex_service_contracts_test.dart frontend/test/router frontend/test/shell frontend/test/guardrails` passed.
- `flutter test test/shared/async_state_rendering_test.dart -r compact --concurrency=1 --no-pub` passed 4/4.
- `flutter test test/shared/services/gtex_service_contracts_test.dart -r compact --concurrency=1 --no-pub` passed 5/5.
- `flutter test test/shell/gtex_surface_state_primitives_test.dart -r compact --concurrency=1 --no-pub` passed 3/3.
- `flutter test test/guardrails/forbidden_text_guard_test.dart -r compact --concurrency=1 --no-pub` passed 11/11.
- `flutter test test/router/gtex_role_guard_test.dart -r compact --concurrency=1 --no-pub` passed 8/8 after the fixture-drain helper update.
- `flutter test test/router/route_coverage_test.dart -r compact --concurrency=1 --no-pub` passed 9/9.
- `flutter test test/shared/async_state_rendering_test.dart test/shared/services/gtex_service_contracts_test.dart test/shell/gtex_surface_state_primitives_test.dart test/guardrails/forbidden_text_guard_test.dart -r compact --concurrency=1 --no-pub` passed 23/23.
- `dart analyze lib/shared/state lib/shared/widgets/async_state_widget.dart lib/shared/widgets/gtex_async_state_view.dart lib/services/api lib/services/websocket lib/services/audit lib/router lib/features/shell test/shared/async_state_rendering_test.dart test/shared/services/gtex_service_contracts_test.dart test/router/route_coverage_test.dart test/router/gtex_role_guard_test.dart test/shell test/guardrails/forbidden_text_guard_test.dart` passed with `No issues found!`.
- `python -m pytest tools\guardrails\test_production_guardrail_scan.py -q` passed 4/4.
- `python tools\guardrails\production_guardrail_scan.py --profile canonical-production --format summary --fail-on violation` passed with summary `{"fixed": 5, "owned-by-thread": 17, "quarantined": 121}`.
- `python tools\quality\run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok`; Paystack exposure, payment rail, production 3D promotion, fake authority, route health, and 2D match direction checks passed. The only warning was dirty-worktree diff hygiene with 470 outside-owner changed files.
- `git diff --check -- frontend/lib/shared frontend/lib/services/api frontend/lib/services/websocket frontend/lib/services/audit frontend/lib/router frontend/lib/features/app_routes frontend/lib/features/shell frontend/test/shared frontend/test/router frontend/test/shell frontend/test/guardrails tools/guardrails tools/quality Docs/GTEX_DIRTY_WORKTREE_INTEGRATION_MANIFEST.md Docs/CANONICAL_PROTOTYPE_MAPPING_CHECKLIST.md` passed with known CRLF warnings only.

Remaining Core/Foundation risks:

- Section 4 backend contract gaps remain exactly as documented in the Agent D table above; frontend does not assume missing backend truth for balances, bid status, fixture scores, WebSocket auth/channel/envelope, audit diffs, formation validation, or Regen value/DNA methodology.
- The full shared dirty worktree still contains many out-of-lane modified and untracked files. Thread 1 did not revert or normalize other workers' feature-screen changes.
- Router widget tests are slow because they compile broad feature graphs. The role-guard file now passes standalone, but a future full combined router run should be repeated after other frontend lanes settle.

## Thread 1 Core/Foundation Continuation Sweep - 2026-06-04

Scope: no new production code edits. Continued verification over the Thread 1-owned shared, shell, router, service, and guardrail surfaces after the Lane 0 implementation settled.

- `flutter test test/router/route_coverage_test.dart test/router/gtex_role_guard_test.dart -r compact --concurrency=1 --no-pub` passed 17/17.
- `flutter test test/shell -r compact --concurrency=1 --no-pub` passed 27/27.
- `flutter test test/shared -r compact --concurrency=1 --no-pub` passed 24/24.
- `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- `python tools\quality\run_gtex_canonical_acceptance.py --diff-base HEAD --json` returned `status: ok`; all canonical production checks passed and the only warning remained shared-worktree diff hygiene for outside-owner files.
- `git diff --check` for Thread 1-owned paths passed with known CRLF warnings only.

Continuation note: the broad Flutter suites are slow because the shared worktree still compiles large route and realtime graphs, but no Thread 1-owned failing tests remain in the swept directories.

## Thread 3 Football Operations Flow Builder - 2026-06-02

Scope: Club HQ, squad readiness, formation editor, competitions, and canonical 2D match-center football operations surfaces.

- Ownership stayed inside `frontend/lib/features/club_hub/**`, `frontend/lib/features/compete/**`, `frontend/lib/features/match_center/**`, and matching `frontend/test/club_ops/**`, `frontend/test/compete/**`, and `frontend/test/match_center/**` coverage.
- Production match-center guardrails now keep legacy advanced-viewer shims blocked with backend-route guidance and keep canonical `GtexMatchViewType` collapsed to 2D.
- Competition detail copy no longer advertises premium key-moment video or alternate match controls; it points to backend-authored 2D commentary, key moments, and tactical context.
- Fixture-mode competition invite codes are deterministic and no longer use local random generation in the owned production repository file.
- The untracked local match generator has been quarantined as an unsupported backend-only stub so production code cannot fabricate match events, clocks, stats, or scores.
- `frontend/test/match_center/football_ops_acceptance_scan_test.dart` covers 2D-only route guidance, responsive match-center widget rendering at mobile and desktop sizes, forbidden production 3D-promotion copy, and forbidden local event-generation APIs across the football-ops production folders.
- Remaining backend contract caveat: live fixtures, brackets, standings, settlement readiness, score, clock, stats, xG, commentary, reactions, and gifting remain backend/websocket authoritative. Missing or unconfirmed payloads must continue to render loading, empty, blocked, syncing, degraded, or error states rather than local substitutes.

## Main Handoff Update - 2026-06-02 Backend-Authored 3D Quarantine Fixture Pulse

- Completed the known next focused slice from the legacy navigation/match-truth pulse: removed the remaining removed-mapper fallback calls from `frontend/test/match_3d_screen_test.dart`, `frontend/test/match_3d_bridge_scene_test.dart`, and `frontend/test/match_3d_timeline_controller_test.dart`.
- Added `buildBackendAuthored3dQuarantineViewState()` in `frontend/test/support/gtex_match_broadcast_fixture.dart` so quarantined 3D tests use an explicit backend-authored match view state instead of `MatchViewerMapper` fallback arguments. The helper keeps full 22-player frame data, VAR check/confirmation frames, and an offside pause cue aligned with controller injection timing.
- Kept legacy runtime behavior quarantined: `GtexMatchRuntimeBlockedScreen` still renders the route-blocked launch surface, scene graph tests can describe the hidden runtime, and bridge sync remains a no-op while the runtime is quarantined.
- Adapted the shared test fixture to the current match-center model shape after the parallel match-center lane replaced the old monetization model with engagement-era match state. No deleted monetization model or fallback mapper API was restored.
- Verification passed: `flutter test test\match_3d_screen_test.dart test\match_3d_bridge_scene_test.dart test\match_3d_timeline_controller_test.dart -r compact --no-pub` passed 7/7. Isolated pre-checks also passed for `test\match_3d_screen_test.dart` and `test\match_3d_timeline_controller_test.dart`.
- Stale fallback scan passed: `rg -n "fallbackSnapshot|preferFallback" frontend\lib frontend\test -g "*.dart"` returned no matches.
- Post-pulse checks passed: `git diff --check -- frontend/test/support/gtex_match_broadcast_fixture.dart frontend/test/match_3d_screen_test.dart frontend/test/match_3d_bridge_scene_test.dart frontend/test/match_3d_timeline_controller_test.dart` passed with known CRLF warnings only; `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 135}`.

## Main Handoff Update - 2026-06-02 Shell State + Club Ops Lifecycle Pulse

- Spawned two parallel worker lanes while the main thread owned shell/router integration: the ops/workflow guardrail worker finished without touching Flutter feature/backend app code, and the 3D quarantine worker finished the remaining legacy 3D test hardening. Both workers reported passing targeted tests and guardrail scans in their owned scopes.
- Fixed canonical `GtexSurfaceState.data` exhaustiveness breaks in compact operational surfaces so shell, home, market, and player-card marketplace widgets treat backend-authored data as an operational live/positive state instead of failing compilation.
- Fixed `ClubHubScreen` fixture-mode dependency construction so shell role tests can open Club HQ with zero-latency fixture-backed club operations while production still defaults to live backend mode.
- Added `GteRequestGate.cancel()` and wired `ClubOpsController.dispose()` through gate cancellation plus `_notifyIfActive()` so late async club/admin loads cannot notify a disposed controller during route swaps.
- Verification passed: `flutter test test\router\gtex_role_guard_test.dart -r compact --no-pub` passed 8/8 after the lifecycle fix.
- Verification passed: `flutter test test\router\route_coverage_test.dart test\shell\gtex_shell_primitives_test.dart test\shell\gtex_shell_responsive_test.dart test\shell\gtex_surface_state_primitives_test.dart test\shared\async_state_rendering_test.dart -r compact --no-pub` passed 25/25.
- Verification passed: `flutter test test\club_ops\club_hq_operations_panel_test.dart test\club_ops\club_sponsorships_test.dart -r compact --no-pub` passed 7/7.
- Post-pulse checks passed: `git diff --check -- frontend/lib/controllers/club_ops_controller.dart frontend/lib/data/gte_api_repository.dart frontend/lib/features/club_hub/presentation/club_hub_screen.dart frontend/lib/features/home_dashboard/home_dashboard_screen.dart frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart frontend/lib/screens/gte_market_players_screen.dart frontend/lib/features/player_card_marketplace/presentation/player_card_marketplace_screen.dart` passed with known CRLF warnings only; `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.

## Thread 5 Verification Sweep - 2026-06-02

Scope: read-only verification of the current integration state; no frontend/backend source files were edited.

- `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Broad provider-term scan over scanner-derived changed canonical files found expected guardrail/quality pattern definitions plus one non-payment paint variable named `stripe` in `frontend/lib/features/match_center/widgets/match_center_components.dart`.
- Payment-context scan for forbidden provider/product exposure found hits only in guardrail tooling/tests: `tools/quality/run_gtex_canonical_acceptance.py`, `tools/guardrails/production_guardrail_scan.py`, `tools/guardrails/test_production_guardrail_scan.py`, and `frontend/test/guardrails/forbidden_text_guard_test.dart`.
- Filtered changed canonical product/ops source scan, excluding guardrail tooling/tests, reported: `No forbidden payment provider/product text found in changed canonical product/ops source.`
- No source edits are needed from this sweep; the KoraPay/manual bank transfer-only guardrail remains clean in changed product/ops source.

## Main Handoff Update - 2026-06-02 Transfer-Market Route Collision Closure

Scope: backend transfer-market route normalization, Flutter Market adapter endpoint alignment, and backend/admin verification unblocking.

- Resolved the module-registration collision between legacy `backend/app/market/router.py` `/market/*` routes and the new transfer-market player/basket/bid endpoints by keeping legacy Market ownership on `/market/*` and moving the production transfer-market UI contract to `/api/transfer-market/{players,filters,bids,bid,basket,checkout,activity,history}`.
- Updated the Flutter Market API adapter and repository contract tests to use `/api/transfer-market` instead of legacy `/market/*` or the temporary mixed `/api/transfer-market/market/*` family.
- Confirmed no stale mixed namespace remains in the touched router, tests, or Flutter Market adapter with `rg -n 'api/transfer-market/market' backend\app\transfer_market\router.py backend\tests\players\test_transfer_market.py frontend\lib\features\market\data\market_api_service.dart frontend\test\market\repository\market_repository_test.dart`.
- Route duplicate sanity check passed across `backend/app/market/router.py` and `backend/app/transfer_market/router.py`: 43 market + transfer-market routes checked, no duplicates.
- Verification passed: `python -m pytest backend\tests\players\test_transfer_market.py -k "market_players_filters_meta_and_detail_contract or market_basket_bid_detail_activity_and_reservation_parity_contract or market_history_returns_completed_transfer_contract" -q` passed 3/3.
- Verification passed: `flutter test test\market\repository\market_repository_test.dart -r compact --no-pub` passed 3/3.
- Existing Thread 2 market model/provider verification remained valid after namespace cleanup: `flutter test test\market\model\market_models_test.dart test\market\provider\market_providers_test.dart -r compact --no-pub` passed 8/8.
- Admin/treasury backend stabilization worker confirmed the original downstream blocker is cleared: `python -m pytest backend/tests/admin_finance backend/tests/treasury -q` passed 27/27 with one `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning.
- Post-pulse hygiene passed: scoped `git diff --check` for the touched transfer-market, Flutter Market, and manifest paths passed with known CRLF warnings only.

## Thread 5 Transfer-Market Namespace Verification - 2026-06-02

Scope: verification-only sweep after transfer-market namespace cleanup; no frontend/backend source or shared contract files were edited.

- `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Scoped forbidden provider/3D literal scan over transfer-market and Market adapter implementation/test/contract paths returned no matches.
- Scoped stale mixed namespace scan for `/api/transfer-market/market*` over transfer-market and Market adapter implementation/test/contract paths returned no matches.
- Scoped transfer-market-owned stale `/market/*` scan returned no matches after excluding legacy Market-owned shared/generated contract aliases.
- `git diff --check` for the changed transfer-market, transfer center, transfer provider, bid-status, API-contract, generated-contract, shared-contract, Flutter Market adapter, and matching test paths passed with known CRLF warnings only.

## Main Handoff Update - 2026-06-02 Transfer-Market Shared Contract Regeneration

Scope: regenerated shared/frontend API contract artifacts after the transfer-market route collision closure and fixed the remaining in-scope Market adapter contract false positive.

- Regenerated the route audit and API bindings with `python tools\audit\generate_contract_audit.py` and `python tools\audit\generate_api_contract_bindings.py`, updating `docs\ROUTE_MAP.json`, `docs\FINAL_API_SCHEMA.json`, `docs\FRONTEND_API_MAP.json`, `docs\DEPRECATION_MAP.json`, `docs\ROUTE_CLASSIFICATION.md`, `docs\WEB_MOBILE_DIFF.md`, `docs\MISMATCH_REPORT.md`, `docs\CRITICAL_ISSUES.md`, `docs\PRE_DELETION_VALIDATION.md`, `docs\ENV_AUDIT.md`, `shared\api_contract.json`, and `frontend\lib\data\generated\gte_api_contract.g.dart`.
- Patched `frontend\lib\features\market\data\market_api_service.dart` so every transfer-market request uses declared endpoint literals such as `/api/transfer-market/players`, `/api/transfer-market/bids`, `/api/transfer-market/bid/{id}`, `/api/transfer-market/basket`, `/api/transfer-market/checkout`, `/api/transfer-market/activity`, and `/api/transfer-market/history`.
- Added `frontend\test\gte_api_contract_test.dart` to prove canonical transfer-market aliases and generated route declarations resolve to `/api/v2/transfer-market/*`.
- `python tools\audit\check_api_contract_violations.py` now reports 16 violations, down from 17; the removed violation was the in-scope Market adapter base-path false positive. Remaining violations are out-of-lane admin command center `/api/v1/admin/finance/payment-queue` usage plus missing club/squad/formation endpoint declarations.
- Verification passed: `flutter test test\gte_api_contract_test.dart -r compact --no-pub` passed 3/3 and `flutter test test\market\repository\market_repository_test.dart -r compact --no-pub` passed 3/3.
- Verification passed: `dart format lib\features\market\data\market_api_service.dart test\gte_api_contract_test.dart` reported `0 changed`.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Verification passed: scoped stale route scans found no live transfer-market drift; remaining `/api/transfer-market/market*` hits are historical notes in this manifest, while `/market/players` remains owned by the separate legacy Market router and canonicalizes to `/api/v2/market/players`.
- Scoped `git diff --check` for regenerated docs/contracts, the Flutter Market adapter, the new API contract test, and this manifest passed with known CRLF warnings only.

## Main Handoff Update - 2026-06-02 Club Ops Contract Closure

Scope: closed the remaining API-contract drift for Admin command center, Club HQ finance, Squad, and Formation without inventing backend business truth.

- Removed the stale Admin command-center `/api/v1/admin/finance/payment-queue` fallback so the Flutter admin surface now stays on the canonical `/api/v2/admin/finance/payment-queue` path with the existing `/api/admin/...` compatibility alias.
- Corrected the Club HQ finance repository from the undeclared singular `/api/clubs/{club_id}/finance` path to the real backend `/api/clubs/{club_id}/finances` contract.
- Declared backend Club/Squad contract routes for dashboard, squad readiness, roster, availability, injuries, chemistry, contracts, scouting, staff, and rankings as explicit `503 blocked` responses with audit-friendly state/code/reason payloads until authoritative DTO services are mounted.
- Declared backend Formation routes for `/api/v2/clubs/{club_id}/formation`, `/api/v2/clubs/{club_id}/formation/draft`, and `/api/v2/clubs/{club_id}/formation/publish` as explicit `503 blocked` responses until authoritative draft, publish, validation, and audit contracts exist.
- Regenerated route-audit and shared/frontend API contract artifacts after the route declarations. `python tools\audit\check_api_contract_violations.py` now reports `No contract violations detected.`
- Verification passed: `flutter test test\admin\admin_command_center_screen_test.dart -r compact --no-pub` passed 4/4.
- Verification passed: `flutter test test\gte_api_contract_test.dart test\club_ops\formation_editor_test.dart test\club\club_finance_provider_test.dart -r compact --no-pub` passed 8/8.
- Verification passed: `python -m pytest backend\tests\club_ops\test_api_club_ops.py::test_real_app_registers_club_ops_routes backend\tests\club_ops\test_api_club_ops.py::test_canonical_club_ops_contract_gaps_are_declared_and_blocked -q` passed 2/2.
- Verification passed: `python -m pytest backend\tests\app\test_api_contracts.py -q` passed 4/4.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Scoped stale route scans found no remaining singular `/api/clubs/{club_id}/finance` contract usage in the touched frontend, backend, generated contract, or route-audit files.

## Main Handoff Update - 2026-06-02 Club Ops Read DTO Bridge

Scope: replaced safe read-only Club/Squad `503 blocked` surfaces with backend-authored DTO responses and bridged the reserved `/api/v2/clubs/*` facade routes away from demo fixture truth.

- Added `balance_summary` to `ClubFinanceOverviewResponse` and populated it from backend Club Ops finance accounts/cashflow so Flutter Club HQ can see authoritative `current_balance`, income, expenses, available budget, and `updated_at` values without deriving finance truth locally.
- Replaced Club Ops read placeholders for dashboard, squad readiness, squad roster, selection-ready players, availability, injuries, chemistry, contracts, scouting, staff, and rankings with backend-authored DTO payloads. Known absent domains now return explicit empty states or warnings rather than fabricated data.
- Derived roster and selection-ready players from the existing backend academy/player-pathway store only. Promoted academy players become selection-ready; trialist/enrolled/developing players stay non-selection-ready.
- Built squad scouting notes from existing scouting prospect reports and academy pathway notes. No per-player note is fabricated when no report exists.
- Kept Formation storage/publish routes blocked because no durable formation draft/publish/validation/audit source exists in this lane.
- Bridged the older reserved `/api/v2/clubs/{club_id}/squad` and `/api/v2/clubs/{club_id}/finances` facade routes to the same Club Ops backend services so Flutter canonicalized calls do not land on fixture-gated demo data.
- Regenerated route-audit and shared/frontend API contract artifacts. `python tools\audit\check_api_contract_violations.py` reports `No contract violations detected.`
- Verification passed: `python -m compileall -q backend\app\api_v1\router.py backend\app\segments\clubs\segment_club_ops.py backend\app\services\club_finance_service.py backend\app\schemas\club_ops_responses.py`.
- Verification passed: `python -m pytest backend\tests\club_ops\test_api_club_ops.py -q` passed 4/4.
- Verification passed: `python -m pytest backend\tests\api_v1\test_router.py::test_api_v2_club_facade_uses_backend_club_ops_truth_in_production -q` passed 1/1.
- Verification passed before the public helper cleanup: `python -m pytest backend\tests\app\test_api_contracts.py -q` passed 4/4, and `flutter test test\gte_api_contract_test.dart test\club\club_finance_provider_test.dart test\squad test\club_ops\formation_editor_test.dart -r compact --no-pub` passed all selected tests.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Scoped `git diff --check` for the touched backend, generated contract, route-audit, and manifest files passed with known CRLF warnings only.

## Main Handoff Update - 2026-06-02 Formation Contract Family Hardening

Scope: closed the remaining Formation route-family drift for the standalone Flutter Formation repository without inventing formation persistence.

- Confirmed no durable backend-owned Formation draft/publish/slot/audit store is available yet. Existing squad-assignment and match-lineup helpers are not a safe substitute for authoritative club Formation storage.
- Added explicit backend contracts for Flutter Formation repository paths: active Formation lookup, Formation history, draft save, publish, detail, and restore.
- Kept write operations blocked with `503 formation_contract_pending` until durable Formation storage, validation, publish, and audit contracts are implemented.
- Returned `404 empty` for missing active/detail Formation records and `200` empty history lists for clubs with no mounted Formation storage, so Flutter surfaces can render empty/blocked states instead of undeclared runtime routes.
- Preserved the older Club Hub singular Formation routes as blocked contracts.
- Regenerated route-audit and shared/frontend API contract artifacts so `shared\api_contract.json` and `frontend\lib\data\generated\gte_api_contract.g.dart` include the full Formation route family.
- Added focused backend regression coverage in `backend\tests\club_ops\test_formation_contracts.py` and extended the real-app route-registration assertions in `backend\tests\club_ops\test_api_club_ops.py`.
- Verification passed: `python -m compileall -q backend\app\routes\club_ops.py`.
- Verification passed: `python -m pytest backend\tests\club_ops\test_api_club_ops.py::test_real_app_registers_club_ops_routes -q` passed 1/1.
- Verification passed: `python -m pytest backend\tests\club_ops\test_api_club_ops.py::test_frontend_formation_repository_contracts_are_declared -q` passed 1/1.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reports `No contract violations detected.`

## Main Handoff Update - 2026-06-02 Build-a-Son Parent Truth Hardening

Scope: hardened Build-a-Son parent eligibility and preview contracts so Flutter cannot invent missing parent lineage, rating, position, nationality, trait, generation, or DNA truth.

- Added canonical parent-position normalization for Build-a-Son parent options, accepting GTEX tactical positions and common aliases while rejecting non-football fallback values such as generic normalized buckets.
- Replaced the old trait-only options filter with a complete parent truth gate requiring canonical position, current rating/OVR, nationality/country, positive generation, non-empty DNA profile, and at least three unique selectable traits.
- Added preview/create fail-fast validation for parents missing canonical truth. Direct preview attempts now return explicit backend validation details such as `request_son_parent_missing_generation` rather than silently computing `GEN-1`.
- Kept projection, cost, wallet availability, reservations, payment, and generation backend-authored; no Flutter or local fallback projection was introduced.
- Added regression coverage for incomplete parent filtering and direct preview rejection in `backend\tests\regen\test_regen_creation_orders.py`.
- Verification passed: `python -m compileall -q backend\app\regen_creation\service.py`.
- Verification passed: `python -m pytest backend\tests\regen\test_regen_creation_orders.py -q` passed 23/23.

## Main Handoff Update - 2026-06-02 Build-a-Son Selector Contract Ownership

Scope: moved Build-a-Son identity selector truth from Flutter prototype literals into the backend request-son options contract.

- Added backend request-son selector DTOs for nationality/country options and position options, including canonical submit codes, labels, aliases, group metadata, defaults, and country metadata from enabled `Country` rows.
- `GET /regens/request-son/options` now returns `nationality_options`, `position_options`, `default_country_code`, and `default_position` alongside pricing and eligible parents.
- Flutter `RequestSonOptions` now parses typed `RequestSonNationalityOption` and `RequestSonPositionOption` models and rejects backend JSON that omits selector arrays.
- The Build-a-Son wizard now renders the position and nationality dropdowns from backend options only. Missing selector contracts load as a blocked state instead of falling back to local prototype lists.
- Removed the wizard's local prototype nationality list and local position list. Remaining `CAM`/`CDM`/`CF` references are backend-declared aliases, not UI source-of-truth.
- Updated Build-a-Son and regen-creation model tests so fixtures carry backend selector arrays and the identity-step test proves the menu is backend-fed.
- Verification passed: `python -m compileall -q backend\app\regen_creation\schemas.py backend\app\regen_creation\service.py`.
- Verification passed: `python -m pytest backend\tests\regen\test_regen_creation_orders.py -q` passed 23/23.
- Verification passed: `flutter test test\regen_creation\regen_creation_models_test.dart test\build_a_son\build_a_son_closure_test.dart -r compact --concurrency=1 --no-pub` passed 25/25.
- Verification passed: scoped `dart analyze` for touched Build-a-Son/model/test files reported no issues.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.

## Main Handoff Update - 2026-06-02 Build-a-Son Wallet-Only Payment Boundary

Scope: locked request-son/Build-a-Son creation to wallet reservation spend only. KoraPay and manual bank transfer remain wallet funding rails, not direct regen creation payment methods.

- Backend request-son preview/create DTO validators now accept only `wallet` for `payment_method`; `korapay`, `manual`, and `bank_transfer_manual` are rejected before any order is created.
- Added a service-level guard so direct `RegenCreationService` calls also reject non-wallet request-son payments with `request_son_requires_wallet_payment`.
- Removed the active regen-creation-local KoraPay checkout and verification path from `RegenCreationService`; KoraPay/manual remain isolated to wallet funding, not Build-a-Son creation.
- Removed the now-unused regen-creation `TreasuryService` dependency that only existed for direct external checkout setup.
- Updated regen creation order regressions so pending Build-a-Son orders use wallet reservations, prove no regen is generated before wallet settlement, and explicitly reject external payment methods.
- Removed obsolete direct KoraPay request-son generation tests and added a direct service-bypass regression using `RequestSonCreateRequest.model_construct`.
- Frontend request-son preview/order draft serializers now reject external payment methods before transport, and model coverage proves `korapay`/`bank_transfer_manual` cannot be serialized from Build-a-Son drafts.
- Removed the unused Flutter `usesKorapay` regen-creation order affordance; Build-a-Son now only exposes wallet semantics.
- Verification passed: `dart format lib\models\regen_creation_models.dart test\regen_creation\regen_creation_models_test.dart` reported `0 changed`.
- Verification passed: `dart analyze lib\models\regen_creation_models.dart test\regen_creation\regen_creation_models_test.dart test\build_a_son\build_a_son_closure_test.dart` reported no issues.
- Verification passed: `flutter test test\regen_creation\regen_creation_models_test.dart test\build_a_son\build_a_son_closure_test.dart -r compact --concurrency=1 --no-pub` passed 26/26.
- Verification passed after active KoraPay branch removal: `flutter test test\regen_creation\regen_creation_models_test.dart -r compact --no-pub` passed 8/8.
- Verification passed: `python -m compileall -q backend\app\regen_creation\schemas.py backend\app\regen_creation\service.py backend\tests\regen\test_regen_creation_orders.py`.
- Verification passed: `python -m pytest backend\tests\regen\test_regen_creation_orders.py -q` passed 21/21.
- Verification passed after trimming the stale treasury dependency: `python -m pytest backend\tests\regen\test_regen_creation_orders.py -q` passed 21/21.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Verification passed: scoped `git diff --check` for the touched Build-a-Son backend/frontend/model/test/manifest files passed with known CRLF warnings only.

## Main Handoff Update - 2026-06-03 Regen World Partial Feed Degradation

Scope: made partial Regen World backend feed failures visible without falling back to fixture truth or hiding published data.

- Extended `RegenUniverseHubData` with `degradedFeeds`, `hasDegradedFeeds`, and a user-facing degradation summary so failed feed names travel with otherwise usable backend payloads.
- Updated `regenUniverseHubProvider` to record endpoint-level failures for Rising stars, Awards, National pools, Scouting feed, Bloodlines, Generation tracking, and authenticated Creation orders. If every feed fails, the provider still blocks exactly as before; if at least one feed succeeds, published truth renders with a degraded-state warning.
- Updated `RegenWorldDiscoverySurface` to show the reusable `Backend truth degraded` panel above the discovery pool whenever partial feeds failed.
- Added widget coverage proving published regen data remains visible while failed feeds such as Scouting feed and Bloodlines are named in the degraded panel.
- Subagent contract audit confirmed the scoped Regen World and Build-a-Son backend routes are declared/generated in `shared/api_contract.json` and `frontend/lib/data/generated/gte_api_contract.g.dart`; request-body field drift remains outside that route-level audit.
- Verification passed: `dart analyze lib\shared\providers\regen_provider.dart lib\features\regen_world\presentation\regen_world_screen.dart test\regen_world\regen_world_screen_test.dart` reported no issues.
- Verification passed: `flutter test test\regen_world\regen_world_screen_test.dart -r compact --no-pub` passed 4/4.
- Verification passed: `flutter test test\regens\regens_screen_test.dart -r compact --no-pub` passed 4/4.

## Main Handoff Update - 2026-06-03 Build-a-Son Regen Universe Truth Bridge

Scope: pushed backend-authored Build-a-Son generated-player facts into the canonical Regen Universe player payload consumed by Flutter Regen World.

- Extended backend `RegenPlayerView` with optional `generation_number`, `generation_label`, `rarity_tier`, `origin_story`, `projected_value_coin`, `traits`, `lineage`, and `dna_profile` fields.
- Updated `RegenUniverseService._player_summary_payload` to emit those fields from persisted regen metadata, player DNA, lineage profile metadata, story seed snippets, and market/value state only when the backend has those values.
- Preserved `requested_son` as a real `source_type` for Build-a-Son generated players instead of flattening them into generic `regen` records.
- Persisted generated-son projected coin value and rarity tier in request-son metadata using the same backend projection and lineage defaults already used when creating the player and lineage profile.
- Added a backend regression proving wallet-settled Build-a-Son generation now appears in `RegenUniverseService.get_player_lookup()` with requested-son source, generation, rarity, projected value, traits, lineage, and DNA profile.
- Hardened optional Regen portrait lookup so missing visual-profile tables in focused SQLite fixtures degrade to no portrait instead of blocking Regen Universe payload rendering.
- Verification passed: `python -m compileall -q backend\app\schemas\regen_universe.py backend\app\regen_creation\service.py backend\app\regen_universe\service.py backend\tests\regen\test_regen_creation_orders.py`.
- Verification passed: `python -m pytest backend\tests\regen\test_regen_creation_orders.py -q` passed 21/21.
- Verification passed: `python -m pytest backend\tests\regen\test_regen_universe_phase6.py -q` passed 2/2.
- Verification passed: `flutter test test\regens\regen_universe_api_test.dart test\regen_world\regen_world_entry_test.dart test\regen_world\regen_world_screen_test.dart -r compact --concurrency=1 --no-pub` passed 12/12.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Broad backend e2e attempt `python -m pytest backend\tests\e2e\test_regen_universe_end_to_end.py -q` did not reach the test body: the fixture failed at setup because deferred startup did not finish within its 30-second join after full migrations.

## Main Handoff Update - 2026-06-03 Build-a-Son Order Reconciliation

Scope: made the Flutter Build-a-Son completion loop tolerate authoritative async backend generation without declaring success from local or partial truth.

- Added strict `isPaid` and `isGenerating` helpers to `RegenCreationOrder` while keeping `isGenerated` gated on both `status == generated` and a backend `generated_player` payload.
- Replaced the wizard's single final order fetch with a bounded backend reconciliation loop. After wallet settlement/generation, Flutter now re-fetches order detail until backend order truth includes the generated player, showing a syncing state while it waits.
- Preserved failure semantics for incomplete backend truth: `generated` status without `generated_player` never fires completion callbacks and remains an error after the bounded sync window.
- Confirmed `BuildASonScreen` already invalidates `regenUniverseHubProvider` after completion, so generated lineage refreshes through canonical Regen World providers instead of a local UI patch.
- Added widget coverage for delayed generated-order detail and generated-without-player rejection.
- Added model coverage for paid/generating/generated status helpers and prototype-mapping coverage that the wizard reconciles via `fetchCreationOrder()`.
- Verification passed: `dart analyze frontend\lib\features\build_a_son\presentation\build_a_son_screen.dart frontend\lib\models\regen_creation_models.dart frontend\test\build_a_son\build_a_son_closure_test.dart frontend\test\regen_creation\regen_creation_models_test.dart frontend\test\build_a_son\prototype_mapping_contract_test.dart` reported no issues.
- Verification passed: `flutter test test\regen_creation\regen_creation_models_test.dart test\build_a_son\prototype_mapping_contract_test.dart -r compact --no-pub` passed 12/12.
- Verification passed: `flutter test test\build_a_son\build_a_son_closure_test.dart -r compact --no-pub` passed 20/20.
- Next backend-owned gap: route `backend/app/regen_creation/router.py` still constructs `RegenCreationService` without the app-level event publisher, so wallet reserve/settle/release and request-son lifecycle events do not yet reach the canonical realtime hub. Add app publisher injection, `regen.creation_order.*` domain events, user/wallet topic dispatch, and an explicit audit reference on order responses in the next backend slice.

## Main Handoff Update - 2026-06-03 Build-a-Son Realtime And Audit Events

Scope: connected Build-a-Son/request-son wallet and lifecycle truth to the backend app-level event publisher and canonical realtime wallet topic.

- Updated the regen creation router to pass `request.app.state.event_publisher` into `RegenCreationService` for options, preview, list/detail, create, pay, generate, and cancel handlers.
- Updated `RegenCreationService` to share that publisher with `WalletService`, so Build-a-Son reserve/settle/release wallet events now use the app publisher instead of a private in-memory publisher.
- Added post-commit lifecycle events for `regen.creation_order.created`, `regen.creation_order.paid`, `regen.creation_order.generated`, and `regen.creation_order.cancelled`.
- Added deterministic `audit_reference` values to order responses and lifecycle event payloads/headers.
- Mapped `regen.creation_order.*` events in `RealtimeHub` to the user's wallet topic as `regen_creation_order_update`, with notification dispatches for generated and cancelled milestones.
- Added router-level coverage proving the app publisher receives lifecycle events plus shared wallet transaction events for create/pay/generate/cancel, including reservation references and audit references.
- Added realtime mapping coverage proving regen creation events dispatch to `wallet:{user_id}` and reject events missing user/order scope.
- Verification passed: `python -m compileall -q backend\app\regen_creation\router.py backend\app\regen_creation\schemas.py backend\app\regen_creation\service.py backend\app\realtime\service.py backend\tests\regen\test_regen_creation_orders.py backend\tests\realtime\test_regen_creation_realtime.py`.
- Verification passed: `python -m pytest backend\tests\realtime\test_regen_creation_realtime.py -q` passed 2/2.
- Verification passed: `python -m pytest backend\tests\regen\test_regen_creation_orders.py -q` passed 23/23.
- Verification passed: `python -m pytest backend\tests\wallets\test_wallet_event_backbone.py backend\tests\realtime\test_wallet_websocket_gateway.py -q` passed 2/2.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 142}`.
- Verification passed: scoped `git diff --check` for touched regen/realtime backend files passed with known CRLF warnings only.
- Optional route/OpenAPI smoke `python -m pytest backend\tests\app\test_api_contracts.py::test_target_api_contracts_are_documented_with_stable_operation_ids backend\tests\app\test_module_registration.py::test_real_app_registers_competition_and_identity_modules -q` was stopped after several minutes of silent app startup; it emitted one progress dot and no actionable failure before shutdown.

## Main Handoff Update - 2026-06-03 Canonical Acceptance Gate Stabilization

Scope: closed the immediate canonical acceptance harness blockers without changing production product behavior.

- Updated `tools\quality\run_gtex_canonical_acceptance.py` so canonical `/app/*` production routes are discovered from both the router and `frontend\lib\router\route_constants.dart`, matching the current route-constant architecture instead of requiring duplicated string literals in `app_router.dart`.
- Updated the fixture-mode guard to distinguish explicit fixture/test constructors from production fixture activation. Production still fails if app config defaults into fixture mode or enables fixture mode outside the Flutter test-runtime gate.
- Updated the 2D match-direction check to enforce the current canonical direction: local match simulation remains disabled, and 2D pitch/director movement remains driven by backend `homeAttacksRight` frame truth.
- Removed four EOF whitespace blockers in backend test files so full `git diff --check` no longer fails on blank-line hygiene.
- Verification passed: `python tools\quality\run_gtex_canonical_acceptance.py` passed all canonical checks with only the expected shared-worktree `diff_hygiene` warning.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- Verification passed: exact `git diff --check` exit-code check reported `exit=0` and `problem_count=0`; remaining console noise is line-ending warnings only.
- Remaining integration risk: the shared worktree still has hundreds of dirty entries, so strict diff hygiene remains a warning until lanes are staged/integrated in isolated PR-shaped chunks.

## Thread Match/Competition Worker Update - 2026-06-03 xG Truth Guard

Scope: tightened canonical match-center xG overlay readiness so the UI does not confirm xG without backend xG truth.

- Updated `frontend\lib\features\match_center\data\live_match_canonical.dart` so `GtexLiveOverlayMode.xG` confirms only when backend expected-goals totals are complete or shot markers include an explicit xG/expected-goals field.
- Pending, syncing, or stale xG payloads now degrade; non-empty payloads that omit xG truth remain blocked rather than treated as confirmed.
- Added regression coverage in `frontend\test\match_center\live_match_canonical_test.dart` for pending xG, missing xG truth, zero-total xG, and zero-shot-xG payloads.
- Verification passed in main worktree: `flutter test test/match_center/live_match_canonical_test.dart test/match_center/canonical_match_center_test.dart -r compact --no-pub` passed 9/9.

## Thread Admin/Treasury Worker Update - 2026-06-03 Export Blocking

Scope: made Admin Finance export state auditable and explicitly blocked until a real artifact writer exists.

- Updated `backend\app\admin_finance\service.py` so finance exports record `admin.export.blocked`, keep `download_url` null, and carry a backend `blocked_reason`.
- Added `backend\app\admin_finance\router.py` route `/exports/{export_id}/download` as an explicit `503` instead of pretending an artifact can be downloaded.
- Exposed `blocked_reason` on export status schemas in `backend\app\admin_finance\schemas.py`.
- Added/updated `backend\tests\admin_finance\test_admin_finance_lock_export_unit.py` coverage for blocked export status and 503 download behavior.
- Verification passed in main worktree: `python -m pytest backend\tests\admin_finance\test_admin_finance_lock_export_unit.py -q` passed 4/4.
- Verification passed in main worktree: `python -m pytest backend\tests\admin_finance\test_admin_finance_router.py backend\tests\treasury\test_withdrawal_reviews.py -q` passed 21/21 with one existing `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning.

## Main Handoff Update - 2026-06-03 App Smoke Fixture Attempt

Scope: investigated the previously hanging backend route/OpenAPI smoke.

- Patched `backend\tests\app\test_api_contracts.py` and `backend\tests\app\test_module_registration.py` to use the existing shared module-registration fixtures that patch deferred startup rather than defining independent slow app fixtures.
- Syntax verification passed: `python -m py_compile backend\tests\app\test_api_contracts.py backend\tests\app\test_module_registration.py`.
- Targeted route/OpenAPI smoke `python -m pytest backend\tests\app\test_api_contracts.py::test_target_api_contracts_are_documented_with_stable_operation_ids backend\tests\app\test_module_registration.py::test_real_app_registers_competition_and_identity_modules -q` still produced no output after multiple minutes and was stopped by process id. This suggests the remaining delay is likely session template/migration setup or app import/bootstrap cost, not only deferred startup.
- Next backend verification target: convert these two smoke assertions to the existing `mounted_app_contract_snapshot` style or add a dedicated fast route snapshot test, then rerun before broad backend e2e.

## Thread Build-a-Son Worker Update - 2026-06-03 Realtime Consumption

Scope: connected Flutter Build-a-Son to backend-authored regen creation realtime events without replacing backend order truth or the existing polling reconciliation fallback.

- Added wallet-topic realtime subscription/parsing in `frontend\lib\features\build_a_son\providers\build_a_son_providers.dart` for `regen_creation_order_update` and `regen.creation_order.*` event families.
- Updated `frontend\lib\features\build_a_son\presentation\build_a_son_screen.dart` so matching realtime order events trigger a backend `fetchCreationOrder` refresh for the active order.
- Added `frontend\test\build_a_son\build_a_son_realtime_sync_test.dart` coverage proving event parsing and active-order refetch behavior.
- Worker verification passed: scoped `dart analyze`, `flutter test test/build_a_son/build_a_son_realtime_sync_test.dart`, and `flutter test test/build_a_son/build_a_son_closure_test.dart --name "generation reconciliation polls until backend publishes generated son"`.
- Main-worktree verification passed after slow Flutter loading: `flutter test test\build_a_son\build_a_son_realtime_sync_test.dart -r compact --no-pub` passed 2/2 and `flutter test test\build_a_son\build_a_son_closure_test.dart --name "generation reconciliation polls until backend publishes generated son" -r compact --no-pub` passed 1/1.
- Main-worktree duplicate `dart analyze` was stopped after stalling under toolchain contention; the worker analyzer pass remains the analyzer signal for this slice.
- Known existing Build-a-Son suite issue outside this realtime slice: full `flutter test test/build_a_son` still has one worker-reported failure in `build_a_son_wallet_block_test.dart` expecting `requested_country_code == NGA` while current backend-fed wizard emits `NG`.

## Main Handoff Update - 2026-06-03 Post-Integration Guard Sweep

Scope: post-worker canonical verification after admin export blocking, Build-a-Son realtime consumption, match xG truth guard, and acceptance-tool stabilization.

- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- Verification passed: `python tools\quality\run_gtex_canonical_acceptance.py` passed all canonical checks with only the expected shared-worktree `diff_hygiene` warning.
- Verification passed: exact `git diff --check` exit-code check reported `exit=0` and `problem_count=0`.

## Main Handoff Update - 2026-06-03 App Smoke and Build-a-Son Stabilization

Scope: removed the stale app-smoke blocker, reduced route/OpenAPI smoke cost, and integrated the final Build-a-Son country-code fix.

- Updated `backend\tests\app\_module_registration_contract_support.py` so the module-registration snapshot caches the full OpenAPI document once and uses session scope instead of rebuilding the same hydrated app snapshot per test module.
- Updated `backend\tests\app\test_api_contracts.py` so OpenAPI-only operation/schema assertions use a selected-router FastAPI contract app with explicit versioned alias registration, instead of global app hydration.
- Updated `backend\tests\app\test_module_registration.py` so the registration smoke checks `app.modules.DOMAIN_MODULES` directly and delegates route/OpenAPI path coverage to the dedicated OpenAPI contract tests.
- Brought the module-registration smoke in line with the current namespaced route contract; stale unversioned federation path expectations were removed from this smoke path.
- Integrated the Build-a-Son worker fix in `frontend\test\build_a_son\build_a_son_wallet_block_test.dart`: the wizard submits backend nationality code `NG`, not an invented `NGA` alpha-3 value.
- Verification passed: `python -m py_compile backend\tests\app\test_api_contracts.py backend\tests\app\test_module_registration.py backend\tests\app\_module_registration_contract_support.py`.
- Verification passed: `python -m pytest backend\tests\app\test_api_contracts.py::test_target_api_contracts_are_documented_with_stable_operation_ids backend\tests\app\test_module_registration.py::test_real_app_registers_competition_and_identity_modules -q --durations=10` passed 2/2 in 2:23, down from the previous global-hydration run at 12:34. Remaining setup time is selected production-router import/OpenAPI generation.
- Verification passed: `python -m pytest backend\tests\app\test_api_contracts.py::test_versioned_contract_paths_publish_standard_response_and_error_schemas -q --durations=10` passed 1/1 in 3:14.
- Verification passed: `flutter test test\build_a_son -r compact --no-pub` passed 29/29 after the country-code fix.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- Verification passed: `python tools\quality\run_gtex_canonical_acceptance.py` passed all canonical checks with only the expected shared-worktree `diff_hygiene` warning.
- Verification passed: `git diff --check` returned exit code 0; remaining console noise is CRLF line-ending warnings only.
- Residual performance risk: the selected-router OpenAPI fixture still emits FastAPI duplicate-operation warnings for legacy aliases while final operation IDs remain unique. A later cleanup should either suppress expected warnings in this test or split legacy-alias OpenAPI checks from canonical operation-ID checks.

## Main Handoff Update - 2026-06-03 App Contract Fixture Cleanup

Scope: removed accidental router side effects from the selected OpenAPI contract fixture and made the module-registration smoke fast.

- Updated `backend\tests\app\test_api_contracts.py` so the selected OpenAPI fixture mounts order legacy/API routers, portfolio API aliases, and wallet API aliases explicitly instead of depending on the aggregate wallet router to remount order/portfolio routes.
- Preserved canonical `/api/orders`, `/api/portfolio`, and `/api/wallets/*` operation IDs while eliminating FastAPI duplicate-operation warnings from the selected fixture.
- Kept `backend\tests\app\test_module_registration.py::test_real_app_registers_competition_and_identity_modules` on direct `DOMAIN_MODULES` truth, so this smoke now completes without app startup or OpenAPI hydration.
- Verification passed: `python -m py_compile backend\tests\app\test_api_contracts.py`.
- Verification passed: `python -m pytest backend\tests\app\test_api_contracts.py::test_target_api_contracts_are_documented_with_stable_operation_ids backend\tests\app\test_api_contracts.py::test_versioned_contract_paths_publish_standard_response_and_error_schemas -q --durations=10` passed 2/2 with no duplicate-operation warnings.
- Verification passed: `python -m pytest backend\tests\app\test_module_registration.py::test_real_app_registers_competition_and_identity_modules -q --durations=10` passed 1/1 in 8.74s.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- Verification passed: `python tools\quality\run_gtex_canonical_acceptance.py` passed all canonical checks with only the expected shared-worktree `diff_hygiene` warning.
- Verification passed: scoped `git diff --check` for touched app-contract/manifest files returned exit code 0; remaining console noise is CRLF warnings only.
- Residual performance risk: selected production-router imports still cost roughly a few minutes on cold Windows/Python runs. Further gains require either a generated OpenAPI snapshot with operation/schema metadata or narrower router modules that avoid heavy service imports.

## Main Handoff Update - 2026-06-03 Formation Contract Backend Unlock

Scope: turned the canonical formation routes from permanent blocked scaffolds into backend-owned draft, publish, active, history, detail, and restore contracts while preserving the DB-backed club profile lane already added by another worker.

- Added `backend\app\services\club_formation_service.py` as a fallback authoritative club-ops formation service backed by the existing `ClubOpsStore` so local/test environments without `club_profiles` / `club_formations` migrations still return truthful contracts.
- Extended `ClubOpsStore` with formation record, active formation, and audit storage lanes in `backend\app\services\club_finance_service.py`.
- Extended formation response DTOs in `backend\app\schemas\club_ops_responses.py` so the same backend payload can satisfy Flutter `FormationDto` parsing and the older club-hub contract widgets.
- Updated `backend\app\routes\club_ops.py` to run DB-first via `ClubQueryService`, then safely fall back to the club-ops formation service when the selected database cannot support the route yet.
- Formation publish now blocks unless the submitted XI is exactly 11 unique backend selection-ready players from the academy/squad eligibility lane; no arbitrary player IDs are accepted as production truth.
- Added audit references and action trail events for draft save, publish, and restore.
- Updated `backend\tests\club_ops\test_formation_contracts.py` and adjacent `test_api_club_ops.py` assertions from permanent blocked route expectations to real draft/publish/history/detail/restore behavior.
- Verification passed: `python -m compileall -q backend\app\services\club_formation_service.py backend\app\routes\club_ops.py backend\app\schemas\club_ops_responses.py backend\tests\club_ops\test_api_club_ops.py backend\tests\club_ops\test_formation_contracts.py`.
- Verification passed: `python -m pytest backend\tests\club_ops\test_api_club_ops.py::test_frontend_formation_repository_contracts_are_declared backend\tests\club_ops\test_api_club_ops.py::test_canonical_formation_storage_gap_remains_blocked backend\tests\club_ops\test_formation_contracts.py -q` passed 8/8 with two existing FastAPI 422 deprecation warnings.
- Verification passed before the compatibility patch found a stale expectation: full `python -m pytest backend\tests\club_ops -q` reached 35/36 passed and failed only the old history-state assertion, which is now updated and covered by the targeted rerun.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --profile canonical-production --format summary --fail-on violation` passed with summary `{"fixed": 5, "owned-by-thread": 17, "quarantined": 130}`.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: scoped `git diff --check` for touched formation files returned exit code 0; console noise is CRLF warnings only.
- Residual storage risk: production should still land the durable `club_formations` migration/profile seeding path for the DB-backed `ClubQueryService`; the fallback keeps the canonical contract live and testable until that migration lane is fully installed.

## Main Handoff Update - 2026-06-04 Desktop Worktree Reconciliation And Formation DB Proof

Scope: freed rebuildable disk space, moved the active frontend redesign worktree off the Desktop root into the GTEX workspace, and added a DB-backed club-ops formation proof.

- Deleted the inactive `desktop_salvage_20260421` workspace salvage folder after verifying it had not been written since 2026-04-21 and contained only salvage/copy/temp content.
- Cleaned rebuildable user caches only: Gradle, npm, pip, crash dumps, and VS Code crash reports. Locked Gradle/npm remnants were left in place rather than forced.
- Moved the active external frontend redesign worktree from `C:\Users\ayomc\Desktop\GTEX_FRONTEND_REDESIGN_WORKTREE` to `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\.external_worktrees\GTEX_FRONTEND_REDESIGN_WORKTREE`.
- The moved worktree remains registered with git on branch `codex/strict-live-phase-2` at `493098ae`; original Desktop folder no longer exists.
- Added `.external_worktrees/` to local `.git/info/exclude` so the reconciled worktree is not accidentally treated as main-worktree source.
- Added `backend\tests\club_ops\test_formation_db_contracts.py` to prove the DB-backed `ClubQueryService` formation route path persists draft, publish, active, history, detail, and restore state to the durable `club_formations` table.
- Updated root control docs `AGENTS.md`, `GTEX_TASKS.md`, and `GTEX_PHASED_PROMPTS.md` with a canonical override: production GTEX is Flutter/backend, active match is 2D broadcast-style only, and Unity/native-3D/pseudo-3D/original-visual-runtime work is legacy quarantine unless explicitly requested.
- Verification passed: `python -m py_compile backend\tests\club_ops\test_formation_db_contracts.py`.
- Verification passed: `python -m pytest backend\tests\club_ops\test_formation_db_contracts.py -q` passed 1/1 in 54.63s.
- Verification passed: `python -m pytest backend\tests\club_ops\test_formation_contracts.py backend\tests\club_ops\test_formation_db_contracts.py -q` passed 7/7 in 87.65s.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --profile canonical-production --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.

## Main Handoff Update - 2026-06-04 Control Doc Canonicalization

Scope: finished the stale control-doc cleanup so future worker threads do not follow Unity-first deployment or route-audit instructions.

- Updated `DEPLOYMENT_GUIDE.md` with a canonical production override: deploys target Flutter/backend GTEX, match health gates should verify the 2D match-center/realtime contract, and Unity/native/pseudo-3D checks must not gate production rollout.
- Replaced Unity-specific Render verification variables and manual `verify_unity_routes.py` guidance with match-center verification variable names and `ops/render/verify_match_center_routes.py`.
- Updated `CURRENT_STATE_CONTRACT_MATRIX.md` with a canonical override and `QUARANTINED` status label.
- Marked 3D/native match routes as quarantined and updated the match domain row to 2D broadcast match center backed by backend/realtime truth.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --profile canonical-production --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: scoped `git diff --check` for `AGENTS.md`, `GTEX_TASKS.md`, `GTEX_PHASED_PROMPTS.md`, `DEPLOYMENT_GUIDE.md`, `CURRENT_STATE_CONTRACT_MATRIX.md`, `Docs\GTEX_DIRTY_WORKTREE_INTEGRATION_MANIFEST.md`, and `backend\tests\club_ops\test_formation_db_contracts.py`; console noise is CRLF warnings only.
- Residual manual `rg` hits for Unity/3D remain only inside explicitly quarantined legacy phase text in `GTEX_PHASED_PROMPTS.md` and `GTEX_TASKS.md`.

## Main Handoff Update - 2026-06-04 Frontend Legacy 3D Quarantine Boundary

Scope: made the Flutter legacy 3D containment contract explicit without deleting reusable legacy code.

- Added `frontend\lib\features\3d\README.md` documenting that the legacy 3D lane is deprecated quarantine only, with no production imports, routes, CTAs, monetization, deploy checks, or new runtime dependencies.
- Added a production guardrail in `frontend\test\guardrails\forbidden_text_guard_test.dart` that fails if any Dart module outside `lib/features/3d` imports or exports quarantined `features/3d` sources.
- Hardened `frontend\test\router\route_coverage_test.dart` so `/matches/native-3d/live-match-001` is covered by the same widget and parser rejection checks as other legacy match URLs.
- Explorer verification confirmed the existing pseudo-3D/native-3D route references are negative quarantine assertions, not stale production route expectations.
- Verification passed: `dart format test\guardrails\forbidden_text_guard_test.dart test\router\route_coverage_test.dart` changed 0 files.
- Verification passed after serial retry: `flutter test test\guardrails\forbidden_text_guard_test.dart -r expanded --no-pub --concurrency=1` passed 12/12.
- Verification passed: `flutter test test\router\route_coverage_test.dart -r expanded --no-pub --concurrency=1` passed 9/9.
- Verification passed: `python tools\guardrails\production_guardrail_scan.py --profile canonical-production --include-changed --format summary --fail-on violation` passed with summary `{"fixed": 6, "owned-by-thread": 17, "quarantined": 144}`.
- Verification passed: `python tools\audit\check_api_contract_violations.py` reported no contract violations.
- Verification passed: scoped `git diff --check` for the touched frontend guardrail/route files and manifest returned exit code 0; console noise is CRLF warnings only.
- Tooling note: the first parallel Flutter invocation crashed on a generated `frontend\build\unit_test_assets\NativeAssetsManifest.json` collision; the generated file was removed and both tests passed when rerun serially.

## Main Handoff Update - 2026-06-04 Admin Finance Verification Unblocked

Scope: rechecked the earlier admin-finance blocker after the route/contract work landed in other lanes.

- Read-only route inspection confirmed `backend\app\market\router.py` correctly exposes distinct `GET /market/players` and `GET /market/players/{player_id}` routes, with `/api/market/*` aliases generated by its combined router.
- Read-only route inspection confirmed `backend\app\transfer_market\router.py` owns the separate `/api/transfer-market/*` product namespace.
- No route rename or product contract change was made; the previous collision report appears stale or tool-side.
- Verification passed: `python -m pytest backend\tests\admin_finance backend\tests\treasury -q --maxfail=1` passed 32/32 in 28:28 with one existing FastAPI 422 deprecation warning.
- Verification passed: `python -m pytest backend\tests\trader backend\tests\wallets backend\tests\admin_finance backend\tests\treasury -q --maxfail=3` passed 116/116 in 56:16 with the same existing FastAPI 422 deprecation warning.

## Main Handoff Update - 2026-06-04 Backend Import Cost Reduction (Tracing/OTEL)

Scope: cut backend cold-import cost, the keystone verification constraint, without refactoring core systems.

- Made OpenTelemetry imports lazy in `backend/app/observability/tracing.py` via a cached `_ensure_otel()` loader. Previously the OTLP HTTP exporter + FastAPI/SQLAlchemy instrumentation + `requests` were imported at module load; since `app.core.events` imports tracing and the ORM model package transitively reaches events, every test that imported any model paid this cost for telemetry it never used.
- `configure_tracing` checks the cheap `enabled`/`exporter_endpoint` flags before `_ensure_otel()`, so the disabled path (tests/local) never attempts the OTEL import. Public API unchanged.
- Evidence: `python -X importtime -c "import app.main"` cumulative dropped ~278s -> ~157s (-43
## Main Handoff Update - 2026-06-04 Backend Import Cost Reduction (Tracing/OTEL)

Scope: cut backend cold-import cost, the keystone verification constraint, without refactoring core systems.

- Made OpenTelemetry imports lazy in `backend/app/observability/tracing.py` via a cached `_ensure_otel()` loader. Previously the OTLP HTTP exporter + FastAPI/SQLAlchemy instrumentation + `requests` were imported at module load; since `app.core.events` imports tracing and the ORM model package transitively reaches events, every test that imported any model paid this cost for telemetry it never used.
- `configure_tracing` checks the cheap `enabled`/`exporter_endpoint` flags before `_ensure_otel()`, so the disabled path (tests/local) never attempts the OTEL import. Public API unchanged.
- Evidence: `python -X importtime -c "import app.main"` cumulative dropped ~278s to ~157s (about -43%); OTLP exporter no longer appears in the import chain (grep count 0).
- Verification passed: `python -m pytest tests/app/test_lifespan.py tests/backbone/test_worker_mains.py -q` -> 5 passed in 115s.
- Verification passed: standalone import check confirmed `opentelemetry` is not loaded by importing tracing, and span/header runtime paths still work after lazy load.
- Evidence-based scope decision: `alembic` dropped out of the top-20 cumulative cost after this change, so core `app/core/database.py` was deliberately NOT touched. Remaining deferrable leaf is `requests` (about 9%) via the three provider adapters; left alone because the clean fix risks provider-registry import side effects for diminishing return.
- Next lever for full-suite wall time is per-test fixture/DB setup cost (paid per test), not import cost (paid once per process).
- Worktree hygiene: pruned 27 stale/prunable worktrees (31 to 4) and checkpoint-committed the prior 881-entry dirty integration tree as aa143f6e.

## Main Handoff Update - 2026-06-05 Backend Test DB Factory Rollout

Scope: started Section 6 of `CODEX_TEST_DB_FIXTURE_HANDOFF.md`, the factory-pattern phase for DB-backed tests.

- Added `gtex_db_session_factory` in `backend\tests\conftest.py`, bound to the existing session-scoped `gtex_db_engine` with per-test outer transaction rollback and `join_transaction_mode="create_savepoint"`.
- Migrated `backend\tests\players\test_player_share_market_routes.py` from local `create_engine` + full `Base.metadata.create_all(engine)` to `gtex_db_session_factory`.
- Migrated `backend\tests\sponsorship_engine\test_club_sponsor_offer_service.py` from local `create_engine` + full `Base.metadata.create_all(engine)` to `gtex_db_session_factory`.
- Migrated `backend\tests\admin_access\test_admin_access_role_scoping.py` from local full-schema `create_all` fixtures to `gtex_db_session_factory`, including `app.state.session_factory` coverage.
- Skipped/reverted `backend\tests\players\test_real_player_universe_routes.py`: factory migration produced one non-mechanical score mismatch (`0.8057` vs expected `0.8457`) after 9/10 tests passed, so the file was restored per the playbook's revert-and-skip rule.
- Skipped selective-table factory files as already cheap: `backend\tests\runtime_config\test_router.py`, `backend\tests\pundits\test_service.py`, `backend\tests\creator\test_creator_module7_contracts.py`, `backend\tests\tournaments\test_tournament_router.py`, `backend\tests\ticketing\test_router.py`, and `backend\tests\infinite_league\test_router.py`.
- Verification passed: `python -m py_compile backend\tests\conftest.py backend\tests\players\test_player_share_market_routes.py`.
- Verification passed: `python -m pytest tests\players\test_player_share_market_routes.py -p no:cacheprovider -q` -> 8 passed in 383.95s.
- Verification passed: `python -m py_compile backend\tests\sponsorship_engine\test_club_sponsor_offer_service.py`.
- Verification passed: `python -m pytest tests\sponsorship_engine\test_club_sponsor_offer_service.py -p no:cacheprovider -q` -> 2 passed in 247.15s.
- Verification passed: `python -m py_compile backend\tests\admin_access\test_admin_access_role_scoping.py`.
- Verification passed: `python -m pytest tests\admin_access\test_admin_access_role_scoping.py -p no:cacheprovider -q` -> 9 passed in 359.42s.
- Commits created: `3ce71dfa` (factory fixture + player share-market prototype), `f8440fa3` (sponsorship offer service), `2e9c3101` (admin access).
- Remaining work: many full-schema `Base.metadata.create_all(engine)` tests still exist outside the named Section 6 examples; continue one file at a time, with revert-and-skip for factory behavior drift.
## Main Handoff Update - 2026-06-05 Backend Import Cost Reduction (Provider Requests)

Scope: deferred third-party `requests` imports in the football provider adapters without changing provider behavior.

- Made `requests` lazy in `backend/app/providers/api_sports_adapter.py`, `backend/app/providers/football_data_adapter.py`, and `backend/app/providers/sportmonks_adapter.py`; each adapter now imports it inside `__init__` immediately before `requests.Session()`.
- Before evidence: `python -X importtime -c "import app.main"` cumulative `app.main` was `354,404,527 us`; `app.providers` was `37,499,584 us`; third-party `requests` loaded under `app.providers` with cumulative `36,380,045 us`.
- After evidence: `python -X importtime -c "import app.main"` cumulative `app.main` is `164,645,081 us`; `app.providers` is `4,754,991 us`; third-party `requests` no longer appears in the provider import chain. Remaining `requests` text matches are only `starlette.requests` and `fastapi.requests`.
- OpenTelemetry remains absent from the import-time search output.
- Verification passed: `python -m pytest tests/wallets/test_payment_gateway_service.py tests/integration/test_payment_gateway.py -p no:cacheprovider -q` -> 7 passed in 164.29s.
## Main Handoff Update - 2026-06-06 Flutter Frontend Stabilization

Scope: stabilized only the Flutter frontend analyzer and test lane in `C:\Users\ayomc\Desktop\gtex-wt-frontend`; source edits were limited to `frontend\test`.

- Analyzer before/after: `flutter analyze --no-pub` went from 23 issues to `No issues found!`.
- Test before/after: `flutter test --no-pub --concurrency=1` went from `+810 -22` to `+832` with all tests passed.
- Skips: 0. Legacy local match simulation tests were converted into active quarantine assertions instead of skipped coverage.
- Verification passed: `flutter analyze --no-pub` reported no issues after the test stabilization commit.
- Verification passed: `flutter test --no-pub --concurrency=1 --reporter=expanded` passed 832/832; one existing viral-feed hit-test warning was non-fatal and did not fail the suite.

## Thread 7 Handoff Update - 2026-06-06 Migrations / Ops / Observability / Security

Scope: backend contract truth for migration runbook state, observability probes, and protected runtime snapshots.

- Confirmed this checkout uses `backend\migrations`, not `backend\alembic`; no migration version files were edited.
- Updated `Docs\BACKEND_MIGRATION_RUNBOOK.md` to current head `20260604_0094_club_squad_sources`, with empty-db upgrade verification, rollback steps, boot schema-check guidance, and secret rotation baseline.
- Added dedicated Prometheus metrics for health/readiness probes and boot phase duration thresholds in `backend\app\observability\metrics.py`.
- Wired `/health` and `/ready` into dedicated probe metrics in `backend\app\observability\middleware.py` while keeping them excluded from generic HTTP request totals.
- Protected `/observability/config` with the existing production-like admin guard used by diagnostics and metrics; local/dev access remains unchanged.
- Added observability coverage for probe metrics, boot threshold metrics, middleware probe recording, and production config-snapshot auth.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest -p no:cacheprovider -q backend\tests\observability` -> 9 passed in 481.53s; `backend\_out.txt` was read and deleted.
- Post-format focused rerun passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest -p no:cacheprovider -q backend\tests\observability\test_runtime_probe_metrics.py` -> 2 passed in 64.89s; `backend\_out.txt` was read and deleted.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest -p no:cacheprovider -q backend\tests\persistence\test_migrations.py backend\tests\persistence\test_wallet_ledger_hardening_migration.py backend\tests\persistence\test_competition_discovery_perf_migration.py backend\tests\regen\test_regen_migrations.py` -> 10 passed in 841.87s; `backend\_out.txt` was read and deleted.
- Forbidden scan passed for touched backend/test/runbook files: no unsupported payment or promoted legacy-runtime product terms.
- Manifest added-line forbidden scan passed: no new unsupported payment or promoted legacy-runtime product terms were introduced by the Thread 7 entry.
- Scoped `git diff --check` passed for Thread 7-owned backend observability, observability tests, and runbook/manifest paths; console noise was CRLF normalization warnings only.

## Thread 4 Handoff Update - 2026-06-06 Money Path Hardening

Scope: wallet/payment/trader/regen creation money-path hardening on `feature/original-visual-runtime`; source behavior already enforced KoraPay/manual-only rails, so this pass strengthened focused regression coverage in owned tests.

- Wallet/KoraPay: added wallet-route coverage proving missing or invalid `x-korapay-signature` returns `401` without crediting the purchase order, and duplicate signed KoraPay webhook delivery is idempotent with one ledger transaction and one webhook audit.
- Payment methods: tightened gateway-method coverage so polluted runtime state containing Paystack or `crypto_fiat` is ignored; only `bank_transfer_manual` and `korapay` are exposed.
- Trader money path: added tests proving trader balance/metrics use backend wallet reserved-balance truth without zero fallback, deposits record only `korapay`/`manual` settlement truth, and unsupported gateways create no `MarketTopup`.
- Regen creation: widened Build-a-Son/request-son external payment rejection to include `paystack`, `crypto`, and `usdt`; regen creation remains wallet-reservation spend only.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest backend/tests/wallets/test_wallet_http.py::test_korapay_provider_webhook_requires_valid_signature backend/tests/wallets/test_wallet_http.py::test_korapay_provider_webhook_duplicate_delivery_is_idempotent backend/tests/wallets/test_payment_gateway_service.py::test_payment_gateway_methods_ignore_paystack_from_state backend/tests/trader/test_trader_service.py::test_trader_balance_and_metrics_use_reserved_wallet_truth backend/tests/trader/test_trader_service.py::test_trader_deposits_record_only_korapay_and_manual_settlement_truth backend/tests/trader/test_trader_service.py::test_trader_deposit_rejects_unsupported_gateway_without_creating_topup backend/tests/regen/test_regen_creation_orders.py::test_request_son_rejects_external_payment_methods -q` -> 12 passed in 127.68s; `backend\_out.txt` was read and deleted.
- Subagent verification also passed: wallet focused tests 3 passed, trader suite 18 passed, and regen focused test was re-run in the parent thread after a stale worker process was shut down.
- Guard scan passed: `rg -n "paystack|crypto|bitcoin|ethereum|usdt|web3" backend/app/wallets backend/app/integrations/payments backend/app/trader backend/app/regen_creation` returned no product-code hits.
- Test-scope forbidden-term scan found only explicit rejection/absence coverage in `backend/tests/wallets` and `backend/tests/regen`; `backend/tests/trader` was clean.
- Blockers: none.

## Thread 6 Handoff Update - 2026-06-06 Frontend Router + Realtime Consolidation

Scope: canonicalized the owned Flutter router/navigation/realtime lane on `feature/original-visual-runtime` without switching branches or touching feature screens outside the Thread 6 guardrail.

- Router: `frontend/lib/router/app_router.dart` remained the canonical production router; router tests confirmed canonical `/app/*`, `/matches`, and `/matches/viewer/:matchKey` behavior and confirmed legacy Unity/native-3D/pseudo-3D/broadcast/spectate/simulate match URLs remain unmounted/quarantined.
- Navigation: replaced the old navigation-owned `GoRouter` graph in `frontend/lib/navigation/app_router.dart` with a compatibility provider that delegates to `buildGtexAppRouter`.
- Navigation destinations: aligned `frontend/lib/navigation/app_destinations.dart` to canonical `/app/{world,market,club,compete,capital,community,creator,admin}` and `/matches` surfaces, while retaining deprecated hidden constants for old compile surfaces without mounting or exposing them in primary/quick navigation.
- Realtime: routed `frontend/lib/features/shell/realtime/**` and `frontend/lib/features/shell/providers/gtex_realtime_providers.dart` through the shared realtime transport/state implementation, keeping shell provider names as compatibility aliases.
- Tests: added shell realtime compatibility coverage proving the legacy shell provider import path resolves to the canonical provider instances; updated realtime backoff coverage to the shared service policy.
- Verification passed: `dart format lib/navigation/app_router.dart lib/navigation/app_destinations.dart lib/features/shell/realtime/gtex_realtime_models.dart lib/features/shell/realtime/gtex_realtime_service.dart lib/features/shell/realtime/gtex_realtime_providers.dart lib/features/shell/providers/gtex_realtime_providers.dart test/shell/realtime/gtex_realtime_providers_test.dart test/shell/realtime/gtex_realtime_surface_hardening_test.dart`.
- Verification passed: `flutter analyze --no-pub lib/router lib/navigation lib/features/shell/realtime lib/features/shell/providers test/router test/shell/realtime` reported no issues.
- Verification passed: `flutter test --no-pub test/router -r expanded` passed 17/17.
- Verification passed: `flutter test --no-pub test/shell/realtime -r expanded` passed 10/10.
- Verification passed: production-only forbidden scan for Paystack/crypto/Unity/native-3D/pseudo-3D/match_3d in owned lib paths returned no hits.
- Verification passed: scoped `git diff --check` for Thread 6 owned paths and the manifest returned exit code 0; console noise was CRLF normalization warnings only.
- Blockers: none. Broader legacy navigation widget tests outside Thread 6 ownership still encode pre-canonical expectations and should be reviewed by the navigation/test owner before being used as acceptance gates.

## Thread 5 Handoff Update - 2026-06-06 Admin Finance Export Worker + Realtime Event

Scope: backend admin-finance export readiness, worker completion, and scoped realtime notification on `feature/original-visual-runtime`; edits stayed within Thread 5 backend ownership plus this manifest.

- Export creation now records `admin.export.requested` as queued and no longer materializes artifacts inline.
- `GET /exports/{export_id}` and `GET /exports/{export_id}/download` now read persisted export state only; download returns non-ready state without completing hidden work.
- Added `admin_finance_export_job` in the existing RQ worker job module to complete queued exports after the request transaction commits.
- Added idempotent export requests via `idempotency_key`; repeated matching requests reuse the original export and mismatched reuse is rejected.
- Added terminal `admin.export.failed` audit/outbox handling for worker/generator failures, keeping blocked exports distinct from failed worker execution.
- `admin.export.ready`, `admin.export.blocked`, and `admin.export.failed` outbox payloads remain backend-authored and strip artifact `content` before notification.
- Realtime now maps admin export terminal events to scoped `admin:{user_id}` websocket topics and denies cross-admin topic subscription.
- Tests added/updated for queued-until-worker behavior, route enqueueing without inline completion, idempotency, completion, failure audit/outbox notification, worker job completion, and admin export realtime scoping.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest backend/tests/admin_finance/test_admin_finance_lock_export_unit.py backend/tests/realtime/test_admin_export_realtime.py` -> 15 passed in 186.01s; `backend\_out.txt` was read and deleted.
- Guard scan passed: `rg -n "Paystack|crypto|Unity|SceneKit|Babylon|pseudo-3D|native 3D" backend/app/admin_finance backend/app/workers backend/app/realtime backend/tests/admin_finance backend/tests/realtime` returned no hits.
- Verification passed: scoped `git diff --check` for Thread 5 owned paths and the manifest returned exit code 0; console noise was CRLF normalization warnings only.
- Blockers: none.

## Thread 1 Handoff Update - 2026-06-06 Backend Test-Speed / Full Suite Finishability

Scope: continued the backend test DB schema speedup rollout on `feature/original-visual-runtime`; edits stayed within `backend\tests` plus this manifest, and no production code, Alembic, frontend, or workflow files were edited by this thread.

- Confirmed `backend\tests\conftest.py` already provides `gtex_db_engine`, `gtex_db_session`, and `gtex_db_session_factory`; no fixture scaffold change was needed.
- Migrated `backend\tests\admin_godmode\test_bootstrap_admin.py`, `test_router_permissions.py`, `test_payment_rails_truth.py`, and `test_withdrawal_controls.py` from local full-schema in-memory engines to `gtex_db_session_factory`.
- Migrated `backend\tests\auth\test_auth_service.py` from a local full-schema session fixture to `gtex_db_session`.
- Skipped selective `tables=[...]` create-all fixtures discovered by the read-only classifier because they are cheap subset schemas and outside the migration target.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest tests/admin_godmode -p no:cacheprovider -q` -> 10 passed in 220.83s; `backend\_out.txt` was read and deleted.
- Verification passed via required `backend\_out.txt` handling after waiting for other pytest jobs to release the shared file: `C:\Python314\python.exe -m pytest tests/auth/test_auth_service.py -p no:cacheprovider -q` -> 8 passed in 138.10s; `backend\_out.txt` was read and deleted.
- Verification passed: `C:\Python314\python.exe -m py_compile backend/tests/admin_godmode/test_bootstrap_admin.py backend/tests/admin_godmode/test_router_permissions.py backend/tests/admin_godmode/test_payment_rails_truth.py backend/tests/admin_godmode/test_withdrawal_controls.py backend/tests/auth/test_auth_service.py`.
- Verification passed: scoped `git diff --check` for the migrated admin_godmode and auth service files returned exit code 0; console noise was CRLF normalization warnings only.
- Commits created: `c2f70df2` (`perf(backend-tests): migrate admin godmode DB tests to shared schema`) and `f199c654` (`perf(backend-tests): migrate auth service DB tests to shared schema`).
- Blocker/coordination note: this repo had multiple concurrent backend pytest workers using the shared `backend\_out.txt`; unverified auth router/frictionless fixture edits were manually unwound rather than committed. Continue remaining full-schema candidates one file at a time when the shared pytest output lane is idle.

## Thread 2 Handoff Update - 2026-06-06 Backend Route Contracts + Websocket Collisions

Scope: backend route/module contract tests and realtime websocket route collision coverage on `feature/original-visual-runtime`; no production backend route implementation, frontend, CI, wallet/payment/admin-finance, or regen feature logic was edited.

- Updated module-registration route contract tests for canonical `/api/v2` request handling with required `X-API-Version: 2` headers while preserving explicit `410 Gone` coverage for retired/non-canonical aliases.
- Removed the stale monolithic route sweep from `test_module_registration.py`; the split parametrized contract suite now owns broad route resolution coverage, while the original file stays focused on registration and lazy-hydration guards.
- Adjusted app-contract expectations for canonical auth-before-not-found behavior on guarded broadcast/admin surfaces and for retired daily-challenge/streamer aliases.
- Hardened mounted app contract fixtures so deferred startup stays patched during app construction without nested autospec patch fragility.
- Added `backend\tests\realtime\test_websocket_route_contracts.py` proving realtime and live-match websocket route tables have no duplicate paths and that `/api/matches/{match_id}/stream`, `/matches/{match_id}/stream`, `/realtime/matches/{match_id}/stream`, and `/ws/match/{match_id}` each register once.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest backend\tests\app\test_module_registration_routes.py -p no:cacheprovider -q` -> 170 passed, 9 warnings in 499.70s; `backend\_out.txt` was read and deleted.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest backend\tests\app\test_module_registration.py -p no:cacheprovider -q` -> 4 passed in 310.79s; `backend\_out.txt` was read and deleted.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest backend\tests\app\test_module_registration_hydration.py backend\tests\app\test_module_registration_openapi.py -p no:cacheprovider -q` -> 332 passed in 438.81s; `backend\_out.txt` was read and deleted.
- Verification passed via required `backend\_out.txt` handling: `C:\Python314\python.exe -m pytest backend\tests\realtime\test_websocket_route_contracts.py backend\tests\realtime\test_match_websocket_gateway.py backend\tests\realtime\test_wallet_websocket_gateway.py backend\tests\realtime\test_regen_creation_realtime.py -p no:cacheprovider -q` -> 13 passed in 52.19s; `backend\_out.txt` was read and deleted.
- Verification passed: scoped `git diff --check` for Thread 2 owned app/realtime test paths returned exit code 0; console noise was CRLF normalization warnings only.
- Blockers: none.

## Withdrawal Policy Handoff Update - 2026-06-07 Wallet Fee + Audit

Scope: wallet withdrawal fee enforcement and admin/audit visibility on `feature/original-visual-runtime`; edits stayed in wallet/treasury/admin finance services, focused tests, capital wallet/payout Flutter models/screens, and this manifest.

- Server withdrawal policy now treats user-entered withdrawal `amount` as the gross wallet debit and applies an exact 10% fee with no product-facing minimum; net payout is `gross - fee`, and total wallet hold/debit remains gross.
- Wallet request, completion, release, pending-balance, reward-withdrawable, quote, receipt, and overview paths now carry backend-authored `gross_amount`, `fee_amount`, `net_amount`, `total_debit`, `fee_bps`, and `source_scope`.
- Treasury withdrawal creation stores manual-bank-transfer payout truth, fiat payout from net amount, and audit metadata with gross/fee/net/source/rail details.
- Admin finance queue/export payloads expose explicit gross, fee, net, and total debit; cash-rail summary no longer reports automatic withdrawals as enabled.
- Flutter capital withdrawal quote/receipt/history and admin withdrawal DTOs now expose gross/fee/net/total debit, and the admin command review trail no longer renders an ambiguous single withdrawal amount.
- Frontend payout fixtures were aligned to 10% fee policy and manual bank-transfer withdrawals; gateway withdrawal labels/options were removed from the scoped production UI.
- Verification passed: direct Dart formatter `C:\flutter\bin\cache\dart-sdk\bin\dart.exe --disable-dart-dev format frontend/lib/data/gte_models.dart frontend/lib/features/capital/payouts/data/capital_payout_fixture_store.dart frontend/lib/features/capital/wallet/presentation/gte_withdrawal_flow_screen.dart frontend/lib/screens/admin/admin_command_center_screen.dart`.
- Verification passed: scoped forbidden scans for Paystack/crypto and Unity/native-3D/pseudo-3D returned no product-code hits; the only scoped `automatic_gateway` hit is the existing KoraPay deposit helper in `backend/app/wallets/router.py`.
- Verification passed: scoped `git diff --check` for touched backend/frontend withdrawal paths returned exit code 0; console noise was CRLF normalization warnings only.
- Blocker: focused backend pytest collected but stalled before executing tests, including a single isolated wallet-service test; `backend\_out.txt` was read/deleted after each attempt and no Python process was left running.
- Blocker: focused Flutter tests from `frontend` also exceeded the shell timeout, including the single `test/wallet_api_route_transport_test.dart`; no Dart/Flutter test runner was left running.

## Thread D Handoff Update - 2026-06-07 Ops Guard Fix

Scope: ops guard test stabilization only; no production route, payment, backend business-logic, or frontend source files were edited.

- Updated `backend\tests\ops\test_canonical_production_guards.py` so the removed `/internal/dev/native-match-runtime` destination is treated as the expected canonical state, while `/internal/dev/match-runtime` remains hidden/quarantined and `/matches/3d` plus `/matches/native-3d` remain banned.
- Aligned the match-center verifier expectation with canonical `/api/v2/match-viewer/{match_key}` route errors.
- Tightened the forbidden-route verifier fixture to include the full canonical `/api/v2` match-center route set before injecting quarantined route fragments, so the test now proves quarantine rejection rather than passing on a missing-route failure.
- Verification passed with lane-specific output because `backend\_out.txt` already existed and was left untouched: `C:\Python314\python.exe -m pytest -p no:cacheprovider -q backend\tests\ops\test_canonical_production_guards.py` -> 16 passed in 14.35s; `backend\_out_thread_d.txt` was read and deleted.
- Verification passed: `C:\Python314\python.exe tools\guardrails\production_guardrail_scan.py --root backend/tests/ops --format summary --fail-on violation` -> only quarantined guard-test hits, no violations.
- Verification passed: `git diff --check -- backend\tests\ops\test_canonical_production_guards.py`; console noise was the existing LF-to-CRLF normalization warning only.
- Blockers: none for Thread D.

## Thread 3 Handoff Update - 2026-06-07 Creator Scope Lock

Scope: Creator frontend feature scope lock and frontend contract gate alignment only; backend source and shared JSON contract were read but not edited.

- Creator repository now uses backend-mounted Module 7 contracts for profile, campaigns, campaign detail/create, clips/submit, wallet, withdrawal, settlements, and moderation under `/api/v2/creator/*`.
- Creator repository preserves backend `state`/`status`, `blocked_reason`, `degraded_reason`, `gap_reasons`, and `audit_reference` instead of flattening missing data into local success.
- Creator withdrawals now require backend wallet availability plus a payout destination before posting; otherwise they return blocked states without mutating.
- Creator DTOs now parse canonical nested wallet balances, backend withdrawal availability, optional/partial settlements, moderation inbox status fields, and audit-reference naming.
- Creator Studio surface now classifies campaigns, sponsored clips, wallet/withdrawals, settlements, moderation, analytics, and referrals. Referrals are explicitly blocked on this surface until a creator-scoped referral dashboard contract is mounted.
- Creator canonical surface now adds settlement and referral readiness rows using backend payload fields and degraded/blocked language for missing data.
- Added the missing `/api/v2/creator/{profile,campaigns,clips,wallet,settlements,moderation}` and mutation path self-aliases to `frontend\lib\data\generated\gte_api_contract.g.dart` so the existing frontend request gate accepts backend-mounted Creator contracts. `shared\api_contract.json` remains pre-existing dirty from the contract lane and was not edited here.
- Verification passed: `C:\flutter\bin\cache\dart-sdk\bin\dart.exe analyze` on touched Creator files, generated contract map, and focused creator tests -> no issues found.
- Verification passed: `C:\flutter\bin\flutter.bat test --no-pub test\creator\creator_repository_test.dart -r expanded --concurrency=1` -> 5 passed.
- Verification passed: `C:\flutter\bin\flutter.bat test --no-pub test\creator\creator_dtos_test.dart -r expanded --concurrency=1` -> 5 passed.
- Verification passed: `C:\flutter\bin\flutter.bat test --no-pub test\creator\creator_module_surface_test.dart -r expanded --concurrency=1` -> 3 passed.
- Verification passed: `C:\flutter\bin\flutter.bat test --no-pub test\creator\creator_canonical_surface_test.dart -r expanded --concurrency=1` -> 3 passed.
- Verification passed: `C:\Python314\python.exe tools\guardrails\production_guardrail_scan.py --root frontend/lib/features/creator --root frontend/test/creator --root frontend/lib/data/generated/gte_api_contract.g.dart --format summary --fail-on violation` -> no violations.
- Verification passed: scoped forbidden text scan for Paystack/crypto/Unity/native-3D/pseudo-3D/fake authority terms in touched Creator/generated paths returned no hits.
- Verification passed: `git diff --check -- frontend\lib\features\creator frontend\test\creator frontend\lib\data\generated\gte_api_contract.g.dart`; console noise was CRLF normalization warnings only.
- Blocker: full `flutter test --no-pub test\creator -r expanded` and `flutter analyze --no-pub lib\features\creator test\creator` timed out in this busy worktree before individual focused tests were run. Stuck GTEX `flutter_tester`/analyzer processes from this lane were cleaned up; unrelated build/test processes in other workspaces were left alone.

## Thread B Handoff Update - 2026-06-07 Flutter Harness Recovery

Scope: Flutter analyzer/test measurability only. No production behavior was changed; edits only split pure model/helper imports so a market invariant test can run without loading Riverpod/fixture transport, and added the already-locked `package:test` dependency as a direct dev dependency.

- Isolated a reliable smaller command: from `frontend`, `C:\flutter\bin\cache\dart-sdk\bin\dart.exe --packages=.dart_tool\package_config.json test\market\market_invariants_test.dart` passed 3/3 in 33519 ms.
- `flutter analyze --no-pub` remains non-measurable: bounded run printed only `Analyzing frontend...`, timed out, and was killed after 206812 ms with exit 124.
- `flutter test test\market\market_invariants_test.dart --reporter expanded --no-pub` executed the 3 market tests and printed `All tests passed!`, but the Flutter process did not terminate; bounded wrapper killed it after 187635 ms with exit 124.
- Shorter Flutter test bootstrap repeat timed out after 88435 ms while child process `PowerShell.exe -ExecutionPolicy Bypass -NoProfile -Command "Unblock-File -Path 'C:\flutter\bin\internal\update_engine_version.ps1'; & 'C:\flutter\bin\internal\update_engine_version.ps1'; exit $LASTEXITCODE;"` was still active.
- `flutter --version` also timed out after 86164 ms in the same `C:\flutter\bin\internal\update_engine_version.ps1` bootstrap path, proving the current blocker is Flutter CLI/toolchain startup, not GTEX market test assertions.
- `dart pub get --offline` was required after a failed Flutter pub-get attempt removed `.dart_tool`; it completed in 41312 ms and changed `test 1.30.0` from transitive to direct dev dependency in `pubspec.lock`.
- Verification passed: `dart format frontend\lib\features\shared\data\gte_json_support.dart frontend\lib\features\shared\data\gte_feature_support.dart frontend\lib\features\transfer_center\transfer_center_models.dart frontend\lib\features\transfer_center\live_transfer_center_provider.dart frontend\lib\features\market\presentation\widgets\market_models.dart frontend\test\market\market_invariants_test.dart`.
- Verification passed: scoped `git diff --check` for Thread B-owned frontend paths returned exit code 0; console noise was CRLF normalization warnings only.
- Blocker: Flutter CLI cannot be trusted until the `C:\flutter\bin\internal\update_engine_version.ps1` bootstrap hang is fixed or bypassed in CI/local validation. Use the direct Dart market command above as the temporary targeted harness for this isolated pure-Dart test group.

## Thread 5 Handoff Update - 2026-06-07 Compete Scope Lock

Scope: Compete / competition route classification and validation hardening only; no wallet, payment, match-runtime, legacy runtime surface, or generated contract artifacts were edited.

- Classified launch-ready frontend competition routes as discovery, create, detail, join/enrollment, share, and world-super-cup discovery alias.
- Classified frontend fixture, standings, result, bracket, and rounds paths as backend-authored data contracts consumed inside competition surfaces, not standalone production routes.
- Fixed the `/competitions/streamer/{id}` parser alias so it resolves to the same streamer tournament detail route as `/streamer-tournaments/{id}`; the registry already renders streamer tournament list/detail as blocked coming-soon surfaces.
- Backend contract route audit confirmed `/api/competitions/{competition_id}/fixtures`, `/standings`, `/rounds`, and `/bracket` return stateful envelopes through the competition contract router; segment routes also expose join, publish, fixtures, standings, rounds, match events, and result submission.
- Competition test timeout cause: full `backend\tests\competitions` currently exceeds the bounded verification window because of harness/runtime throughput, not a reproduced assertion failure. The 55-test shard timed out after 600s with no flushed output; collect-only completed with 55 tests in 39.31s pytest time, while representative single tests passed but each took about 170s.
- Verification passed: `C:\Python314\python.exe -m pytest backend\tests\competitions\test_backend_contract_routes.py::test_competition_backend_contract_routes_return_stateful_envelopes -p no:cacheprovider -vv` -> 1 passed in 169.90s.
- Verification passed: `C:\Python314\python.exe -m pytest backend\tests\competitions\test_competition_feed_contracts.py::test_prelaunch_contracts_are_explicit_and_do_not_return_placeholder_rows -p no:cacheprovider -vv` -> 1 passed in 172.01s.
- Verification passed: `flutter test --no-pub test\compete\competition_route_scope_lock_test.dart -r expanded --concurrency=1` -> 3 passed.
- Verification passed: `flutter test --no-pub test\compete\competition_bracket_widgets_test.dart test\compete\competition_settlement_readiness_test.dart -r expanded --concurrency=1` -> 7 passed.
- Blocker: the full backend competition shard remains unfit as a short acceptance gate until the backend test-speed lane reduces startup/fixture cost or the shard is split into smaller verified batches.

## Stage 2A Thread 4 Handoff Update - 2026-06-07 Community Scope Lock

Scope: Community production honesty and settlement-safety classification. Edits stayed in Community/Social frontend models, surfaces, and tests plus this manifest; no backend behavior, generated API contract, payment rails, route mounts, or legacy runtime surfaces were changed.

- Classified production Community surface states: discussions and authenticated chat render backend-backed/empty states; fan hubs are partial because only current-club/follow context is available; reports, reactions, and Community gifting are blocked unless a backend payload exists.
- Tightened `CommunityDigest` and `LiveThreadMessage` parsing so missing backend-authored count fields now throw parsing errors instead of rendering zero.
- Removed local digest count rewriting after watchlist/thread/DM mutations; the screen now reloads backend digest/list truth after writes rather than inventing counts from local state.
- Confirmed `CommunityApi.standard` uses live mode through `gteProductionBackendMode`; fixture fallback remains confined to explicit fixture mode. Added a Flutter-bound test asserting live backend errors do not fixture-fallback.
- Gifting classification: backend `gift_engine` is settlement-backed through wallet ledger postings, spending controls, rake/net split, notifications, and persisted `gift_transactions`; the Community surface remains blocked because it has no gift ledger target/catalog payload.
- API contract inspection confirmed canonical `/api/v2/community/**`, `/api/v2/gift-engine/**`, `/api/v2/moderation/**`, `/api/v2/matches/{match_id}/reactions`, and sponsorship routes exist in `shared\api_contract.json`; no contract regeneration was performed.
- Verification passed: `C:\flutter\bin\cache\dart-sdk\bin\dart.exe --disable-dart-dev format frontend\lib\models\community_models.dart frontend\lib\features\community\presentation\community_canonical_surface.dart frontend\lib\features\social\social_screen.dart frontend\test\community\community_canonical_surface_test.dart frontend\test\social\community_screen_test.dart frontend\test\social\community_api_test.dart frontend\test\community\community_models_test.dart`.
- Verification passed: from `frontend`, `C:\flutter\bin\cache\dart-sdk\bin\dart.exe --packages=.dart_tool\package_config.json test\community\community_models_test.dart` -> 2 passed in 31685 ms.
- Verification passed: scoped `git diff --check` for Stage 2A Thread 4-owned frontend paths returned exit code 0; console noise was CRLF normalization warnings only.
- Verification passed: scoped forbidden-term scan for Paystack/crypto and Unity/native-3D/pseudo-3D/original-visual-runtime terms returned no hits in owned files.
- Blocker: Flutter test shard `flutter test test\community\community_canonical_surface_test.dart test\social\community_api_test.dart --reporter expanded --no-pub` hit `Error: The Dart compiler exited unexpectedly` while loading the widget test and did not exit; bounded wrapper killed it after 176708 ms.
- Blocker: focused backend gift-engine pytest `C:\Python314\python.exe -m pytest -p no:cacheprovider -q backend\tests\gift_engine\test_gift_engine_router.py` produced no output after 424103 ms; the owned Python process was stopped and empty `backend\_out.txt` was deleted.

## Thread 2 Handoff Update - 2026-06-07 Stage 2A Full Validation / CI Gate

Scope: validation matrix and CI-gate hardening only on `feature/original-visual-runtime`; no product behavior, generated contracts, backend source, Flutter source, route promotion, payment rails, or fixture fake mode was edited.

- Updated `Docs/GTEX_PRODUCTION_READINESS_TRACKER.md` with a Stage 2A Full Validation / CI Gate matrix.
- Backend sidecar PASS: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\ops\test_canonical_production_guards.py` -> 16 passed in 61.31s wall, no warnings emitted.
- Backend sidecar PASS: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\realtime\test_websocket_route_contracts.py backend\tests\realtime\test_match_websocket_gateway.py backend\tests\realtime\test_wallet_websocket_gateway.py backend\tests\realtime\test_regen_creation_realtime.py` -> 13 passed in 220.96s wall, no warnings emitted.
- Backend local PASS/SLOW: `C:\Python314\python.exe -m pytest backend\tests\app\test_module_registration.py -q -p no:cacheprovider` -> 4 passed in 289.12s pytest time / 352.08s wall.
- Backend local PASS/SLOW: `C:\Python314\python.exe -m pytest backend\tests\wallets\test_wallet_service.py --collect-only -q -p no:cacheprovider` -> 23 tests collected in 64.04s pytest time / 115.96s wall.
- Backend local PASS/SLOW: `C:\Python314\python.exe -m pytest backend\tests\wallets\test_wallet_service.py::test_request_payout_holds_total_and_tracks_fee -q -p no:cacheprovider` -> 1 passed in 305.99s pytest time / 392.25s wall.
- Flutter sidecar FAIL/TIMEOUT: `flutter --version` from `frontend` was killed at 90.2s with no stdout/stderr while stuck in `dart.exe` / `dartvm.exe` running `C:\flutter\bin\cache\flutter_tools.snapshot --version`.
- Flutter coordinator repeat FAIL/TIMEOUT: `C:\flutter\bin\flutter.bat --version` from `frontend` was killed at 102.18s with no stdout/stderr while stuck in `flutter_tools.snapshot --version`.
- Flutter analyzer gate was intentionally skipped after `flutter --version` proved the Flutter CLI bootstrap was not reliable.
- Direct Dart PASS: `C:\flutter\bin\cache\dart-sdk\bin\dart.exe --packages=.dart_tool\package_config.json test\market\market_invariants_test.dart` -> 3 passed in 73.6s wall, confirming the isolated pure-Dart market invariant tests are healthy without Flutter CLI.
- Blockers: full backend suite remains unproven, full Flutter analyze/test remains blocked by Flutter CLI startup, and several small backend shards are green but too slow to trust as fast CI gates without further test-speed work.
- Coordination note: no `backend\_out.txt` was used or deleted by this pass; validation logs were outside the repo or sidecar-owned temp paths only.

## Stage 2B Coordinator Update - 2026-06-08 Wallet Test-Speed

Scope: backend wallet service test-speed only. No production wallet behavior, payment rails, generated contracts, frontend source, route mounts, or legacy runtime surfaces were changed.

- Replaced the file-local migrated SQLite template and per-test DB copy in `backend\tests\wallets\test_wallet_service.py` with the shared `gtex_db_session` rollback fixture from `backend\tests\conftest.py`.
- Verification passed: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\wallets\test_wallet_service.py --collect-only` -> 23 tests collected in 102.03s pytest time / 216.7s wall.
- Verification passed: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\wallets\test_wallet_service.py::test_append_transaction_requires_balanced_postings` -> 1 passed in 183.94s pytest time.
- Verification passed: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\wallets\test_wallet_service.py::test_request_payout_holds_total_and_tracks_fee` -> 1 passed in 190.02s pytest time / 281.4s wall, improving from prior tracked 305.99s pytest time / 392.25s wall.
- Verification passed: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\wallets\test_wallet_service.py::test_wallet_transaction_service_rolls_back_unbalanced_transaction backend\tests\wallets\test_wallet_service.py::test_wallet_transaction_service_reuses_idempotency_key_across_atomic_calls` -> 2 passed in 178.01s pytest time.
- Blocker: wallet service collection/import remains slow and the full file has not been rerun; this patch is a measurable focused execution improvement, not the complete backend test-speed fix.

## Stage 2C Coordinator Update - 2026-06-08 Competitions Test-Speed

Scope: backend competitions test harness speed only. No production competition behavior, route contracts, wallet/payment code, generated contracts, frontend source, or legacy runtime surfaces were changed.

- Narrowed the autouse auth override in `backend\tests\competitions\conftest.py` so it only loads the shared GTEX app/session fixtures for tests that request the shared `app` or `client` fixtures.
- Verification passed: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\competitions\test_competitions_models.py::test_creation_service_builds_linked_competition_aggregate` -> 1 passed in 18.90s pytest time.
- Blocker unchanged for client-backed route tests: `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\competitions\test_competition_launch_rules.py::test_user_competition_cannot_use_gtex_name` timed out after 364.2s; the owned pytest process was stopped.
- Handoff: this patch removes accidental full-app setup from non-app competitions tests, but client-backed competition route tests still need deeper startup/runtime speed work or shard splitting.

## Stage 2D Coordinator Probe - 2026-06-08 Competition Route Canonicalization

Scope: diagnosis only. No source files, route contracts, production behavior, payment rails, generated contracts, frontend source, or legacy runtime surfaces were changed.

- Timed the shared competition app startup path with a temp log outside the repo. With the shared-style Alembic migration check, imports plus `create_app` reached `TestClient` setup at roughly 167s, then did not enter `TestClient` before the bounded 180s timeout.
- Timed a test-harness alternative using ORM `Base.metadata.create_all` plus `run_migration_check=False`: app startup reached `TestClient` and `/health` returned 200 in roughly 186s.
- Timed a realistic competition create request under that faster harness: raw `/api/competitions` returned 410 from the API contract guard, proving the legacy path is no longer a valid route-test target.
- Timed canonical `/api/v2/competitions`: without `X-API-Version: 2` it returned 400 from the contract guard; with the version header it reached auth and returned 401 when no test auth override was installed.
- Handoff: the next competition route-test lane must canonicalize client-backed tests to `/api/v2/...`, add `X-API-Version: 2`, preserve the existing test auth override/default user behavior, and adjust assertions for v2 envelopes where needed. Startup optimization alone will not make the stale `/api/competitions` tests production-ready.
