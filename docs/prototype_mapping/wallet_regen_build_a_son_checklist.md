# Wallet, Regen World, and Build-a-Son Prototype Mapping

Source: `C:\Users\ayomc\Downloads\Gtex_prototype_v13 (5).html`

Scope read:
- `renderBuildASon()` around line 1890
- `completeBuildSon()` around line 2047
- `renderWallet()` around line 2330
- `renderRegenWorld()` around line 4991

Flutter targets inspected:
- `frontend/lib/screens/wallet/gte_wallet_overview_screen.dart`
- `frontend/lib/screens/wallet/gte_funding_flow_screen.dart`
- `frontend/lib/screens/wallet/gte_deposit_history_screen.dart`
- `frontend/lib/screens/wallet/gte_withdrawal_flow_screen.dart`
- `frontend/lib/features/regens/regens_screen.dart`
- `frontend/lib/features/regen_creation/presentation/build_a_son_wizard.dart`
- `frontend/lib/features/regen_creation/data/build_a_son_creation_client.dart`
- `frontend/lib/data/regen_creation_api.dart`
- `frontend/lib/data/regen_universe_api.dart`
- `frontend/lib/shared/providers/regen_provider.dart`

## Wallet

Prototype state and data:
- `showEmptyWallet` toggles populated vs empty wallet presentation.
- Populated totals: total balance `GTC 4,820`, approximate fiat `NGN 11,811`, `GTEX Coin (GTC) 4,820`, `Fan Coin (FNC) 1,100`.
- Empty totals: `GTC 0`, `NGN 0.00`, both coin chips zero.
- Primary actions: `Fund via KoraPay`, `Manual Transfer`, `Withdraw`.
- Empty deposit state title: `No Deposits Yet`; action: `Make First Deposit`.
- Empty transaction state uses three skeleton strips and message `No transactions yet - activity will appear here`.
- Deposit history rows:
  - May 26, KoraPay, `GTC 500`, Approved
  - May 24, Manual, `GTC 1,200`, Approved
  - May 20, Manual, `GTC 800`, Pending
  - May 15, KoraPay, `GTC 300`, Rejected
- Transaction log rows:
  - Transfer - Rashford K. signed, debit, `-GTC 2,400`, May 26
  - KoraPay deposit, credit, `+GTC 500`, May 26
  - Competition entry - West Africa Cup, debit, `-GTC 100`, May 24
  - Gift received from fan_441, credit, `+FNC 50`, May 23
  - Manual bank transfer deposit, credit, `+GTC 1,200`, May 24

Wallet payment modal requirements:
- KoraPay flow: amount selection (`GTC 500`, `1,000`, `2,000`, `5,000`, `10,000`, custom), checkout summary at `1 GTC ~= NGN 2.45`, awaiting payment, funded success with generated `KP-*` reference.
- Manual flow: bank details, exact reference, amount in NGN, proof upload, under admin review, approved success.
- Manual bank demo data: Zenith Bank, GTEX Operations Ltd, account number `1234567890`, generated `GTEX-*` reference.
- Withdrawal flow: GTC amount, verified bank account selector, KYC note, 1-3 business day processing message, submit request.

Production Flutter checklist:
- [x] Wallet overview already loads backend-backed overview, GTC summary, FNC/credit summary, recent transactions, and withdrawal eligibility in `gte_wallet_overview_screen.dart`.
- [x] Overview already has Deposit, Withdraw, and Transaction History actions.
- [x] Funding screen already separates automatic provider flow from manual deposit/proof review flow in `gte_funding_flow_screen.dart`.
- [x] Deposit/transaction history already has empty, loading, error, refresh, and ledger-list states in `gte_deposit_history_screen.dart`.
- [x] Withdrawal screen already uses backend eligibility, quote, request, receipt, and list states.
- [ ] Preserve the prototype's populated/empty visual states as test fixtures only; balances and statuses must come from wallet APIs.
- [ ] Keep KoraPay, manual transfer, and withdrawal as first-class wallet actions even if production button labels differ.
- [ ] Make sure transaction rows distinguish credit/debit, GTC/FNC units, date, status/reference, and auditability.
- [ ] Do not port the prototype's simulated success transitions as authority; production must wait on top-up verification, manual review, or withdrawal lifecycle.

## Build-a-Son Wizard

Prototype state:
- Wizard opens when `buildSonStep > 0`; initial inactive step is `0`.
- Step state: `buildSonStep`, `buildSonParent`, `buildSonTraits`, `buildSonName`, `buildSonPos`, `buildSonNat`.
- Defaults: parent `null`, traits `[]`, name empty, position `CAM`, nationality `NGA`.
- Affordability uses `walletGTC - walletReserved`; prototype defaults are `walletGTC = 4820`, `walletReserved = 0`.

Prototype steps and validation:
- Step 1 `Choose Parent`: pick a senior squad player from `SQUAD_POOL`; block next with toast `Select a parent first`.
- Step 2 `Inherit Traits`: show selected parent card and parent traits; choose exactly 3 traits; block next with toast `Select 3 traits to inherit`.
- Step 3 `Name & Position`: name input, position select, nationality select; block next with toast `Give your son a name`.
- Step 4 `Confirm`: preview generated son, parent, generation, projected OVR, potential, development time, DNA bars, cost, and affordability.
- Cancel resets step, parent, traits, and name, then returns to main render.

Prototype exact trait pool:
- Pace Burst
- Clinical Finisher
- Dribbler
- Vision Pass
- Aerial Threat
- Engine
- Late Runner
- Ghost Goal
- Set Piece Taker
- Tenacious Tackle
- Composite Touch
- Poacher

Prototype identity options:
- Positions: `GK`, `CB`, `LB`, `RB`, `CDM`, `CM`, `CAM`, `LM`, `RM`, `LW`, `RW`, `ST`, `CF`
- Nationalities: `NGA` Nigeria, `GHA` Ghana, `SEN` Senegal, `CIV` Ivory Coast, `BRA` Brazil, `ZAF` South Africa

Prototype confirm preview:
- Generation is parent generation plus one.
- Preview location/status is `Academy`.
- Projected DNA bars: `PAC`, `SHO`, `DRI`, `PAS`, `DEF`, `PHY`.
- Creation cost is fixed at `GTC 200`.
- Cost card shows available balance or insufficient amount.
- Insufficient state text tells the user to top up or release pending bids.
- CTA label is `Create GEN-{sonGen} Regen - GTC 200`.

Prototype completion behavior:
- Rechecks `walletGTC - walletReserved >= 200`.
- Deducts `GTC 200` locally.
- Pushes a new academy player with name, position, age 14-16, nationality, `GEN-{sonGen}`, week counter `0`, selected traits, and parent.
- Calculates academy OVR as projected OVR minus 12, minimum 45.
- Resets wizard state, switches `squadTab` to `academy`, saves state, rerenders, and shows a success toast.

Production Flutter checklist:
- [x] `build_a_son_wizard.dart` already implements the four-step flow, async option loading, backend preview, wallet availability card, submit state, and completion callback.
- [x] `BuildASonCreationClient` already maps to `fetchRequestSonOptions`, `previewRequestSon`, `createRequestSonOrder`, `payWithWallet`, and `generateAfterPayment`.
- [x] Models already include parent generation, traits, lineage, DNA, pricing, wallet availability, and generated order fields.
- [x] Step navigation already uses prototype wording `Name & Position`; the section title `Identity` remains supporting copy only.
- [ ] Reconcile static fallback trait labels with the exact prototype trait pool, or document that backend-provided traits supersede the prototype pool.
- [x] Default position needs no further review in Flutter: canonical state starts at prototype `CAM`; backend `AM` and `DM` positions normalize to visible `CAM` and `CDM` labels before request serialization.
- [x] Keep exactly-three trait validation and parent trait highlighting.
- [x] Keep nationality and position options aligned with the prototype unless backend options become authoritative.
- [x] Use backend preview totals for cost, OVR, potential, DNA, generation, and wallet availability; never rely on the prototype random projection math.
- [x] Completion creates an order, requires backend wallet reservation evidence before wallet payment, generates after payment, refreshes wallet truth around settlement, and then refreshes requested sons/academy data. Do not locally mutate an academy list as authority.

Current Flutter implementation map, verified 2026-05-31:
- Canonical feature barrel: `frontend/lib/features/build_a_son/build_a_son.dart`.
- Canonical wizard and UI lifecycle: `frontend/lib/features/build_a_son/presentation/build_a_son_screen.dart`.
- Legacy compatibility adapter only: `frontend/lib/features/regen_creation/presentation/build_a_son_wizard.dart`.
- Canonical client boundary: `frontend/lib/features/build_a_son/data/build_a_son_creation_client.dart`.
- Legacy data adapter only: `frontend/lib/features/regen_creation/data/build_a_son_creation_client.dart`.
- Provider wiring: `frontend/lib/features/build_a_son/providers/build_a_son_providers.dart`.
- Backend API client: `frontend/lib/data/regen_creation_api.dart`.
- Backend-owned DTOs: `frontend/lib/models/regen_creation_models.dart`.
- Frontend parity tests: `frontend/test/build_a_son/build_a_son_closure_test.dart`, `frontend/test/build_a_son/build_a_son_wallet_block_test.dart`, `frontend/test/build_a_son/request_son_legacy_adapter_test.dart`, and `frontend/test/regen_creation/build_a_son_wizard_test.dart`.

Prototype-to-production mapping:
- `renderBuildASon()` step state maps to `BuildASonWizard` step labels: `Choose Parent`, `Inherit Traits`, `Name & Position`, and `Confirm`.
- `renderBuildASon()` parent picker maps to `RequestSonOptions.eligibleParents` and `RegenCreationParentPlayer`; Flutter must not invent eligible parents.
- `renderBuildASon()` trait selection maps to `_selectedTraits.length == 3`; trait availability comes from the selected backend parent rather than a production hardcoded pool.
- `renderBuildASon()` identity fields map to `RequestSonPreviewDraft.requestedName`, `requestedPosition`, and `requestedCountryCode`.
- `renderBuildASon()` DNA/cost/OVR/POT/generation confirmation maps to `RequestSonPreview`; Flutter blocks confirmation when the backend preview omits required projection, price, or wallet evidence.
- `completeBuildSon()` maps to `createRequestSonOrder`, backend wallet reservation evidence, `payWithWallet`, `generateAfterPayment`, and `cancelCreationOrder` for failed reserved-wallet rollbacks; Flutter refreshes canonical wallet and regen state after completion and does not deduct balances or mutate academy players locally.
- Prototype wallet affordability (`walletGTC - walletReserved`) maps to backend `RegenCreationWalletAvailability`; lock reasons and insufficient-fund messaging remain backend-owned.

## Regen World

Prototype state and filters:
- `regenGenFilter`: `all`, `gen-1`, `gen-2`, `gen-3`.
- `regenDetailId`: selected card id or null.
- Hero labels: `Regen World`, `Discover Regen Talent`, `Regen Season Active`.
- Hero metrics: discovered count, elite count where `pot >= 80`, GEN-3 rare count.
- Search placeholder: `Search regens by name, trait, or position...`
- Filters: `All Positions`, `All Values`, sort by `Potential`, `Value`, or `Newest`, plus generation pills.
- Empty state: `No Regens Found`, clear/show-all action.
- Bottom education strip explains GEN-1 first generation, GEN-2/GEN-3 inherited compounded traits, higher generations rarer and often more valuable.

Prototype `REGEN_DATA` records:
- `kwame`: Kwame Jr., CAM, POT 82, Ghana, NGN 1.8M, GEN-2, traits Ghost Goal/Dribbler/Leadership/High Work Rate, origin Lagos Academy, lineage Kwame Sr. -> Asante G. -> Kwame Jr.
- `adekunle`: Adekunle S., LB, POT 74, Nigeria, NGN 800K, GEN-1, traits Tenacious Tackle/Pace Burst/Set Piece Taker, origin Kano Youth System, self lineage only.
- `amara2`: Amara D. Jr., CM, POT 79, Senegal, NGN 1.2M, GEN-2, traits Vision Pass/Engine/Box to Box/Late Runner, origin Dakar Academy, father Diallo Sr.
- `tunde3`: Tunde III, ST, POT 88, Nigeria, NGN 3.4M, GEN-3, traits Clinical Finisher/Aerial Threat/Speed Burst/Poacher/Ice Cold, origin Lagos City Academy, Tunde I -> Tunde II -> Tunde III.
- `kofi`: Kofi A., GK, POT 77, Ghana, NGN 950K, GEN-1, traits Sweeper Keeper/Command Area/Distribution, origin Kumasi FC Youth, self lineage only.
- `ibrahim2`: Ibrahim D. Jr., CB, POT 76, South Africa, NGN 1.1M, GEN-2, traits Brick Wall/Aerial Duel/Composed Under Pressure, origin Cape Town FC Youth, father Ibrahim D.

Prototype card/detail UI:
- Card shows generation chip, nationality, name, position/origin, POT badge, 10-segment DNA integrity bar, first three traits with overflow count, discovery value, and `+ Basket`.
- Selecting a card toggles a three-column detail panel.
- Detail panel includes DNA Breakdown, all traits, inherited-from note, Lineage Tree, and Action Panel.
- Action panel actions: Add to Basket, Watch Regen, Place Bid.

Production Flutter checklist:
- [x] `RegensScreen` already hydrates a backend-backed hub via `regenUniverseHubProvider`.
- [x] Hub already combines rising stars, awards, national regens, scouting feed, tracking, and authenticated request-son orders.
- [x] API client already targets `rising-stars`, `scouting-feed`, `national-regens`, `awards`, and `tracking` with fixtures as fallback.
- [ ] Add prototype-style discovery metrics: total discovered, elite POT 80+, and GEN-3 rare. Current hero metrics are awards/national pool/rising stars/requested sons.
- [ ] Add generation filter pills and empty-state clear action for all/GEN-1/GEN-2/GEN-3.
- [ ] Add search, position, value, and sort controls if Regen World is intended to match the prototype discovery pool.
- [ ] Add card-level DNA integrity, discovery value, generation, origin, and visible trait chips.
- [ ] Add selected regen detail panel with DNA bars, all traits, inherited-from text, lineage tree, and action panel.
- [ ] Wire Add to Basket, Watch Regen, and Place Bid to production marketplace/watchlist/bid flows, or mark unavailable with deliberate disabled states.
- [ ] Treat prototype `REGEN_DATA` as visual fixture seed only; production must use Regen Universe APIs and lineage endpoints when available.

## Cross-Flow Production Notes

- Wallet balance and reserved funds affect Build-a-Son affordability in the prototype; production should keep this backend-authoritative through preview and wallet availability payloads.
- Build-a-Son completion should refresh both wallet state and regen/requested-son state after payment/generation.
- Regen World and Build-a-Son should share generation, DNA stat, trait, lineage, and academy terminology so a created son appears consistent with discovery cards.
- Prototype local state (`walletGTC`, `walletReserved`, `ACADEMY_PLAYERS`, `REGEN_DATA`) is useful for fixture parity, not source of truth.

## Phase 6 Consumer Economy Closure Checklist

Verification date: 2026-05-29.

This section is a docs/verification closure snapshot only. Production code was scanned and tested read-only; remaining items are handoff gaps for implementation owners.

### Wallet

- [x] Wallet screens read backend overview, summaries, transactions, KYC, rails, deposit history, withdrawal eligibility, quotes, requests, receipts, and user bank accounts.
- [x] KoraPay, manual transfer, and withdrawal remain backend lifecycle actions; scoped scan found no retired provider wording in the consumer economy production paths inspected.
- [x] Targeted frontend tests passed for canonical wallet balance authority and KYC truth.
- [x] Targeted backend wallet service tests passed.
- [ ] Staging evidence is still needed for real KoraPay top-up initialization/verification, manual proof review, withdrawal settlement, receipt retrieval, and operations reconciliation.

### Regen World

- [x] `RegensScreen` hydrates from backend Regen Universe feeds and authenticated request-son orders instead of prototype `REGEN_DATA`.
- [x] Search/filter/card/detail surfaces are built around backend-provided generation, lineage, DNA, trait, value, and eligibility fields.
- [x] Fixture data remains available for explicit fixture mode; standard live clients do not silently fall back to fixtures.
- [x] Targeted frontend Regen Universe API tests passed.
- [ ] Marketplace action wiring for Add to Basket, Watch Regen, and Place Bid was not proven in this pass; keep disabled/unavailable states explicit until live endpoints are verified.
- [ ] Staging evidence is still needed for live lineage/tracking completeness, national-pool-only eligibility, and tradable regen card behavior.

### Build-a-Son

- [x] Build-a-Son blocks confirmation until backend preview confirms selected parent, exactly three selected traits, OVR, POT, generation, DNA, currency, pricing, and wallet availability.
- [x] Flutter does not calculate random projection truth or locally mutate an academy list as authority.
- [x] Targeted frontend Build-a-Son wizard tests passed.
- [x] Targeted backend request-son order, wallet payment, KoraPay callback, and generation tests passed.
- [ ] Backend regen creation still uses seeded `Random(...)` for preview/generation. This is deterministic backend authority, not a frontend random projection, but product/ops should explicitly accept it as the production generation algorithm.
- [ ] Backend KoraPay checkout still has a non-production `https://mock.korapay.local/...` fallback when secrets are absent; production raises instead, but staging should prove real provider initialization and callback.

### Capital / Trader

- [x] Standard Trader API construction normalizes non-fixture modes to live mode.
- [x] `GteAuthedApi.withFallback` returns fixture data only when the client is explicitly in fixture mode.
- [x] Targeted frontend Trader API tests passed, including the parser case that does not invent missing market truth.
- [x] Targeted backend Trader service and router contract tests passed.
- [ ] Seeded Trader fixtures remain for test/dev fixture mode; deployment config should verify Capital never boots with fixture mode in production.
- [ ] Trader request/response schemas should receive the same strictness audit as wallet schemas before final production sign-off.

### API / Model Strictness

- [x] Wallet schemas include explicit `extra="forbid"` on key request models.
- [x] Build-a-Son frontend contract-blocks incomplete backend preview payloads instead of filling missing player, projection, or wallet fields.
- [x] Standard Regen Universe, Regen Creation, and Trader client factories normalize non-fixture modes to live mode.
- [ ] Extend strict request/response model review across regen creation and trader schemas; do not rely on parser defaults for production money, player, order, bid, or regen truth.
- [ ] Keep fixture factories and seeded data named as fixture-only test/dev support in deployment documentation.

### Verification Scans

- [x] Scoped forbidden-text scan covered wallet, Regen World, Build-a-Son, Trader/Capital, API/client, model, and related test paths.
- [x] No scoped production-path hits were found for retired payment rails, promoted legacy runtime wording, fixture leakage, or hardcoded product truth.
- [x] Follow-up findings were limited to `backend/app/regen_creation/service.py`: deterministic seeded `Random(...)` and the non-production `mock.korapay.local` KoraPay fallback.
- [x] Broad truth scan found fixture/fallback wording in explicit fixture clients/parsers; the inspected standard live clients do not silently use those fixtures.

### Remaining Backend Gaps

- [ ] Full staging e2e was not run here: live KoraPay top-up, manual deposit approval/rejection, withdrawal settlement, request-son KoraPay callback, generated academy visibility, and Regen World action wiring remain to be proven.
- [ ] Migration and generated API-contract drift were not validated beyond the targeted tests above.
- [ ] Production code was intentionally left untouched during this verification/docs pass.
