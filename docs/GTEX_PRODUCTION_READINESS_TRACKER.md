# GTEX Production Readiness Tracker

Last updated: 2026-06-09

Coordinator scope: this document tracks production readiness, worker ownership, merge order, and acceptance criteria for the canonical GTEX Flutter/backend football operating system. It does not introduce product behavior.

## Scope Lock

- Canonical production app is Flutter plus backend football economy OS.
- Active match experience is the 2D broadcast-style Match Center only.
- Unity, native 3D, pseudo-3D, and original visual runtime surfaces are quarantined/reference only.
- Payment rails are KoraPay and manual bank transfer only.
- No Paystack product-facing rail, label, route, schema default, workflow, copy, or contract.
- Frontend must reflect backend truth. Missing backend data renders loading, empty, blocked, syncing, degraded, confirmed, or error states.

## Current Readiness Snapshot

| Area | Current state | Coordinator note |
| --- | --- | --- |
| Branch/release state | Dirty active integration branch | Branch `feature/original-visual-runtime` contains verified first-wave fixes, but the current worktree changes remain unstaged/uncommitted. Do not push or cut a release branch yet. |
| Backend suite | Partially verified, full suite still unproven | Multiple focused shards are green and test-speed migration continues; full `backend/tests` has not yet completed green. |
| Flutter suite | Targeted main-worktree evidence, full gate still untrusted | Active shell route and route coverage tests have green handoff evidence; market invariants are measurable through Dart. Full `flutter analyze` / full Flutter test remains a main-worktree validation blocker because of Flutter CLI bootstrap hangs. |
| API/guardrails | PASS targeted | Coordinator re-check on 2026-06-07: API contract violations pass, production guardrail scan passes, and `git diff --check` passes with CRLF warnings only. |
| Generated/shared contracts | Dirty but checker-clean | `shared/api_contract.json` now declares backend-mounted Creator Module 7 `/api/v2/creator/*` contracts and the Dart binding was regenerated from shared. Stage only after contract-owner diff review because the shared JSON still carries route-order churn. |
| Money path | PASS focused, E2E pending | Transfer reservation suite passed in verifier handoff, and wallet/treasury withdrawal fee focused tests passed. Full money-path launch proof and frontend main-worktree gates remain pending. |
| Match direction | Scope locked | Keep canonical 2D Match Center. Do not satisfy failing tests by re-promoting native/3D routes. |

## Stage 1.5 Verified State

| Thread / lane | State | Evidence | Coordinator action |
| --- | --- | --- | --- |
| Backend test-speed | PASS for committed batches; IN PROGRESS overall | Verified `admin_godmode` 10/10, `auth_service` 8/8, plus later committed DB fixture migrations in club squad, observability dashboard, pricing, media, fraud, real-player, referral, creator/agent lanes. | Continue safe fixture migrations one file/batch at a time; do not claim full backend green yet. |
| Route contracts + websocket collisions | PASS targeted | Thread 2 reports module route contracts 170 passed, module registration 4 passed, hydration/openapi 332 passed, websocket route/gateway/realtime suite 13 passed. | Safe to integrate before regenerated API contracts. |
| Frontend router + realtime | PASS targeted | Thread 6 reports `flutter analyze --no-pub` for router/navigation/realtime paths clean, router tests 17/17, shell realtime tests 10/10, forbidden scan clean. | Merge after route contracts; broader legacy navigation tests remain a separate owner issue. |
| Flutter stabilization worktree | PASS in separate worktree | `gtex-wt-frontend` reports analyze 0 issues and serial test 832/832 with 0 skips. | Treat as proof the frontend lane can be green; rerun on main worktree after current dirty frontend changes are settled. |
| Money path hardening | PASS targeted | Thread 4 reports 12 focused backend tests passed, wallet/trader/regen checks passed, no product-code Paystack/crypto hits. | Keep KoraPay/manual-only guardrails; merge before dependent withdrawal policy changes. |
| Admin finance export + realtime | PASS targeted | Thread 5 reports admin finance export/realtime suite 15 passed, guard scan clean. | Integrate near money path and realtime after route contracts. |
| Admin finance payment queue audit | PASS targeted | `python -B -m pytest -p no:cacheprovider -q backend\tests\admin_finance\test_admin_finance_router.py`: 16 passed in 128.06s, 1 warning. | Treasury audit events now stamp application-time `created_at`, so payment-queue reinstate summaries surface the latest review event deterministically. |
| Ops/migrations/observability | PASS targeted | Thread 7 reports observability 9 passed plus post-format 2 passed; migration/regen persistence suite 10 passed; forbidden scans and diff-check passed. | Integrate before staging dry-run work. |
| First-wave verifier matrix | PASS targeted | Verifier handoff reports API contract PASS, guardrail PASS, diff-check PASS, transfer reservation pytest 34 passed, wallet/treasury withdrawal pytest 11 passed, and temp output cleanup PASS. | Use as focused staging evidence; still require final main-worktree gates before release. |
| Ops guard test | PASS local | Coordinator reran `python -m pytest -p no:cacheprovider -q backend\tests\ops\test_canonical_production_guards.py`: 16 passed. | Safe to stage with guardrail-test batch after diff review. |
| Active shell route mount | PASS targeted | Handoff reports `frontend/test/active_shell_route_mount_test.dart` 3/3, route coverage 9/9, and targeted analyze on the route test passed. | Safe to stage with Flutter route/harness batch; do not re-promote retired match routes. |
| Withdrawal 10% fee policy | PASS focused, full gate pending | Verifier handoff reports 11 selected wallet service, wallet HTTP, and treasury withdrawal review tests passed for gross/fee/net behavior. | Stage as one money cluster only after frontend display/model changes are reviewed and final main-worktree checks are queued. |
| Full backend suite | FAIL by absence of proof | No current full `C:\Python314\python.exe -m pytest backend/tests -p no:cacheprovider` green result. | Remains a hard launch blocker. |
| Generated API contract | PASS targeted / STAGE REVIEW | Coordinator rerun of `python tools\audit\check_api_contract_violations.py` reports zero violations after reconciling Creator Module 7 paths into `shared/api_contract.json` and regenerating Dart from shared. | Safe for contract-owner review; do not hand-edit generated Dart. |

## Stage 2A Dirty Worktree Integration Batches

| Batch | Files | Stage together? | Current decision |
| --- | --- | --- | --- |
| Runtime-local admin toggles | `.runtime/admin_god_mode.json` | No | Preserve unstaged as local runtime state. It flips admin/payment-mode toggles; do not stage. Because the file is tracked, ignore rules will not hide this modification. Revert only by explicit runtime/admin owner decision. |
| Coordinator docs | `Docs/GTEX_PRODUCTION_READINESS_TRACKER.md`, `docs/GTEX_DIRTY_WORKTREE_INTEGRATION_MANIFEST.md` | Yes, after final read | Stage after coordinator review confirms handoff text is current and no stale blocker language remains. |
| Market bid-withdraw contract | `frontend/lib/features/market/data/market_api_service.dart`, `shared/api_contract.json` | Yes | Stage as a contract batch after reviewing `shared/api_contract.json` reorder noise. Current contract checker passes and frontend uses `/api/v2/transfer-market/bid/$bidId/withdraw`. |
| Transfer reservation settlement | `backend/app/services/player_lifecycle_service.py`, `backend/tests/players/test_transfer_bid_wallet_reservations.py` | Yes | Stage as a focused money-safety batch. Verifier handoff reports the full transfer reservation file passed 34 tests. |
| Withdrawal fee/admin finance cluster | `backend/app/wallets/service.py`, `backend/app/wallets/router.py`, `backend/app/treasury/service.py`, `backend/app/admin_finance/service.py`, `backend/tests/wallets/test_wallet_service.py`, `backend/tests/wallets/test_wallet_http.py`, `backend/tests/treasury/test_withdrawal_reviews.py`, `frontend/lib/data/gte_models.dart`, `frontend/lib/features/capital/payouts/data/capital_payout_fixture_store.dart`, `frontend/lib/features/capital/wallet/presentation/gte_withdrawal_flow_screen.dart`, `frontend/lib/screens/admin/admin_command_center_screen.dart` | Yes | Stage as one verified money/UI truth cluster after frontend display diff review. Backend focused wallet/treasury tests passed; final Flutter main-worktree gate is still pending. |
| Flutter harness and route-test support | `frontend/pubspec.yaml`, `frontend/pubspec.lock`, `frontend/lib/features/shared/data/gte_json_support.dart`, `frontend/lib/features/shared/data/gte_feature_support.dart`, `frontend/lib/features/transfer_center/transfer_center_models.dart`, `frontend/lib/features/transfer_center/live_transfer_center_provider.dart`, `frontend/lib/features/market/presentation/widgets/market_models.dart`, `frontend/test/market/market_invariants_test.dart`, `frontend/test/active_shell_route_mount_test.dart` | Yes | Stage as one frontend test-harness batch after market invariant, active shell route, and route coverage commands remain green. `frontend/pubspec.*` belongs here because it adds the direct `test` dev dependency used by both test fixes. |
| Ops guard test | `backend/tests/ops/test_canonical_production_guards.py` | Yes, small batch | Stage with guardrail-test evidence. Local coordinator rerun passed 16/16 without loosening Unity/3D/Paystack guardrails. |
| Admin/Ops/Money smoke assertions | `backend/tests/admin_finance/test_admin_finance_router.py` | Yes, small test batch | Stage after reviewing assertion-only diff. Handoff reports admin finance gross/fee/net/total-debit, manual rail truth, withdrawal audit, and transfer audit assertions passed 10/10 in the targeted smoke. |
| Community scope-lock | `frontend/lib/models/community_models.dart`, `frontend/lib/features/community/presentation/community_canonical_surface.dart`, `frontend/lib/features/social/social_screen.dart`, `frontend/test/community/community_canonical_surface_test.dart`, `frontend/test/community/community_models_test.dart`, `frontend/test/social/community_api_test.dart`, `frontend/test/social/community_screen_test.dart` | Yes | Stage as a frontend product-honesty batch only after test strategy is accepted. Direct Dart model test passed; Flutter community tests and backend gift-engine shard remain blocked by harness/runtime stalls. Community gifting remains intentionally blocked in UI. |
| Compete route scope-lock | `frontend/lib/features/app_routes/gte_route_data.dart`, `frontend/test/compete/competition_route_scope_lock_test.dart` | Yes | Stage as a route classification batch. Handoff reports route scope-lock and bracket/settlement Flutter tests passed; full backend competitions shard remains too slow, though representative backend tests passed. |
| Creator scope-lock | `frontend/lib/features/creator/data/creator_repository.dart`, `frontend/lib/features/creator/data/creator_dtos.dart`, `frontend/lib/features/creator/providers/creator_providers.dart`, `frontend/lib/features/creator/presentation/creator_module_surface.dart`, `frontend/lib/features/creator/presentation/creator_canonical_surface.dart`, creator tests, `frontend/lib/data/generated/gte_api_contract.g.dart`, `shared/api_contract.json` | Yes, after contract diff review | Product-honesty direction is good, individual Creator tests passed in handoff, and the API checker is back to zero after shared/generated reconciliation. Stage as a Creator contract/scope-lock batch after reviewing shared-contract churn. |

## Stage 2A Full Validation / CI Gate Matrix - 2026-06-07

| Gate / shard | Command | Result | Runtime | Evidence | Coordinator note |
| --- | --- | --- | --- | --- | --- |
| Backend ops guard | `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\ops\test_canonical_production_guards.py` | PASS | 61.31s wall | 16 passed, no warnings emitted | Reliable targeted guard shard; no Unity/native-3D/Paystack production relaxation introduced. |
| Backend realtime websocket contracts | `C:\Python314\python.exe -B -m pytest -p no:cacheprovider -q backend\tests\realtime\test_websocket_route_contracts.py backend\tests\realtime\test_match_websocket_gateway.py backend\tests\realtime\test_wallet_websocket_gateway.py backend\tests\realtime\test_regen_creation_realtime.py` | PASS | 220.96s wall | 13 passed, no warnings emitted | Reliable targeted websocket shard, but startup cost is still high for a small gate. |
| Backend module registration smoke | `C:\Python314\python.exe -m pytest backend\tests\app\test_module_registration.py -q -p no:cacheprovider` | PASS / SLOW | 352.08s wall; pytest 289.12s | 4 passed | Behavior is green, but a four-test smoke shard taking nearly six minutes is a CI finishability warning. |
| Backend wallet service collection | `C:\Python314\python.exe -m pytest backend\tests\wallets\test_wallet_service.py --collect-only -q -p no:cacheprovider` | PASS / SLOW | 115.96s wall; pytest collection 64.04s | 23 tests collected | Previous "stalled before executing" blocker is now narrowed to very slow import/collection, not collection failure. |
| Backend withdrawal fee truth | `C:\Python314\python.exe -m pytest backend\tests\wallets\test_wallet_service.py::test_request_payout_holds_total_and_tracks_fee -q -p no:cacheprovider` | PASS / SLOW | 392.25s wall; pytest 305.99s | 1 passed | Gross/fee/net behavior passes for this focused test, but the shard is too slow to be a trustworthy fast PR gate yet. |
| Flutter CLI version bootstrap | `C:\flutter\bin\flutter.bat --version` from `frontend` | FAIL / TIMEOUT | Sidecar killed at 90.2s; coordinator repeats killed at 102.18s and 49.04s | No stdout/stderr; clean retry after stale-lock cleanup recreated zero-byte `flutter.bat.lock` and `lockfile`; no `dart.exe`, `dartvm.exe`, `flutter.exe`, or `flutter_tester.exe` remained afterward | Root cause is Flutter CLI wrapper/tool startup, not GTEX assertions. Direct Dart remains usable for pure-Dart tests; do not treat `flutter.bat` gates as reliable until this is fixed. |
| Direct cached Flutter tool snapshot | `C:\flutter\bin\cache\dart-sdk\bin\dart.exe --packages=C:\flutter\packages\flutter_tools\.dart_tool\package_config.json C:\flutter\bin\cache\flutter_tools.snapshot --version` | PASS for version only | 2026-06-07 local diagnostic | Printed Flutter 3.41.4 stable, framework revision `ff37bef603`, Dart 3.11.1 | Confirms the SDK snapshot can execute a simple version command; it does not unblock analyzer/test because direct snapshot `analyze --no-pub test\active_shell_route_mount_test.dart` still timed out without output. |
| Flutter analyzer | `flutter analyze --no-pub` from `frontend` | BLOCKED / SKIPPED | 0s in sidecar after CLI timeout proof | Not run broadly | Do not treat main-worktree Flutter analyzer as reliable until the Flutter CLI bootstrap hang is fixed or a documented CI runner bypass exists. |
| Direct Dart market invariants | `C:\flutter\bin\cache\dart-sdk\bin\dart.exe --packages=.dart_tool\package_config.json test\market\market_invariants_test.dart` | PASS | 73.6s wall | 3 passed | Confirms the isolated pure-Dart market invariant assertions are healthy without invoking Flutter CLI. |
| Full backend suite | `C:\Python314\python.exe -m pytest backend\tests -p no:cacheprovider` | NOT RUN / UNPROVEN | Not attempted in this Stage 2A pass | No current full green evidence | Still a hard launch blocker; run only after slow shard migration or it will not be a credible gate. |
| Full Flutter test suite | `flutter test --no-pub --concurrency=1` | NOT RUN / BLOCKED | Not attempted after CLI bootstrap timeout | No current main-worktree full green evidence | Still blocked by Flutter CLI startup; side-worktree green evidence is useful but not a substitute for final main-worktree gate. |

No fake fixture mode, production workaround, route promotion, payment-rail change, generated contract staging, or source behavior edit was introduced by this validation pass.

## Stage 2B Backend Test-Speed Follow-up - 2026-06-08

| Gate / shard | Change | Result | Evidence | Coordinator note |
| --- | --- | --- | --- | --- |
| Backend wallet service shared fixture migration | `backend/tests/wallets/test_wallet_service.py` now uses the shared `gtex_db_session` rollback fixture instead of a file-local migrated SQLite template plus per-test DB copy; multi-session atomic transaction tests use `gtex_db_session_factory`. | PASS / SLOW, improved focused execution | `test_request_payout_holds_total_and_tracks_fee`: 1 passed in 190.02s pytest time / 281.4s wall after migration, versus prior tracker evidence of 305.99s pytest time / 392.25s wall. `test_append_transaction_requires_balanced_postings`: 1 passed in 183.94s. Atomic transaction service pair: 2 passed in 178.01s. | This is a real speed improvement for focused wallet execution, but not a full fix. Collection remains slow: 23 tests collected in 102.03s pytest time / 216.7s wall after migration. Keep wallet service on the backend test-speed blocker list until import/collection cost is reduced. |
| Backend competitions autouse auth fixture narrowing | `backend/tests/competitions/conftest.py` now skips shared-app auth override setup for tests that do not request the shared `app` or `client` fixtures. | PASS for non-app test, client route still blocked | `test_creation_service_builds_linked_competition_aggregate`: 1 passed in 18.90s pytest time. `test_user_competition_cannot_use_gtex_name` still timed out after 364.2s and the owned pytest process was stopped. | This prevents unnecessary full-app setup for pure competitions tests, but does not solve client-backed competition route startup/runtime cost. Keep competitions API route tests on the backend test-speed blocker list. |
| Backend competitions canonical-route probe | Timed the client-backed competition startup path outside pytest to separate startup cost from handler behavior. | BLOCKER NARROWED | Shared-style app with Alembic migration check reached `create_app` at 167.59s and then did not enter `TestClient` before the 180s timeout. ORM `Base.metadata.create_all` plus `run_migration_check=False` reached `TestClient` at 235.18s and raw `/api/competitions` returned 410 from the contract guard. Canonical `/api/v2/competitions` without `X-API-Version: 2` returned 400; with the header and no auth override it reached auth and returned 401. | Client-backed competition tests are not only slow; many still target legacy `/api/competitions` paths. The next route-test modernization lane must use canonical `/api/v2/...` paths, include `X-API-Version: 2`, preserve the test auth override, and account for v2 response envelopes. |
| Backend competitions route modernization | `backend/tests/competitions/conftest.py`, `backend/tests/competitions/api_helpers.py`, `backend/tests/competitions/test_competition_launch_rules.py` | PASS targeted | `python -m pytest -p no:cacheprovider -q backend/tests/competitions/test_competition_launch_rules.py`: 3 passed in 45.76s. Narrow cases also passed individually after fixture adjustment. | Canonical v2 competition route tests now use `/api/v2/...`, `X-API-Version: 2`, token-backed auth headers, and a seeded club-owned entrant fixture. This shard is no longer a blocker for the current route modernization lane. |

## Hard Launch Blockers

| Blocker | Owner | Acceptance |
| --- | --- | --- |
| Full backend pytest must complete and pass | Backend test-speed lane plus main integrator | `C:\Python314\python.exe -m pytest backend/tests -p no:cacheprovider` completes green, with temp output removed. |
| Remaining full-schema DB tests slow the suite | Backend test-speed lane | Safe full `Base.metadata.create_all(engine)` tests migrated to `gtex_db_session` / `gtex_db_session_factory`; risky/selective fixtures documented as skipped. |
| Main-worktree Flutter gate must be refreshed | Flutter router/shell plus current frontend owners | After dirty frontend wallet/market/contract changes settle, `flutter analyze --no-pub` and `flutter test --no-pub --concurrency=1` pass from the main worktree. |
| Route/ops guard regression in final tree | Router/realtime or guardrails owner | Route/module/websocket contracts remain green and `backend/tests/ops/test_canonical_production_guards.py` passes without production Unity/native/3D promotion after all dirty batches are integrated. |
| Generated/shared contract staging review | API contract owner plus main integrator | `shared/api_contract.json`, generated Dart, and contract docs agree; API contract checker is back to zero violations; no route-order churn or hand-patched generated map is staged without review. |
| Withdrawal fee production E2E proof | Money-path owner | Backend focused tests remain green, frontend capital/admin displays compile, and final main-worktree gates prove gross/fee/net/total-debit truth with KoraPay/manual-only rails. |
| Money-path launch proof | Money-path owner | Wallet, transfer bids, trader, Build-a-Son, admin finance, disputes, reservations, settlement, release, fee policy, and audit tests pass with KoraPay/manual-only rails. |
| Merge-gating CI trust | CI owner | Full backend, Flutter analyze/test, guardrails, API contract generation/checks, and deploy blockers run on PRs. |

## Feature-Completion Blockers

| Feature/domain | Status | Required completion |
| --- | --- | --- |
| Build-a-Son / regen creation | Partial | Backend preview/create/payment/generation contracts must be authoritative; Flutter wizard must use backend projections and wallet availability. |
| Regen World | Partial | Lineage, traits, DNA, generation, origin story, projected value, rarity, and nationality need backend-backed UI signoff. |
| Match Center | Strong but not final | Shell mount and route tests must prove the canonical 2D broadcast surface; websocket data remains authoritative. |
| Competitions | Partial | Backend competition route/API failures and settlement readiness flows must be green. |
| Wallet / transfer bids | Partial | Reservation, release, accepted-bid settlement, and locked/available balance truth must pass end-to-end. |
| Trader / Capital | Partial | Backend contract gaps and blocked-state duplication must be resolved; no local market truth. |
| Creator / Community | Scope-lock in progress | Community now blocks gifting/reactions/reports without backend payloads; Creator now uses backend-mounted Module 7 contracts and contract drift is reconciled. Final main-worktree Flutter gate still applies before release. |
| Admin command queues | Partial | Admin finance export worker and audit paths require green worker/WS/export tests. |
| Decision-queue backend modules | Decision required | Reward engine, betting, club infra, live ops, ticketing, moments, ultimate/infinite league, and similar modules need ship/hide/deprecate decisions. |

## Validation Blockers

| Validation | Current blocker | Acceptance |
| --- | --- | --- |
| Backend full suite | Previously timed out/failed; still being sped up | Full backend run green. |
| Backend route/module contracts | Targeted PASS; keep under watch | Thread 2 route/module/openapi/websocket contract shards stay green after merge ordering. |
| Frontend full suite | PASS in `gtex-wt-frontend`; main worktree unverified after dirty changes | `flutter analyze --no-pub` and `flutter test --no-pub --concurrency=1` green on the final main integration tree. |
| Visual QA | Harness exists, evidence incomplete | Desktop/tablet/mobile screenshots generated and reviewed for key surfaces. |
| Websocket collision checks | Added/partially verified | HTTP and websocket route collision tests green. |
| Staging dry run | Not complete | Deploy, smoke, rollback rehearsal, KoraPay/manual payment dry-run, live match smoke, and admin export smoke complete. |

## Worker Ownership

| Lane | Owns | Must not touch | Acceptance criteria |
| --- | --- | --- | --- |
| Coordinator/main | Readiness tracker, integration order, manifest notes, conflict flags | Feature implementation unless required for coordination | Tracker current; merge order documented; conflicts called out before staging. |
| Backend test-speed | `backend/tests/**` fixture-speed migrations only | `backend/app/**`, Alembic, frontend, generated contracts | One verified commit per safe file/batch; skipped risky files documented. |
| Money path | Wallets, treasury, payment integrations, transfer bids, trader settlement, Build-a-Son payment, admin finance tests | Router shell, Match Center UI, Unity/3D | KoraPay/manual-only proof, idempotent webhooks, reservations/audit green. |
| Router/realtime | `frontend/lib/router/**`, canonical shell route mounts, shared realtime, route tests | Wallet business truth, generated contracts unless coordinated | One production router, canonical `/app/**`, websocket/route collision tests green. |
| Match Center | `frontend/lib/features/match_center/**`, live match/realtime backend contracts | Legacy 3D/native production promotion | Backend-authored score/clock/events/stats; no fake clocks/scores. |
| Feature product flows | Build-a-Son, Regen World, competitions, creator/community surfaces | Core router except requested route additions | Prototype behavior translated through backend DTOs/repositories and canonical state views. |
| CI/guardrails | `.github/workflows/**`, `tools/guardrails/**`, `tools/quality/**` | Product code except guardrail hooks | PR and deploy gates cover backend, Flutter, contracts, guardrails, deploy blockers. |
| Ops/migrations | Alembic, readiness/health, observability config, runbooks | Feature UX and payment logic | Empty-db upgrade, rollback/runbook, health/readiness, OTLP/metrics/logging evidence. |
| GA verification | Visual/load/staging smoke harnesses and release evidence | Feature redesign | Screenshot, load, smoke, rollback, backup/DR evidence captured. |

## Conflict Watchlist

- `frontend/lib/router/app_router.dart` and shell route mounts: router owner only.
- `frontend/lib/shared/realtime/**`: router/realtime owner unless Match Center owns feature-specific payload parsing.
- `backend/app/wallets/**`, `backend/app/treasury/**`, payment providers: money-path owner only.
- Withdrawal fee policy cluster: `backend/app/wallets/**`, `backend/app/treasury/**`, `backend/app/admin_finance/**`, `frontend/lib/features/capital/**`, `frontend/lib/data/gte_models.dart`, `frontend/lib/features/market/**`, and `shared/api_contract.json` must move as one verified unit or not at all.
- `shared/api_contract.json`, generated Dart API contract, frontend DTOs, and contract docs: regenerate only after route source and withdrawal payload stabilization.
- Creator contract lane: `frontend/lib/data/generated/gte_api_contract.g.dart` Creator additions now have matching `shared/api_contract.json` endpoint declarations and a clean API contract checker; stage them together only.
- `backend\_out.txt`: shared scratch file is actively contested by backend workers; do not delete unless it belongs to your own completed pytest command.
- `Docs/GTEX_DIRTY_WORKTREE_INTEGRATION_MANIFEST.md`: active multi-thread handoff file; append-only unless coordinating with the current thread owner.
- `.runtime/admin_god_mode.json`: local tracked runtime state. Preserve unstaged; do not stage, ignore, or revert from coordinator lane.
- `Gtex_Test_Migration/**`: quarantine/reference only.
- Mixed `docs/` and `Docs/` casing: defer cleanup until reports are absorbed and no active thread references are broken.

## Recommended Next Merge Order

1. Coordinator docs batch, after this tracker is re-read and stale Stage 1.5 language is removed.
2. Ops guard test batch, because it is small, locally verified 16/16, and does not touch product behavior.
3. Contract reconciliation batch: market bid-withdraw plus Creator `/api/v2/creator/*` endpoints across shared JSON and generated Dart; current checker is zero, pending diff review.
4. Transfer reservation settlement batch, using the 34-test focused transfer reservation pass as evidence.
5. Flutter harness and active-shell route-test batch, after the Dart market invariant and targeted Flutter route commands remain green.
6. Withdrawal fee/admin finance cluster, staged as one money/UI truth unit after frontend display diff review and queued final Flutter gate.
7. Admin/Ops/Money smoke assertion batch.
8. Community and Compete scope-lock batches, because they are product-honesty changes with bounded files and known validation caveats.
9. Creator scope-lock batch with the reconciled contract files, after reviewing shared JSON churn.
10. Main-worktree Flutter full analyze/test rerun after all frontend dirty batches are integrated.
11. Backend full-suite shard matrix, then full backend pytest.
12. Visual/load/DR evidence, clean release branch, CI green, then PR/merge decision.

## Immediate Coordinator Actions

- Keep worker file ownership explicit before new edits start.
- Treat older report claims as evidence, not final truth, when newer verified commits supersede them.
- Do not stage generated contract artifacts until the route owner confirms source route stabilization and coordinator reviews the `shared/api_contract.json` reorder churn.
- Keep the API contract checker at zero; do not let future hand-patched generated Dart maps become the contract source of truth.
- Do not stage withdrawal-fee frontend/admin display changes without the matching backend wallet/treasury/admin finance changes.
- Keep `.runtime/admin_god_mode.json` unstaged as runtime-local state unless its owner explicitly asks for a revert or template/ignore change.
- Do not resolve guard failures by adding production Unity/native/3D paths.
- Keep backend test-speed pressure on the remaining full-schema fixtures until full pytest becomes finishable.
- Re-run final gates on the main worktree, not only on side worktrees, after the first-wave fixes are integrated.
