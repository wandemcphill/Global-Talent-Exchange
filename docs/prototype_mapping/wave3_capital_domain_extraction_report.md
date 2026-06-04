# GTEX Wave 3 Capital Domain Extraction Report

Date: 2026-06-02

Scope: Wave 3 frontend consumer/capital extraction update from local repo state. Code was edited under capital-owned consumer surfaces, adjacent consumer finance surfaces, guardrail tooling, and this report. No backend, admin command center, match center, compete, router, or shell primitives were edited.

## Financial Extraction Report

Current local source shows capital ownership concentrated under `frontend/lib/features/capital/**`.

Observed extracted capital areas:
- Wallet presentation, wallet providers, wallet summary widget, wallet facade, wallet display/availability DTOs, wallet fixture store, and wallet transport models live under `frontend/lib/features/capital/wallet/**`.
- Trader dashboard/API and `ExchangeHubProvider` live under `frontend/lib/features/capital/trader/**`.
- Dispute screens/API live under `frontend/lib/features/capital/disputes/**`.
- Admin finance API lives under `frontend/lib/features/capital/settlement/data/admin_finance_api.dart`.
- Creator league admin settlement and creator stadium monetization settlement live under `frontend/lib/features/capital/settlement/**`.
- Club sale and creator share market liquidity live under `frontend/lib/features/capital/liquidity/**`.

Wallet facade status:
- `CapitalWalletApi` exists at `frontend/lib/features/capital/wallet/data/capital_wallet_api.dart`.
- It is the wallet boundary for summary, overview, transactions, top-up, conversion, deposit, withdrawal, policy/compliance, KYC, bank account, attachment upload, display snapshot, availability, and market snapshot flows.
- The facade supports both repository-backed fixture/test usage and live `GteAuthedApi` usage.
- It now exposes ledger and policy requirement reads used by consumer controllers, plus `capitalWalletApiForClient(...)` so adjacent consumer surfaces do not instantiate wallet transport directly.

Backend-derived wallet DTO status:
- `CapitalWalletAvailability` parses backend-shaped wallet availability fields including available, reserved, locked, pending withdrawal, total balance, currency, blocked reason, and lock reasons.
- `CapitalWalletDisplaySnapshot` adapts backend wallet summary/availability into presentation-safe display state and requires backend-derived total balance when constructed from availability.
- `CapitalWalletMarketSnapshot` is built from backend wallet display snapshots, wallet overview, and compliance status.
- Wallet transport models now live in `frontend/lib/features/capital/wallet/data/capital_wallet_transport_models.dart`; they include backend-derived balances, pending deposits/withdrawals, withdrawable amount, lock reasons, policy blocking reason, and deposit/withdrawal rail modes.

Wallet presentation no longer using `controller.api`:
- A scoped source scan of `frontend/lib/features/capital/wallet/**` found wallet screens using `widget.controller.walletApi` / `_walletApi`.
- The wallet presentation paths observed were overview, funding, deposit history, withdrawal flow, KYC, policy/compliance, and bank details.
- Capital dispute presentation uses `CapitalDisputeApi` / `controller.disputeApi`.
- A source scan found no direct `controller.api` calls inside `frontend/lib/features/capital/**`.

Consumer finance truth cleanup:
- Transfer market wallet display, withdrawal quote, and buy-capacity UI no longer derive money values from local `walletBalanceGtex`, `nairaPerGtex`, or share-price math. Those states now render backend-required/blocked copy.
- Jackpot no longer ships fixture jackpot/wallet payloads or hardcoded jackpot wallet balances. Contributions require backend-derived `CapitalWalletAvailability`.
- Build-a-Son no longer decides wallet eligibility by comparing displayed `availableBalanceCoin` against cost in Flutter. Confirmation trusts backend `can_pay_with_wallet` / blocked state.
- Portfolio capital bars no longer derive reserve, exposure, available-cash, or allocation ratios locally; progress indicators now show backend-sync/blocked states while backend/model amounts remain visible.
- Creator share market no longer pre-fills max share issuance with `1000` or displays missing holdings as `0` GTEX Coin; missing holding financial fields now render backend sync required.
- Capital trader provider no longer embeds local payout limits or a GTEX-to-NGN rate.
- Club sale market fixture fallback is now explicit fixture-mode behavior; standard/liveThenFixture repository construction is clamped to live mode.
- Club sale owner-offer route authorization now obtains its repository through the capital-owned `clubSaleMarketRepositoryForClient(...)` factory instead of constructing liquidity repositories in route-builder code.
- App and legacy controller composition now obtain wallet, dispute, and trader APIs through capital-owned factory helpers.
- Transfer-market allocation/trade sheets no longer label slider intent as reserved funds or display locally multiplied player-order quote values.
- Transfer-market exchange hub state no longer carries hidden placeholder wallet, spend, trade-count, withdrawal, or KYC-tier defaults.
- Dispute fixture queues, sequencing, seeds, user replies, admin replies, admin filtering, and open-dispute counts now live in `CapitalDisputeFixtureStore`.
- `GteExchangeApiClient.fixture` obtains capital-enabled fixture repositories through `createCapitalFixtureRepository(...)` instead of directly constructing `GteMockApi.capitalFixtures`.
- KYC profile state, user bank-account state, user bank sequencing, seeded KYC/bank fixtures, KYC submission, admin KYC queue/review projection, active-bank account mutation, and bank-account resolution now live in `CapitalWalletFixtureStore`.
- Treasury settings state, treasury bank-account state, treasury bank sequencing, seeded treasury rails, settings updates, active treasury bank selection, and treasury bank CRUD now live in `CapitalTreasuryFixtureStore` under capital settlement.
- Payout withdrawal queue state, withdrawal sequencing, seeded withdrawals, withdrawal eligibility/quote/receipt, withdrawal request creation, admin withdrawal queue filtering, admin status mutation, pending withdrawal totals, receipt fallback, and withdrawal status parsing now live in `CapitalPayoutFixtureStore` under capital payouts.
- Deposit queue state, deposit sequencing, seeded deposits, pending deposit totals, user deposit creation/submission, admin deposit queue filtering, admin confirm/reject/review mutation, and deposit status parsing now live in `CapitalDepositFixtureStore` under capital settlement.
- Policy document state, policy acceptance state, seeded policy fixtures, compliance status projection, policy requirement calculation, and policy acceptance mutation now live in `CapitalPolicyFixtureStore` under capital settlement.
- Trader ticker state, orderbook state, order queue state, order sequencing, session order tracking, seeded trader/order fixtures, ticker/orderbook merging, user order placement, and user order cancellation now live in `CapitalTraderFixtureStore` under capital trader.
- Portfolio holdings state, portfolio summary state, seeded portfolio fixtures, holding quantity adjustment, and portfolio summary rebuilds now live in `CapitalPortfolioFixtureStore` under capital trader.
- Admin buyback preview/execution composition, liquidity-band math, payout-band math, buyback payout ratio, order fill mutation, wallet crediting, and portfolio reduction now live in `CapitalBuybackFixtureStore` under capital trader.
- Treasury dashboard aggregation over pending deposits, pending withdrawals, KYC review count, open disputes, wallet liability, and pending treasury exposure now lives in `CapitalTreasuryDashboardFixtureStore` under capital settlement.

Fixture delegation status:
- `GteMockApi.capitalFixtures(...)` exists as an explicit opt-in path.
- Default capital fixtures remain fail-closed in `GteMockApi` when explicit capital fixtures are not enabled.
- `GteMockApi` delegates wallet summary, fan wallet summary, ledger, transactions, top-up sessions, ledger sequence, and transaction sequence state to `CapitalWalletFixtureStore`.
- Observed wallet mutation helpers include order reserve/release, coin crediting, coin-to-fan conversion, withdrawal reserve/release/settlement, top-up session storage, and top-up verification.
- Observed wallet compliance helpers include KYC submit/review, admin KYC projection/filtering, user bank account create/update/list, active-bank selection, KYC country/status labels, and withdrawal bank resolution.
- Treasury rail helpers now include settings reads/updates, active bank-account resolution, treasury bank-account list/create/update, and treasury seed data under `frontend/lib/features/capital/settlement/data/capital_treasury_fixture_store.dart`.
- Payout helpers now include backend-shaped withdrawal eligibility, quote, receipt, active pending totals, user withdrawal creation, admin queue projection, and wallet reserve/settle/release mutations through the capital wallet store.
- Deposit helpers now include backend-shaped user deposit creation/submission, pending deposit counts/amounts, admin queue projection, review/reject/confirm lifecycle, and wallet credit mutation through the capital wallet store.
- Policy helpers now include backend-shaped policy listing/detail reads, compliance status, missing required policy acceptances, and acceptance mutation.
- Trader helpers now include backend-shaped ticker/orderbook/list/fetch/place/cancel behavior plus wallet reserve/release mutation through the capital wallet store.
- Portfolio helpers now include backend-shaped portfolio reads and wallet-aware summary rebuilds through the capital wallet store.
- Buyback helpers now include backend-shaped preview/execution behavior over the capital trader, portfolio, and wallet stores.
- Treasury dashboard helpers now compose backend-shaped aggregate values from capital wallet, deposit, payout, and dispute stores.

## Forbidden Import Report

Visible source posture:
- Deleted legacy financial implementation paths appear as git deletions for `frontend/lib/screens/wallet/**`, `frontend/lib/screens/trader/trader_dashboard_screen.dart`, `frontend/lib/screens/support/gte_support_dispute_screens.dart`, `frontend/lib/data/trader_api.dart`, `frontend/lib/data/dispute_engine_api.dart`, `frontend/lib/data/admin_finance_api.dart`, and `frontend/lib/widgets/gte_wallet_summary_card.dart`.
- New capital-owned replacements are present under `frontend/lib/features/capital/**`.
- Renderer/native bridge ownership is separated under `frontend/lib/features/3d/**`.
- Competition ownership has moved toward `frontend/lib/features/compete/**`, while legacy competition files show as deleted in git status.

Guardrail code visible in `tools/guardrails/production_guardrail_scan.py` rejects:
- Renderer/native bridge references outside authorized frontend zones.
- Financial domain imports from legacy wallet/trader/dispute/admin-finance paths.
- Consumer wallet summary reads outside capital wallet ownership/shared low-level data clients.
- Consumer UI regressions to `controller.walletSummary`.
- Legacy mock wallet fixture fields outside capital wallet fixture ownership.
- Direct mock wallet fixture mutation outside capital-owned fixture helpers.
- Direct `controller.api` calls from capital feature surfaces.
- Legacy financial implementation paths outside `frontend/lib/features/capital/**`.
- Route/app composition construction for wallet, dispute, trader, and club-sale liquidity APIs is routed through capital-owned factories.
- Capital-enabled fixture repository construction is routed through `frontend/lib/features/capital/capital_fixture_repository.dart`.
- `capital-fixture-direct-mock-construction` guardrail blocks new production callers from using `GteMockApi.capitalFixtures` directly outside the legacy shim.
- `extracted-capital-fixture-state-outside-capital` guardrail blocks extracted wallet, KYC/bank, treasury, payout, deposit, dispute, policy, trader, portfolio, buyback, and treasury dashboard fixture state from returning to non-capital owners.

Forbidden import/text scans were run for this update and passed with no violations.

## CI Enforcement Report

Visible enforcement owner:
- `tools/guardrails/production_guardrail_scan.py`

Visible CI/guardrail intent:
- The guardrail tool contains rules for capital import ownership, wallet summary consumer boundaries, `controller.walletSummary` regressions, mock wallet fixture ownership, direct mock wallet fixture mutation, renderer/native bridge quarantine, and legacy implementation path deletion.
- `frontend/test/guardrails/**` exists in the working tree, indicating guardrail tests are present locally.

Current validation:
- `python tools/guardrails/production_guardrail_scan.py --root frontend/lib --root frontend/test --format summary --fail-on violation` passed with `{"owned-by-thread": 95, "quarantined": 9}`.
- `python tools/guardrails/production_guardrail_scan.py --profile default --format summary --fail-on violation` passed with `{"owned-by-thread": 95, "quarantined": 102}`.
- `dart analyze` passed for the touched capital/wallet/dispute/trader/liquidity, app-route, transfer, Build-a-Son, jackpot, controller, notification, portfolio, guardrail, and wallet/build/trader test slices.
- `dart analyze` passed for the capital fixture factory, capital disputes, `gte_mock_api.dart`, and `gte_exchange_api_client.dart` after dispute fixture extraction.
- `dart analyze` passed for `capital_wallet_fixture_store.dart`, `gte_mock_api.dart`, `gte_exchange_api_client.dart`, and `capital_fixture_repository.dart` after KYC/bank fixture extraction.
- `dart analyze` passed for `capital_treasury_fixture_store.dart`, settlement exports, capital wallet/dispute stores, the capital fixture factory, `gte_mock_api.dart`, and `gte_exchange_api_client.dart` after treasury rail extraction.
- `dart analyze` passed for `capital_payout_fixture_store.dart`, payouts exports, capital treasury/wallet stores, `gte_mock_api.dart`, and `gte_exchange_api_client.dart` after payout withdrawal extraction.
- Focused `flutter test` passed: 59 tests across Build-a-Son, transfer market, wallet, guardrails, trader/dispute transport, and jackpot.
- Focused `flutter test` passed: 37 tests across club-sale liquidity, secondary backend-mode strictness, trader API, transfer market, wallet, and guardrails.
- Focused reruns passed for `test/trader/trader_api_test.dart` and `test/transfer_market/transfer_market_screen_test.dart` after removing transfer-market placeholder financial state.
- Focused rerun passed for `test/dispute_engine_api_transport_test.dart test/gte_mock_api_test.dart test/gte_exchange_api_client_test.dart test/guardrails/forbidden_text_guard_test.dart`.
- Focused rerun passed for wallet backend-truth tests: bank details, compliance center, KYC, model strictness, and canonical overview.
- Focused rerun passed for 40 tests across dispute transport, mock API, exchange client, guardrails, and wallet backend-truth suites after treasury rail extraction.
- Focused reruns passed after payout extraction: `gte_mock_api_test.dart`, wallet overview/model strictness tests, and forbidden text guardrail tests.
- Current guardrail reruns passed with `{"owned-by-thread": 95, "quarantined": 9}` for `frontend/lib` + `frontend/test`, and `{"owned-by-thread": 95, "quarantined": 102}` for the default profile.
- Current production-only forbidden scan outside authorized `frontend/lib/features/3d/**` returned no matches for Paystack, Unity, native 3D, pseudo-3D, SceneKit, Babylon, native renderer, or experimental bridge wording.
- Current deposit extraction validation: `dart format` passed on `gte_mock_api.dart`, settlement exports, and `capital_deposit_fixture_store.dart`; stale mock deposit symbol scan found no mock-level deposit requests, sequence, seed list, or status parser; `git diff --check` passed for the touched deposit files.
- Current policy/trader/portfolio/buyback/dashboard extraction validation: `dart format` passed on `gte_mock_api.dart`, settlement/trader exports, `capital_policy_fixture_store.dart`, `capital_trader_fixture_store.dart`, `capital_portfolio_fixture_store.dart`, `capital_buyback_fixture_store.dart`, and `capital_treasury_dashboard_fixture_store.dart`; stale mock policy, trader, portfolio, buyback, and dashboard fixture symbol scans found no old mock-owned state; `flutter test test/wallet/wallet_compliance_center_backend_truth_test.dart -r compact` passed; `flutter test test/gte_mock_api_test.dart -r compact --concurrency=1` passed 4 tests including order submit/cancel balance sync and illiquid orderbook behavior.
- A transient Flutter native-assets copy error occurred on the first final `gte_mock_api_test.dart` retry, then the same targeted test passed on rerun.
- Current Dart validation blocker: targeted `dart analyze` for the capital deposit/treasury/wallet/payout stores plus `gte_mock_api.dart` and `gte_exchange_api_client.dart`, and later for the capital trader store plus `gte_mock_api.dart`, remained active under local Dart process contention and was stopped after no result. The focused mock API Flutter test later passed.
- A final analyzer retry for `exchange_hub_provider.dart` and `exchange_hub_widgets.dart` crashed the Dart analysis server without diagnostics. Formatting, focused Flutter tests, guardrails, and fake-field scans passed for the same slice.
- `git diff --check` passed for touched tracked files; Git emitted CRLF normalization warnings on existing Windows-touched files but no whitespace errors.

## Deleted Leakage Systems Report

Deleted or moved leakage paths visible from local git/source state:
- Legacy wallet screens are deleted from `frontend/lib/screens/wallet/**`.
- Legacy trader dashboard is deleted from `frontend/lib/screens/trader/trader_dashboard_screen.dart`.
- Legacy support dispute screen is deleted from `frontend/lib/screens/support/gte_support_dispute_screens.dart`.
- Legacy capital APIs are deleted from `frontend/lib/data/trader_api.dart`, `frontend/lib/data/dispute_engine_api.dart`, and `frontend/lib/data/admin_finance_api.dart`.
- Legacy wallet summary widget is deleted from `frontend/lib/widgets/gte_wallet_summary_card.dart`.
- Legacy competition controllers/screens/widgets/features show as deleted, with replacement ownership under `frontend/lib/features/compete/**`.
- Legacy match and 3D files show as deleted from older shared paths, with replacements under `frontend/lib/features/match_center/**` and `frontend/lib/features/3d/**`.

Quarantined rather than fully deleted:
- `frontend/lib/data/gte_mock_api.dart` still contains capital fixture orchestration, but wallet state and mutation helpers are delegated to `CapitalWalletFixtureStore`, and capital fixture behavior is gated behind explicit `GteMockApi.capitalFixtures(...)` opt-in.
- `frontend/lib/data/gte_models.dart`, `frontend/lib/data/gte_api_repository.dart`, and `frontend/lib/data/gte_exchange_api_client.dart` remain shared compatibility/repository layers that expose or route capital types while the app transition continues.
- Jackpot fixture payloads and hardcoded jackpot wallet values were removed from the production route.
- Transfer-market local wallet/NGN/purchasing calculations were removed from the wallet and buy-flow surfaces.
- Portfolio local capital ratio calculations were removed from presentation.
- Creator-share missing holding zero-money placeholders were removed.
- Club-sale fallback fixture behavior is explicit through fixture construction instead of standard/liveThenFixture production construction.

## Canonical Ownership Report

Canonical ownership as observed:
- Capital root: `frontend/lib/features/capital/**`
- Capital wallet: `frontend/lib/features/capital/wallet/**`
- Capital trader: `frontend/lib/features/capital/trader/**`
- Capital disputes: `frontend/lib/features/capital/disputes/**`
- Capital liquidity: `frontend/lib/features/capital/liquidity/**`
- Capital settlement: `frontend/lib/features/capital/settlement/**`
- Capital payouts marker/export: `frontend/lib/features/capital/payouts/**`
- Capital wallet facade: `frontend/lib/features/capital/wallet/data/capital_wallet_api.dart`
- Capital wallet presentation DTOs: `capital_wallet_availability.dart`, `capital_wallet_display_snapshot.dart`, and `CapitalWalletMarketSnapshot` in `capital_wallet_api.dart`
- Capital wallet fixture owner: `frontend/lib/features/capital/wallet/data/capital_wallet_fixture_store.dart`
- Competition: `frontend/lib/features/compete/**`
- Live match center: `frontend/lib/features/match_center/**`
- Renderer/native bridge: `frontend/lib/features/3d/**` and `frontend/lib/native/**`

Current consumer posture:
- `GteExchangeController` exposes `walletApi` and stores `CapitalWalletDisplaySnapshot` wallet display state.
- `GteExchangeController` exposes `disputeApi` and a capital trader API factory for consumer surfaces.
- Legacy `GteAppController` also stores `CapitalWalletDisplaySnapshot` wallet display state.
- Transfer market loads a `CapitalWalletMarketSnapshot` through capital wallet providers/facades and no longer computes local purchasing power.
- Transfer-market trade UI now blocks buy capacity and quote display behind backend wallet/quote truth instead of deriving order value from share price multiplication.
- Transfer-market dashboard stats render backend-required states instead of local zero/default spend, trade, matchday, bank, or KYC values.
- Dispute presentation and admin review fixtures now share capital-owned fixture state rather than `GteMockApi` owning dispute queues.
- Build-a-Son and Jackpot use backend-derived wallet availability evidence.
- Wallet UI uses `CapitalWalletApi` rather than direct controller repository access.

## Unresolved Architectural Risks

- `GteMockApi` remains a compatibility fixture shim, but Wave 3 capital fixture state now lives behind capital-owned wallet, settlement, payouts, disputes, and trader stores.
- Remaining `GteMockApi` risk is compatibility orchestration and broad repository surface area, not direct capital state ownership.
- Shared compatibility layers remain: `GteExchangeApiClient`, `GteApiRepository`, and `gte_models.dart` still expose or route capital transport types.
- Admin finance is capital-owned by path, but admin operational surfaces still need continued review to ensure they never become settlement authority.
- Club sale market still has fixture repository support under capital liquidity, but fixture fallback is now explicit and standard/liveThenFixture construction is live-mode strict.
- App/legacy controllers still remain shared composition surfaces, but wallet, dispute, trader, and club-sale liquidity construction now goes through capital-owned factories.
- Full all-repo frontend analyzer/test status was not run; validation was targeted to the touched Wave 3 surfaces.
- Production/staging proof is still needed for real top-up initialization/verification, manual proof review, withdrawal settlement, receipt retrieval, and operations reconciliation.

## Validation Notes

Commands run for this refresh:
- `dart format` on touched Dart files.
- `dart format lib/data/gte_mock_api.dart lib/features/capital/settlement/settlement.dart lib/features/capital/settlement/data/capital_deposit_fixture_store.dart`
- `dart format lib/data/gte_mock_api.dart lib/features/capital/trader/data/capital_trader_fixture_store.dart lib/features/capital/trader/trader.dart`
- `dart format lib/data/gte_mock_api.dart lib/features/capital/trader/data/capital_portfolio_fixture_store.dart lib/features/capital/trader/data/capital_trader_fixture_store.dart lib/features/capital/trader/trader.dart`
- `dart format lib/data/gte_mock_api.dart lib/features/capital/settlement/data/capital_treasury_dashboard_fixture_store.dart lib/features/capital/settlement/settlement.dart`
- `dart analyze` on touched capital, transfer, Build-a-Son, jackpot, controller, notification, portfolio, guardrail, and focused test slices.
- `flutter test test/build_a_son/build_a_son_closure_test.dart test/build_a_son/build_a_son_wallet_block_test.dart test/transfer_market/transfer_market_screen_test.dart test/wallet_api_route_transport_test.dart test/gte_funding_flow_screen_test.dart test/wallet/wallet_overview_canonical_state_test.dart test/wallet/wallet_model_strictness_test.dart test/wallet/wallet_kyc_backend_truth_test.dart test/wallet/wallet_compliance_center_backend_truth_test.dart test/wallet/wallet_bank_details_backend_truth_test.dart test/guardrails/forbidden_text_guard_test.dart test/trader/trader_api_test.dart test/dispute_engine_api_transport_test.dart test/gtex_jackpot_route_screen_test.dart -r compact`
- `flutter test test/club_sale_market/club_sale_market_screen_test.dart test/club_sale_market/club_sale_market_controller_test.dart test/secondary_api_backend_mode_test.dart -r compact`
- `flutter test test/trader/trader_api_test.dart -r compact`
- `flutter test test/transfer_market/transfer_market_screen_test.dart -r expanded`
- `flutter test test/dispute_engine_api_transport_test.dart test/gte_mock_api_test.dart test/gte_exchange_api_client_test.dart test/guardrails/forbidden_text_guard_test.dart -r compact`
- `flutter test test/wallet/wallet_bank_details_backend_truth_test.dart test/wallet/wallet_compliance_center_backend_truth_test.dart test/wallet/wallet_kyc_backend_truth_test.dart test/wallet/wallet_model_strictness_test.dart test/wallet/wallet_overview_canonical_state_test.dart -r compact`
- `python tools/guardrails/production_guardrail_scan.py --root frontend/lib --root frontend/test --format summary --fail-on violation`
- `python tools/guardrails/production_guardrail_scan.py --profile default --format summary --fail-on violation`
- `rg -n -i "\b(paystack|unity|native[- ]?3d|pseudo[- ]?3d|scenekit|babylon|native renderer|experimental bridge)\b" frontend/lib | Select-String -NotMatch "frontend[/\\]lib[/\\]features[/\\]3d"`
- `rg -n "_depositRequests|_depositSequence|_seedDeposits|_depositStatusFromString" frontend/lib/data/gte_mock_api.dart`
- `rg -n "_policyDocuments|_policyAcceptances|_seedPolicyDocuments|_seedPolicyAcceptances|_currentMissingPolicyRequirements" frontend/lib/data/gte_mock_api.dart`
- `rg -n "_baseTickers|_baseOrderBooks|_sessionOrderIds|_orderSequence|_seedTickers|_seedOrderBooks|_seedOrders" frontend/lib/data/gte_mock_api.dart`
- `rg -n "_portfolioSummary|_seedPortfolioHoldings|_seedPortfolioSummary|_baseTickers|_baseOrderBooks|_sessionOrderIds|_orderSequence|_seedTickers|_seedOrderBooks|_seedOrders" frontend/lib/data/gte_mock_api.dart`
- `rg -n "_liquidityBandForPrice|_payoutBandForPrice|_adminBuybackPayoutRatio" frontend/lib/data/gte_mock_api.dart`
- `git diff --check -- frontend/lib/data/gte_mock_api.dart frontend/lib/features/capital/settlement/data/capital_deposit_fixture_store.dart frontend/lib/features/capital/settlement/settlement.dart`
- `git diff --check -- frontend/lib/data/gte_mock_api.dart frontend/lib/features/capital/settlement/data/capital_treasury_dashboard_fixture_store.dart frontend/lib/features/capital/settlement/settlement.dart frontend/lib/features/capital/trader/data/capital_buyback_fixture_store.dart frontend/lib/features/capital/trader/data/capital_portfolio_fixture_store.dart frontend/lib/features/capital/trader/data/capital_trader_fixture_store.dart frontend/lib/features/capital/trader/trader.dart tools/guardrails/production_guardrail_scan.py docs/prototype_mapping/wave3_capital_domain_extraction_report.md`
- `flutter test test/wallet/wallet_compliance_center_backend_truth_test.dart -r compact`
- `flutter test test/gte_mock_api_test.dart -r compact --concurrency=1`
- Forbidden text scan via guardrail test/scanner for Paystack, Unity, SceneKit, Babylon, native renderer, experimental bridge, and pseudo-3D wording.
- Additional fake-field scan for `walletBalanceGtex`, `fanCoinBalance`, `weeklySpendNaira`, `matchesWatched`, `tradesMade`, `withdrawalUsedTodayNaira`, `ComplianceTier`, `orderValue`, and reserve-label regressions in transfer/capital trader surfaces.
- `git diff --check` on touched tracked files.

Commands not run:
- Full all-repo `flutter test`.
- Unity batchmode build.
